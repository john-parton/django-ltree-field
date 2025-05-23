from typing import ClassVar

from django.contrib.postgres.indexes import GistIndex
from django.db import models

from django_ltree_field.fields import LTreeField
from django_ltree_field.models import AbstractAutoNode


# Test models
class SimpleNode(models.Model):
    path = LTreeField(unique=True)

    class Meta:
        indexes: ClassVar = [
            GistIndex(
                fields=("path",),
                opclasses=("gist_ltree_ops(siglen=100)",),
                name="simple_node_path_idx",
            ),
        ]
        ordering: ClassVar = ["path"]

    def __str__(self):
        return ".".join(self.path)


class NullableNode(models.Model):
    path = LTreeField(null=True, unique=True)

    class Meta:
        indexes: ClassVar = [
            GistIndex(
                fields=("path",),
                name="nullable_node_path_idx",
            ),
        ]
        ordering: ClassVar = ["path"]

    def __str__(self):
        if self.path is None:
            return "NULL"
        return ".".join(self.path)


class ProtectedNode(models.Model):
    path = LTreeField(triggers=LTreeField.PROTECT, unique=True)

    class Meta:
        indexes: ClassVar = [
            GistIndex(
                fields=("path",),
                name="protected_node_path_idx",
            ),
        ]
        ordering: ClassVar = ["path"]

    def __str__(self):
        return ".".join(self.path)


class AutoNode(AbstractAutoNode):
    name = models.CharField(max_length=255)
