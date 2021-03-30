=============================
PostgreSQL LTreeField for Django
=============================

.. image:: https://badge.fury.io/py/django-ltree-field.svg
    :target: https://badge.fury.io/py/django-ltree-field

.. image:: https://travis-ci.org/john-parton/django-ltree-field.svg?branch=master
    :target: https://travis-ci.org/john-parton/django-ltree-field

.. image:: https://codecov.io/gh/john-parton/django-ltree-field/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/john-parton/django-ltree-field

LTreeField for Django

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
* Does virtually no sanity checking. You can insert nodes without roots, and other
* Does not implement an abstract "Node" model which has a nice API (See django-ltree-model for an example)

Future Features?
----------------

* Implement an LTree python class to use as a container. Current my_obj.path[0] will return the first character
of the path, but it is probably more logical to return the first label. Subclass UserList?


Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox


Development commands
---------------------

::

    pip install -r requirements_dev.txt
    invoke -l


Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
