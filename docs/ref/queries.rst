==============
Making queries
==============

.. _querying-ltreefield:

Querying ``~django_ltree_field.fields.LTreeField``
======================

Lookups implementation is different for :class:`~django_ltree_field.fields.LTreeField`,
mainly due to the rich set of operators and functions available in PostgreSQL
for the ``ltree`` type. To demonstrate, we will use the following example model::

.. code-block:: python

    from django.db import models
    from django_ltree_field.fields import LTreeField


    class Location(models.Model):
        path = LTreeField(unique=True)

        def __str__(self):
            return self.path

Let's assume we have the following data:

.. code-block:: pycon

    >>> Location.objects.bulk_create([
    ...     Location(path='Europe'),
    ...     Location(path='Europe.Spain'),
    ...     Location(path='Europe.Spain.Madrid'),
    ...     Location(path='Europe.France'),
    ...     Location(path='Europe.France.Paris'),
    ...     Location(path='Asia'),
    ...     Location(path='Asia.Japan'),
    ...     Location(path='Asia.Japan.Tokyo'),
    ... ])

.. _ltree-hierarchy-lookups:

Hierarchy lookups
-----------------

These lookups leverage the PostgreSQL ``ltree`` operators ``@>`` (ancestor) and ``<@`` (descendant).

``ancestor_of``
~~~~~~~~~~~~~~~

Returns objects whose ``path`` is an ancestor of the given path (but not the path itself). Uses the ``@>`` operator.

.. code-block:: pycon

    >>> Location.objects.filter(path__ancestor_of='Europe.Spain.Madrid')
    <QuerySet [<Location: Europe>, <Location: Europe.Spain>]>

    >>> Location.objects.filter(path__ancestor_of='Asia')
    <QuerySet []>

``descendant_of``
~~~~~~~~~~~~~~~~~

Returns objects whose ``path`` is a descendant of the given path (but not the path itself). Uses the ``<@`` operator.

.. code-block:: pycon

    >>> Location.objects.filter(path__descendant_of='Europe')
    <QuerySet [<Location: Europe.Spain>, <Location: Europe.Spain.Madrid>, <Location: Europe.France>, <Location: Europe.France.Paris>]>

    >>> Location.objects.filter(path__descendant_of='Asia.Japan')
    <QuerySet [<Location: Asia.Japan.Tokyo>]>

``child_of``
~~~~~~~~~~~~

Returns objects whose ``path`` is a direct child of the given path. This is a shortcut for ``subpath(path, 0, nlevel(path)-1) = parent_path``.

.. code-block:: pycon

    >>> Location.objects.filter(path__child_of='Europe')
    <QuerySet [<Location: Europe.Spain>, <Location: Europe.France>]>

    >>> Location.objects.filter(path__child_of='Europe.Spain')
    <QuerySet [<Location: Europe.Spain.Madrid>]>

``parent_of``
~~~~~~~~~~~~~

Returns the object whose ``path`` is the direct parent of the given path. This is a shortcut for ``path = subpath(child_path, 0, nlevel(child_path)-1)``.

.. code-block:: pycon

    >>> Location.objects.filter(path__parent_of='Europe.Spain.Madrid')
    <QuerySet [<Location: Europe.Spain>]>

    >>> Location.objects.filter(path__parent_of='Asia')
    <QuerySet []>

``sibling_of``
~~~~~~~~~~~~~~

Returns objects whose ``path`` shares the same parent as the given path (including the path itself if it exists). This is a shortcut for ``subpath(path, 0, -1) = subpath(sibling_path, 0, -1)``.

.. code-block:: pycon

    >>> Location.objects.filter(path__sibling_of='Europe.Spain')
    <QuerySet [<Location: Europe.Spain>, <Location: Europe.France>]>

    >>> Location.objects.filter(path__sibling_of='Asia.Japan.Tokyo')
    <QuerySet [<Location: Asia.Japan.Tokyo>]>


.. _ltree-containment-lookups:

Containment lookups
-------------------

These lookups are similar to the hierarchy lookups but *include* the path itself in the results if it matches. They correspond directly to the PostgreSQL ``@>`` and ``<@`` operators without the additional ``<>`` check used by ``ancestor_of`` and ``descendant_of``.

``contains``
~~~~~~~~~~~~

Returns objects whose ``path`` is an ancestor of *or the same as* the given path. Uses the ``@>`` operator directly.

