from __future__ import annotations

from contextlib import suppress
from typing import ClassVar
from django.db.models import QuerySet
from django_ltree_field.fields import IntegerLTreeField

from django.db import models
from django.contrib.postgres.indexes import GistIndex

import enum


type Path = tuple[int, ...]


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

    def get_insertion_range(cls, **kwargs) -> tuple[Path | None, Path | None]:
        """Get a valid insertion range for a new node."""
        positions: dict[RelativePosition, tuple[int]] = {}

        for position in RelativePosition:
            with suppress(KeyError):
                positions[position] = kwargs.pop(position.value)

        if len(positions) != 1:
            msg = f"Could not resolve position: {positions!r}"
            raise TypeError(msg)

        if kwargs:
            msg = f"Unexpected kwargs: {kwargs!r}"
            raise TypeError(msg)

        position, relative_to = positions.popitem()

        match position:
            case RelativePosition.ROOT:
                left = (
                    cls.objects.filter(path__depth=1)
                    .order_by("-path")
                    .values_list("path", flat=True)
                    .first()
                )
                right = None
                return left, right
            case RelativePosition.FIRST_CHILD:
                right = (
                    cls.objects.filter(path__child_of=relative_to)
                    .order_by("path")
                    .first()
                )
                left = None
                return left, right
            case RelativePosition.LAST_CHILD:
                left = (
                    cls.objects.filter(path__child_of=relative_to)
                    .order_by("-path")
                    .first()
                )
                right = None
                return left, right
            case RelativePosition.BEFORE:
                left = (
                    cls.objects.filter(
                        path__sibling_of=relative_to, path__lt=relative_to
                    )
                    .order_by("-path")
                    .first()
                )
                right = (
                    cls.objects.filter(
                        path__sibling_of=relative_to, path__gt=relative_to
                    )
                    .order_by("path")
                    .first()
                )
                return (
                    cls.objects.filter(path__lt=relative_to).order_by("-path").first()
                )
            case RelativePosition.AFTER:
                return cls.objects.filter(path__gt=relative_to).order_by("path").first()

        return cls.objects.filter(path__contains=path).order_by("-path").first()
