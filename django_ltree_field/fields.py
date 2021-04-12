from functools import partial

from django.contrib.postgres.forms import SimpleArrayField
from django.db import models
from django.db.models import Lookup, Transform
from django.db.models.lookups import PostgresOperatorLookup
from django import forms

from .validators import label_validator


class LTreeField(models.Field):
    def db_type(self, connection):
        return 'ltree'

    def formfield(self, **kwargs):
        # Set up some overrideable defaults
        defaults = {
            # Bind required positional argument
            'form_class': partial(
                SimpleArrayField,
                forms.CharField(
                    validators=[label_validator]
                )
            ),
            'min_length': 1,
            'delimiter': '.'
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    # TODO Implement validate method?

    def from_db_value(self, value, *args, **kwargs):
        # NULL
        if value is None:
            return None
        # Special "root" object
        if value == '':
            return []
        # Dotted string
        if not isinstance(value, list):
            return value.split('.')
        # Something else
        return value

    def get_prep_value(self, value):
        if value is None:
            return None
        if isinstance(value, list):
            return '.'.join(value)
        return value

    def get_transform(self, name):
        # This implements index and slicing lookups
        # So path__0 gives the root label and
        # path__0_2 gives the first two labels
        transform = super().get_transform(name)
        if transform:
            return transform

        # Postgres uses 0-indexing for the Subltree function
        # No need to shift by one like the Array transforms
        # I think this is a little busted
        # a regular index should probably return the label (characters) and not a path
        # with one label
        # The slice 0_3 method should return a path
        # If you really do want the label as a path you can do path__0_1
        try:
            indices = list(map(int, name.split('_')))
        except ValueError:
            pass
        else:

            # Bind the indices as appropriate
            if len(indices) == 1:
                return partial(IndexTransform, *indices)
            elif len(indices) == 2:
                return partial(SliceTransform, *indices)


# Same as DataContains, but different lookup name for easier usability
@LTreeField.register_lookup
class AncestorOfLookup(PostgresOperatorLookup):
    # *inclusive* of the path in question, as per postgres conventions
    lookup_name = 'ancestor_of'
    postgres_operator = '@>'


@LTreeField.register_lookup
class DescendantOfLookup(PostgresOperatorLookup):
    # *inclusive* of the path in question, as per postgres conventions
    lookup_name = 'descendant_of'
    postgres_operator = '<@'


@LTreeField.register_lookup
class SiblingOfLookup(Lookup):
    # This can be done other ways, but it's a common enough use-case/
    # pattern that we want a shortcut
    lookup_name = 'sibling_of'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return 'subpath(%s, 0, -1) = subpath(%s, 0, -1)' % (lhs, rhs), params


@LTreeField.register_lookup
class ChildOfLookup(Lookup):
    # This can be done other ways, but it's a common enough use-case/
    # pattern that we want a shortcut
    lookup_name = 'child_of'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return 'subpath(%s, 0, -1) = %s' % (lhs, rhs), params


@LTreeField.register_lookup
class ParentOfLookup(Lookup):
    # This can be done other ways, but it's a common enough use-case/
    # pattern that we want a shortcut
    lookup_name = 'parent_of'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return '%s = subpath(%s, 0, -1)' % (lhs, rhs), params


@LTreeField.register_lookup
class MatchesLookup(PostgresOperatorLookup):
    lookup_name = 'matches'
    postgres_operator = '~'


@LTreeField.register_lookup
class SearchLookup(PostgresOperatorLookup):
    lookup_name = 'search'
    postgres_operator = '@'


@LTreeField.register_lookup
class DepthTransform(Transform):
    # "depth" is slightly more usable than "nlevel"
    # And less confusing than "len"
    # Might be more generic if support for a backend other than postgres were ever added
    # If that backend uses a different function
    lookup_name = 'depth'
    function = 'NLEVEL'

    output_field = models.PositiveIntegerField()


class IndexTransform(Transform):
    def __init__(self, index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = index

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return 'subltree(%s, %%s, %%s)' % lhs, params + [self.index, self.index + 1]

    output_field = models.CharField()


class SliceTransform(Transform):
    def __init__(self, start, end, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start = start
        self.end = end

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return 'subltree(%s, %%s, %%s)' % lhs, params + [self.start, self.end]

    @property
    def output_field(self):
        return LTreeField()
