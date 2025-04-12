from __future__ import annotations

from functools import partial
from typing import Any, Literal, Protocol

from django.core.exceptions import ValidationError
from django.contrib.postgres.lookups import ContainedBy, DataContains
from django.db import models
from django.db.models import Lookup, Transform
from django.db.models.lookups import PostgresOperatorLookup
from django.utils.translation import gettext_lazy as _

from .constants import LTreeTrigger
from .integer_paths import default_codec


class LTreeField(models.Field):
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

        # Bind the indices as appropriate
        if len(indices) == 1:
            return partial(IndexTransform, *indices, output_field=type(self))
        if len(indices) == 2:
            return partial(SliceTransform, *indices, output_field=type(self))

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
    def __init__(self, index: int):
        super().__init__()
        self.index = index

    def as_sql(self, compiler, connection):  # noqa: ARG002
        lhs, params = compiler.compile(self.lhs)
        return f"subltree({lhs}, %s, %s)", params + [self.index, self.index + 1]


class SliceTransform(Transform):
    def __init__(self, start: int, end: int):
        super().__init__()
        self.start = start
        self.end = end

    def as_sql(self, compiler, connection):  # noqa: ARG002
        lhs, params = compiler.compile(self.lhs)
        return f"subltree({lhs}, %s, %s)", params + [self.start, self.end]


class CodecProtocol(Protocol):
    max_value: int  # Maybe this should be on the field directly?

    def decode(self, value: str) -> int: ...

    def encode(self, value: int) -> str: ...


class IntegerLTreeField(LTreeField):
    codec: CodecProtocol

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        self.codec = kwargs.pop("codec") if "codec" in kwargs else default_codec()
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["codec"] = self.codec
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection) -> tuple[int, ...] | None:
        return self.to_python(value)

    def to_python(self, value) -> tuple[int, ...] | None:
        if value is None:
            return None

        if isinstance(value, tuple):
            # Doesn't actually check that values are integers
            return value

        if not isinstance(value, str):
            msg = _("Expected string")
            raise ValidationError(msg)

        return tuple(self.codec.decode(label) for label in value.split("."))

    def get_prep_value(self, value: list[int] | tuple[int] | str | None) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            # Just assume the user knows what they're doing
            return value

        if not isinstance(value, (list, tuple)):
            msg = _("Expected list or tuple")
            raise ValidationError(msg)

        for label in value:
            if not isinstance(label, int):
                msg = _("Expected integer")
                raise ValidationError(msg)
            if label < 0:
                msg = _("Expected positive integer")
                raise ValidationError(msg)

        return ".".join(self.codec.encode(label) for label in value)
