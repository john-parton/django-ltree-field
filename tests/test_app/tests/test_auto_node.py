from django.test import TestCase

from tests.test_app.models import AutoNode


class TestAutoNode(TestCase):
    def test_create_default(self):
        """Test creating a node, default a root node"""
        AutoNode.objects.create(
            name="Test Root1",
        )

        self.assertTrue(
            AutoNode.objects.filter(
                path__depth=1,
                name="Test Root1",
            ).exists()
        )

    def test_create_root(self):
        """Test creating a node, default a root node"""
        AutoNode.objects.create(
            name="Test Root2",
            position=AutoNode.position.root,
        )

        self.assertTrue(
            AutoNode.objects.filter(
                path__depth=1,
                name="Test Root2",
            ).exists()
        )

    def test_create_first_child_of(self):
        """Test creating a node, default a root node"""
        root = AutoNode.objects.create(
            name="Test Root3",
            position=AutoNode.position.root,
        )

        names = [
            "Test Child1",
            "Test Child2",
            "Test Child3",
        ]

        for name in names:
            AutoNode.objects.create(
                name=name,
                position=AutoNode.position.first_child_of(root),
            )

        children = list(root.children().values_list("name", flat=True))

        # We inserted them right-to-left
        names.reverse()
        self.assertSequenceEqual(
            names,
            children,
        )

    def test_create_last_child_of(self):
        """Test creating a node, default a root node"""
        root = AutoNode.objects.create(
            name="Test Root4",
            position=AutoNode.position.root,
        )

        names = [
            "Test Child4",
            "Test Child5",
            "Test Child6",
        ]

        for name in names:
            root.add_child(
                name=name,
            )

        children = list(root.children().values_list("name", flat=True))

        # We inserted them left-to-right
        self.assertSequenceEqual(
            names,
            children,
        )
