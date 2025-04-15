from __future__ import annotations

from collections.abc import Iterable
import itertools as it
from dataclasses import dataclass
from django.db.models import Expression
import math
import string
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Collection,
    Protocol,
    Self,
    TypedDict,
    assert_never,
    cast,
)

from django.contrib.postgres.indexes import GistIndex
from django.db import models
from django.db.models import When, Case, F, Value, Q
from numpy import insert

from django_ltree_field.fields import IntegerLTreeField, LTreeField

if TYPE_CHECKING:
    from collections.abc import Iterator


class _NodeProtocol(Protocol):
    path: str


class _BaseRelativePosition: ...


class Root(_BaseRelativePosition):
    pass


@dataclass
class FirstChildOf(_BaseRelativePosition):
    rel_obj: _NodeProtocol


@dataclass
class LastChildOf(_BaseRelativePosition):
    rel_obj: _NodeProtocol


@dataclass
class Before(_BaseRelativePosition):
    rel_obj: _NodeProtocol


@dataclass
class After(_BaseRelativePosition):
    rel_obj: _NodeProtocol


type RelativePosition = Root | FirstChildOf | LastChildOf | Before | After


class Labeler:
    """Fixed width lexicographical string generator."""

    alphabet: str
    alphabet_reverse: dict[str, int]

    def __init__(self, alphabet: str):
        self.alphabet = alphabet

    def label[T](self, items: Collection[T]) -> zip[tuple[str, T]]:
        """Generates fixed width labels for items such that sorting the labels
        is equivalent to the given order.

        Parameters
        ----------
        items : Iterable[T]

        Yields
        ------
        Iterator[tuple[T, str]]
            An iterator over tuples of items and their corresponding labels.
        """
        # Get required width
        width = math.ceil(math.log(len(items), len(self.alphabet)))

        return zip(
            self._iter(width=width),
            items,
            strict=False,
        )

    def _iter(self, *, width: int) -> Iterator[str]:
        """Generate lexicographical combinations of the given width.

        Parameters
        ----------
        width : int
            The width of the combinations to generate.

        Yields
        ------
        Iterator[str]
            An iterator over the lexicographical combinations of the given width.
        """
        for chars in it.product(self.alphabet, repeat=width):
            yield "".join(chars)


@dataclass
class _Update:
    condition: Q
    expression: Expression

    def update(self, manager: models.Manager):
        return manager.filter(self.condition).update(path=self.expression)

    async def aupdate(self, manager: models.Manager):
        return await manager.filter(self.condition).aupdate(path=self.expression)

    @classmethod
    def from_data(cls, data: list[tuple[str, str]]) -> Self | None:
        if not data:
            return None

        return cls(
            condition=Q(path__in=[row[0] for row in data]),
            expression=Case(
                *(
                    When(
                        path=row[0],
                        then=Value(row[1]),
                    )
                    for row in data
                ),
                default=F("path"),
            ),
        )


class _InsertStrategy(TypedDict):
    update: _Update | None
    insertion_point: str


