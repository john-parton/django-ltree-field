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

        return zip(
            self._iter(
                width=self._label_width(len(items)),
            ),
            items,
            strict=False,
        )

    def _label_width(self, n: int) -> int:
        """Calculate the width of the labels needed for n items.

        The width is determined by the size of the alphabet and the number
        of items. The width is calculated using the formula:
        ceil(log(n, len(alphabet)))

        Parameters
        ----------
        n : int
            The number of items to label.

        Returns
        -------
        int
            The width of the labels needed for n items.
        """
        return max(
            math.ceil(math.log(n, len(self.alphabet))),
            1,
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
