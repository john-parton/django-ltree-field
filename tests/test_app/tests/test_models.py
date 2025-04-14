"""
test_django_tree_field
------------

Tests for `django_ltree_field` models module.
"""

from django.contrib.postgres.fields import ArrayField
from django.db.models import Count, Exists, OuterRef, Q, Subquery, Value
from django.db.models.functions import Cast
from django.db.utils import InternalError
from django.test import TestCase

from django_ltree_field.fields import LTreeField
from django_ltree_field.functions import Concat, Subpath

from tests.test_app.models import ProtectedNode, SimpleNode


from django.db.utils import ProgrammingError

# class TestIntegerNode(TestCase):
#     def test_create(self):
#         IntegerNode.objects.create(path=(100, 200, 300))
#         assert False, IntegerNode.objects.all().values("path")


class TestCascade(TestCase):
    # def test_forbid_unrooted(self):
    # with self.assertRaises(ValueError):
    #     SimpleNode.objects.create(path="fjkdlsdfjkl.sdf.fsdsdf")
    def test_cascade_create(self):
        with self.assertRaises(ProgrammingError):
            ProtectedNode.objects.create(path="Top.Unrooted.Deep.Down")

    def test_cascade_delete(self):
        SimpleNode.objects.create(path="Top")
        SimpleNode.objects.create(path="Top.Collections")

        self.assertTrue(SimpleNode.objects.filter(path="Top.Collections").exists())

        SimpleNode.objects.filter(path="Top").delete()

        self.assertFalse(SimpleNode.objects.filter(path="Top.Collections").exists())

    def test_cascade_update(self):
        SimpleNode.objects.create(path="Top")
        SimpleNode.objects.create(path="Top.Collections")

        self.assertTrue(SimpleNode.objects.filter(path="Top.Collections").exists())

        SimpleNode.objects.filter(path="Top").update(path="Top2")

        self.assertFalse(SimpleNode.objects.filter(path="Top.Collections").exists())
        self.assertTrue(SimpleNode.objects.filter(path="Top2.Collections").exists())

    def test_bulk_move(self):
        # Example to move all matching nodes to be children of a new nodeIs j
        SimpleNode.objects.update(
            path=Concat(
                Value("Top2"),
                Subpath("path", Value(1)),
            )
        )


