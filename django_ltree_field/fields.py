from __future__ import annotations

from functools import partial
from typing import Callable, Literal

from django.contrib.postgres.lookups import ContainedBy, DataContains
from django.db import models
from django.db.models import Lookup, Value
from django.db.models.lookups import PostgresOperatorLookup
from django.utils.translation import gettext_lazy as _

from django_ltree_field.functions import NLevel, Subpath
from django_ltree_field.functions.ltree import SubLTree

from .constants import LTreeTrigger


def _partial_right[R](func: Callable[..., R], *outer_args) -> Callable[..., R]:
    """Similar to functools.partial, but allows for partial application of
    positional arguments starting from the right
    """

    def inner(*inner_args, **kwargs):
        return func(*inner_args, *outer_args, **kwargs)

    return inner


class LTreeField(models.Field):
    """
    A field for PostgreSQL ltree data type, representing a label path.

    This field is used to store hierarchical data in a tree-like structure.

    Attributes
    ----------
    triggers : LTreeTrigger, optional
        Specifies the behavior for database triggers when modifying the tree structure.
        The `triggers` argument can be set to one of the following:

        - `LTreeField.PROTECT`: Prevent deletion of nodes with children.
        - `LTreeField.CASCADE`: Automatically delete child nodes when a parent is deleted.

        Defaults to `LTreeField.CASCADE`.

    Notes
    -----
    The default form widget for this field is a `django.forms.TextInput`.
    """

    # Aliases for users
    PROTECT = LTreeTrigger.PROTECT
    CASCADE = LTreeTrigger.CASCADE

    triggers: LTreeTrigger | None

    def __init__(
        self,
        *args,
        triggers: LTreeTrigger | None = LTreeTrigger.CASCADE,
        **kwargs,
    ):
        self.triggers = triggers
        super().__init__(*args, **kwargs)

    @property
    def description(self):
        return _("Path (ltree)")

    def db_type(self, connection) -> Literal["ltree"]:
        return "ltree"

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["triggers"] = self.triggers
        return name, path, args, kwargs

    # TODO Implement validate method?

    def get_transform(self, name: str):
        if transform := super().get_transform(name):
            return transform

        # This implements index and slicing lookups
        # So path__0 gives the root label and
        # path__0_2 gives the first two labels

        # Postgres uses 0-indexing for the Subltree function
        # No need to shift by one like the Array transforms
        # I think this is a little busted
        # a regular index should probably return the label (characters) and not a path
        # with one label
        # The slice 0_3 method should return a path
        # If you really do want the label as a path you can do path__0_1
        try:
            indices = list(map(int, name.split("_")))
        except ValueError:
            return None

        match indices:
            # Bind the indices as appropriate
            case [index]:
                return _partial_right(Subpath, Value(index), Value(1))
            case [start, end]:
                return _partial_right(SubLTree, Value(start), Value(end))
            case _:
                return None


LTreeField.register_lookup(ContainedBy)
LTreeField.register_lookup(DataContains)
LTreeField.register_lookup(NLevel)


@LTreeField.register_lookup
class SiblingOfLookup(Lookup):
    # This can be done other ways, but it's a common enough use-case/pattern that we
    # want a shortcut
    lookup_name = "sibling_of"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return f"subpath({lhs}, 0, -1) = subpath({rhs}, 0, -1)", params


@LTreeField.register_lookup
class ChildOfLookup(Lookup):
    # This can be done other ways, but it's a common enough use-case/pattern that we
    # want a shortcut
    lookup_name = "child_of"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return f"subpath({lhs}, 0, -1) = {rhs}", params


@LTreeField.register_lookup
class ParentOfLookup(Lookup):
    # This can be done other ways, but it's a common enough use-case/
    # pattern that we want a shortcut
    lookup_name = "parent_of"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return f"{lhs} = subpath({rhs}, 0, -1)", params


@LTreeField.register_lookup
class MatchesLookup(PostgresOperatorLookup):
    lookup_name = "matches"
    postgres_operator = "~"


@LTreeField.register_lookup
class SearchLookup(PostgresOperatorLookup):
    lookup_name = "search"
    postgres_operator = "@"


class _PostgresOperatorProperLookup(Lookup):
    # Same as PostgresOperatorLookup, but always excludes exact matches

    postgres_operator = None

    def as_postgresql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        # Double up params
        params = (lhs_params + rhs_params) * 2
        return f"{lhs} {self.postgres_operator} {rhs} AND {lhs} <> {rhs}", params


@LTreeField.register_lookup
class DescendantOfLookup(_PostgresOperatorProperLookup):
    postgres_operator = "<@"
    lookup_name = "descendant_of"


@LTreeField.register_lookup
class AncestorOfLookup(_PostgresOperatorProperLookup):
    postgres_operator = "@>"
    lookup_name = "ancestor_of"
