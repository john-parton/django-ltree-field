from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Literal, Self

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
        )

        self.save(update_fields=["path"])

    async def amove(
        self,
        position: RelativePositionType,
    ) -> None:
        self.path = await self.__class__.objects.amove_nodes(
            position,
        )

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

    # Similar to treebeard's API

    @classmethod
    def add_root(cls, **kwargs):
        """
        Create a root node.

        Parameters
        ----------
        **kwargs
            The keyword arguments to pass to the model's constructor.

        Returns
        -------
        Self
            The created root node.
        """
        return cls.objects.create(
            position=cls.position.root,
            **kwargs,
        )

    def add_child(self, **kwargs):
        """
        Create a child node.

        Parameters
        ----------
        **kwargs
            The keyword arguments to pass to the model's constructor.

        Returns
        -------
        Self
            The created child node.
        """
        return self.__class__.objects.create(
            position=self.position.last_child_of(self),
            **kwargs,
        )

    def add_sibling(self, pos: Literal["before", "after"], /, **kwargs) -> Self:
        """
        Create a sibling node.

        Parameters
        ----------
        pos : Literal["before", "after"]
            The position of the sibling node relative to this node.
            - "before": Before this node
            - "after": After this node
        **kwargs
            The keyword arguments to pass to the model's constructor.

        Returns
        -------
        Self
            The created sibling node.
        """

        return self.__class__.objects.create(
            position=(
                self.position.after(self)
                if pos == "after"
                else self.position.before(self)
            ),
            **kwargs,
        )
