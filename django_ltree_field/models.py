from __future__ import annotations

from contextlib import suppress
from tkinter import NO
from typing import ClassVar, Literal, Self
from django.db.models import QuerySet
from django_ltree_field.fields import IntegerLTreeField

from django.db import models
from django.contrib.postgres.indexes import GistIndex

import enum


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
