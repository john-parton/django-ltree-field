=====
Usage
=====

To use PostgreSQL LTreeField for Django in a project, add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'django_ltree_field.apps.DjangoLtreePy36Config',
        ...
    )

Add PostgreSQL LTreeField for Django's URL patterns:

.. code-block:: python

    from django_ltree_field import urls as django_ltree_field_urls


    urlpatterns = [
        ...
        url(r'^', include(django_ltree_field_urls)),
        ...
    ]
