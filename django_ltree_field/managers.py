from __future__ import annotations

import itertools as it
import string
from dataclasses import dataclass
from typing import (
    NotRequired,
    Self,
    TypedDict,
    assert_never,
)

from django.db import models
from django.db.models import Case, Expression, F, Q, Value, When

from django_ltree_field.fields import LTreeField

from .labeler import Labeler
from .position import (
    After,
    Before,
    FirstChildOf,
    LastChildOf,
    RelativePositionType,
    Root,
)


@dataclass
class _Update:
    updates: list[tuple[str, str]]
    insertion_points: list[str]

    @property
    def condition(self) -> Q:
        return Q(path__in=[row[0] for row in self.updates])

    @property
    def expression(self) -> Expression:
        return Case(
            *(
                When(
                    path=row[0],
                    then=Value(row[1]),
                )
                for row in self.updates
            ),
            default=F("path"),
            output_field=LTreeField(),
        )

    def update(self, manager: models.Manager):
        if not self.updates:
            return 0

        return manager.filter(self.condition).update(path=self.expression)

    async def aupdate(self, manager: models.Manager):
        if not self.updates:
            return 0

        return await manager.filter(self.condition).aupdate(path=self.expression)

    @classmethod
    def _get_prefix(cls, position: RelativePositionType) -> str:
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

    @classmethod
    def _insert_placeholder(
        cls,
        *,
        paths: list[str],
        position: RelativePositionType,
        count: int = 1,
    ) -> list[str | None]:
        # Insert {count} None sentinels at the appropriate position
        sentinels = [None] * count

        match position:
            case After(rel_obj):
                # Insert sentinels after rel_obj.path
                i = paths.index(rel_obj.path) + 1
                return paths[:i] + sentinels + paths[i:]
            case Before(rel_obj):
                # Insert sentinels before rel_obj.path
                i = paths.index(rel_obj.path)
                return paths[:i] + sentinels + paths[i:]
            case LastChildOf(rel_obj):
                # Insert sentinels at the end
                return paths + sentinels
            case FirstChildOf(rel_obj):
                # Insert sentinels at the beginning
                return sentinels + paths
            case Root():
                # Insert sentinels at the end
                return paths + sentinels
            case _:
                assert_never(position)

    @classmethod
    def calculate(
        cls,
        position: RelativePositionType,
        *,
        paths: list[str],
        count: int = 1,
        labeler: Labeler,
    ) -> Self:
        """Implementation of move_nodes logic shared between sync and async versions."""

        paths_to_update = cls._insert_placeholder(
            position=position,
            paths=paths,
            count=count,
        )

        _updates: list[tuple[str, str]] = []

        insertion_points: list[str] = []

        prefix = cls._get_prefix(position)

        for suffix, path in labeler.label(paths_to_update):
            new_path = f"{prefix}{suffix}"

            if path is None:
                # Whenever we find a None sentinel, we need to insert a new path
                insertion_points.append(new_path)
                continue

            if new_path != path:
                _updates.append((path, new_path))

        if not insertion_points:
            raise AssertionError

        return cls(
            updates=_updates,
            insertion_points=insertion_points,
        )


class _TreeNode(TypedDict):
    children: NotRequired[list[_TreeNode]]


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

    def _flatten_tree(self, tree: _TreeNode, path: str):
        children = tree.pop("children", [])

        yield self.model(
            **tree,
            path=path,
        )

        for suffix, child in self._labeler.label(children):
            yield from self._flatten_tree(child, f"{path}.{suffix}")

    def init_tree(
        self, *trees: _TreeNode, position: RelativePositionType | None = None
    ):
        if position is None:
            position = Root()

        # Tree is a dictionary with a key "children" which is recursive
        # other keys are attributes to be passed to initializer
        paths = self.move_nodes(position)

        return list(
            it.chain.from_iterable(
                map(
                    self._flatten_tree,
                    trees,
                    paths,
                )
            )
        )

    def create(self, *args, **kwargs):
        position = kwargs.pop("position", Root())

        path = self.move_nodes(position)[0]

        return super().create(
            *args,
            **kwargs,
            path=path,
        )

    async def acreate(self, *args, **kwargs):
        position = kwargs.pop("position", Root())

        path = (await self.amove_nodes(position))[0]

        return await super().acreate(
            *args,
            **kwargs,
            path=path,
        )

    def _get_siblings(self, position: RelativePositionType) -> Self:
        match position:
            case After(rel_obj) | Before(rel_obj):
                queryset = self.filter(path__sibling_of=rel_obj.path)
            case LastChildOf(rel_obj) | FirstChildOf(rel_obj):
                queryset = self.filter(path__child_of=rel_obj.path)
            case Root():
                queryset = self.filter(path__depth=1)
            case _:
                assert_never(position)

        return queryset.values_list("path", flat=True)

    def move_nodes(
        self,
        position: RelativePositionType,
        *,
        count: int = 1,
    ) -> list[str]:
        updater = _Update.calculate(
            position=position,
            paths=list(self._get_siblings(position)),
            count=count,
            labeler=self._labeler,
        )

        updater.update(self)

        return updater.insertion_points

    async def amove_nodes(
        self, position: RelativePositionType, *, count: int = 1
    ) -> list[str]:
        updater = _Update.calculate(
            position=position,
            paths=[path async for path in self._get_siblings(position)],
            count=count,
            labeler=self._labeler,
        )

        await updater.aupdate(self)

        return updater.insertion_points
