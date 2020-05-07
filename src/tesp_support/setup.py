# Copyright (C) 2017-2020 Battelle Memorial Institute
# file: setup.py

from setuptools import setup, find_packages


setup(
    name='tesp_support',
    version='0.6.4',
    author='Thomas McDermott',
    author_email='Thomas.McDermott@PNNL.gov',
    description='Python support for the Transactive Energy Simulation Platform',
    long_description='\n\n'.join(
        open(f, 'rb').read().decode('utf-8')
        for f in ['README.rst', 'CHANGELOG.rst']),
    url='https://github.com/pnnl/tesp',
    license='BSD',
    install_requires=[
        'pandas>=0.25.1',
        'numpy>=1.17.2',
        'scipy>=1.3.1',
        'matplotlib>=3.0.0',
        'networkx>=2.4',
        'PYPOWER>=5.1.4'
    ],
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering',
    ],
    zip_safe=False
)
