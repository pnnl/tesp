============
Introduction
============

Transactive Energy Simulation Platform (TESP) simulates 
the electric power distribution grid with transactive control
of loads and resources. Current features include:

* GridLAB-D for the distribution system and residential loads
* EnergyPlus for large buildings
* MATPOWER or PYPOWER for the bulk power systems
* Bindings for transactive agents in Python, Java or C++

The goal of TESP is that researchers can focus their work
on the last item, to push advances in the field.

Installation
============

tesp_support can be installed using pip_::

  $ pip install tesp_support

However, in order to be useful, tesp_support needs custom versions of 
GridLAB-D and EnergyPlus.  It also requires Python 3.5 or later, with 
Numpy, SciPy_ and PYPOWER_.  There will be cross-platform installers of 
the complete TESP for Windows, Linux and Mac OS X made available on GitHub.  

Using TESP
==========

This is a developer's platform for electric power grid research.  See 
http://tesp.readthedocs.io/en/latest/ for user instructions, and 
http://github.com/pnnl/tesp for source code.  

License & Copyright
===================

#	Copyright (C) 2017-2018 Battelle Memorial Institute

Links
=====

* GridLAB-D_

.. _Python: http://www.python.org
.. _pip: https://pip.pypa.io
.. _SciPy: http://www.scipy.org
.. _MATPOWER: http://www.pserc.cornell.edu/matpower/
.. _PYPOWER: https://github.com/rwl/PYPOWER
.. _GridLAB-D: http://gridlab-d.shoutwiki.com
.. _EnergyPlus: https://energyplus.net/
.. _TESP: http://tesp.readthedocs.io/en/latest/