class TestProtected(TestCase):
    def test_protected_create(self):
        with self.assertRaises(ProgrammingError):
            ProtectedNode.objects.create(path="Top.Unrooted.Deep.Down")

    def test_protected_delete(self):
        ProtectedNode.objects.create(path="Top")
        ProtectedNode.objects.create(path="Top.Collections")

        self.assertTrue(ProtectedNode.objects.filter(path="Top.Collections").exists())

        with self.assertRaises(ProgrammingError):
            ProtectedNode.objects.filter(path="Top").delete()

    def test_protected_update(self):
        ProtectedNode.objects.create(path="Top")
        ProtectedNode.objects.create(path="Top.Collections")

        self.assertTrue(ProtectedNode.objects.filter(path="Top.Collections").exists())

        with self.assertRaises(ProgrammingError):
            ProtectedNode.objects.filter(path="Top").update(path="Top2")


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
            [
                "Top.Collections",
                "Top.Hobbies",
                "Top.Science",
            ],
            list(
                SimpleNode.objects.filter(
                    path__depth=2,
                ).values_list(
                    "path",
                    flat=True,
                )
            ),
        )

        # Make sure transformer "values" works
        self.assertEqual(
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            ).values_list(
                "path__depth",
                flat=True,
            )[0],
            4,
        )

    def test_sibling_of(self):
        self.assertSequenceEqual(
            [
                "Top.Collections",
                "Top.Hobbies",
                "Top.Science",
            ],
            list(
                SimpleNode.objects.filter(
                    path__sibling_of="Top.Science",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

    def test_child_of(self):
        self.assertSequenceEqual(
            [
                "Top.Collections",
                "Top.Hobbies",
                "Top.Science",
            ],
            list(
                SimpleNode.objects.filter(
                    path__child_of="Top",
                ).values_list(
                    "path",
                    flat=True,
                )
            ),
        )

    def test_contains(self):
        self.assertSequenceEqual(
            [
                "Top",
                "Top.Collections",
                "Top.Collections.Pictures",
            ],
            list(
                SimpleNode.objects.filter(
                    path__contains="Top.Collections.Pictures",
                ).values_list(
                    "path",
                    flat=True,
                )
            ),
        )

    # The following tests runs through all the examples from the postgres documentation, listed
    # here: https://www.postgresql.org/docs/9.1/ltree.html#AEN141210

    # The postgres docs call this "inheritance", but we usually call it "is_descendant"
    def test_contained_by(self):
        self.assertSequenceEqual(
            [
                "Top.Science",
                "Top.Science.Astronomy",
                "Top.Science.Astronomy.Astrophysics",
                "Top.Science.Astronomy.Cosmology",
            ],
            list(
                SimpleNode.objects.filter(
                    path__contained_by="Top.Science",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

    def test_contained_by_list(self):
        self.assertSequenceEqual(
            [
                "Top.Collections.Pictures.Astronomy",
                "Top.Collections.Pictures.Astronomy.Astronauts",
                "Top.Collections.Pictures.Astronomy.Galaxies",
                "Top.Collections.Pictures.Astronomy.Stars",
                "Top.Science",
                "Top.Science.Astronomy",
                "Top.Science.Astronomy.Astrophysics",
                "Top.Science.Astronomy.Cosmology",
            ],
            list(
                SimpleNode.objects.filter(
                    path__contained_by=Cast(
                        Value(
                            [
                                "Top.Collections.Pictures.Astronomy",
                                "Top.Science",
                            ]
                        ),
                        ArrayField(LTreeField()),
                    ),
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

    def test_strictly_contained_by(self):
        # We could have this as a custom lookup, but django doesn't tend to provide
        # these in the core library
        self.assertSequenceEqual(
            [
                "Top.Science.Astronomy",
                "Top.Science.Astronomy.Astrophysics",
                "Top.Science.Astronomy.Cosmology",
            ],
            list(
                SimpleNode.objects.filter(
                    ~Q(path="Top.Science") & Q(path__contained_by="Top.Science")
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

    def test_pattern_matching(self):
        self.assertSequenceEqual(
            [
                "Top.Collections.Pictures.Astronomy",
                "Top.Collections.Pictures.Astronomy.Astronauts",
                "Top.Collections.Pictures.Astronomy.Galaxies",
                "Top.Collections.Pictures.Astronomy.Stars",
                "Top.Science.Astronomy",
                "Top.Science.Astronomy.Astrophysics",
                "Top.Science.Astronomy.Cosmology",
            ],
            list(
                SimpleNode.objects.filter(
                    path__matches="*.Astronomy.*",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

        self.assertSequenceEqual(
            [
                "Top.Science.Astronomy",
                "Top.Science.Astronomy.Astrophysics",
                "Top.Science.Astronomy.Cosmology",
            ],
            list(
                SimpleNode.objects.filter(
                    path__matches="*.!pictures@.Astronomy.*",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

    def test_search(self):
        self.assertSequenceEqual(
            [
                "Top.Hobbies.Amateurs_Astronomy",
                "Top.Science.Astronomy",
                "Top.Science.Astronomy.Astrophysics",
                "Top.Science.Astronomy.Cosmology",
            ],
            list(
                SimpleNode.objects.filter(
                    path__search="Astro*% & !pictures@",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

        self.assertSequenceEqual(
            [
                "Top.Science.Astronomy",
                "Top.Science.Astronomy.Astrophysics",
                "Top.Science.Astronomy.Cosmology",
            ],
            list(
                SimpleNode.objects.filter(
                    path__search="Astro* & !pictures@",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

    # Also tests out our Concat and Subpath functions
    def test_path_construction(self):
        queryset = SimpleNode.objects.annotate(
            # Inserts "Space" as the 3rd level path
            new_path=Concat(
                Subpath("path", Value(0), Value(2)),
                Value("Space"),
                Subpath("path", Value(2)),
            )
        ).filter(
            path__contained_by="Top.Science.Astronomy",
        )

        self.assertSequenceEqual(
            [
                "Top.Science.Space.Astronomy",
                "Top.Science.Space.Astronomy.Astrophysics",
                "Top.Science.Space.Astronomy.Cosmology",
            ],
            list(
                queryset.values_list(
                    "new_path",
                    flat=True,
                ),
            ),
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
            [
                ("Top", 3),
                ("Top.Collections", 1),
                ("Top.Collections.Pictures", 1),
                ("Top.Collections.Pictures.Astronomy", 3),
                ("Top.Collections.Pictures.Astronomy.Astronauts", 0),
                ("Top.Collections.Pictures.Astronomy.Galaxies", 0),
                ("Top.Collections.Pictures.Astronomy.Stars", 0),
                ("Top.Hobbies", 1),
                ("Top.Hobbies.Amateurs_Astronomy", 0),
                ("Top.Science", 1),
                ("Top.Science.Astronomy", 2),
                ("Top.Science.Astronomy.Astrophysics", 0),
                ("Top.Science.Astronomy.Cosmology", 0),
            ],
            list(qs),
        )

    def test_is_leaf(self):
        qs = SimpleNode.objects.filter(
            ~Exists(
                SimpleNode.objects.filter(
                    # Exclude self
                    # Could also do ~Q(path=OuterRef("path"))
                    Q(path__contained_by=OuterRef("path")) & ~Q(id=OuterRef("id"))
                )
                .order_by()
                .values("id")
            )
        )

        self.assertSequenceEqual(
            [
                "Top.Collections.Pictures.Astronomy.Astronauts",
                "Top.Collections.Pictures.Astronomy.Galaxies",
                "Top.Collections.Pictures.Astronomy.Stars",
                "Top.Hobbies.Amateurs_Astronomy",
                "Top.Science.Astronomy.Astrophysics",
                "Top.Science.Astronomy.Cosmology",
            ],
            list(
                qs.values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

    def tearDown(self):
        pass