.. code-block:: pycon

    >>> Location.objects.filter(path__contains='Europe.Spain')
    <QuerySet [<Location: Europe>, <Location: Europe.Spain>]>

    # Can also check against an array of paths
    >>> from django.contrib.postgres.fields import ArrayField
    >>> from django.db.models.functions import Cast
    >>> from django.db.models import Value
    >>> from django_ltree_field.fields import LTreeField
    >>> Location.objects.filter(
    ...     path__contains=Cast(Value(['Europe.Spain', 'Asia.Japan']), ArrayField(LTreeField()))
    ... )
    <QuerySet [<Location: Europe>, <Location: Europe.Spain>, <Location: Asia>, <Location: Asia.Japan>]>

``contained_by``
~~~~~~~~~~~~~~~~

Returns objects whose ``path`` is a descendant of *or the same as* the given path. Uses the ``<@`` operator directly.

.. code-block:: pycon

    >>> Location.objects.filter(path__contained_by='Europe.France')
    <QuerySet [<Location: Europe.France>, <Location: Europe.France.Paris>]>

    # Can also check against an array of paths
    >>> Location.objects.filter(
    ...     path__contained_by=Cast(Value(['Europe.Spain', 'Asia.Japan']), ArrayField(LTreeField()))
    ... )
    <QuerySet [<Location: Europe.Spain>, <Location: Europe.Spain.Madrid>, <Location: Asia.Japan>, <Location: Asia.Japan.Tokyo>]>


.. _ltree-pattern-matching-lookups:

Pattern matching lookups
------------------------

These lookups use PostgreSQL's ``ltree`` pattern matching capabilities.

``matches``
~~~~~~~~~~~

Returns objects where the ``path`` matches the given `lquery <https://www.postgresql.org/docs/current/ltree.html#LTREE-LQUERY>`_ pattern. Uses the ``~`` operator.

.. code-block:: pycon

    # Find paths with 'Europe' followed by exactly one label
    >>> Location.objects.filter(path__matches='Europe.*{1}')
    <QuerySet [<Location: Europe.Spain>, <Location: Europe.France>]>

    # Find paths under Europe or Asia ending in 'Madrid' or 'Tokyo'
    >>> Location.objects.filter(path__matches='{Europe,Asia}.*{Madrid,Tokyo}')
    <QuerySet [<Location: Europe.Spain.Madrid>, <Location: Asia.Japan.Tokyo>]>

    # Find paths under Europe that contain 'Paris' anywhere
    >>> Location.objects.filter(path__matches='Europe.*.Paris.*')
    <QuerySet [<Location: Europe.France.Paris>]>

``search``
~~~~~~~~~~

Returns objects where the ``path`` matches the given `ltxtquery <https://www.postgresql.org/docs/current/ltree.html#LTREE-LTXTQUERY>`_ full-text search query. Uses the ``@`` operator.

.. code-block:: pycon

    # Find paths containing 'Japan' but not 'Tokyo'
    >>> Location.objects.filter(path__search='Japan & !Tokyo')
    <QuerySet [<Location: Asia.Japan>]>

    # Find paths containing 'Europe' and either 'Spain' or 'France'
    >>> Location.objects.filter(path__search='Europe & (Spain | France)')
    <QuerySet [<Location: Europe.Spain>, <Location: Europe.Spain.Madrid>, <Location: Europe.France>, <Location: Europe.France.Paris>]>


.. _ltree-other-lookups:

Other lookups and transforms
----------------------------

``depth``
~~~~~~~~~

Can be used as a lookup to filter by the number of labels in the path, or as a transform to retrieve the depth. Uses the ``nlevel()`` function.

.. code-block:: pycon

    # Filter by depth
    >>> Location.objects.filter(path__depth=2)
    <QuerySet [<Location: Europe.Spain>, <Location: Europe.France>, <Location: Asia.Japan>]>

    # Get depth as a value
    >>> Location.objects.filter(path='Europe.Spain.Madrid').values('path__depth')
    <QuerySet [{'path__depth': 3}]>

.. _ltree-indexing-slicing:

Indexing and Slicing
~~~~~~~~~~~~~~~~~~~~

You can access specific labels or subpaths using index and slice notation directly in lookups or transforms. Uses ``subpath()`` and ``subltree()`` functions.

.. code-block:: pycon

    # Get the first label (index 0)
    >>> Location.objects.filter(path='Europe.Spain.Madrid').values('path__0')
    <QuerySet [{'path__0': 'Europe'}]>

    # Get labels from index 1 up to (but not including) index 3
    >>> Location.objects.filter(path='Europe.Spain.Madrid').values('path__1_3')
    <QuerySet [{'path__1_3': 'Spain.Madrid'}]>

    # Filter based on the second label (index 1)
    >>> Location.objects.filter(path__1='France')
    <QuerySet [<Location: Europe.France>]>