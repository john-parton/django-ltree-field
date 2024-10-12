from __future__ import annotations

import itertools as it

from django.test import TestCase

from django_ltree_field.integer_paths import default_codec, legacy_codec


class TestCode(TestCase):
    # Primarily important for migrations
    def test_codec_comparison(self):
        self.assertEqual(
            default_codec(),
            default_codec(),
        )
        self.assertNotEqual(
            default_codec(),
            legacy_codec(),
        )
        self.assertNotEqual(
            default_codec(length=5),
            default_codec(length=6),
        )

    def test_codec_bijection(self):
        # This test just exhaustively checks that the codec is a bijection.
        # Length is limited to 3, because even with a short length max_value is 262143
        # and 250046.
        codecs = [
            default_codec(length=3),
            legacy_codec(length=3),
        ]

        for codec in codecs:
            with self.subTest(codec=codec):
                for i in range(codec.max_value):
                    self.assertEqual(
                        i,
                        codec.decode(codec.encode(i)),
                    )

    def test_codec_order_preserving(self):
        codec = default_codec(length=3)

        vals = (codec.encode(x) for x in range(codec.max_value))

        for lower_val, upper_val in it.pairwise(vals):
            self.assertLess(lower_val, upper_val)
