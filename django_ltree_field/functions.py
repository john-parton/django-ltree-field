from __future__ import annotations

from django.db import models
from django.db.models import Expression, Func

from .fields import LTreeField


# This should be a Transform?
class SubLTree(Func):
    """Returns subpath of ltree from position start to position end-1 (counting from 0)."""

    function = "subltree"
    arity = 3
    output_field = LTreeField()  # type: ignore[assignment]


class Subpath(Func):
    """Returns subpath of ltree.

    Three args returns subpath of ltree starting at position offset, with length len.
    If offset is negative, subpath starts that far from the end of the path.
    If len is negative, leaves that many labels off the end of the path.
    Two args returns subpath of ltree starting at position offset, extending to end of path.
    If offset is negative, subpath starts that far from the end of the path.
    """

    function = "subpath"
    output_field = LTreeField()  # type: ignore[assignment]

    def __init__(self, *expressions: Expression):
        if len(expressions) not in {2, 3}:
            msg = "Subpath takes 2 or 3 arguments"
            raise ValueError(msg)
        super().__init__(*expressions)


class NLevel(Func):
    function = "nlevel"
    arity = 1
    output_field = models.PositiveIntegerField()  # type: ignore[assignment]


class Index(Func):
    function = "index"
    output_field = models.IntegerField()  # type: ignore[assignment]

    def __init__(self, *expressions: Expression):
        if len(expressions) not in {2, 3}:
            msg = "Index takes 2 or 3 arguments"
            raise ValueError(msg)
        super().__init__(*expressions)


# No text2ltree or ltree2text functions... not sure how useful they would be\
# How does this differ from Cast()? Just use Cast?


# I really doubt the usefulness of this function, but it's here for completion sake
# Note in 2024: I found a use for it, so I'm glad it's here
class LCA(Func):
    function = "lca"
    output_field = LTreeField()  # type: ignore[assignment]

    @property
    def template(self) -> str:  # type: ignore[assignment]
        """Return the template for this function."""
        # Kind of hacky way to handle allowing a single array arg
        # We might want to be smarter than this
        # We might want to require users to be more explicit, but django doesn't
        # exactly have great built-in array support, maybe?
        if len(self.source_expressions) == 1:
            return "%(function)s(%(expressions)s::ltree[])"
        return "%(function)s(%(expressions)s)"

    def __init__(self, *expressions: Expression):
        # Postgres docs say that LCA will only admit up to 8 arguments, but we'll let
        # the database backend throw that error, seems unlikely to occur
        # So arity should really be 1..=8
        if not expressions:
            msg = "LCA takes at least one argument"
            raise ValueError(msg)
        super().__init__(*expressions)


class Concat(Func):
    """
    Concatenate ltree paths together. Uses the postgres || operator.

    If you don't pass in at least one ltree, it will probably do text concatenation,
    which you almost certainly don't actually want. So don't do that.
    """

    function = ""  # will result in parenthesis only
    output_field = LTreeField()  # type: ignore[assignment]
    arg_joiner = " || "

    def __init__(self, *expressions: Expression):
        if len(expressions) < 2:
            msg = "Concat takes at least 2 arguments"
            raise ValueError(msg)
        super().__init__(*expressions)
