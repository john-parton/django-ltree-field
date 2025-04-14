"""
Tests for django_ltree_field path insertion utilities.

This module tests the path insertion utilities used for managing the
insertion of new nodes in tree structures.
"""

from django.test import TestCase

from django_ltree_field.path_insertion import (
    range_excluding,
    rewrite_children_dense,
    rewrite_children_sparse,
)


class TestRangeExcluding(TestCase):
    """Tests for the range_excluding function."""

    def test_range_excluding_middle(self):
        """Test excluding a value in the middle of the range."""
        result = list(range_excluding(5, excluding=2))
        self.assertEqual(result, [0, 1, 3, 4])

    def test_range_excluding_start(self):
        """Test excluding the first value in the range."""
        result = list(range_excluding(5, excluding=0))
        self.assertEqual(result, [1, 2, 3, 4])

    def test_range_excluding_end(self):
        """Test excluding a value at the end of the range."""
        result = list(range_excluding(5, excluding=4))
        self.assertEqual(result, [0, 1, 2, 3])

    def test_range_excluding_beyond(self):
        """Test excluding a value beyond the range."""
        with self.assertRaises(ValueError) as context:
            list(range_excluding(5, excluding=5))

        self.assertIn("Excluding value must be less than stop", str(context.exception))

    def test_range_excluding_negative(self):
        """Test excluding a negative value."""
        with self.assertRaises(ValueError) as context:
            list(range_excluding(5, excluding=-1))

        self.assertIn("Excluding value must be non-negative", str(context.exception))


class TestRewriteChildrenDense(TestCase):
    """Tests for the rewrite_children_dense function."""

    def test_simple_case(self):
        """Test a simple case of rewriting children."""
        children = [0, 1, 2, 3]
        result = rewrite_children_dense(children, nth_child=1)

        self.assertEqual(result.new_child_index, 1)
        # Expected moves: [(0, 0), (2, 2), (3, 3)]
        self.assertEqual(len(result.moves), 3)
        self.assertIn((0, 0), result.moves)
        self.assertIn((2, 2), result.moves)
        self.assertIn((3, 3), result.moves)

    def test_insertion_at_beginning(self):
        """Test inserting at the beginning of the list."""
        children = [0, 1, 2, 3]
        result = rewrite_children_dense(children, nth_child=0)

        self.assertEqual(result.new_child_index, 0)
        # Expected moves: [(0, 1), (1, 2), (2, 3)]
        self.assertEqual(len(result.moves), 3)
        self.assertIn((0, 1), result.moves)
        self.assertIn((1, 2), result.moves)
        self.assertIn((2, 3), result.moves)

    def test_insertion_at_end(self):
        """Test inserting at the end of the list."""
        children = [0, 1, 2, 3]
        result = rewrite_children_dense(children, nth_child=4)

        self.assertEqual(result.new_child_index, 4)
        self.assertEqual(len(result.moves), 0)  # No moves needed

    def test_with_sparse_children(self):
        """Test with non-contiguous children indices."""
        children = [0, 2, 5, 10]
        result = rewrite_children_dense(children, nth_child=2)

        self.assertEqual(result.new_child_index, 2)
        # Expected moves: [(0, 0), (5, 3), (10, 4)]
        self.assertEqual(len(result.moves), 3)
        self.assertIn((0, 0), result.moves)
        self.assertIn((5, 3), result.moves)
        self.assertIn((10, 4), result.moves)

    def test_negative_nth_child(self):
        """Test with a negative nth_child value."""
        children = [0, 1, 2, 3]

        with self.assertRaises(AssertionError) as context:
            rewrite_children_dense(children, nth_child=-1)

        self.assertIn(
            "nth_child must be greater than or equal to 0", str(context.exception)
        )


class TestRewriteChildrenSparse(TestCase):
    """Tests for the rewrite_children_sparse function."""

    def test_simple_case(self):
        """Test a simple case of sparse rewriting."""
        children = [0, 20, 40, 60]
        result = rewrite_children_sparse(children, nth_child=2, max_value=100)

        self.assertEqual(result.new_child_index, 40)
        # With 5 children (4 existing + 1 new) and max_value=100, step should be 20
        # Resulting in positions 0, 20, 40(new), 60, 80
        # So moves would be [(0, 0), (20, 20), (60, 60)]
        self.assertEqual(len(result.moves), 3)
        self.assertIn((0, 0), result.moves)
        self.assertIn((20, 20), result.moves)
        self.assertIn((60, 60), result.moves)

    def test_with_centering(self):
        """Test sparse rewriting with centering of values."""
        children = [10, 20, 30, 40]
        result = rewrite_children_sparse(children, nth_child=2, max_value=100)

        # With 5 children (4 existing + 1 new) and max_value=100, step should be 20
        # Centered positions would be around 10, 30, 50(new), 70, 90
        self.assertEqual(result.new_child_index, 50)

        # Moves would be calculated to center the distribution
        self.assertEqual(len(result.moves), 4)

    def test_nth_child_out_of_range(self):
        """Test with nth_child greater than max_value."""
        children = [0, 20, 40, 60]

        with self.assertRaises(AssertionError) as context:
            rewrite_children_sparse(children, nth_child=101, max_value=100)

        self.assertIn(
            "nth_child must be less than or equal to max_value", str(context.exception)
        )

    def test_negative_nth_child(self):
        """Test with negative nth_child value."""
        children = [0, 20, 40, 60]

        with self.assertRaises(AssertionError) as context:
            rewrite_children_sparse(children, nth_child=-1, max_value=100)

        self.assertIn(
            "nth_child must be greater than or equal to 0", str(context.exception)
        )

    def test_too_many_children(self):
        """Test with too many children to fit in available space."""
        children = list(range(100))  # 100 children

        with self.assertRaises(AssertionError) as context:
            rewrite_children_sparse(
                children, nth_child=50, max_value=50
            )  # Not enough space

        self.assertIn(
            "Too many children to fit in the available space", str(context.exception)
        )
