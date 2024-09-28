"""
test_django_tree_field
------------

Tests for `django_ltree_field` models module.
"""

from django.db.models import Q, Value, OuterRef, Subquery, Count
from django.test import TestCase

from django_ltree_field.functions import Concat, Subpath

from .models import SimpleNode


class TestSimpleNode(TestCase):
    # TODO
    # test_parent_of
    # test_index
    # test_slice
    # test_lca (both array args and variadic args)
    # test other functions

    def setUp(self):
        # Bulk create the example fixture
        PATHS = [
            "Top",
            "Top.Collections",
            "Top.Collections.Pictures",
            "Top.Collections.Pictures.Astronomy",
            "Top.Collections.Pictures.Astronomy.Astronauts",
            "Top.Collections.Pictures.Astronomy.Galaxies",
            "Top.Collections.Pictures.Astronomy.Stars",
            "Top.Hobbies",
            "Top.Hobbies.Amateurs_Astronomy",
            "Top.Science",
            "Top.Science.Astronomy",
            "Top.Science.Astronomy.Astrophysics",
            "Top.Science.Astronomy.Cosmology",
        ]

        SimpleNode.objects.bulk_create(SimpleNode(path=path) for path in PATHS)

    def test_depth(self):
        # Make sure lookup works
        self.assertSequenceEqual(
            [["Top", "Collections"], ["Top", "Hobbies"], ["Top", "Science"]],
            SimpleNode.objects.filter(path__depth=2).values_list("path", flat=True),
        )

        # Make sure transformer "values" works
        self.assertEqual(
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy"
            ).values_list("path__depth", flat=True)[0],
            4,
        )

    def test_sibling_of(self):
        self.assertSequenceEqual(
            [["Top", "Collections"], ["Top", "Hobbies"], ["Top", "Science"]],
            SimpleNode.objects.filter(path__sibling_of="Top.Science").values_list(
                "path", flat=True
            ),
        )

    def test_child_of(self):
        self.assertSequenceEqual(
            [["Top", "Collections"], ["Top", "Hobbies"], ["Top", "Science"]],
            SimpleNode.objects.filter(path__child_of="Top").values_list(
                "path", flat=True
            ),
        )

    def test_ancestor_of(self):
        self.assertSequenceEqual(
            [["Top"], ["Top", "Collections"], ["Top", "Collections", "Pictures"]],
            SimpleNode.objects.filter(
                path__ancestor_of="Top.Collections.Pictures"
            ).values_list("path", flat=True),
        )

    def test_strict_descendant_of(self):
        # We could make this a __strict_descendant_of lookup or something, but
        # that's a little strange
        self.assertSequenceEqual(
            [
                ["Top", "Science", "Astronomy"],
                ["Top", "Science", "Astronomy", "Astrophysics"],
                ["Top", "Science", "Astronomy", "Cosmology"],
            ],
            SimpleNode.objects.filter(
                ~Q(path="Top.Science") & Q(path__descendant_of="Top.Science")
            ).values_list("path", flat=True),
        )

    # The following tests runs through all the examples from the postgres documentation, listed
    # here: https://www.postgresql.org/docs/9.1/ltree.html#AEN141210

    # The postgres docs call this "inheritance", but we usually call it "is_descendant"
    def test_descendant_of(self):
        self.assertSequenceEqual(
            [
                ["Top", "Science"],
                ["Top", "Science", "Astronomy"],
                ["Top", "Science", "Astronomy", "Astrophysics"],
                ["Top", "Science", "Astronomy", "Cosmology"],
            ],
            SimpleNode.objects.filter(path__descendant_of="Top.Science").values_list(
                "path", flat=True
            ),
        )

    def test_pattern_matching(self):
        self.assertSequenceEqual(
            [
                ["Top", "Collections", "Pictures", "Astronomy"],
                ["Top", "Collections", "Pictures", "Astronomy", "Astronauts"],
                ["Top", "Collections", "Pictures", "Astronomy", "Galaxies"],
                ["Top", "Collections", "Pictures", "Astronomy", "Stars"],
                ["Top", "Science", "Astronomy"],
                ["Top", "Science", "Astronomy", "Astrophysics"],
                ["Top", "Science", "Astronomy", "Cosmology"],
            ],
            SimpleNode.objects.filter(path__matches="*.Astronomy.*").values_list(
                "path", flat=True
            ),
        )

        self.assertSequenceEqual(
            [
                ["Top", "Science", "Astronomy"],
                ["Top", "Science", "Astronomy", "Astrophysics"],
                ["Top", "Science", "Astronomy", "Cosmology"],
            ],
            SimpleNode.objects.filter(
                path__matches="*.!pictures@.Astronomy.*"
            ).values_list("path", flat=True),
        )

    def test_search(self):
        self.assertSequenceEqual(
            [
                ["Top", "Hobbies", "Amateurs_Astronomy"],
                ["Top", "Science", "Astronomy"],
                ["Top", "Science", "Astronomy", "Astrophysics"],
                ["Top", "Science", "Astronomy", "Cosmology"],
            ],
            SimpleNode.objects.filter(path__search="Astro*% & !pictures@").values_list(
                "path", flat=True
            ),
        )

        self.assertSequenceEqual(
            [
                ["Top", "Science", "Astronomy"],
                ["Top", "Science", "Astronomy", "Astrophysics"],
                ["Top", "Science", "Astronomy", "Cosmology"],
            ],
            SimpleNode.objects.filter(path__search="Astro* & !pictures@").values_list(
                "path", flat=True
            ),
        )

    # Also tests out our Concat and Subpath functions
    def test_path_construction(self):
        queryset = SimpleNode.objects.annotate(
            # Inserts "Space" as the 3rd level path
            new_path=Concat(Subpath("path", 0, 2), Value("Space"), Subpath("path", 2))
        ).filter(path__descendant_of="Top.Science.Astronomy")

        self.assertSequenceEqual(
            [
                ["Top", "Science", "Space", "Astronomy"],
                ["Top", "Science", "Space", "Astronomy", "Astrophysics"],
                ["Top", "Science", "Space", "Astronomy", "Cosmology"],
            ],
            queryset.values_list("new_path", flat=True),
        )

    def test_num_children(self):
        # Efficiently count the number of children of each node in one query
        qs = (
            SimpleNode.objects.annotate(
                num_children=Subquery(
                    SimpleNode.objects.filter(path__child_of=OuterRef("path"))
                    .order_by()
                    .annotate(dummy=Value(1))
                    .values("dummy")
                    .annotate(count=Count("id"))
                    .values("count")
                )
            )
            .values_list("path", "num_children")
            .order_by("path")
        )

        self.assertSequenceEqual(
            list(qs),
            [
                (["Top"], 3),
                (["Top", "Collections"], 1),
                (["Top", "Collections", "Pictures"], 1),
                (["Top", "Collections", "Pictures", "Astronomy"], 3),
                (["Top", "Collections", "Pictures", "Astronomy", "Astronauts"], 0),
                (["Top", "Collections", "Pictures", "Astronomy", "Galaxies"], 0),
                (["Top", "Collections", "Pictures", "Astronomy", "Stars"], 0),
                (["Top", "Hobbies"], 1),
                (["Top", "Hobbies", "Amateurs_Astronomy"], 0),
                (["Top", "Science"], 1),
                (["Top", "Science", "Astronomy"], 2),
                (["Top", "Science", "Astronomy", "Astrophysics"], 0),
                (["Top", "Science", "Astronomy", "Cosmology"], 0),
            ],
        )

    def tearDown(self):
        pass
