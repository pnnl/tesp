# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: setup.py

from setuptools import setup, find_packages


setup(
    name='tesp_support',
    version='1.2.0',
    author='Trevor Hardy',
    author_email='trevor.hardy@PNNL.gov',
    description='Python support for the Transactive Energy Simulation Platform',
    long_description='\n\n'.join(
        open(f, 'rb').read().decode('utf-8')
        for f in ['README.rst', 'CHANGELOG.rst']),
    url='https://github.com/pnnl/tesp',
    license='BSD',
    install_requires=[
        'pandas~=1.4.3',
        'numpy~=1.21.6',
        'scipy~=1.8.1',
        'matplotlib~=3.5.3',
        'networkx~=2.8.5',
        'PYPOWER==5.1.5',
        'pyutilib==5.8.0',
        'Pyomo==5.6.8'
    ],
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.8',
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
        'Programming Language :: Python :: 3.8',
        'Topic :: Scientific/Engineering'
    ],
    zip_safe=False
)
