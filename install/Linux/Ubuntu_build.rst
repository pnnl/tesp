Building on Ubuntu
------------------

This procedure builds all components from scratch. If you've already
built GridLAB-D on your machine, please take note of the specific
GitHub branch requirements for TESP:

- feature/1146 for GridLAB-D
- develop for FNCS
- fncs-v8.3.0 for EnergyPlus
- develop for HELICS 2.0

You may also need to upgrade the gcc and g++ compilers. This build 
procedure has been tested with Ubuntu 18.04 LTS and gcc/g++ 7.3.0.

When you finish the build, try :ref:`RunExamples`.

Preparation - Python Packages, Java, build tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 # build tools and Java support
 sudo apt-get install git
 sudo apt-get install build-essential
 sudo apt-get install autoconf
 sudo apt-get install libtool
 sudo apt-get install cmake
 sudo apt-get install libjsoncpp-dev
 sudo apt-get install default-jre
 sudo apt-get install default-jdk

 # python3 support
 # first install Python 3.6 or later from https://www.python.org/downloads/ or https://repo.continuum.io/
 sudo apt-get install python3
 sudo apt-get install python3-pip
 sudo apt-get install python3-tk
 pip3 install tesp_support --upgrade
 opf 

 # for HELICS and FNCS
 sudo apt-get install libboost-dev
 sudo apt-get install libboost-program-options-dev
 sudo apt-get install libboost-test-dev
 sudo apt-get install libboost-filesystem-dev
 sudo apt-get install libzmq5-dev
 sudo apt-get install libczmq-dev

Checkout PNNL repositories from github
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src
 git config --global user.name "your user name"
 git config --global user.email "your email"
 git clone -b develop https://github.com/FNCS/fncs.git
 git clone -b develop https://github.com/GMLC-TDC/HELICS-src
 git clone -b feature/1146 https://github.com/gridlab-d/gridlab-d.git
 git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git
 git clone -b master https://github.com/pnnl/tesp.git

Choosing and Configuring the Install Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Consistent with instructions for other PNNL software that uses FNCS, we will
use the environment variable $FNCS_INSTALL to specify where all executables and
libraries will be installed.  If you have the permissions and only need one 
version of TESP, FNCS and GridLAB-D, you may install everything into /usr/local,
which is the default value of $FNCS_INSTALL. In this case, leave out all 
configuration parameters that reference $FNCS_INSTALL in the instructions below.

If you don't have administrative permission for /usr/local, or you want to maintain
multiple versions, then you must specify and use $FNCS_INSTALL. For example, 
a directory called *FNCS_install* under your home directory. The following example
is for Ubuntu; other flavors of Linux may differ.

::

 sudo gedit /etc/environment
 #
 # add these two lines in the *environment* file, and save it:
 #
 FNCS_INSTALL="$HOME/FNCS_install"
 # or FNCS_INSTALL="/usr/local"
 GLPATH="$FNCS_INSTALL/lib/gridlabd:$FNCS_INSTALL/share/gridlabd"
 #
 # Use this command before proceeding with the subsequent build steps
 #
 source /etc/environment

FNCS and HELICS with Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your Java version may have removed *javah*.  If that's the case, use *javac -h* instead.

::

 cd ~/src

 cd ../fncs
 autoreconf -if
 ./configure 'CXXFLAGS=-w' 'CFLAGS=-w' --prefix=$FNCS_INSTALL --with-zmq=$FNCS_INSTALL
 make
 sudo make install

 cd java
 mkdir build
 cd build
 cmake ..
 make
 cp fncs.jar ~/src/tesp/examples/loadshed/java
 cp libJNIfncs.so ~/src/tesp/examples/loadshed/java

GridLAB-D with Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you encounter build errors with GridLAB-D, please try
adding *-std=c++11* to *CXXFLAGS*.

::

 cd ~/src/gridlab-d
 autoreconf -isf

 cd third_party
 tar -xvzf xerces-c-3.1.1.tar.gz
 cd xerces-c-3.1.1
 ./configure 'CXXFLAGS=-w' 'CFLAGS=-w'
 make
 sudo make install
 cd ../..

 # for debugging ./configure --with-fncs=$FNCS_INSTALL 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -g -O0'
 ./configure --with-fncs=$FNCS_INSTALL 'CXXFLAGS=-w' 'CFLAGS=-w'

 sudo make
 sudo make install
 gridlabd --validate 

EnergyPlus with Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src/EnergyPlus
 mkdir build
 cd build
 cmake ..
 make

 # Before installing, we need components of the public version, including but not limited to 
 #  the critical Energy+.idd file
 # The compatible public version is at https://github.com/NREL/EnergyPlus/releases/tag/v8.3.0
 # That public version should be installed to /usr/local/EnergyPlus-8-3-0 before going further

 sudo make install

 # Similar to the experience with Mac and Windows, this installation step wrongly puts
 #  the build products in /usr/local instead of /usr/local/bin and /usr/local/lib
 #  the following commands will copy FNCS-compatible EnergyPlus over the public version
 cd /usr/local
 cp energyplus-8.3.0 EnergyPlus-8-3-0
 cp libenergyplusapi.so.8.3.0 EnergyPlus-8-3-0

 # if ReadVarsESO is not found at the end of a simulation, try this
 /usr/local/EnergyPlus-8-3-0$ sudo ln -s PostProcess/ReadVarsESO ReadVarsESO

Build eplus_json
~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/src/energyplus
 # the following steps are also in go.sh
 autoheader
 aclocal
 automake --add-missing
 autoconf
 ./configure --prefix=$FNCS_INSTALL --with-zmq=$FNCS_INSTALL
 make
 sudo make install

Prepare for Testing
~~~~~~~~~~~~~~~~~~~

This command ensures Ubuntu will find all the new libraries, 
before you try :ref:`RunExamples`.

::

 sudo ldconfig

In case you have both Python 2 and Python 3 installed, the TESP example
scripts and post-processing programs only invoke *python3*.

::

 gedit ~/.profile
 #
 # edit the line with PATH as follows, to put Python 3 before other
 # directories in the path, and then save the file
 #
 PATH="$HOME/miniconda3/bin:$HOME/bin: and more directories"

DEPRECATED: MATPOWER, MATLAB Runtime (MCR) and wrapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This procedure to support MATPOWER is no longer used in TESP at PNNL, but it may
be useful to others working with TESP and MATPOWER.

::

 cd ~/src/tesp/src/matpower/ubuntu
 ./get_mcr.sh
 mkdir temp
 mv *.zip temp
 cd temp
 unzip MCR_R2013a_glnxa64_installer.zip
 ./install  # choose /usr/local/MATLAB/MCR/v81 for installation target directory
 cd ..
 make

 # so far, start_MATPOWER executable is built
 # see MATLAB_MCR.conf for instructions to add MCR libraries to the Ubuntu search path
 # unfortunately, this creates problems for other applications, and had to be un-done.
 # need to investigate further: 
 # see http://sgpsproject.sourceforge.net/JavierVGomez/index.php/Solving_issues_with_GLIBCXX_and_libstdc%2B%2B 


