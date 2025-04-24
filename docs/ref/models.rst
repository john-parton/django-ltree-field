.. _abstract-auto-node:

====================
AbstractAutoNode
====================

``django_ltree_field.models.AbstractAutoNode`` provides an abstract base class
for models that require automatic management of their hierarchical position
using an ``LTreeField``. It simplifies common tree operations like creating nodes,
moving nodes, and querying relationships.

Subclassing ``AbstractAutoNode``
--------------------------------

To use ``AbstractAutoNode``, simply inherit from it in your model definition.
You must define any additional fields your model requires.

.. code-block:: python

    from django.db import models
    from django_ltree_field.models import AbstractAutoNode

    class Category(AbstractAutoNode):
        name = models.CharField(max_length=50)
        # Add any other fields specific to your category model

        class Meta(AbstractAutoNode.Meta):
            # Optional: Add specific meta options for your model
            verbose_name = "Category"
            verbose_name_plural = "Categories"

        def __str__(self):
            # Display the path and name for clarity
            # The number of leading spaces indicates the depth
            depth_indicator = ". " * (self.path.count('.') -1)
            return f"{depth_indicator}{self.name}"

Key Features and Usage
----------------------

*   **Automatic Path Management**: The ``path`` field (an ``LTreeField``) is automatically managed.
You don't typically set it directly.
*   **Custom Manager**: It uses ``AutoNodeManager`` (available as ``objects``) which provides
    methods for creating and manipulating the tree structure.
*   **Positioning**: Nodes are created relative to other nodes using the ``position`` attribute,
    which provides options like ``root``, ``first_child_of(target)``, ``last_child_of(target)``,
    ``left_sibling_of(target)``, and ``right_sibling_of(target)``.

Creating Nodes
~~~~~~~~~~~~~~

The primary way to create nodes is using the ``create_tree`` method on the manager.
This method can create a single node or an entire tree structure from a nested dictionary.

.. code-block:: pycon

    >>> from myapp.models import Category

    # Create a root node
    >>> root = Category.objects.create_tree({'name': 'Electronics'})
    >>> print(root)
    Electronics

    # Create a child node
    >>> tv = Category.objects.create_tree(
    ...     {'name': 'Televisions'},
    ...     position=Category.position.first_child_of(root)
    ... )
    >>> print(tv)
    . Televisions

    # Create a nested tree structure
    >>> Category.objects.create_tree({
    ...     'name': 'Clothing',
    ...     'children': [
    ...         {'name': 'Mens'},
    ...         {'name': 'Womens', 'children': [{'name': 'Dresses'}]},
    ...     ]
    ... })

Querying Relationships
~~~~~~~~~~~~~~~~~~~~~~

Instance methods are provided for easy querying of common hierarchical relationships:

.. code-block:: pycon

    >>> electronics = Category.objects.get(name='Electronics')
    >>> tv = Category.objects.get(name='Televisions')

    # Get parent
    >>> tv.parent().first()
    <Category: Electronics>

    # Get children
    >>> electronics.children()
    <QuerySet [<Category: . Televisions>]>

    # Get all descendants
    >>> clothing = Category.objects.get(name='Clothing')
    >>> clothing.descendants()
    <QuerySet [<Category: . Mens>, <Category: . Womens>, <Category: . . Dresses>]>

Moving Nodes
~~~~~~~~~~~~

Nodes can be moved within the tree using the ``move()`` instance method (or ``amove()`` for async).
This automatically updates the ``path`` of the node and all its descendants.

.. code-block:: pycon

    >>> mens = Category.objects.get(name='Mens')
    >>> womens = Category.objects.get(name='Womens')

    # Move 'Mens' to be the right sibling of 'Womens'
    >>> mens.move(Category.position.right_sibling_of(womens))
    >>> print(mens)
    . Mens

    # Verify new order (assuming default path ordering)
    >>> clothing = Category.objects.get(name='Clothing')
    >>> list(clothing.children().values_list('name', flat=True))
    ['Womens', 'Mens']

Common Patterns
---------------

*   **Building Navigation Menus**: Query children or descendants to build dynamic menus.
*   **Category Trees**: Represent product categories, organizational structures, etc.
*   **Breadcrumbs**: Use ``ancestor_of`` or iterate through parents to generate breadcrumb trails.
*   **Access Control**: Check if a user's access path is an ancestor of a resource path.
