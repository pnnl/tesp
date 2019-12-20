Building on Ubuntu
------------------

This procedure builds all components from scratch. If you've already
built GridLAB-D on your machine, please take note of the specific
GitHub branch requirements for TESP:

- feature/1173 for GridLAB-D
- develop for FNCS
- fncs-v8.3.0 for EnergyPlus
- master for HELICS 2.0

You may also need to upgrade the gcc and g++ compilers. This build 
procedure has been tested with Ubuntu 18.04 LTS and gcc/g++ 7.3.0.

When you finish the build, try :ref:`RunExamples`.

Preparation - Virtual Machine or Windows Subsystem for Linux (WSL)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Linux can be installed on Windows (or Mac) using a virtual machine (VM), such as
VirtualBox from https://www.virtualbox.org/ The following instructions have
been written for the example of installing Ubuntu 18.04 under VirtualBox for Windows.
The same instructions also work for Ubuntu 18.04 under VMWare Fusion for Mac OS X.

Another option is to use the WSL feature built in to Windows, as described at
https://github.com/michaeltreat/Windows-Subsystem-For-Linux-Setup-Guide. WSL does not support
graphical applications, including the Eclipse IDE, but it may have other advantages for
building and running command-line tools, like TESP and GridLAB-D. The following
instructions work for Ubuntu 18.04 set up that way under WSL, with a few suggested 
changes to the TESP build:

- from the *cdwr* prompt, use *mkdir usrc* instead of *mkdir ~/src* before checking out repositories from GitHub. This makes it easier to keep track of separate source trees for Windows and Linux, if you are building from both on the same machine.
- the first step of *sudo apt-get install git* may be unnecessary
- when building the Java 10 binding for FNCS, you have to manually copy the fncs.jar and libFNCSjni.so to the correct place. The paths are different because of how WSL integrates the Windows and Linux file systems
- for HELICS bindings, add PYTHONPATH and JAVAPATH to *~/.profile* instead of *~/.bashrc*

Preparation - Python Packages, Java, build tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 # build tools and Java support
 sudo apt-get -y install git
 sudo apt-get -y install build-essential
 sudo apt-get -y install autoconf
 sudo apt-get -y install libtool
 sudo apt-get -y install libjsoncpp-dev
 sudo apt-get -y install gfortran
 sudo apt-get -y install openjdk-11-jre-headless
 sudo apt-get -y install openjdk-11-jdk-headless

 # install current version of CMake from Kitware

 # install python3.7+ support from https://repo.continuum.io/
 pip3 install tesp_support --upgrade
 opf 

 # for HELICS and FNCS with ns-3
 sudo apt-get -y install libzmq5-dev
 sudo apt-get -y install libczmq-dev

Checkout PNNL repositories from github
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As noted above, we suggest *mkdir usrc* instead of *mkdir ~/src* on WSL.

::

 mkdir ~/src
 cd ~/src
 git config --global user.name "your user name"
 git config --global user.email "your email"
 git clone -b develop https://github.com/FNCS/fncs.git
 git clone -b master https://github.com/GMLC-TDC/HELICS-src
 git clone -b feature/1173 https://github.com/gridlab-d/gridlab-d.git
 git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git
 git clone -b develop https://github.com/pnnl/tesp.git

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

FNCS and HELICS
~~~~~~~~~~~~~~~

To build the shared libraries for FNCS with Python bindings:

::

 cd ~/src/fncs
 autoreconf -if
 ./configure 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2' --prefix=$FNCS_INSTALL --with-zmq=$FNCS_INSTALL
 make
 sudo make install

To build the Java interface for version 10 or later, which has *javah* replaced by *javac -h*:

::

 sudo ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java
 cd java
 make
 make install

The *make install* step may not work on WSL. A manual example is *cp fncs.jar ../../tesp/examples/loadshed/java*

To build HELICS 2.0 with Python and Java bindings:

::

 cd ~/src/HELICS-src
 mkdir build
 cd build
 cmake -DBUILD_PYTHON_INTERFACE=ON -DBUILD_JAVA_INTERFACE=ON -DBUILD_SHARED_LIBS=ON -DJAVA_AWT_INCLUDE_PATH=NotNeeded -DHELICS_DISABLE_BOOST=ON -DCMAKE_BUILD_TYPE=Release ..
 make -j4
 sudo make install

Test that HELICS and FNCS start:

::

 sudo ldconfig
 helics_player --version
 helics_recorder --version
 fncs_broker --version # look for the program to start, then exit with error

To set up Python and Java to run with HELICS, add this to your *~/.bashrc* file (try *~/.profile* if using Windows Subsystem for Linux):

::

 export PYTHONPATH=/usr/local/python:$PYTHONPATH
 export JAVAPATH=/usr/local/java:$JAVAPATH

Then test HELICS from Python 3:

::

 python3
 >>> import helics
 >>> helics.helicsGetVersion()
 >>> quit()

GridLAB-D
~~~~~~~~~

To link with both FNCS and HELICS, and run the autotest suite:

::

 cd ~/src/gridlab-d
 autoreconf -isf

 # use current version of Xerces
 sudo apt-get install libxerces-c-dev

 # in the following, replace $FNCS_INSTALL with /usr/local to just use the default location
 ./configure --with-fncs=/usr/local --with-helics=/usr/local --enable-silent-rules 'CFLAGS=-w -O2' 'CXXFLAGS=-w -O2 -std=c++14' 'LDFLAGS=-w'

 # for debugging use 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -std=c++14 -g -O0' and 'LDFLAGS=-w -g -O0'

 make
 sudo make install
 gridlabd --validate 

EnergyPlus with Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 # Before installing, we need components of the public version, including but not limited to 
 #  the critical Energy+.idd file
 # The compatible public version is at https://github.com/NREL/EnergyPlus/releases/tag/v8.3.0
 # That public version should be installed to /usr/local/EnergyPlus-8-3-0 before going further

 cd ~/src/EnergyPlus
 mkdir build
 cd build
 cmake -DBUILD_FORTRAN=ON -DBUILD_PACKAGE=ON -DENABLE_INSTALL_REMOTE=OFF ..
 make -j4
 sudo make install

 # Similar to the experience with Mac and Windows, this installation step wrongly puts
 #  the build products in /usr/local instead of /usr/local/bin and /usr/local/lib
 #  the following commands will copy FNCS-compatible EnergyPlus over the public version
 cd /usr/local
 sudo cp energyplus-8.3.0 EnergyPlus-8-3-0
 sudo cp libenergyplusapi.so.8.3.0 EnergyPlus-8-3-0

 # if ReadVarsESO is not found at the end of a simulation, try this
 cd /usr/local/EnergyPlus-8-3-0
 sudo ln -s PostProcess/ReadVarsESO ReadVarsESO

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

Build ns3 with HELICS
~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src
 git clone https://gitlab.com/nsnam/ns-3-dev.git
 cd ns-3-dev
 git clone https://github.com/GMLC-TDC/helics-ns3 contrib/helics
 ./waf configure --with-helics=/usr/local --disable-werror --enable-examples --enable-tests
 ./waf build 

Prepare for Testing
~~~~~~~~~~~~~~~~~~~

This command ensures Ubuntu will find all the new libraries, 
before you try :ref:`RunExamples`.

::

 sudo ldconfig

In case you have both Python 2 and Python 3 installed, the TESP example
scripts and post-processing programs only invoke *python3*.

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


