
from django.db import models
from django.db.models import Func

from .fields import LTreeField


# This should be a Transform?
class SubLTree(Func):
    """Returns subpath of ltree from position start to position end-1 (counting from 0).
    """
    function = 'subltree'
    arity = 3
    output_field = LTreeField()


class Subpath(Func):
    """Returns subpath of ltree.
    Three args returns subpath of ltree starting at position offset, with length len.
    If offset is negative, subpath starts that far from the end of the path.
    If len is negative, leaves that many labels off the end of the path.
    Two args returns subpath of ltree starting at position offset, extending to end of path.
    If offset is negative, subpath starts that far from the end of the path.
    """
    function = 'subpath'
    output_field = LTreeField()

    def __init__(self, *expressions, **extra):
        if len(expressions) not in {2, 3}:
            raise ValueError('Subpath takes 2 or 3 arguments')
        super().__init__(*expressions, **extra)


class NLevel(Func):
    function = 'nlevel'
    arity = 1
    output_field = models.PositiveIntegerField()


class Index(Func):
    function = 'index'
    output_field = models.IntegerField()

    def __init__(self, *expressions, **extra):
        if len(expressions) not in {2, 3}:
            raise ValueError('Index takes 2 or 3 arguments')
        super().__init__(*expressions, **extra)


# No text2ltree or ltree2text functions... not sure how useful they would be\
# How does this differ from Cast()? Just use Cast?

# I really doubt the usefulness of this function, but it's here for completion sake
class LCA(Func):
    function = 'lca'
    output_field = LTreeField()

    @property
    def template(self):
        # Kind of hacky way to handle allowing a single array arg
        # We might want to be smarter than this
        if len(self.source_expressions) == 1:
            return '%(function)s(%(expressions)s::ltree[])'
        else:
            return '%(function)s(%(expressions)s)'

    def __init__(self, *expressions, **extra):
        # Postgres docs say that LCA will only admit up to 8 arguments, but we'll let
        # the database backend throw that error, seems unlikely to occur
        # So arity should really be 1..=8
        if not expressions:
            raise ValueError('LCA takes at least one argument')
        super().__init__(*expressions, **extra)


class Concat(Func):
    """
    Concatenate ltree paths together. Uses the postgres || operator.
    If you don't pass in at least one ltree, it will probably do text concatenation,
    which you almost certainly don't actually want. So don't do that.
    """
    function = None
    output_field = LTreeField()
    template = '%(expressions)s'
    arg_joiner = ' || '

    def __init__(self, *expressions, **extra):
        if len(expressions) < 2:
            raise ValueError('Concat takes at least 2 arguments')
        super().__init__(*expressions, **extra)
