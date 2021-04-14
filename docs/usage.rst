==========
Background
==========

It is highly recommend that you familiarize yourself with
`the PostgreSQL documentation for the ltree type <https://www.postgresql.org/docs/current/ltree.html>`_.

The features correspond closely to the PostgreSQL behavior.

The PostgreSQL ltree type implements the "materialized path" pattern for storing "trees" or hierarchical labels. A "path" is a
dotted sequence of labels. From the PostgreSQL docs:

    A label is a sequence of alphanumeric characters and underscores (for example, in C locale the characters
    A-Za-z0-9\_ are allowed). Labels must be less than 256 characters long.

    A label path is a sequence of zero or more labels separated by dots, for example L1.L2.L3, representing a path from the
    root of a hierarchical tree to a particular node. The length of a label path cannot exceed 65535 labels.

In Python, a label is a simple string, and a label path is represented as a list of strings. To manipulate a path in Python,
use the standard list and string methods.


========
Examples
========

Examples will assume you have a model named `SimpleNode` with a `path` attribute configured like so:

.. code-block:: python

    from django_ltree_field.fields import LTreeField

    class SimpleNode(models.Model):
        path = LTreeField(index=True, unique=True)

        class Meta:
            ordering = ['path']


Create a a bunch of nodes

.. code-block:: python

    PATHS = [
        'Top', 'Top.Science', 'Top.Science.Astronomy', 'Top.Science.Astronomy.Astrophysics',
        'Top.Science.Astronomy.Cosmology', 'Top.Hobbies', 'Top.Hobbies.Amateurs_Astronomy',
        'Top.Collections', 'Top.Collections.Pictures', 'Top.Collections.Pictures.Astronomy',
        'Top.Collections.Pictures.Astronomy.Stars', 'Top.Collections.Pictures.Astronomy.Galaxies',
        'Top.Collections.Pictures.Astronomy.Astronauts'
    ]

    SimpleNode.objects.bulk_create(
        SimpleNode(path=path) for path in PATHS
    )

Now, we have a model populated with data describing the hierarchy shown below::

                            Top
                         /   |  \
                 Science Hobbies Collections
                     /       |              \
            Astronomy   Amateurs_Astronomy Pictures
               /  \                            |
    Astrophysics  Cosmology                Astronomy
                                            /  |    \
                                     Galaxies Stars Astronauts
