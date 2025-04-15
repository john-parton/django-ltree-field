from __future__ import annotations

import itertools as it
import math
from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator


class Labeler:
    """Fixed width lexicographical string generator."""

    alphabet: str

    def __init__(self, alphabet: str):
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
        if not items:
            return iter([])

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
