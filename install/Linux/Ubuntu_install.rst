.. _LinuxInstall:

Installing on Linux
-------------------

The following procedure was tested on a clean installation of Ubuntu 18.04 LTS.
This comes with a minimal *python3* installation. By default there is no *root* user,
but the installing user will need administrative privileges to run *sudo* commands.
The TESP software and examples take about 900MB under a created /opt/tesp directory.
In addition, you may need several GB of disk space to run simulations.

1. Download the latest installer from https://github.com/pnnl/tesp/releases

2. Open a Terminal and navigate to the Downloads directory

3. *chmod +x ./tesp-1.0.0-linux-x64-installer.run*

4. *sudo ./tesp-1.0.0-linux-x64-installer.run*

The installer invokes these commands to install TESP prerequisites:

::

 sudo apt-get -y install libjsoncpp-dev
 sudo apt-get -y install libxerces-c-dev
 sudo apt-get -y install libzmq5
 sudo apt-get -y install libczmq-dev
 sudo apt-get -y install libklu1
 sudo apt-get -y install coinor-cbc
 sudo apt-get -y install openjdk-11-jre-headless
 sudo apt-get -y install openjdk-11-jdk-headless
 sudo apt-get -y install python3-tk
 sudo apt-get -y install python3-pip
 pip3 install tesp_support --upgrade
 pip3 install psst --upgrade

This process will install HELICS, FNCS, and several co-simulation federates under
/opt/tesp. The TESP_INSTALL environment variable should be set to /opt/tesp

If you have already installed GridLAB-D, EnergyPlus, ns-3 or another simulator before TESP,
it may be necessary to manually adjust your PATH and GLPATH environment variables when
running TESP.  The TESP versions of these simulators are built with HELICS and FNCS interfaces,
which are not normally included in other versions of the simulators. In GridLAB-D, you may
get an error message about "module connection" not being found. With other simulators, you
might see the FNCS or HELICS broker hang, waiting for a federate that's unable to connect.

To get started after basic installation:

1. log out and log back in, to ensure PATH changes take effect
2. Try the YouTube tutorials at https://www.youtube.com/channel/UCMKOTNGldZ3OdDzHRJ_myeg
3. Try :ref:`RunExamples` 

You may also use the `Docker Version`_. This option is useful for distributed processing, and for 
isolating TESP from your other software, including other versions of GridLAB-D. However, 
it may require a little more data file management.

.. _`Docker Version`: https://github.com/pnnl/tesp/blob/develop/install/Docker/ReadMe.md



