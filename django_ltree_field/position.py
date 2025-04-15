from __future__ import annotations
from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _

from .paths import Path, PathFactory


class RelativePosition(models.TextChoices):
    CHILD = "child_of", _("Child of")
    FIRST_CHILD = "first_child_of", ("First child of")
    # Same functionality as child_of
    LAST_CHILD = "last_child_of", _("Last child of")
    # These could be "before" and "after"
    BEFORE = "before", _("Before")
    AFTER = "after", _("After")

    # Right-most root element
    ROOT = "root", _("Last root")

    # Consider just making its own functions
    # Or put back on manager or something

    @classmethod
    def resolve(
        cls, kwargs, path_field: str, path_factory: PathFactory
    ) -> tuple[Path, int | None]:
        """Parse kwargs and normalize relative position to always be
        tuple = (parent_path, nth-child)
        """
        # Path field is used to unwrap/duck-type models that have a path attribute
        positions: dict[RelativePosition, Any] = {}

        for position in cls:
            try:
                positions[position] = kwargs.pop(position.value)
            except KeyError:
                continue

        if len(positions) != 1:
            msg = f"Could not resolve position: {positions!r}"
            raise TypeError(msg)

        position, relative_to = positions.popitem()

        if position == cls.ROOT:
            if relative_to is not True:
                msg = f"Expected kwarg root=True, got root={relative_to!r}"
                raise ValueError(msg)
            return (), None

        # Duck-type model instances
        # Might want to use isinstance instead?
        if hasattr(relative_to, path_field):
            relative_to = getattr(relative_to, path_field)

        if not isinstance(relative_to, tuple):
            msg = f"Expected tuple, got {type(relative_to)}"
            raise TypeError(msg)

        # TODO Better error handling here?
        # Convert strings to lists?
        if not isinstance(relative_to, list):
            relative_to = relative_to.split(".")

        # last_child_of is a more verbose alias for child_of
        if position in {cls.CHILD, cls.LAST_CHILD}:
            return relative_to, None
        if position == cls.FIRST_CHILD:
            return relative_to, 0
        if position in {cls.BEFORE, cls.AFTER}:
            parent, child_index = path_factory.split(relative_to)

            if position == cls.AFTER:
                child_index += 1

            return parent, child_index
        # Should never get here
        raise Exception


class SortedPosition(models.TextChoices):
    CHILD = "child_of", _("Child of")
    SIBLING = "sibling", _("Sibling of")
    ROOT = "root", _("Root")

    @classmethod
    def resolve(
        cls, kwargs, path_field: str, path_factory: PathFactory
    ) -> tuple[Path, int | None]:
        """Parse kwargs and normalize relative position to always be
        tuple = (parent_path, nth-child)
        """
        # Path field is used to unwrap/duck-type models that have a path attribute
        positions: dict[SortedPosition, any] = {}

        for position in cls:
            try:
                positions[position] = kwargs.pop(position.value)
            except KeyError:
                continue

        if len(positions) != 1:
            raise TypeError(f"Could not resolve position: {positions!r}")

        position, relative_to = positions.popitem()

        if position == cls.ROOT:
            if relative_to is not True:
                raise ValueError(f"Expected kwarg root=True, got root={relative_to!r}")
            return [], None

        # Duck-type model instances
        # Might want to use isinstance instead?
        if hasattr(relative_to, path_field):
            relative_to = getattr(relative_to, path_field)

        # TODO Better error handling here?
        # Convert strings to lists?
        if not isinstance(relative_to, list):
            relative_to = relative_to.split(".")

        # last_child_of is a more verbose alias for child_of
        if position == cls.CHILD:
            return relative_to, None
        if position == cls.SIBLING:
            parent, child_index = path_factory.split(relative_to)
            return parent, None
        # Should never get here
        raise Exception
