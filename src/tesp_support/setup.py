#	Copyright (C) 2017-2018 Battelle Memorial Institute

from setuptools import setup, find_packages


setup(
    name='tesp_support',
    version='0.1.9',
    author='Thomas McDermott',
    author_email='Thomas.McDermott@PNNL.gov',
    description='Python support for the Transactive Energy Simulation Platform',
    long_description='\n\n'.join(
        open(f, 'rb').read().decode('utf-8')
        for f in ['README.rst', 'CHANGELOG.rst']),
    url='https://github.com/pnnl/tesp',
    license='BSD',
    install_requires=[
        'numpy>=1.15.4',
        'scipy>=1.1.0',
        'matplotlib>=3.0.0',
        'networkx>=2.1',
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
        'Programming Language :: Python :: 3.6',
        'Topic :: Scientific/Engineering',
    ],
    zip_safe=False
)
