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

- *comms_metrics*; a Power Distribution System Model Analysis tool not yet public though pypi. Not only can it perform metric calculations, it also has the ability to plot the models as a network and parse different file formats as pre-processing for the data analysis.
- *energyplus*; C++ code to build a simple interface agent for EnergyPlus; this is part of the TESP distribution and used in the te30, sgip1 and energyplus examples.
- *jupyter*; a prototype Jupyter notebook used for post-processing demonstrations and training
- *tesp_support*; utilities for building and running using PYPOWER with or without FNCS/HELICS co-simulations

Files
=====

- *README.rst*; this file

License & Copyright
===================

- Copyright (c) 2017-2024 Battelle Memorial Institute
- See LICENSE file at https://github.com/pnnl/tesp

