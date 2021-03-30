
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
    arity = 2
    output_field = models.IntegerField()


# No text2ltree or ltree2text functions... not sure how useful they would be

# # I really doubt the usefulness of this function
# class LCA(Func):
#     function = 'lca'
#     # This isn't supposed to take more than 9 arguments, according to docs


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
