from django.db import models

from django_ltree_field.fields import LTreeField


# Test models
class SimpleNode(models.Model):
    path = LTreeField(db_index=True)

    class Meta:
        ordering = ['path']

    def __str__(self):
        return '.'.join(self.path)


class NullableNode(models.Model):
    path = LTreeField(null=True)

    class Meta:
        ordering = ['path']

    def __str__(self):
        if self.path is None:
            return 'NULL'
        return '.'.join(self.path)
