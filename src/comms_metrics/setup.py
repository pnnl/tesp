# -*- coding: utf-8 -*-
"""
Created on Tue Mar 30 07:28:23 2021

@author: barn553
"""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt") as fh:
    requirements = fh.read()

setuptools.setup(
    name='validation',
    version='0.0.1',
    # scripts=['dokr'] ,
    author="Corinne Roth",
    author_email="corinne.roth@pnnl.gov",
    description="Power Distribution System Model Analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # TODO: get the right url
    # url="?",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # ??
        "Operating System :: OS Independent",
    ],
)
