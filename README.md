# PostgreSQL LTreeField for Django

[![image](https://badge.fury.io/py/django-ltree-field.svg)](https://badge.fury.io/py/django-ltree-field)

[![image](https://codecov.io/gh/john-parton/django-ltree-field/branch/master/graph/badge.svg)](https://codecov.io/gh/john-parton/django-ltree-field)

Minimalist Django Field for the PostgreSQL ltree Type.

django-ltree-field attempts to make very few assumptions about your use
case.

For a higher level API based on django-ltree-field, consider using a
prebuilt model from
[django-ltree-utils](https://github.com/john-parton/django-ltree-utils).

It *should* be possible to re-implement the
[django-treebeard](https://github.com/django-treebeard/django-treebeard)
API, allowing for drop-in compatibility, but that is not a specific goal
at this time. If someone starts this, let me know and I will provide
some assistance.

## Documentation

The full documentation is at
<https://django-ltree-field.readthedocs.io>.

## Quickstart

Install PostgreSQL LTreeField for Django:

    pip install django-ltree-field

Add it to your \`INSTALLED_APPS\`:

``` python
INSTALLED_APPS = (
    ...
    'django_ltree_field',
    ...
)
```

Add an LTreeField to a new or existing model:

``` python
from django_ltree_field.fields import LTreeField

class SimpleNode(models.Model):
    path = LTreeField(index=True, unique=True)

    class Meta:
        ordering = ['path']
```

## Features

-   Implements logic to make the ltree PostgreSQL type usable.
-   Patches Django to install Postgres Triggers to keep the tree state consistent.
-   LTreeField accepts a string of dotted labels.
-   Relatively complete set of lookups and transforms.

## Non-Features

-   PostgreSQL compatibility only

## Future Features

I will happily accept *minimal* features required to make the field be
reasonably usable. In particular, every operator, function, and example
on the [official PostgreSQL
docs](https://www.postgresql.org/docs/current/ltree.html) should be
implemented with Django\'s ORM, with no RawSQL or non-idiomatic code.

Higher-level or richer features should be contributed to
[django-ltree-utils](https://github.com/john-parton/django-ltree-utils).
As a rule of thumb, if an operation requires referencing more than one
row at a time, or maintaining some more complicated state, it probably
belongs there.

## Running Tests

You need to have a reasonably updated version of PostgreSQL listening on
port 5444. You can use
[docker-compose](https://docs.docker.com/compose/) to start a server

    docker-compose up

Does the code actually work?

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install -r requirements.txt -r requirements_test.txt --upgrade
    (myenv) $ ./runtests.py

## Previous Releases

