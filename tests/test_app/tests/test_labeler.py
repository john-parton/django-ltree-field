"""
Tests for django_ltree_field labeler module.

This module tests the Labeler class which is used for generating fixed-width
lexicographical labels for collections of items.
"""

import itertools as it
import unittest
from typing import Any, Never

from django_ltree_field.labeler import Labeler


class TestLabeler(unittest.TestCase):
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
        # Test with Unicode characters
        unicode_alphabet = "あいうえお"
        labeler = Labeler(unicode_alphabet)
        self.assertEqual(labeler.alphabet, unicode_alphabet)

        # Test with duplicate characters in alphabet
        with self.assertRaises(ValueError) as context:
            Labeler("aabbc")

        self.assertEqual(
            str(context.exception), "Alphabet must contain unique characters."
        )

    def test_label_empty_items(self):
        """Test labeling an empty collection."""
        labeler = Labeler("abc")
        items: list[Never] = []
        result = list(labeler.label(items))
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

        with self.assertRaises(TypeError) as context:
            list(labeler.label(42))  # pyright: ignore[reportArgumentType, reportUnknownArgumentType]

        self.assertEqual(str(context.exception), "Expected Collection, got int")

    def test_width_calculation(self):
        """Test that the correct label width is calculated based on items count and alphabet size."""
        # Test with binary alphabet
        labeler = Labeler("01")

        # 2 items with alphabet size 2 need width=1
        items = ["item1", "item2"]
        result = list(labeler.label(items))
        self.assertEqual(len(result[0][0]), 1)  # Width should be 1

        # 5 items with alphabet size 2 need width=3
        # log_2(5) = 2.32, ceil(2.32) = 3
        items = ["item1", "item2", "item3", "item4", "item5"]
        result = list(labeler.label(items))
        self.assertEqual(len(result[0][0]), 3)  # Width should be 3

        # Test with larger alphabet
        labeler = Labeler("abcdefghij")  # Size 10 alphabet

        # 100 items with alphabet size 10 need width=2
        # log_10(100) = 2, ceil(2) = 2
        items = [f"item{i}" for i in range(100)]
        result = list(labeler.label(items))
        self.assertEqual(len(result[0][0]), 2)  # Width should be 2

    def test_different_item_types(self):
        """Test labeling with different item types."""
        labeler = Labeler("abc")

        # Test with a mix of item types
        items: list[Any] = [42, "string", True, 3.14, None, [1, 2, 3]]
        result = list(labeler.label(items))

        self.assertEqual(len(result), 6)

        # Verify items are preserved in result
        items_result = [r[1] for r in result]
        self.assertEqual(items_result, items)

        # The width is calculated based on the number of items.
        # For 6 items with alphabet size 3, we need ceil(log_3(6)) = 2 characters
        label_width = max(len(label) for label, _ in result)
        self.assertEqual(label_width, 2)

    def test_exact_power_items(self):
        """Test with exact power of alphabet size items to verify width calculations."""
        labeler = Labeler("01")  # Binary alphabet

        # 8 items with binary alphabet (2^3) should produce width=3 labels
        items = [f"item{i}" for i in range(8)]
        result = list(labeler.label(items))

        # Verify all labels have width 3
        for label, _ in result:
            self.assertEqual(len(label), 3)

        # Check all possible 3-digit binary combinations are included
        labels = [r[0] for r in result]
        expected_labels = ["000", "001", "010", "011", "100", "101", "110", "111"]
        self.assertEqual(sorted(labels), expected_labels)

    def test_width_minimum_one(self):
        """Test that width is at least 1 even when mathematically it could be 0."""
        # With alphabet size 10 and only 1 item, log_10(1) = 0,
        # but the implementation should use width=1 as minimum
        labeler = Labeler("0123456789")
        items = ["single_item"]
        result = list(labeler.label(items))
        self.assertEqual(len(result[0][0]), 1)  # Width should be at least 1

    def test_very_large_item_count(self):
        """Test width calculation with a large number of items."""
        # This test validates the width calculation formula with a large collection
        # Without generating all the labels (which would be inefficient)
        labeler = Labeler("01")  # Binary alphabet

        # Create a collection large enough to require a width of exactly 20
        items_count = 2**20

        # Create a list-like object with __len__ but without generating all items
        class SizedIterable:
            def __init__(self, size):
                self.size = size

            def __contains__(self, item):
                return item is None

            def __len__(self):
                return self.size

            def __iter__(self):
                # We won't be iterating through all items, just checking the label width
                return iter([None] * min(10, self.size))

        items = SizedIterable(items_count)

        # Get just the first few labels to check the width
        result = list(it.islice(labeler.label(items), 5))

        # Check that the width is correct (should be 20 for > 2^19 items with binary alphabet)
        self.assertEqual(len(result[0][0]), 20)

    def test_error_messages_short_alphabet(self):
        """Test that an appropriate error message is raised for short alphabets."""
        with self.assertRaises(ValueError) as context:
            Labeler("")

        self.assertEqual(
            str(context.exception), "Alphabet must contain at least 2 characters."
        )

        with self.assertRaises(ValueError) as context:
            Labeler("a")

        self.assertEqual(
            str(context.exception), "Alphabet must contain at least 2 characters."
        )

    def test_non_collection_error_message(self):
        """Test specific error message for non-collection input."""
        labeler = Labeler("abc")

        # Test with various non-collection types
        non_collections = [
            42,  # int
            3.14,  # float
            True,  # bool
            lambda x: x,  # function
        ]

        for item in non_collections:
            with self.assertRaises(TypeError) as context:
                list(labeler.label(item))  # pyright: ignore[reportArgumentType]

            expected_msg = f"Expected Collection, got {type(item).__name__}"
            self.assertEqual(str(context.exception), expected_msg)

    def test_parametrized_width_calculation(self):
        """Test width calculation with different alphabet sizes and item counts."""
        test_cases = [
            # (alphabet, num_items, expected_width)
            ("01", 1, 1),  # Minimum width is 1
            ("01", 2, 1),  # log_2(2) = 1
            ("01", 3, 2),  # log_2(3) ≈ 1.58, ceil = 2
            ("01", 4, 2),  # log_2(4) = 2
            ("01", 5, 3),  # log_2(5) ≈ 2.32, ceil = 3
            ("0123", 5, 2),  # log_4(5) ≈ 1.16, ceil = 2
            ("0123", 16, 2),  # log_4(16) = 2
            ("0123", 17, 3),  # log_4(17) ≈ 2.04, ceil = 3
            ("0123456789", 10, 1),  # log_10(10) = 1
            ("0123456789", 11, 2),  # log_10(11) ≈ 1.04, ceil = 2
        ]

        for alphabet, num_items, expected_width in test_cases:
            with self.subTest(alphabet=alphabet, num_items=num_items):
                labeler = Labeler(alphabet)
                items = list(range(num_items))
                result = list(labeler.label(items))

                if result:  # If any results were produced
                    actual_width = len(result[0][0])
                    self.assertEqual(
                        actual_width,
                        expected_width,
                        f"For alphabet size {len(alphabet)} and {num_items} items, "
                        f"expected width {expected_width} but got {actual_width}",
                    )
