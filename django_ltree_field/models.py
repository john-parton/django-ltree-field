from __future__ import annotations

import abc
import enum
import itertools as it
from collections.abc import Iterator
from typing import ClassVar, Literal, Self

from django.contrib.postgres.indexes import GistIndex
from django.db import models
from django.db.models import When

from django_ltree_field.fields import IntegerLTreeField

type Path = tuple[int, ...]


class NotProvided(enum.Enum):
    NOT_PROVIDED = enum.auto()


NOT_PROVIDED = NotProvided.NOT_PROVIDED


class RelativePosition(enum.Enum):
    # CHILD = "child_of", _("Child of")
    FIRST_CHILD = "first_child_of"
    # Same functionality as child_of
    LAST_CHILD = "last_child_of"
    # These could be "before" and "after"
    BEFORE = "before"
    AFTER = "after"

    # Right-most root element
    ROOT = "root"


class RelativePosition(abc.ABC):
    pass


class After(RelativePosition):
    def __init__(self, rel_obj):
        self.rel_obj = rel_obj


class Root(RelativePosition):
    def __init__(self):
        pass


class Before[T: models.Model](RelativePosition):
    def __init__(self, rel_obj: T | tuple[int, ...]):
        self.rel_obj = rel_obj


class LastChildOf(RelativePosition):
    def __init__(self, rel_obj):
        self.rel_obj = rel_obj


class FirstChildOf(RelativePosition):
    def __init__(self, rel_obj):
        self.rel_obj = rel_obj


def range_excluding(stop: int, *, excluding: int) -> Iterator[int]:
    """Generate a range of integers excluding a specific value.

    Parameters
    ----------
    stop : int
        The end of the range.
    excluding : int
        The value to exclude.

    Returns
    -------
    Iterator[int]
        An iterator over the range of integers.
    """
    if excluding >= stop:
        return iter(range(stop))

    if excluding == 0:
        return iter(range(1, stop))

    return it.chain(
        range(excluding),
        range(excluding + 1, stop),
    )


class SparseStrategy:
    max_value: int

    def __init__(self, max_value: int):
        self.max_value = max_value

    def choose_path(
        self,
        left_child: int | None,
        right_child: int | None,
    ) -> int:
        """Given a left index and right index, choose an index in between."""
        if left_child is None and right_child is None:
            msg = "Expected left_child and/or right_child to be provided"
            raise TypeError(msg)

        if left_child is None:
            left_child = 0

        if right_child is None:
            right_child = self.max_value

        if right_child < left_child or (right_child - left_child) <= 1:
            raise AssertionError

        return (left_child + right_child) // 2

    def rewrite_tree(self, manager, parent: Path, path_field: str, nth_child: int):
        """Rewrite the tree to make room for a new node.

        Parameters
        ----------
        manager
            The manager to use for updating the tree.
        parent : Path
            The path of the parent node.
        path_field : str
            The name of the path field.
        nth_child : int
            The index of the new child.
        """
        object_ids: list[int] = list(
            manager.filter(
                **{
                    f"{path_field}__child_of": parent,
                }
            )
            .order_by(path_field)
            .values_list(
                "id",
                flat=True,
            )
        )

        whens: list[When] = []

        def child_to_index(
            child: int, *, _slot_width=self.max_value / (len(object_ids) + 1)
        ) -> int:
            return int(manager.get(id=child).path[-1])

        slots = self.max_value / (len(object_ids) + 1)

        for i, object_id in zip(
            range_excluding(len(object_ids), excluding=nth_child),
            object_ids,
            strict=True,
        ):
            whens.append(When(id=object_id, then=Value(round(slots * i))))


class DenseStrategy:
    def choose_path(
        self,
        path_lower: tuple[int, ...],
        path_upper: tuple[int, ...] | None,
    ) -> tuple[int, ...]:
        # Pick a spot right in the middle as a heuristic
        raise AssertionError


class AutoNodeManager(models.Manager):
    path_field: str
    sparse: bool

    def __init__(self, *args, **kwargs):
        self.path_field = kwargs.pop("path_field", "path")
        self.sparse = kwargs.pop("sparse", True)
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)

        if self.sparse:
            field = cls._meta.get_field(self.path_field)

            if not isinstance(field, IntegerLTreeField):
                raise ValueError(f"Expected IntegerLTreeField, got {field!r}")
            self.insertion_strategy = SparseStrategy(field.codec.max_value)
        else:
            self.insertion_strategy = DenseStrategy()

    def claim_root(self):
        self.filter(
            **{
                f"{self.path_field}__depth": 1,
            }
        )

        return self.create(path=(0,))


class AbstractAutoNode(models.Model):
    path = IntegerLTreeField(triggers=IntegerLTreeField.CASCADE, null=False)

    class Meta:
        abstract = True
        indexes: ClassVar = [
            GistIndex(
                fields=("path",),
                name="%(app_label)s_%(class)s__path_idx",
            ),
        ]
        ordering: ClassVar = ["path"]

    type MoveTarget = Literal[NotProvided.NOT_PROVIDED] | Self | tuple[int, ...]

    @classmethod
    def claim_position(
        cls, position: After | Before | LastChildOf | FirstChildOf | Root
    ) -> None:
        """Claim a path for a new node or move an existing node."""
        match position:
            case After(rel_obj):
                path_clone = tuple(*rel_obj.path[:-1], rel_obj.path[-1] + 1)
                left = cls.objects.filter(
                    path__sibling_of=rel_obj.path,
                    path__gt=rel_obj.path,
                ).first()
                right = None
            case Before(rel_obj):
                self.path = rel_obj.path
                self.save()
            case LastChildOf(rel_obj):
                self.path = rel_obj.path
                self.save()
            case FirstChildOf(rel_obj):
                self.path = rel_obj.path
            case Root():
                left = cls.objects.filter(path__depth=1).last()
                right = None

    def find_path(self, **kwargs):
        """Find a range of absolute paths based on relative position."""

    def open_path(self, **kwargs):
        """Open a path to a target node."""

    def move(self, **kwargs):
        """Move a node to a new location."""

    def move(
        self,
        **kwargs: MoveTarget,
    ) -> None:
        path, nth_child = RelativePosition.resolve(
            kwargs,
            path_field="path",
            path_factory=self.__class__.path,
        )

        if nth_child is not None:
            raise ValueError(f"Expected nth_child=None, got nth_child={nth_child!r}")

        self.path = path

        self.save()
