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

    def test_edge_case_alphabets(self):
        """Test initialization with edge case alphabets."""
        # Test with single character alphabet
        labeler = Labeler("a")
        self.assertEqual(labeler.alphabet, "a")

        # Test with empty alphabet
        # Note: Current implementation allows empty alphabet
        labeler = Labeler("")
        self.assertEqual(labeler.alphabet, "")

        # Test behavior of empty alphabet with labeling
        # This should not produce any labels (or raise an exception due to math.log with base 0)
        with self.assertRaises(Exception):
            result = list(labeler.label(["item"]))

        # Test with Unicode characters
        unicode_alphabet = "あいうえお"
        labeler = Labeler(unicode_alphabet)
        self.assertEqual(labeler.alphabet, unicode_alphabet)

        # Test with duplicate characters in alphabet
        # Note: This test depends on implementation details.
        # The current implementation doesn't deduplicate the alphabet.
        labeler = Labeler("aabbc")
        self.assertEqual(labeler.alphabet, "aabbc")

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

    def test_tuple_returned(self):
        """Test that label() returns tuples of (label, item)."""
        labeler = Labeler("abc")
        items = ["item1", "item2", "item3"]
        for pair in labeler.label(items):
            self.assertIsInstance(pair, tuple)
            self.assertEqual(len(pair), 2)
            self.assertIsInstance(pair[0], str)  # label
            self.assertIsInstance(pair[1], str)  # original item

    def test_error_handling_non_iterable(self):
        """Test error handling when non-iterable items are provided."""
        labeler = Labeler("abc")

        # TODO Implement this
