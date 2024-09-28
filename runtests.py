#!/usr/bin/env python

import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner


def run_tests(tests):
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.test_settings"
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    return test_runner.run_tests(tests)


if __name__ == "__main__":
    failures = run_tests(["tests"])
    sys.exit(bool(failures))
