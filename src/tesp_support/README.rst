============
Introduction
============

Transactive Energy Simulation Platform (TESP) simulates 
the electric power distribution grid with transactive control
of loads and resources. Current features include:

* GridLAB-D_ for the distribution system and residential loads
* EnergyPlus_ for large buildings
* MATPOWER_ or PYPOWER_ for the bulk power systems
* Bindings for transactive agents in Python_, Java or C++

The goal of TESP_ is that researchers can focus their work
on the last item, to push advances in the field.

Installation
============

tesp_support can be installed using pip_::

  $ pip install tesp_support

However, in order to be useful, tesp_support needs custom versions of 
GridLAB-D and EnergyPlus.  It also requires Python 3.6 or later, with 
NumPy_, SciPy_, NetworkX_, Matplotlib_ and PYPOWER_.  There are 
cross-platform installers of the complete TESP for Windows, Linux and Mac 
OS X on GitHub.  A Docker_ version is also available for users.  

Development Work Flow for tesp_support
======================================

* From this directory, 'pip install -e .' points Python to this cloned repository for any calls to tesp_support functions
* See the https://github.com/pnnl/tesp/tree/master/src/tesp_support/tesp_support for a roadmap of existing Python source files, and some documentation.  Any changes or additions to the code need to be made in this directory.  
* Run tests from any other directory on this computer
* When ready, edit the tesp_support version number and dependencies in setup.py
* To deploy, 'python setup.py sdist upload' 
* Any user gets the changes with 'pip install tesp_support --upgrade'
* Use 'pip show tesp_support' to verify the version and location on your computer

Using TESP
==========

This is a developer's platform for electric power grid research.  See 
http://tesp.readthedocs.io/en/latest/ for user instructions, and 
http://github.com/pnnl/tesp for source code.  

Links to Dependencies
=====================

* Docker_
* EnergyPlus_
* GridLAB-D_
* Matplotlib_
* MATPOWER_
* NetworkX_
* NumPy_
* Pandas_
* pip_
* PYPOWER_
* Python_
* SciPy_
* TESP_

Subdirectories
==============

- *tesp_support*; Python code for agents, configuration and post-processing.
- *test*; scripts that support testing the package; not automated.

License & Copyright
===================

- Copyright (C) 2017-2019 Battelle Memorial Institute

.. _Docker: https://www.docker.com
.. _Python: http://www.python.org
.. _pip: https://pip.pypa.io
.. _Pandas: https://pandas.pydata.org
.. _NumPy: http://www.numpy.org
.. _SciPy: http://www.scipy.org
.. _Matplotlib: https://matplotlib.org
.. _NetworkX: http://networkx.github.io
.. _MATPOWER: http://www.pserc.cornell.edu/matpower/
.. _PYPOWER: https://github.com/rwl/PYPOWER
.. _GridLAB-D: http://gridlab-d.shoutwiki.com
.. _EnergyPlus: https://energyplus.net/
.. _TESP: http://tesp.readthedocs.io/en/latest/
