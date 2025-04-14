"""
Tests for django_ltree_field position utilities.

This module tests the position utilities used for managing
the relative positioning of nodes in a tree structure.
"""

from django.test import TestCase

from django_ltree_field.position import RelativePosition, SortedPosition


# Simple mock class for path factory testing
class MockPathFactory:
    @staticmethod
    def split(path):
        """Split a path into parent and child index."""
        return path[:-1], len(path) - 1


class TestRelativePosition(TestCase):
    """Tests for the RelativePosition class."""

    def test_child_position_resolve(self):
        """Test resolving CHILD position."""
        kwargs = {"child_of": ["Top", "Collections"]}
        result, nth_child = RelativePosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertIsNone(nth_child)
        self.assertEqual(kwargs, {})  # kwargs should be modified

    def test_last_child_position_resolve(self):
        """Test resolving LAST_CHILD position."""
        kwargs = {"last_child_of": ["Top", "Collections"]}
        result, nth_child = RelativePosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertIsNone(nth_child)
        self.assertEqual(kwargs, {})

    def test_first_child_position_resolve(self):
        """Test resolving FIRST_CHILD position."""
        kwargs = {"first_child_of": ["Top", "Collections"]}
        result, nth_child = RelativePosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertEqual(nth_child, 0)
        self.assertEqual(kwargs, {})

    def test_before_position_resolve(self):
        """Test resolving BEFORE position."""
        kwargs = {"before": ["Top", "Collections", "Pictures"]}
        result, nth_child = RelativePosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertEqual(nth_child, 2)  # Index of "Pictures" in the parent
        self.assertEqual(kwargs, {})

    def test_after_position_resolve(self):
        """Test resolving AFTER position."""
        kwargs = {"after": ["Top", "Collections", "Pictures"]}
        result, nth_child = RelativePosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertEqual(nth_child, 3)  # Index after "Pictures" in the parent
        self.assertEqual(kwargs, {})

    def test_root_position_resolve(self):
        """Test resolving ROOT position."""
        kwargs = {"root": True}
        result, nth_child = RelativePosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, [])
        self.assertIsNone(nth_child)
        self.assertEqual(kwargs, {})

    def test_root_position_invalid_value(self):
        """Test resolving ROOT position with invalid value."""
        kwargs = {"root": "not_true"}

        with self.assertRaises(ValueError) as context:
            RelativePosition.resolve(
                kwargs, path_field="path", path_factory=MockPathFactory()
            )

        self.assertIn("Expected kwarg root=True", str(context.exception))

    def test_no_position_specified(self):
        """Test when no position is specified."""
        kwargs = {"some_other_param": "value"}

        with self.assertRaises(TypeError) as context:
            RelativePosition.resolve(
                kwargs, path_field="path", path_factory=MockPathFactory()
            )

        self.assertIn("Could not resolve position", str(context.exception))

    def test_multiple_positions_specified(self):
        """Test when multiple positions are specified."""
        kwargs = {"child_of": ["Top"], "before": ["Top", "Collections"]}

        with self.assertRaises(TypeError) as context:
            RelativePosition.resolve(
                kwargs, path_field="path", path_factory=MockPathFactory()
            )

        self.assertIn("Could not resolve position", str(context.exception))

    def test_model_instance_path(self):
        """Test with a model instance that has a path attribute."""

        class MockModel:
            path = ["Top", "Collections"]

        kwargs = {"child_of": MockModel()}
        result, nth_child = RelativePosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertIsNone(nth_child)

    def test_string_path(self):
        """Test with a string path that needs to be split."""
        kwargs = {"child_of": "Top.Collections"}
        result, nth_child = RelativePosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertIsNone(nth_child)

    def test_invalid_path_type(self):
        """Test with an invalid path type."""
        kwargs = {"child_of": 123}  # Not a tuple, list, or string

        with self.assertRaises(TypeError) as context:
            RelativePosition.resolve(
                kwargs, path_field="path", path_factory=MockPathFactory()
            )

        self.assertIn("Expected tuple", str(context.exception))


class TestSortedPosition(TestCase):
    """Tests for the SortedPosition class."""

    def test_child_position_resolve(self):
        """Test resolving CHILD position."""
        kwargs = {"child_of": ["Top", "Collections"]}
        result, nth_child = SortedPosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertIsNone(nth_child)
        self.assertEqual(kwargs, {})

    def test_sibling_position_resolve(self):
        """Test resolving SIBLING position."""
        kwargs = {"sibling": ["Top", "Collections", "Pictures"]}
        result, nth_child = SortedPosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertIsNone(nth_child)
        self.assertEqual(kwargs, {})

    def test_root_position_resolve(self):
        """Test resolving ROOT position."""
        kwargs = {"root": True}
        result, nth_child = SortedPosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, [])
        self.assertIsNone(nth_child)
        self.assertEqual(kwargs, {})

    def test_root_position_invalid_value(self):
        """Test resolving ROOT position with invalid value."""
        kwargs = {"root": "not_true"}

        with self.assertRaises(ValueError) as context:
            SortedPosition.resolve(
                kwargs, path_field="path", path_factory=MockPathFactory()
            )

        self.assertIn("Expected kwarg root=True", str(context.exception))

    def test_no_position_specified(self):
        """Test when no position is specified."""
        kwargs = {"some_other_param": "value"}

        with self.assertRaises(TypeError) as context:
            SortedPosition.resolve(
                kwargs, path_field="path", path_factory=MockPathFactory()
            )

        self.assertIn("Could not resolve position", str(context.exception))

    def test_multiple_positions_specified(self):
        """Test when multiple positions are specified."""
        kwargs = {"child_of": ["Top"], "sibling": ["Top", "Collections"]}

        with self.assertRaises(TypeError) as context:
            SortedPosition.resolve(
                kwargs, path_field="path", path_factory=MockPathFactory()
            )

        self.assertIn("Could not resolve position", str(context.exception))

    def test_model_instance_path(self):
        """Test with a model instance that has a path attribute."""

        class MockModel:
            path = ["Top", "Collections"]

        kwargs = {"child_of": MockModel()}
        result, nth_child = SortedPosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertIsNone(nth_child)

    def test_string_path(self):
        """Test with a string path that needs to be split."""
        kwargs = {"child_of": "Top.Collections"}
        result, nth_child = SortedPosition.resolve(
            kwargs, path_field="path", path_factory=MockPathFactory()
        )

        self.assertEqual(result, ["Top", "Collections"])
        self.assertIsNone(nth_child)
