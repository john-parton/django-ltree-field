"""
Labeling utility for PostgreSQL ltree path components.

This module provides functionality for generating fixed-width string labels
in lexicographical order. It's primarily used for creating consistent, sortable
labels for tree structures when working with PostgreSQL's ltree data type.

The Labeler class can convert arbitrary collections of items into labeled pairs
where each generated label maintains the original collection's sort order when
the labels are sorted lexicographically.

Example:
    ```python
    labeler = Labeler(alphabet="0123456789")
    items = ["apple", "banana", "cherry"]
    labels = list(labeler.label(items))
    # Results in: [("0", "apple"), ("1", "banana"), ("2", "cherry")]
    ```

The generated labels are guaranteed to be of uniform width and unique within
the provided collection.
"""

from __future__ import annotations

import itertools as it
import math
from collections.abc import Collection, Hashable, Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


def _is_uniq[T: Hashable](iterable: Iterable[T]) -> bool:
    seen = set[T]()

    for item in iterable:
        if item in seen:
            return False
        seen.add(item)
    return True


class Labeler:
    """Fixed width lexicographical string generator."""

    alphabet: str

    def __init__(self, alphabet: str):
        if len(alphabet) < 2:  # noqa: PLR2004
            msg = "Alphabet must contain at least 2 characters."
            raise ValueError(msg)

        if not _is_uniq(alphabet):
            msg = "Alphabet must contain unique characters."
            raise ValueError(msg)

        self.alphabet = alphabet

    def label[T](self, items: Collection[T]) -> Iterator[tuple[str, T]]:
        """Generate fixed width labels for items.

        The labels are generated in lexicographical order based on the provided
        alphabet. The labels are generated in a way that ensures that the
        sorting the labels will give the same order as sorting the items.

        Parameters
        ----------
        items : Iterable[T]
            An iterable of items to label.

        Yields
        ------
        Iterator[tuple[T, str]]
            An iterator over tuples of items and their corresponding labels.
        """
        if not isinstance(items, Collection):  # pyright: ignore[reportUnnecessaryIsInstance]
            msg = f"Expected Collection, got {type(items).__name__}"
            raise TypeError(msg)

        if not items:
            return iter([])

        width = max(
            math.ceil(math.log(len(items), len(self.alphabet))),
            1,
        )

        labels = map(
            "".join,
            it.islice(
                it.product(self.alphabet, repeat=width),
                len(items),
            ),
        )

        return zip(
            labels,
            items,
            strict=True,
        )
