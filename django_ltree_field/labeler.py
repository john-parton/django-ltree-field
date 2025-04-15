from __future__ import annotations

import itertools as it
import math
from collections.abc import Collection
from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


class Labeler:
    """Fixed width lexicographical string generator."""

    alphabet: str

    def __init__(self, alphabet: str):
        if not alphabet:
            msg = "Alphabet must contain at least 1 character."
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

        for chars, item in zip(
            it.product(self.alphabet, repeat=width),
            items,
            strict=False,
        ):
            yield "".join(chars), item
