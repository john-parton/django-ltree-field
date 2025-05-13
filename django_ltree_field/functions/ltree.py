from __future__ import annotations

from functools import cache

from django.db import models
from django.db.models import Expression, Func

type Resolvable = Expression | str


@cache
def LTreeField():
    from django_ltree_field.fields import LTreeField

    return LTreeField()


# This should be a Transform?
class SubLTree(Func):
    """Returns subpath of ltree from position start to position end-1 (counting from 0)."""

    function = "subltree"
    arity = 3

    def __init__(self, *expressions: Resolvable, output_field=None, **kwargs):
        if output_field is None:
            output_field = LTreeField()

        super().__init__(*expressions, output_field=output_field, **kwargs)


class Subpath(Func):
    """Returns subpath of ltree.

    Three args returns subpath of ltree starting at position offset, with length len.
    If offset is negative, subpath starts that far from the end of the path.
    If len is negative, leaves that many labels off the end of the path.
    Two args returns subpath of ltree starting at position offset, extending to end of
    path.
    If offset is negative, subpath starts that far from the end of the path.
    """

    function = "subpath"

    def __init__(self, *expressions: Resolvable, output_field=None, **kwargs):
        if len(expressions) not in {2, 3}:
            msg = "Subpath takes 2 or 3 arguments"
            raise ValueError(msg)

        if output_field is None:
            output_field = LTreeField()

        super().__init__(*expressions, output_field=output_field, **kwargs)


class Index(Func):
    function = "index"

    def __init__(self, *expressions: Resolvable, output_field=None, **kwargs):
        if len(expressions) not in {2, 3}:
            msg = "Index takes 2 or 3 arguments"
            raise ValueError(msg)

        if output_field is None:
            output_field = models.IntegerField()

        super().__init__(*expressions, output_field=output_field, **kwargs)


# No text2ltree or ltree2text functions... not sure how useful they would be?
# How does this differ from Cast()? Just use Cast?


class LCA(Func):
    function = "lca"

    def __init__(self, *expressions: Resolvable, output_field=None, **kwargs):
        # Postgres docs say that LCA will only admit up to 8 arguments, but we'll let
        # the database backend throw that error, seems unlikely to occur
        # So arity should really be 1..=8
        if not expressions:
            msg = "LCA takes at least one argument"
            raise ValueError(msg)

        if output_field is None:
            output_field = LTreeField()

        super().__init__(*expressions, output_field=output_field, **kwargs)


class Concat(Func):
    """
    Concatenate ltree paths together. Uses the postgres || operator.

    If you don't pass in at least one ltree, it will probably do text concatenation,
    which you almost certainly don't actually want. So don't do that.
    """

    function = ""  # will result in parenthesis only
    arg_joiner = " || "

    def __init__(self, *expressions: Resolvable, output_field=None, **kwargs):
        if len(expressions) < 2:
            msg = "Concat takes at least 2 arguments"
            raise ValueError(msg)

        if output_field is None:
            output_field = LTreeField()

        super().__init__(*expressions, output_field=output_field, **kwargs)
