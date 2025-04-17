from __future__ import annotations

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
                output_field=LTreeField(),
            ),
        )


class _InsertStrategy(TypedDict):
    update: _Update | None
    insertion_points: list[str]


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
        yield self.model(
            **tree,
            path=path,
        )

        children = tree.get("children", [])

        for suffix, child in self._labeler.label(children):
            yield from self._flatten_tree(child, f"{path}.{suffix}")

    def init_tree(
        self, tree: _TreeNode, *, position: RelativePositionType | None = None
    ):
        if position is None:
            position = Root()

        # Tree is a dictionary with a key "children" which is recursive
        # other keys are attributes to be passed to initializer
        path = self.move_nodes(position)

        return list(self._flatten_tree(tree, path))

    def create(self, *args, **kwargs):
        position = kwargs.pop("position", Root())

        path = self.move_nodes(position)

        return super().create(
            *args,
            **kwargs,
            path=path,
        )

    async def acreate(self, *args, **kwargs):
        position = kwargs.pop("position", Root())

        path = await self.amove_nodes(position)

        return await super().acreate(
            *args,
            **kwargs,
            path=path,
        )

    def _get_prefix(self, position: RelativePositionType) -> str:
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

    def _get_siblings(self, position: RelativePositionType) -> Self:
        match position:
            case After(rel_obj) | Before(rel_obj):
                return self.filter(path__sibling_of=rel_obj.path)
            case LastChildOf(rel_obj) | FirstChildOf(rel_obj):
                return self.filter(path__child_of=rel_obj.path)
            case Root():
                return self.filter(path__depth=1)
            case _:
                assert_never(position)

    def _insert_placeholder(
        self,
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

    def _get_insert_strategy(
        self,
        *,
        position: RelativePositionType,
        paths: list[str],
        count: int = 1,
    ) -> _InsertStrategy:
        paths_to_update = self._insert_placeholder(
            position=position,
            paths=paths,
            count=count,
        )

        _updates: list[tuple[str, str]] = []

        insertion_points: list[str] = []

        prefix = self._get_prefix(position)

        for suffix, path in self._labeler.label(paths_to_update):
            new_path = f"{prefix}{suffix}"

            if path is None:
                # There should only be one insertion point
                insertion_points.append(new_path)
                continue

            if new_path != path:
                _updates.append((path, new_path))

        if not insertion_points:
            raise AssertionError

        return {
            "update": _Update.from_data(
                _updates,
            ),
            "insertion_points": insertion_points,
        }

    def move_nodes(
        self,
        position: RelativePositionType,
        *,
        count: int = 1,
    ) -> list[str]:
        siblings = self._get_siblings(position)
        paths = list(siblings.values_list("path", flat=True))
        strategy = self._get_insert_strategy(
            position=position,
            paths=paths,
            count=count,
        )

        if strategy["update"] is not None:
            strategy["update"].update(self)

        return strategy["insertion_points"]

    async def amove_nodes(
        self, position: RelativePositionType, *, count: int = 1
    ) -> list[str]:
        siblings = self._get_siblings(position)
        paths = [path async for path in siblings.values_list("path", flat=True)]
        strategy = self._get_insert_strategy(
            position=position,
            paths=paths,
            count=count,
        )

        if strategy["update"] is not None:
            await strategy["update"].aupdate(self)

        return strategy["insertion_points"]
