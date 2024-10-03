==============
Making queries
==============

.. _querying-ltreefield:

Querying ``~django_ltree_field.fields.LTreeField``
======================

Lookups implementation is different in :class:`~django.db.models.LTree`,
mainly due to the rich set of operators and functions available in PostgreSQL
for the ``ltree`` type. To demonstrate, we will use the following example model::

.. code-block:: python

    from django.db import models
    from django_ltree_field.fields import LTreeField


    class Hobby(models.Model):
        path = LTreeField(null=True)

.. _containment-and-key-lookups:

Containment and key lookups
---------------------------

.. fieldlookup:: ltreefield.ancestor_of

``ancestor_of``
~~~~~~~~~~~~

The :lookup:`ancestor_of` lookup is overridden on ``JSONField``. The returned
objects are those where the given ``dict`` of key-value pairs are all
contained in the top-level of the field. For example:

.. code-block:: pycon

    >>> Dog.objects.create(name="Rufus", data={"breed": "labrador", "owner": "Bob"})
    <Dog: Rufus>
    >>> Dog.objects.create(name="Meg", data={"breed": "collie", "owner": "Bob"})
    <Dog: Meg>
    >>> Dog.objects.create(name="Fred", data={})
    <Dog: Fred>
    >>> Dog.objects.filter(data__contains={"owner": "Bob"})
    <QuerySet [<Dog: Rufus>, <Dog: Meg>]>
    >>> Dog.objects.filter(data__contains={"breed": "collie"})
    <QuerySet [<Dog: Meg>]>

.. admonition:: Oracle and SQLite

    ``contains`` is not supported on Oracle and SQLite.

.. fieldlookup:: jsonfield.contained_by

``contained_by``
~~~~~~~~~~~~~~~~

This is the inverse of the :lookup:`contains <jsonfield.contains>` lookup - the
objects returned will be those where the key-value pairs on the object are a
subset of those in the value passed. For example:

.. code-block:: pycon

    >>> Dog.objects.create(name="Rufus", data={"breed": "labrador", "owner": "Bob"})
    <Dog: Rufus>
    >>> Dog.objects.create(name="Meg", data={"breed": "collie", "owner": "Bob"})
    <Dog: Meg>
    >>> Dog.objects.create(name="Fred", data={})
    <Dog: Fred>
    >>> Dog.objects.filter(data__contained_by={"breed": "collie", "owner": "Bob"})
    <QuerySet [<Dog: Meg>, <Dog: Fred>]>
    >>> Dog.objects.filter(data__contained_by={"breed": "collie"})
    <QuerySet [<Dog: Fred>]>

.. admonition:: Oracle and SQLite

    ``contained_by`` is not supported on Oracle and SQLite.

.. fieldlookup:: jsonfield.has_key

``has_key``
~~~~~~~~~~~

Returns objects where the given key is in the top-level of the data. For
example:

.. code-block:: pycon

    >>> Dog.objects.create(name="Rufus", data={"breed": "labrador"})
    <Dog: Rufus>
    >>> Dog.objects.create(name="Meg", data={"breed": "collie", "owner": "Bob"})
    <Dog: Meg>
    >>> Dog.objects.filter(data__has_key="owner")
    <QuerySet [<Dog: Meg>]>

.. fieldlookup:: jsonfield.has_any_keys

``has_keys``
~~~~~~~~~~~~

Returns objects where all of the given keys are in the top-level of the data.
For example:

.. code-block:: pycon

    >>> Dog.objects.create(name="Rufus", data={"breed": "labrador"})
    <Dog: Rufus>
    >>> Dog.objects.create(name="Meg", data={"breed": "collie", "owner": "Bob"})
    <Dog: Meg>
    >>> Dog.objects.filter(data__has_keys=["breed", "owner"])
    <QuerySet [<Dog: Meg>]>

.. fieldlookup:: jsonfield.has_keys

``has_any_keys``
~~~~~~~~~~~~~~~~

Returns objects where any of the given keys are in the top-level of the data.
For example:

.. code-block:: pycon

    >>> Dog.objects.create(name="Rufus", data={"breed": "labrador"})
    <Dog: Rufus>
    >>> Dog.objects.create(name="Meg", data={"owner": "Bob"})
    <Dog: Meg>
    >>> Dog.objects.filter(data__has_any_keys=["owner", "breed"])
    <QuerySet [<Dog: Rufus>, <Dog: Meg>]>