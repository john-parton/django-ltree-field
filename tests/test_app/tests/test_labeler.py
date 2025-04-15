"""
Tests for django_ltree_field labeler module.

This module tests the Labeler class which is used for generating fixed-width
lexicographical labels for collections of items.
"""

from django.test import TestCase

from django_ltree_field.labeler import Labeler


class TestLabeler(TestCase):
    """Tests for the Labeler class."""

    def test_init(self):
        """Test initialization with various alphabets."""
        # Test with numeric alphabet
        labeler = Labeler("0123456789")
        self.assertEqual(labeler.alphabet, "0123456789")

        # Test with alphabetic alphabet
        labeler = Labeler("abc")
        self.assertEqual(labeler.alphabet, "abc")

        # Test with custom alphabet
        labeler = Labeler("xyz_-")
        self.assertEqual(labeler.alphabet, "xyz_-")

    def test_label_empty_items(self):
        """Test labeling an empty collection."""
        labeler = Labeler("abc")
        result = list(labeler.label([]))
        self.assertEqual(result, [])

    def test_label_single_item(self):
        """Test labeling a single item."""
        labeler = Labeler("abc")
        items = ["item"]
        result = list(labeler.label(items))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "item")
        self.assertEqual(result[0][0], "a")

    def test_label_multiple_items(self):
        """Test labeling multiple items with binary alphabet."""
        labeler = Labeler("01")
        items = ["item1", "item2", "item3", "item4"]

        # With 4 items and alphabet size 2, we need at least 2 characters
        # Log base 2 of 4 = 2, so width = 2
        result = list(labeler.label(items))

        self.assertEqual(len(result), 4)
        labels = [r[0] for r in result]
        self.assertEqual(labels, ["00", "01", "10", "11"])

        items_result = [r[1] for r in result]
        self.assertEqual(items_result, ["item1", "item2", "item3", "item4"])

    def test_label_width_calculation(self):
        """Test that label width is calculated correctly for different alphabet sizes."""
        # For alphabet size 2 and 7 items, we need ceil(log_2(7)) = 3 width
        labeler = Labeler("01")
        items = list(range(7))
        result = list(labeler.label(items))
        self.assertEqual(len(result[0][0]), 3)  # Width should be 3

        # For alphabet size 10 and 100 items, we need ceil(log_10(100)) = 2 width
        labeler = Labeler("0123456789")
        items = list(range(100))
        result = list(labeler.label(items))
        self.assertEqual(len(result[0][0]), 2)  # Width should be 2

        # For alphabet size 26 and 500 items, we need ceil(log_26(500)) = 2 width
        labeler = Labeler("abcdefghijklmnopqrstuvwxyz")
        items = list(range(500))
        result = list(labeler.label(items))
        self.assertEqual(len(result[0][0]), 2)  # Width should be 2

    def test_label_order_preservation(self):
        """Test that the order of items is preserved in the labeling."""
        labeler = Labeler("abc")
        items = ["apple", "banana", "cherry", "date"]
        result = list(labeler.label(items))

        # Labels should be in order: "a", "b", "c", "aa", ...
        # But only as many as needed for the items
        labels = [r[0] for r in result]
        items_result = [r[1] for r in result]

        # Check that the items are in the original order
        self.assertEqual(items_result, items)

        # Check that labels are in increasing lexicographic order
        self.assertEqual(labels, sorted(labels))

    def test_iter_method(self):
        """Test the _iter method directly for correct lexicographic ordering."""
        labeler = Labeler("abc")

        # With width 1, should get ["a", "b", "c"]
        result = list(labeler._iter(width=1))
        self.assertEqual(result, ["a", "b", "c"])

        # With width 2, should get ["aa", "ab", "ac", "ba", "bb", "bc", "ca", "cb", "cc"]
        result = list(labeler._iter(width=2))
        self.assertEqual(result, ["aa", "ab", "ac", "ba", "bb", "bc", "ca", "cb", "cc"])

    def test_tuple_returned(self):
        """Test that label() returns tuples of (label, item)."""
        labeler = Labeler("abc")
        items = ["item1", "item2", "item3"]
        for pair in labeler.label(items):
            self.assertIsInstance(pair, tuple)
            self.assertEqual(len(pair), 2)
            self.assertIsInstance(pair[0], str)  # label
            self.assertIsInstance(pair[1], str)  # original item
