from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Self

from django.contrib.postgres.indexes import GistIndex
from django.db import models

from django_ltree_field.fields import LTreeField

from .managers import AutoNodeManager
from .position import RelativePosition, RelativePositionType

if TYPE_CHECKING:
    from django.db.models import QuerySet


class AbstractAutoNode(models.Model):
    path = LTreeField(triggers=LTreeField.CASCADE, null=False)

    position = RelativePosition
    objects = AutoNodeManager()

    class Meta:
        abstract = True
        indexes: ClassVar = [
            GistIndex(
                fields=("path",),
                name="%(app_label)s_%(class)s__path_idx",
            ),
        ]
        ordering: ClassVar = ["path"]

    def move(
        self,
        position: RelativePositionType,
    ) -> None:
        self.path = self.__class__.objects.move_nodes(
            position,
        )[0]

        self.save(update_fields=["path"])

    async def amove(
        self,
        position: RelativePositionType,
    ) -> None:
        self.path = (
            await self.__class__.objects.amove_nodes(
                position,
            )
        )[0]

        await self.asave(update_fields=["path"])

    def parent(self) -> QuerySet[Self]:
        """
        Get the parent of this node.

        Returns
        -------
        QuerySet[Self]
            A queryset of the parent node.
        """
        return self.__class__.objects.filter(
            path__parent_of=self.path,
        )

    def children(self) -> QuerySet[Self]:
        """
        Get the children of this node.

        Returns
        -------
        QuerySet[Self]
            A queryset of child nodes.
        """
        return self.__class__.objects.filter(
            path__child_of=self.path,
        )

    def descendants(self) -> QuerySet[Self]:
        """
        Get the descendants of this node.

        Returns
        -------
        QuerySet[Self]
            A queryset of descendant nodes.
        """
        return self.__class__.objects.filter(
            path__descendant_of=self.path,
        )
