#	Copyright (C) 2017 Battelle Memorial Institute

from setuptools import setup, find_packages


setup(
    name='TESP',
    version='1.0.0',
    author='Thomas McDermott',
    author_email='Thomas.McDermott@PNNL.gov',
    description='Transactive Energy Simulation Platform',
    long_description='\n\n'.join(
        open(f, 'rb').read().decode('utf-8')
        for f in ['README.rst', 'CHANGELOG.rst']),
    url='https://github.com/pnnl/tesp',
    license='BSD',
    install_requires=[
        # Deactivated to avoid problems with system packages.
        # Manual installation of NumPy, SciPy, PYPOWER required.
    ],
    entry_points={'console_scripts': [
        'tesp = tesp.tesp'
    ]},
    packages=find_packages(),
    include_package_data=True,
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
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering',
    ],
)
