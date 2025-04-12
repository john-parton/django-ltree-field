from __future__ import annotations

import itertools as it
from dataclasses import dataclass
from typing import Iterator


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


@dataclass
class MoveOp:
    new_child_index: int
    moves: list[tuple[int, int]]


def rewrite_children_dense(children: list[int], nth_child: int) -> MoveOp:
    """Rewrite the children to make room for a new child.

    Parameters
    ----------
    children : list[int]
        The children to rewrite. The list should contain only non-negative
        integers in ascending order with no duplicates.
    nth_child : int
        An index to leave vacant. This index should be non-negative.
    """
    if nth_child < 0:
        raise AssertionError("nth_child must be greater than or equal to 0")

    return MoveOp(
        new_child_index=nth_child,
        moves=[
            (child, index)
            for index, child in zip(
                range_excluding(len(children), excluding=nth_child),
                children,
                strict=True,
            )
            if index != child
        ],
    )


def rewrite_children_sparse(
    children: list[int], nth_child: int, max_value: int
) -> MoveOp:
    """Rewrite the children to make room for a new child.

    Parameters
    ----------
    children : list[int]
        The children to rewrite. The list should contain only non-negative
        integers in a ascending order with no duplicates.
    nth_child : int
        An index to leave vacant. This index should be non-negative.
    max_value : int
        The maximum value of the children.
    """

    if nth_child < 0:
        raise AssertionError("nth_child must be greater than or equal to 0")

    if nth_child > max_value:
        raise AssertionError("nth_child must be less than or equal to max_value")

    step = int(round(max_value / (len(children) + 1)))

    if step == 0:
        raise AssertionError("Too many children to fit in the available space")

    left_gap = (step * (len(children) + 1) - max_value) // 2

    indexes = (
        i * step + left_gap
        for i in range_excluding(
            len(children),
            excluding=nth_child,
        )
    )

    return MoveOp(
        new_child_index=nth_child * step + left_gap,
        moves=[
            (child, index)
            for index, child in zip(
                indexes,
                children,
                strict=True,
            )
            if index != child
        ],
    )
