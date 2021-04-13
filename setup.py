#!/usr/bin/env python

import setuptools

if __name__ == "__main__":
    setuptools.setup(
        # I can't seem to figure out how to move this to setup.cfg
        version_config={
            "starting_version": "0.0.3"
        },
        setup_requires=['setuptools-git-versioning'],
    )
