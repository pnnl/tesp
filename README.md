# Transactive Energy Simulation Platform (TESP)

Copyright (c) 2017-2018, Battelle Memorial Institute

Documentation: http://tesp.readthedocs.io

License: https://github.com/pnnl/tesp/blob/master/LICENSE

Installation requires three (or four) steps:

1. Install Python 3.6, either from http://www.python.org or https://conda.io/miniconda.html  
2. From a terminal/command window, install TESP Python package support with "**pip install tesp_support**" for you as a user. This automatically installs required packages like numpy, scipy, networkx, matplotlib and PYPOWER.
3. Install the TESP data and (optionally) executable files by choosing your system-specific installer from https://github.com/pnnl/tesp/releases
4. If you didn't install the executables in step 3, use the docker image as described at https://github.com/pnnl/tesp/tree/master/examples/te30/TESP-Docker-Inputs. The docker option is useful for distributed processing, and for isolating TESP from your other software, including other versions of GridLAB-D. However, it may require a little more data file management and it doesn't support Windows 8 or earlier.



