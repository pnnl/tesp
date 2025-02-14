#!/usr/bin/env python

import setuptools

if __name__ == "__main__":
    from pathlib import Path
    # Get the version and long description
    version = Path("version").read_text()
    long_description = Path("README.rst").read_text()
    long_description += Path("CHANGELOG.rst").read_text()
    setuptools.setup(version=version, long_description=long_description)