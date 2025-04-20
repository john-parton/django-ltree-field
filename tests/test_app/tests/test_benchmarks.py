"""
Tests for django_ltree_field schema editor functionality.

This module tests the schema editor mixin that manages ltree triggers
for LTreeFields during model creation, alteration, and deletion.
"""

import pytest
from tests.test_app.models import SimpleNode


def _test_fetch():
    SimpleNode.objects.all().first()
    # You may return anything you want, like the result of a computation
    return 123


@pytest.mark.django_db
def test_my_stuff(benchmark):
    def setup():
        pass

    def teardown():
        pass

    # benchmark something
    result = benchmark(_test_fetch)

    # Extra code, to verify that the run completed correctly.
    # Sometimes you may want to check the result, fast functions
    # are no good if they return incorrect results :-)
    assert result == 123
