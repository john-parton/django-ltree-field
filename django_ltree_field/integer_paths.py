from __future__ import annotations

from dataclasses import KW_ONLY, dataclass, field
import itertools as it
import string
from collections.abc import Iterable

from django.utils.deconstruct import deconstructible
from functools import reduce

# Postgres 16 and later
# For example, in C locale, the characters A-Za-z0-9_- are allowed. Labels must be no more than 1000 characters long.
# # Postgres 15
# A label is a sequence of alphanumeric characters and underscores (for example, in C locale the characters A-Za-z0-9_ are allowed). Labels must be less than 256 characters long.


@deconstructible
@dataclass
class PaddedCodec:
    """Class to encode and decode integers to and from a padded string.

    Postgres ltree type encodes paths as strings. It is useful to be able to do
    "arithmetic" on paths. For instance, if you have a given path, you might want
    an arbitrary path which comes after it or before it.

    It's somewhat tricky to perform this sort of operation directly on a string, but
    is trivial to do on an integer. This class provides an order-preserving bijection
    between positive integers and strings of a given fixed length.

    Parameters
    ----------
    chars : list[str]
        A sequence of unique characters to use for encoding and decoding.
        The characters must be sorted.
    length : int
        The length of the encoded string. Must be greater than 0.

    Raises
    ------
    ValueError
        If the characters are not unique or not sorted.

    Attributes
    ----------
    chars : list[str]
        The characters used for encoding and decoding.
    reverse : dict[str, int]
        A mapping of characters to their index in `chars`.
    base : int
        The number of characters in `chars`.
    length : int
        The length of the encoded string.
    max_value : int
        The maximum value that can be encoded with the given `chars` and `length`.
    """

    chars: list[str]
    _: KW_ONLY
    length: int
    reverse: dict[str, int] = field(init=False)
    base: int = field(init=False)
    max_value: int = field(init=False)

    def __post_init__(self):
        if any(lower > upper for lower, upper in it.pairwise(self.chars)):
            msg = "chars must be sorted"
            raise ValueError(msg)

        self.reverse = {char: index for index, char in enumerate(self.chars)}

        if len(self.reverse) != len(self.chars):
            msg = "chars must be unique"
            raise ValueError(msg)

        self.base = len(self.chars)
        self.max_value = self.base**self.length - 1

    def encode(self, value: int) -> str:
        """Encode an integer as a string.

        Parameters
        ----------
        value : int
            The integer to encode. Must be between 0 and `max_value`.

        Returns
        -------
        str
            The encoded string.

        Raises
        ------
        ValueError
            If the value is less than 0 or greater than `max_value`.
        TypeError
            If the value is not an integer.
        """
        if not isinstance(value, int):  # type: ignore  # noqa: PGH003
            msg = "Value must be an integer"
            raise TypeError(msg)

        if value == 0:
            return self.chars[0] * self.length

        if value < 0 or value > self.max_value:
            msg = f"Value must be between 0 and {self.max_value}"
            raise ValueError(msg)

        result: list[str] = []
        while value > 0:
            value, remainder = divmod(value, self.base)
            result.append(self.chars[remainder])

        return "".join(result[::-1]).rjust(self.length, self.chars[0])

    def decode(self, value: str) -> int:
        if len(value) != self.length:
            msg = f"Value must be {self.length} characters long"
            raise ValueError(msg)

        value = value.lstrip(self.chars[0])

        result = 0
        for char in value:
            result *= self.base
            result += self.reverse[char]
        return result


def default_codec(*, length: int = 5) -> PaddedCodec:
    # For use with Postgres 16 and later
    return PaddedCodec(
        list(
            "-" + string.digits + string.ascii_uppercase + "_" + string.ascii_lowercase
        ),
        length=length,
    )


def legacy_codec(*, length: int = 5) -> PaddedCodec:
    # For use with Postgres 15 and earlier
    return PaddedCodec(
        list(string.digits + string.ascii_uppercase + "_" + string.ascii_lowercase),
        length=length,
    )
