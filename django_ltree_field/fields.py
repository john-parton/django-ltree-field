from __future__ import annotations

from functools import partial
from typing import Literal

from django.contrib.postgres.lookups import ContainedBy, DataContains
from django.db import models
from django.db.models import Lookup, Transform
from django.db.models.lookups import PostgresOperatorLookup


class LTreeField(models.Field):
    def db_type(self, connection) -> Literal["ltree"]:
        return "ltree"

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

        # Bind the indices as appropriate
        if len(indices) == 1:
            return partial(IndexTransform, *indices)
        if len(indices) == 2:
            return partial(SliceTransform, *indices)

        return None


LTreeField.register_lookup(DataContains)
LTreeField.register_lookup(ContainedBy)


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


@LTreeField.register_lookup
class DepthTransform(Transform):
    # "depth" is slightly more usable than "nlevel"
    # And less confusing than "len"
    # Might be more generic if support for a backend other than postgres were ever added
    # If that backend uses a different function
    lookup_name = "depth"
    function = "NLEVEL"

    output_field = models.PositiveIntegerField()  # type: ignore[assignment]


class IndexTransform(Transform):
    output_field = models.CharField()  # type: ignore[assignment]

    def __init__(self, index: int):
        super().__init__()
        self.index = index

    def as_sql(self, compiler, connection):  # noqa: ARG002
        lhs, params = compiler.compile(self.lhs)
        return f"subltree({lhs}, %s, %s)", params + [self.index, self.index + 1]


class SliceTransform(Transform):
    output_field = LTreeField()  # type: ignore[assignment]

    def __init__(self, start: int, end: int):
        super().__init__()
        self.start = start
        self.end = end

    def as_sql(self, compiler, connection):  # noqa: ARG002
        lhs, params = compiler.compile(self.lhs)
        return f"subltree({lhs}, %s, %s)", params + [self.start, self.end]
