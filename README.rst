================================
PostgreSQL LTreeField for Django
================================

.. image:: https://badge.fury.io/py/django-ltree-field.svg
    :target: https://badge.fury.io/py/django-ltree-field

.. image:: https://codecov.io/gh/john-parton/django-ltree-field/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/john-parton/django-ltree-field

Minimalist Django Field for the PostgreSQL ltree Type.

django-ltree-field attempts to make very few assumptions about your use case.

For a higher level API based on django-ltree-field, consider using a prebuilt model from
`django-ltree-utils <https://github.com/john-parton/django-ltree-utils>`_.

It *should* be possible to re-implement the `django-treebeard <https://github.com/django-treebeard/django-treebeard>`_ API,
allowing for drop-in compatibility, but that is not a specific goal at this time. If someone starts this, let me know and I
will provide some assistance.

Documentation
-------------

The full documentation is at https://django-ltree-field.readthedocs.io.

Quickstart
----------

Install PostgreSQL LTreeField for Django::

    pip install django-ltree-field

Add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django_ltree_field',
        ...
    )

Add an LTreeField to a new or existing model:

.. code-block:: python

    from django_ltree_field.fields import LTreeField

    class SimpleNode(models.Model):
        path = LTreeField(index=True, unique=True)

        class Meta:
            ordering = ['path']

Features
--------

* Implements **only** the bare minimum to make the ltree PostgreSQL type usable
* LTreeField accepts a string of dotted labels, or a list of labels
* The ltree type is adapted to a Python list
* Relatively complete set of lookups and transforms.

..
    _ TODO: Link docs for lookups and transforms


Non-Features
------------

* Does not implement an abstract "Node" model which has a nicer API (See django-ltree-utils for ready-made classes and managers)
* Does virtually no sanity checking. You can insert nodes without roots, and generally put the tree in a bad state
* PostgreSQL compatibility only


Future Features
---------------

I will happily accept *minimal* features required to make the field be reasonably usable. In particular, every operator,
function, and example on the `official PostgreSQL docs <https://www.postgresql.org/docs/current/ltree.html>`_
should be implemented with Django's ORM, with no RawSQL or non-idiomatic code.

Higher-level or richer features should be contributed to `django-ltree-utils <https://github.com/john-parton/django-ltree-utils>`_.
As a rule of thumb, if an operation requires referencing more than one row at a time, or maintaining some more complicated
state, it probably belongs there.


Running Tests
-------------

You need to have a reasonably updated version of PostgreSQL listening on port 5444. You can use
`docker-compose <https://docs.docker.com/compose/>`_ to start a server

::

    docker-compose up

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install -r requirements.txt -r requirements_test.txt --upgrade
    (myenv) $ ./runtests.py
