Building the TESP
=================

TESP has been designed to build and run with free compilers. The Python code
has been developed and tested with Python 3, including the NumPy, SciPy,
Matplotlib, Pypower, networkx, Pandas, Pyomo, psst and other packages. 
There are several suitable and free Python distributions that will install these packages. 

At this time, we build on Linux only, to reduce the maintenance burden.
This decision was made easier by the observation that many TESP federates
perform better on Linux than on Windows or Mac OS X, given the same hardware.
Native Windows and Mac OS X builds are still possible, but we recommend the
use of a Linux virtual machine or Docker container to run TESP on those platforms.

.. toctree::
   :maxdepth: 3

   Linux_Build_Link
   Deprecated_Build_Link


