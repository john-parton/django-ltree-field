============
Installation
============

At the command line::

    $ pip install django-ltree-field


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
