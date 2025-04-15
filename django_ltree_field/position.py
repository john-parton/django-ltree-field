from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Protocol,
)


class _NodeProtocol(Protocol):
    path: str


class _BaseRelativePosition: ...


class Root(_BaseRelativePosition):
    pass


@dataclass
class FirstChildOf(_BaseRelativePosition):
    rel_obj: _NodeProtocol


@dataclass
class LastChildOf(_BaseRelativePosition):
    rel_obj: _NodeProtocol


@dataclass
class Before(_BaseRelativePosition):
    rel_obj: _NodeProtocol


@dataclass
class After(_BaseRelativePosition):
    rel_obj: _NodeProtocol


type RelativePosition = Root | FirstChildOf | LastChildOf | Before | After


# These are not-yet used, but placeholders for the future


class _BaseSortedPosition: ...


class SortedRoot(_BaseSortedPosition):
    pass


@dataclass
class SortedChildOf(_BaseSortedPosition):
    rel_obj: _NodeProtocol


@dataclass
class SortedSibling(_BaseSortedPosition):
    rel_obj: _NodeProtocol


type SortedPosition = SortedRoot | SortedChildOf | SortedSibling
