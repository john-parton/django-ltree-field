"""
Tests for django_ltree_field functions module.

This module specifically tests the PostgreSQL ltree functions provided
by django_ltree_field to ensure they work correctly.
"""

from django.contrib.postgres.fields import ArrayField
from django.db.models import Value
from django.test import TestCase

from django_ltree_field.fields import LTreeField
from django_ltree_field.functions import (
    LCA,
    Concat,
    Index,
    NLevel,
    SubLTree,
    Subpath,
)
from tests.test_app.models import SimpleNode


class TestLTreeFunctions(TestCase):
    """Tests for the PostgreSQL ltree functions."""

    def setUp(self):
        """Set up test data with a variety of ltree paths."""
        SimpleNode.objects.bulk_create(
            SimpleNode(path=path)
            for path in [
                "Top",
                "Top.Collections",
                "Top.Collections.Pictures",
                "Top.Collections.Pictures.Astronomy",
                "Top.Collections.Pictures.Astronomy.Stars",
                "Top.Collections.Pictures.Astronomy.Galaxies",
                "Top.Hobbies",
                "Top.Science",
                "Top.Science.Astronomy",
                "Top.Science.Astronomy.Astrophysics",
            ]
        )

    def test_subltree_function(self):
        """Test the SubLTree function that extracts a subpath from an ltree."""
        # Get subpath from position 1 to 3 of path "Top.Collections.Pictures.Astronomy"
        result = (
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            )
            .annotate(
                sub_path=SubLTree("path", Value(1), Value(3)),
            )
            .values_list("sub_path", flat=True)
            .first()
        )

        self.assertEqual(result, "Collections.Pictures")

        # Test with a different path
        result = (
            SimpleNode.objects.filter(
                path="Top.Science.Astronomy.Astrophysics",
            )
            .annotate(
                sub_path=SubLTree("path", Value(0), Value(2)),
            )
            .values_list("sub_path", flat=True)
            .first()
        )

        self.assertEqual(result, "Top.Science")

    def test_subpath_function_two_args(self):
        """Test the Subpath function with two arguments (offset to end)."""
        # Get subpath starting at position 2 to the end of the path
        result = (
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            )
            .annotate(
                sub_path=Subpath("path", Value(2)),
            )
            .values_list("sub_path", flat=True)
            .first()
        )

        self.assertEqual(result, "Pictures.Astronomy")

        # Test with negative offset (from end)
        result = (
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            )
            .annotate(
                sub_path=Subpath("path", Value(-2)),
            )
            .values_list("sub_path", flat=True)
            .first()
        )

        self.assertEqual(result, "Pictures.Astronomy")

    def test_subpath_function_three_args(self):
        """Test the Subpath function with three arguments (offset, length)."""
        # Get subpath starting at position 1 with length 2
        result = (
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            )
            .annotate(
                sub_path=Subpath(
                    "path",
                    Value(1),
                    Value(2),
                )
            )
            .values_list("sub_path", flat=True)
            .first()
        )

        self.assertEqual(result, "Collections.Pictures")

        # Test with negative length (leave off from end)
        result = (
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            )
            .annotate(
                sub_path=Subpath(
                    "path",
                    Value(0),
                    Value(-1),
                )
            )
            .values_list("sub_path", flat=True)
            .first()
        )

        self.assertEqual(result, "Top.Collections.Pictures")

    def test_subpath_validation(self):
        """Test that Subpath function validates argument count correctly."""
        with self.assertRaises(ValueError) as context:
            Subpath("path")

        self.assertIn("Subpath takes 2 or 3 arguments", str(context.exception))

        with self.assertRaises(ValueError) as context:
            Subpath("path", Value(1), Value(2), Value(3))

        self.assertIn("Subpath takes 2 or 3 arguments", str(context.exception))

    def test_nlevel_function(self):
        """Test the NLevel function that returns the number of labels in a path."""
        results = (
            SimpleNode.objects.filter(
                path__in=[
                    "Top",
                    "Top.Collections",
                    "Top.Collections.Pictures.Astronomy",
                ]
            )
            .annotate(depth=NLevel("path"))
            .values_list("path", "depth")
            .order_by("path")
        )

        expected = [
            ("Top", 1),
            ("Top.Collections", 2),
            ("Top.Collections.Pictures.Astronomy", 4),
        ]
        self.assertSequenceEqual(results, expected)

    def test_index_function_two_args(self):
        """Test the Index function that returns the position of a label in a path."""
        # Find "Pictures" in "Top.Collections.Pictures.Astronomy"
        result = (
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            )
            .annotate(
                idx=Index("path", Value("Pictures")),
            )
            .values_list("idx", flat=True)
            .first()
        )

        self.assertEqual(result, 2)  # 0-indexed

        # Test when label doesn't exist
        result = (
            SimpleNode.objects.filter(path="Top.Collections.Pictures")
            .annotate(idx=Index("path", Value("NonExistent")))
            .values_list("idx", flat=True)
            .first()
        )

        self.assertEqual(result, -1)  # -1 when not found

    def test_index_function_three_args(self):
        """Test Index function with three args (path, label, offset)."""
        # Find "Astronomy" in "Top.Collections.Pictures.Astronomy" starting after index 1
        result = (
            SimpleNode.objects.filter(path="Top.Collections.Pictures.Astronomy")
            .annotate(idx=Index("path", Value("Astronomy"), Value(2)))
            .values_list("idx", flat=True)
            .first()
        )

        self.assertEqual(result, 3)  # 0-indexed

        # Test when starting after the label position
        result = (
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            )
            .annotate(
                idx=Index("path", Value("Collections"), Value(2)),
            )
            .values_list("idx", flat=True)
            .first()
        )

        self.assertEqual(result, -1)  # -1 when not found

    def test_index_validation(self):
        """Test that Index function validates argument count correctly."""
        with self.assertRaises(ValueError) as context:
            Index("path")

        self.assertIn("Index takes 2 or 3 arguments", str(context.exception))

        with self.assertRaises(ValueError) as context:
            Index("path", Value("label"), Value(1), Value(2))

        self.assertIn("Index takes 2 or 3 arguments", str(context.exception))

    def test_lca_function(self):
        """Test the LCA (Lowest Common Ancestor) function."""
        # Test with two explicit paths
        nodes = list(
            SimpleNode.objects.filter(
                path__in=[
                    "Top.Collections.Pictures.Astronomy.Stars",
                    "Top.Science.Astronomy",
                ]
            ).values_list("path", flat=True)
        )

        # Get LCA using first path and direct value for second path
        result = (
            SimpleNode.objects.filter(path=nodes[0])
            .annotate(common_ancestor=LCA("path", Value(nodes[1])))
            .values_list("common_ancestor", flat=True)
            .first()
        )

        self.assertEqual(result, "Top")

        # Test with two sibling paths
        nodes = list(
            SimpleNode.objects.filter(
                path__in=[
                    "Top.Collections.Pictures.Astronomy.Stars",
                    "Top.Collections.Pictures.Astronomy.Galaxies",
                ]
            ).values_list("path", flat=True)
        )

        result = (
            SimpleNode.objects.filter(path=nodes[0])
            .annotate(common_ancestor=LCA("path", Value(nodes[1])))
            .values_list("common_ancestor", flat=True)
            .first()
        )

        self.assertEqual(result, "Top.Collections.Pictures.Astronomy")

    def test_lca_with_array(self):
        """Test the LCA function with array input."""
        # Get LCA of multiple paths using array input
        paths = [
            "Top.Collections.Pictures.Astronomy.Stars",
            "Top.Science.Astronomy.Astrophysics",
            "Top.Hobbies",
        ]

        # Using ArrayField to test array input
        from django.db.models.functions import Cast

        node = SimpleNode.objects.first()
        result = (
            SimpleNode.objects.filter(
                id=node.id  # Just need one record
            )
            .annotate(
                common_ancestor=LCA(
                    Cast(Value(paths), output_field=ArrayField(LTreeField()))
                )
            )
            .values_list("common_ancestor", flat=True)
            .first()
        )

        self.assertEqual(result, "Top")

    def test_lca_validation(self):
        """Test that LCA function validates argument count correctly."""
        with self.assertRaises(ValueError) as context:
            LCA()

        self.assertIn("LCA takes at least one argument", str(context.exception))

    def test_concat_function(self):
        """Test the Concat function that joins ltree paths."""
        # Concatenate two parts to form a new path
        result = (
            SimpleNode.objects.filter(path="Top.Collections")
            .annotate(new_path=Concat("path", Value("NewSection")))
            .values_list("new_path", flat=True)
            .first()
        )

        self.assertEqual(result, "Top.Collections.NewSection")

        # Concatenate multiple parts
        result = (
            SimpleNode.objects.filter(path="Top")
            .annotate(
                new_path=Concat("path", Value("New"), Value("Multi"), Value("Part"))
            )
            .values_list("new_path", flat=True)
            .first()
        )

        self.assertEqual(result, "Top.New.Multi.Part")

    def test_concat_validation(self):
        """Test that Concat function validates argument count correctly."""
        with self.assertRaises(ValueError) as context:
            Concat("path")

        self.assertIn("Concat takes at least 2 arguments", str(context.exception))

    def tearDown(self):
        SimpleNode.objects.all().delete()
