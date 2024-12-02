#!/usr/bin/env python

import setuptools

# Get the version from the "version" file which is an output from "stamp.sh"
version = open("version", 'r').readline().strip()

# Set the long-description string which is used by PyPI for the project
# description on the webpage for the package.
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.rst").read_text()
long_description += (this_directory / "CHANGELOG.rst").read_text()

if __name__ == "__main__":
    setuptools.setup(version=version,
                     long_description=long_description
                     )