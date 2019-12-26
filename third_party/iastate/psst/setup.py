#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

requirements = [
    'Click>=6.0',
    'sphinx>=1.4.1',
    'ghp-import>=0.4.1',
    'sphinxcontrib-fulltoc>=1.1',
    'sphinxcontrib-jsdemo>=0.1.4',
    'pandas',
    'future',
    'networkx',
    'matplotlib',
    'pyomo',
    'pypower'
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='psst',
    version='0.1.1a',
    description="Power System Simulation Toolbox",
    long_description=readme,
    author="Dheepak Krishnamurthy",
    author_email='kdheepak89@gmail.com',
    url='https://github.com/power-system-simulation-toolbox/psst',
    packages=[
        'psst',
    ],
    package_dir={'psst':
                 'psst'},
    entry_points={
        'console_scripts': [
            'psst=psst.cli:cli'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='psst',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
