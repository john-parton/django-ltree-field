"""
test_django_tree_field
------------

Tests for `django_ltree_field` models module.
"""

from django.contrib.postgres.fields import ArrayField
from django.db import InternalError
from django.db.models import Count, Exists, OuterRef, Q, Subquery, Value
from django.db.models.functions import Cast
from django.test import TestCase

from django_ltree_field.fields import LTreeField
from django_ltree_field.functions.ltree import Concat, Subpath
from tests.test_app.models import ProtectedNode, SimpleNode


class TestCascade(TestCase):
    def test_forbid_unrooted(self):
        """Test that unrooted paths are forbidden in SimpleNode."""
        with self.assertRaises(InternalError):
            SimpleNode.objects.create(path="Top.Unrooted.Deep.Down")

    def test_cascade_delete(self):
        """Test that deleting a node cascades to all of its descendants."""
        SimpleNode.objects.create(path="Top")
        SimpleNode.objects.create(path="Top.Collections")

        self.assertTrue(SimpleNode.objects.filter(path="Top.Collections").exists())

        SimpleNode.objects.filter(path="Top").delete()

        self.assertFalse(SimpleNode.objects.filter(path="Top.Collections").exists())

    def test_cascade_update(self):
        """Test that updating a node's path cascades to all of its descendants."""
        SimpleNode.objects.create(path="Top")
        SimpleNode.objects.create(path="Top.Collections")

        self.assertTrue(SimpleNode.objects.filter(path="Top.Collections").exists())

        SimpleNode.objects.filter(path="Top").update(path="Top2")

        self.assertFalse(SimpleNode.objects.filter(path="Top.Collections").exists())
        self.assertTrue(SimpleNode.objects.filter(path="Top2.Collections").exists())

    def test_bulk_move(self):
        """Test that bulk moving nodes works correctly with cascading updates."""
        SimpleNode.objects.create(path="MoveMe")
        SimpleNode.objects.create(path="MoveMe.Collections")

        SimpleNode.objects.filter(
            path="MoveMe",
        ).update(path="MoveMe2")

        self.assertSequenceEqual(
            [
                "MoveMe2",
                "MoveMe2.Collections",
            ],
            list(
                SimpleNode.objects.filter(
                    path__contained_by="MoveMe2",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )


class TestProtected(TestCase):
    def test_protected_create(self):
        """Test that unrooted paths are forbidden in ProtectedNode."""
        with self.assertRaises(InternalError):
            ProtectedNode.objects.create(path="Top.Unrooted.Deep.Down")

    def test_protected_delete(self):
        """Test that deleting a node with children raises an error in ProtectedNode."""
        ProtectedNode.objects.create(path="Top")
        ProtectedNode.objects.create(path="Top.Collections")

        self.assertTrue(ProtectedNode.objects.filter(path="Top.Collections").exists())

        with self.assertRaises(InternalError):
            ProtectedNode.objects.filter(path="Top").delete()

    def test_protected_update(self):
        """Test that updating a node with children raises an error in ProtectedNode."""
        ProtectedNode.objects.create(path="Top")
        ProtectedNode.objects.create(path="Top.Collections")

        self.assertTrue(ProtectedNode.objects.filter(path="Top.Collections").exists())

        with self.assertRaises(InternalError):
            ProtectedNode.objects.filter(path="Top").update(path="Top2")


class TestSimpleNode(TestCase):
    # TODO
    # test_index
    # test_slice
    # test_lca (both array args and variadic args)
    # test other functions

    def setUp(self):
        # Bulk create the example fixture
        SimpleNode.objects.bulk_create(
            SimpleNode(path=path)
            for path in [
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
        )

    def test_parent_of(self):
        """Test parent_of lookup that finds direct parent nodes."""
        self.assertSequenceEqual(
            [
                "Top.Collections.Pictures",
            ],
            list(
                SimpleNode.objects.filter(
                    path__parent_of="Top.Collections.Pictures.Astronomy",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

    def test_depth(self):
        """Test depth lookup and transformer functionality."""
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
        """Test sibling_of lookup that finds sibling nodes."""
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
        """Test child_of lookup that finds direct child nodes."""
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

    def test_descendant_of(self):
        """Test descendant_of lookup that finds descendant nodes but not the node itself."""
        self.assertSequenceEqual(
            [
                "Top.Science.Astronomy",
                "Top.Science.Astronomy.Astrophysics",
                "Top.Science.Astronomy.Cosmology",
            ],
            list(
                SimpleNode.objects.filter(
                    path__descendant_of="Top.Science",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

        # Test with multiple levels of descendants
        self.assertSequenceEqual(
            [
                "Top.Collections.Pictures",
                "Top.Collections.Pictures.Astronomy",
                "Top.Collections.Pictures.Astronomy.Astronauts",
                "Top.Collections.Pictures.Astronomy.Galaxies",
                "Top.Collections.Pictures.Astronomy.Stars",
            ],
            list(
                SimpleNode.objects.filter(
                    path__descendant_of="Top.Collections",
                ).values_list(
                    "path",
                    flat=True,
                ),
            ),
        )

    def test_contains(self):
        """Test contains lookup that finds nodes containing a given path."""
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
        """Test contained_by lookup that finds nodes contained by a given path."""
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
        """Test contained_by lookup with a list of paths."""
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
        """Test strictly contained_by lookup that excludes the given path itself."""
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
        """Test pattern matching lookup that finds nodes matching a given pattern."""
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
        """Test search lookup that finds nodes matching a given search query."""
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
        """Test path construction using Concat and Subpath functions."""
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
        """Test counting the number of children of each node in one query."""
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
        """Test identifying leaf nodes (nodes without children)."""
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

    def test_index(self):
        """Test index functionality for accessing path components by index."""
        # Get the 3rd element (0-indexed) from the path
        self.assertEqual(
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            ).values_list(
                "path__3",
                flat=True,
            )[0],
            "Astronomy",
        )

        # Get the 0th element (first) from all paths
        self.assertSequenceEqual(
            ["Top"] * SimpleNode.objects.count(),
            list(
                SimpleNode.objects.values_list(
                    "path__0",
                    flat=True,
                ),
            ),
        )

    def test_slice(self):
        """Test slice functionality for accessing path component ranges."""
        # Get a slice from index 1 to 3 (exclusive)
        self.assertEqual(
            SimpleNode.objects.filter(
                path="Top.Collections.Pictures.Astronomy",
            ).values_list(
                "path__1_3",
                flat=True,
            )[0],
            "Collections.Pictures",
        )
