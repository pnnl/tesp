==============
src Repository
==============

This directory contains the source code specific to TESP.  Major 
components like EnergyPlus, GridLAB-D, PYPOWER and AMES have their own 
repositories located elsewhere.  Agent developers will normally work only 
in the *tesp_support* subdirectory.  The other subdirectories are mainly 
of interest to those building the whole platform.  

Subdirectories
==============

- *archive/pypower*; legacy files to patch PYPOWER; we have been able to incorporate these patches into the main PYPOWER distribution.
- *energyplus*; C++ code to build a simple interface agent for EnergyPlus; this is part of the TESP distribution and used in the te30, sgip1 and energyplus examples.
- *gridlabd*; legacy files for the house populations and feeder growth model; these features are mostly subsumed into tesp_support
- *jupyter*; a prototype Jupyter notebook used for post-processing demonstrations and training
- *matpower/ubuntu*; legacy code that wraps MATPOWER for TESP, but only on Ubuntu. We now use PYPOWER. In 2017, the wrapping process was very difficult on Mac OS X, and unsuccessful on Windows using free compilers.
- *synComGraph*; graph algorithms to generate a synthetic communication network graph topology corresponding to a given feeder topology
- *tesp_support*; runs PYPOWER without FNCS

Files
=====

- *anim.py*; test code for solution monitor performance improvement, to be removed or relocated
- *monitor.py*; test code for solution monitor performance improvement, to be removed or relocated

License & Copyright
===================

- Copyright (C) 2017-2022 Battelle Memorial Institute

