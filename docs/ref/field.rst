=====================
Model field reference
=====================

.. module:: django_ltree_field.fields
   :synopsis: Fields for storing heirarchical data in Django models.

Field types
===========

.. currentmodule:: django_ltree_field.fields


``LTreeField``
-------------

.. class:: LTreeField(**options)

A field for storing heirarchical data. In Python the data is represented is
represented as a dotted string.

``LTreeField`` is supported on PostgreSQL.

To query ``LTreeField`` in the database, see :ref:`querying-ltreefield`.

Indexing
~~~~~~~~

:class:`~django.db.models.Index` and :attr:`.Field.db_index` both create a
B-tree index, which isn't particularly helpful when querying ``LTreeField``.
You can use :class:`django.contrib.postgres.indexes.GistIndex` that is better suited.


.. code-block:: python

    class Node(models.Model):
        path = LTreeField()

        class Meta:
            indexes = [
                GistIndex(
                    fields=("path",),
                    name="node_path_idx",
                ),
            ]

Advanced usage, supplying `siglen` to the index:

(see https://www.postgresql.org/docs/current/ltree.html#LTREE-INDEXES)

.. code-block:: python

    class Node(models.Model):
        path = LTreeField()

        class Meta:
            indexes = [
                GistIndex(
                    fields=("path",),
                    opclasses=("gist_ltree_ops(siglen=100)",),
                    name="node_path_idx",
                ),
            ]