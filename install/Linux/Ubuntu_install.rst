.. _LinuxInstall:

Installing on Linux (DRAFT)
---------------------------

The following procedure was tested on a clean installation of Ubuntu 18.04 LTS.
It comes with a minimal *python3* installation. By default there is no *root* user,
but the installing user will need administrative privileges to run *sudo* commands.
The specific procedures may differ for other flavors of Linux, or if other versions
of Python and/or Java have been installed.

The installer invokes these commands to install TESP prerequisites (IN PROGRESS):

::

 sudo apt-get -y install libjsoncpp
 sudo apt-get -y install libxerces-c
 sudo apt-get -y install libzmq5
 sudo apt-get -y install libczmq5
 sudo apt-get -y install libklu1
 sudo apt-get -y install coinor-cbc
 sudo apt-get -y install openjdk-11-jre-headless
 sudo apt-get -y install python3-tk
 sudo apt-get -y install python3-pip
 sudo apt-get -y install libjsoncpp
 pip3 install tesp_support --upgrade
 pip3 install psst --upgrade

This process will install HELICS, FNCS, and several co-simulation federates under
/opt/tesp. The TESP_INSTALL environment variable should be set to /opt/tesp

To get started after basic installation:

1. (UPDATE NEEDED) Try the video tutorial at https://github.com/pnnl/tesp/releases
2. (UPDATE NEEDED) Try :ref:`RunExamples` 

You may also use the `Docker Version`_. This option is useful for distributed processing, and for 
isolating TESP from your other software, including other versions of GridLAB-D. However, 
it may require a little more data file management.

.. _`Docker Version`: https://github.com/pnnl/tesp/blob/develop/install/Docker/ReadMe.md



