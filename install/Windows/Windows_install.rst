Installing on Windows, Linux or Mac OSX
---------------------------------------

Installation requires three basic steps:

1. Install Python 3.6, either from http://www.python.org or https://conda.io/miniconda.html  
2. From a terminal/command window, install TESP Python package support with "**pip install tesp_support --upgrade**" for you as a user. This automatically installs required packages like numpy, scipy, networkx, matplotlib and PYPOWER.
3. Install the TESP data and (optionally) executable files by choosing your system-specific installer from https://github.com/pnnl/tesp/releases

To get started after basic installation:

1. Try the video tutorial at https://github.com/pnnl/tesp/releases
2. Try :ref:`RunExamples` 

Optional steps and troubleshooting:

1. If you didn't install the executables in step 3, use the docker image as described at https://github.com/pnnl/tesp/tree/master/examples/te30/TESP-Docker-Inputs. The docker option is useful for distributed processing, and for isolating TESP from your other software, including other versions of GridLAB-D. However, it may require a little more data file management and it doesn't support Windows 8 or earlier.
2. If Miniconda won't install mkl and numpy on Windows, download the "Python wheel" from from http://www.lfd.uci.edu/~gohlke/pythonlibs/ and run "pip install numpy-1.12.1+mkl-cp36-cp36m-win_amd64.whl"
3. If you'll be developing agents in Java, download and install the Java 8 JDK from http://www.oracle.com/technetwork/java/javase/downloads/index.html




