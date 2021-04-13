#!/usr/bin/env python

import setuptools

if __name__ == "__main__":
    setuptools.setup(
        version_config={
            "starting_version": "0.0.3"
        },
        setup_requires=['setuptools-git-versioning'],
    )