class AutoNodeManager(models.Manager):
    _labeler: Labeler

    def __init__(self, *args, **kwargs):
        self._labeler = Labeler(
            # Postgres 16+
            "-" + string.digits + string.ascii_uppercase + "_" + string.ascii_lowercase
            # Postgres 15 and earlier
            # string.digits + string.ascii_uppercase + "_" + string.ascii_lowercase
        )
        super().__init__(*args, **kwargs)

    def _get_prefix(self, position: RelativePosition) -> str:
        match position:
            case After(rel_obj) | Before(rel_obj):
                stem, __, __ = rel_obj.path.rpartition(".")
                return f"{stem}."
            case LastChildOf(rel_obj) | FirstChildOf(rel_obj):
                return f"{rel_obj.path}."
            case Root():
                return ""
            case _:
                assert_never(position)

    def _get_paths_to_update(self, position: RelativePosition) -> list[str | None]:
        match position:
            case After(rel_obj):
                paths = list(
                    self.filter(
                        path__sibling_of=rel_obj.path,
                    ).values_list("path", flat=True)
                )

                # Insert a None sentinel after rel_obj.path
                i = paths.index(rel_obj.path)
                paths.insert(i + 1, None)
                return rel_obj.path.rpartition(".")[0], paths
            case Before(rel_obj):
                paths = list(
                    self.filter(
                        path__sibling_of=rel_obj.path,
                    ).values_list("path", flat=True)
                )

                # Insert a None sentinel before rel_obj.path
                i = paths.index(rel_obj.path)
                paths.insert(i, None)
                return rel_obj.path.rpartition(".")[0], paths
            case LastChildOf(rel_obj):
                paths = list(
                    self.filter(
                        path__child_of=rel_obj.path,
                    ).values_list("path", flat=True)
                )

                # Insert a None sentinel at the end
                paths.append(None)
                return paths
            case FirstChildOf(rel_obj):
                paths = list(
                    self.filter(
                        path__child_of=rel_obj.path,
                    ).values_list("path", flat=True)
                )

                # Insert a None sentinel at the beginning
                paths.insert(0, None)
                return paths
            case Root():
                paths = list(self.filter(path__depth=1).values_list("path", flat=True))
                # Insert a None sentinel at the beginning
                paths.insert(0, None)
                return paths
            case _:
                assert_never(position)

    async def _aget_paths_to_update(
        self, position: RelativePosition
    ) -> list[str | None]:
        match position:
            case After(rel_obj):
                paths = [
                    path
                    async for path in self.filter(
                        path__sibling_of=rel_obj.path,
                    ).values_list("path", flat=True)
                ]

                # Insert a None sentinel after rel_obj.path
                i = paths.index(rel_obj.path)
                paths.insert(i + 1, None)
                return rel_obj.path.rpartition(".")[0], paths
            case Before(rel_obj):
                paths = [
                    path
                    async for path in self.filter(
                        path__sibling_of=rel_obj.path,
                    ).values_list("path", flat=True)
                ]

                # Insert a None sentinel before rel_obj.path
                i = paths.index(rel_obj.path)
                paths.insert(i, None)
                return rel_obj.path.rpartition(".")[0], paths
            case LastChildOf(rel_obj):
                paths = list(
                    self.filter(
                        path__child_of=rel_obj.path,
                    ).values_list("path", flat=True)
                )

                # Insert a None sentinel at the end
                paths.append(None)
                return paths
            case FirstChildOf(rel_obj):
                paths = list(
                    self.filter(
                        path__child_of=rel_obj.path,
                    ).values_list("path", flat=True)
                )

                # Insert a None sentinel at the beginning
                paths.insert(0, None)
                return paths
            case Root():
                paths = list(self.filter(path__depth=1).values_list("path", flat=True))
                # Insert a None sentinel at the beginning
                paths.insert(0, None)
                return paths
            case _:
                assert_never(position)

    def _get_insert_strategy(self, position: RelativePosition) -> _InsertStrategy:
        paths_to_update = self._get_paths_to_update(position)

        _updates: list[tuple[str, str]] = []

        insertion_point = None

        prefix = self._get_prefix(position)

        for suffix, path in self._labeler.label(paths_to_update):
            new_path = f"{prefix}{suffix}"

            if path is None:
                if insertion_point is not None:
                    raise AssertionError
                insertion_point = new_path
                continue

            if new_path != path:
                _updates.append((path, new_path))

        if insertion_point is None:
            raise AssertionError

        return {
            "update": _Update.from_data(
                _updates,
            ),
            "insertion_point": insertion_point,
        }

    def move_nodes(self, position: RelativePosition):
        strategy = self._get_insert_strategy(position)

        if strategy["update"] is not None:
            strategy["update"].update(self)

        return strategy["insertion_point"]


class AbstractAutoNode(models.Model):
    path = LTreeField(triggers=LTreeField.CASCADE, null=False)

    class Meta:
        abstract = True
        indexes: ClassVar = [
            GistIndex(
                fields=("path",),
                name="%(app_label)s_%(class)s__path_idx",
            ),
        ]
        ordering: ClassVar = ["path"]

    @classmethod
    def claim_position(
        cls,
        position: RelativePosition,
    ) -> None:
        """Claim a path for a new node or move an existing node."""
        match position:
            case After(rel_obj):
                parent, __, suffix = rel_obj.path.rpartition(".")
                insert_point = rel_obj.path[:-1] + (rel_obj.path[-1] + 1,)
                do_move = True
            case Before(rel_obj):
                insert_point = rel_obj.path
                do_move = True
            case LastChildOf(rel_obj):
                path = (
                    cls.objects.filter(
                        path__child_of=rel_obj.path,
                    )
                    .order_by("-path")
                    .values_list("path", flat=True)
                    .first()
                )

                if path is None:
                    insert_point = rel_obj.path + (0,)
                else:
                    insert_point = rel_obj.path + (path[-1] + 1,)
                do_move = False
            case FirstChildOf(rel_obj):
                insert_point = rel_obj.path + (0,)
                do_move = True
            case Root():
                insert_point = cls.objects.filter(path__depth=1).last()
                do_move = False

        if do_move:
            updates: list[Self] = []

            stem = insert_point[:-1]
            i = insert_point[-1]

            for obj in cls.objects.filter(
                path__sibling_of=insert_point, path__gt=insert_point
            ):
                i += 1
                new_path = stem + (i,)

                if obj.path != new_path:
                    obj.path = new_path
                    updates.append(obj)

            if updates:
                cls.objects.bulk_update(updates, ["path"])

        return insert_point

    def move(
        self,
        position: RelativePosition,
    ) -> None:
        self.path = self.claim_position(position)

        self.save()
