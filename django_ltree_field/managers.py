from __future__ import annotations

import itertools as it
import string
from typing import (
    TYPE_CHECKING,
    Callable,
    Literal,
    NotRequired,
    Self,
    TypedDict,
    assert_never,
    overload,
)

from django.db import models
from django.db.models import Case, F, Q, Value, When
from django.db.models.lookups import GreaterThan, GreaterThanOrEqual

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

if TYPE_CHECKING:
    from collections.abc import Awaitable


class _MoveData(TypedDict):
    path: str
    do_move: bool


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

    def _flatten_tree_step(self, tree: _TreeNode, path: str):
        children = tree.pop("children", [])

        yield self.model(
            **tree,
            path=path,
        )

        for suffix, child in self._labeler.label(children):
            yield from self._flatten_tree_step(child, f"{path}.{suffix}")

    def _flatten_trees(self, trees: _TreeNode, paths: list[str]):
        return it.chain.from_iterable(
            map(
                self._flatten_tree_step,
                trees,
                paths,
            )
        )

    # Should this be "create_trees" (plural?)
    def create_tree(
        self, *trees: _TreeNode, position: RelativePositionType | None = None
    ):
        """Initialize multiple trees at position."""
        if position is None:
            position = Root()

        # Tree is a dictionary with a key "children" which is recursive
        # other keys are attributes to be passed to initializer
        paths = self.move_nodes(position)

        return self.bulk_create(self._flatten_trees(trees, paths))

    async def acreate_tree(
        self, *trees: _TreeNode, position: RelativePositionType | None = None
    ):
        """Initialize multiple trees at position."""
        if position is None:
            position = Root()

        # Tree is a dictionary with a key "children" which is recursive
        # other keys are attributes to be passed to initializer
        paths = await self.amove_nodes(position)

        return await self.abulk_create(
            self._flatten_trees(trees, paths),
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
            case After(rel_obj):
                queryset = self.filter(path__sibling_of=rel_obj.path).annotate(
                    do_move=GreaterThan(
                        F("path"),
                        Value(rel_obj.path),
                    )
                )
            case Before(rel_obj):
                queryset = self.filter(path__sibling_of=rel_obj.path).annotate(
                    do_move=GreaterThanOrEqual(
                        F("path"),
                        Value(rel_obj.path),
                    )
                )
            case LastChildOf(rel_obj):
                queryset = self.filter(path__child_of=rel_obj.path).annotate(
                    do_move=Value(False),
                )
            case FirstChildOf(rel_obj):
                queryset = self.filter(path__child_of=rel_obj.path).annotate(
                    do_move=Value(True),
                )
            case Root():
                queryset = self.filter(path__depth=1).annotate(do_move=Value(False))
            case _:
                assert_never(position)

        return queryset.values(
            "path",
            "do_move",
        )

    @overload
    def _update_impl(
        self,
        *,
        position: RelativePositionType,
        move_data: list[_MoveData],
        count: int = 1,
        sync: Literal[True],
    ) -> list[str] | Callable[[], list[str]]: ...

    @overload
    def _update_impl(
        self,
        *,
        position: RelativePositionType,
        move_data: list[_MoveData],
        count: int = 1,
        sync: Literal[False],
    ) -> list[str] | Callable[[], Awaitable[list[str]]]: ...

    def _update_impl(
        self,
        *,
        position: RelativePositionType,
        move_data: list[_MoveData],
        count: int = 1,
        sync: bool = True,
    ) -> list[str] | Callable[[], list[str]] | Callable[[], Awaitable[list[str]]]:
        # Sentinels go at the first True move data, or end of list if there isn't one
        placeholder_index = next(
            (i for i, row in enumerate(move_data) if row["do_move"]),
            len(move_data),
        )

        # Copy version of
        # move_data[placeholder_index:placeholder_index] = [None] * count
        with_placeholders = (
            move_data[:placeholder_index]
            + ([None] * count)
            + move_data[placeholder_index:]
        )

        _updates: list[tuple[str, str]] = []

        insertion_points: list[str] = []

        prefix = self._get_prefix(position)

        for suffix, row in self._labeler.label(with_placeholders):
            new_path = f"{prefix}{suffix}"

            if row is None:
                # Whenever we find a None sentinel, we need to insert a new path
                insertion_points.append(new_path)
                continue

            if row["path"] != new_path:
                _updates.append((row["path"], new_path))

        if not insertion_points:
            raise AssertionError

        # Eager return
        if not _updates:
            return insertion_points

        to_update = self.filter(path__in=[row[0] for row in _updates])
        update_kwargs = {
            "path": Case(
                *(
                    When(
                        path=row[0],
                        then=Value(row[1]),
                    )
                    for row in _updates
                ),
                default=F("path"),
                output_field=LTreeField(),
            )
        }

        if sync:

            def inner() -> list[str]:
                to_update.update(**update_kwargs)
                return insertion_points

            return inner

        async def inner() -> list[str]:
            await to_update.aupdate(**update_kwargs)
            return insertion_points

        return inner

    def move_nodes(
        self,
        position: RelativePositionType,
        *,
        count: int = 1,
    ) -> list[str]:
        insertion_points = self._update_impl(
            position=position,
            move_data=list(self._get_siblings(position)),
            count=count,
            sync=True,
        )

        if callable(insertion_points):
            # If the update is a callable, we need to call it to get the result
            return insertion_points()

        return insertion_points

    async def amove_nodes(
        self,
        position: RelativePositionType,
        *,
        count: int = 1,
    ) -> list[str]:
        insertion_points = self._update_impl(
            position=position,
            move_data=[row async for row in self._get_siblings(position)],
            count=count,
            sync=False,
        )

        if callable(insertion_points):
            return await insertion_points()

        return insertion_points
