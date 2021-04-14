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

    class MyModel(models.Model):
        path = LTreeField(index=True, unique=True)

        class Meta:
            ordering = ['path']

Features
--------

* Implements **only** the bare minimum to make the ltree postgres type usuable
* Does virtually no sanity checking. You can insert nodes without roots, and generally put the tree in a
  bad state
* LTreeField accepts a string of dotted labels, or a list of labels
* The ltree type is adapted to a python list
* Does not implement an abstract "Node" model which has a nicer API (See django-ltree-utils for ready-made classes and managers)

Future Features?
----------------

* Only *minimal* features required to make the field be reasonably usable will be added
* Higher-level or richer features should be added to django-ltree-utils


Running Tests
-------------

You need to have a reasonably updated version of PostgreSQL listening on port 5444. You can use
`docker-compose <https://docs.docker.com/compose/>` to start a server

::

    docker-compose up

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install -r requirements.txt -r requirements_test.txt --upgrade
    (myenv) $ ./runtests.py
