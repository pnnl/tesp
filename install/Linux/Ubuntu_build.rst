Building on Ubuntu
------------------

This procedure builds all components from scratch. If you've already
built GridLAB-D on your machine, please take note of the specific
GitHub branch requirements for TESP:

- feature/1173c for GridLAB-D
- feature/opendss for FNCS
- fncs_9.3.0 for EnergyPlus
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
- the first step of *sudo apt-get install git* is not necessary
- when building the Java 10 binding for FNCS, you have to manually copy the fncs.jar and libFNCSjni.so to the correct place. The paths are different because of how WSL integrates the Windows and Linux file systems
- for HELICS bindings, add JAVAPATH to *~/.profile* instead of *~/.bashrc*

Preparation - Build Tools and Java
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 # build tools
 sudo apt-get -y install git-lfs
 sudo apt-get -y install build-essential
 sudo apt-get -y install autoconf
 sudo apt-get -y install libtool
 sudo apt-get -y install libjsoncpp-dev
 sudo apt-get -y install gfortran
 sudo apt-get -y install cmake
 sudo apt-get -y install subversion
 # Java support
 sudo apt-get -y install openjdk-11-jre-headless
 sudo apt-get -y install openjdk-11-jdk-headless
 sudo ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java
 # for HELICS and FNCS
 sudo apt-get -y install libzmq5-dev
 sudo apt-get -y install libczmq-dev
 # for GridLAB-D
 sudo apt-get -y install libxerces-c-dev
 sudo apt-get -y install libsuitesparse-dev
 # end users replace libsuitesparse-dev with libklu1, which is licensed LGPL
 # for AMES market simulator
 sudo apt-get -y install coinor-cbc
 # if not using miniconda (avoid Python 3.7 on Ubuntu for now)
 sudo apt-get -y install python3-pip
 sudo apt-get -y install python3-tk

Preparation - Python 3 and Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you didn't previously install Python 3 using apt, which is the recommended method
and version for TESP, please download and execute a Linux install script for Miniconda 
(Python*3.7*+) from https://docs.conda.io/en/latest/miniconda.html  The script should not be
run as root, otherwise, you won't have permission to install Python packages.
After the script configures Conda please re-open the Ubuntu terminal as instructed.

With Python 3 available, install and test the TESP packages:

::

 pip3 install tesp_support --upgrade
 opf 

In order to install psst:

::

 pip3 install psst --upgrade

Checkout PNNL repositories from github
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As noted above, we suggest *mkdir usrc* instead of *mkdir ~/src* on WSL.

::

 mkdir ~/src
 cd ~/src
 git config --global user.name "your user name"
 git config --global user.email "your email"
 git config --global credential.helper store
 git clone -b feature/opendss https://github.com/FNCS/fncs.git
 git clone -b master https://github.com/GMLC-TDC/HELICS-src
 git clone -b feature/1173c https://github.com/gridlab-d/gridlab-d.git
 git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git
 git clone -b develop https://github.com/pnnl/tesp.git
 git clone https://gitlab.com/nsnam/ns-3-dev.git
 git clone https://github.com/ames-market/psst.git
 svn export https://github.com/gridlab-d/tools/branches/klu-build-update/solver_klu/source/KLU_DLL

Choosing and Configuring the Install Directories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You must define the environment variable *$TESP_INSTALL*, which will receive
the TESP build products, examples and common data files. */opt/tesp* is suggested.

It's possible, but not recommended, to set *$TESP_INSTALL* as /usr/local. There are a few reasons not to:

1. It would result in shared TESP data files and examples being copied to /usr/local/share
2. It complicates building the Linux installer and Docker images
3. The simulators install properly to /usr/local by default, but you still have to explicity set $TESP_INSTALL for the example scripts to run properly.

The following examples are for Ubuntu; other flavors of Linux may differ.

For Ubuntu in a *virtual machine*, first edit or replace the */etc/environment* file.
This is not a script file, and it doesn't support the $variable replacement syntax. If using
$TESP_INSTALL, it has to be spelled out on each line, e.g.:

::

 TESP_INSTALL="/opt/tesp"
 PYHELICS_INSTALL="/opt/tesp"
 PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/tesp/bin:/opt/tesp:/opt/tesp/PreProcess:/opt/tesp/PostProcess"
 GLPATH="/opt/tesp/lib/gridlabd:/opt/tesp/share/gridlabd"
 CXXFLAGS="-I/opt/tesp/share/gridlabd"
 JAVAPATH="/opt/tesp/java"

Log out and log back in to Ubuntu for these */etc/environment* changes to take effect.

For Ubuntu in *WSL*, all changes are made to *~/.profile*.

::

 export TESP_INSTALL="/opt/tesp"
 export PATH="$PATH:$TESP_INSTALL:$TESP_INSTALL/bin:$TESP_INSTALL/PreProcess:$TESP_INSTALL/PostProcess"
 export GLPATH="$TESP_INSTALL/lib/gridlabd:$TESP_INSTALL/share/gridlabd"
 export CXXFLAGS="-I$TESP_INSTALL/share/gridlabd"
 export JAVAPATH="$TESP_INSTALL/java:$JAVAPATH"

Afterward, close and reopen the Ubuntu terminal for these changes to take effect.

The environment variable, CXXFLAGS, does not conflict with CXXFLAGS passed to various
build tools. Only GridLAB-D uses the CXXFLAGS environment variable, and you should
not use the variable append mechanism, i.e., :$CXXFLAGS, with it. This variable
enables all of the GridLAB-D autotest cases to pass.

FNCS and HELICS
~~~~~~~~~~~~~~~

To build the shared libraries for FNCS with Python bindings:

::

 cd ~/src/fncs
 autoreconf -if
 ./configure 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2' --prefix=$TESP_INSTALL
 # leave off --prefix if using the default /usr/local
 make
 sudo make install

To build the Java interface for version 10 or later, which has *javah* replaced by *javac -h*:

::

 cd java
 make
 sudo make install

The *make install* step may not work on WSL. A manual example is *cp fncs.jar $TESP_INSTALL/java*

To build HELICS with Java bindings:

::

 cd ~/src/HELICS-src
 git checkout "v2.5.2"
 mkdir build
 cd build
 cmake -DBUILD_JAVA_INTERFACE=ON -DBUILD_SHARED_LIBS=ON \
       -DJAVA_AWT_INCLUDE_PATH=NotNeeded -DHELICS_DISABLE_BOOST=ON \
       -DCMAKE_INSTALL_PREFIX=$TESP_INSTALL -DCMAKE_BUILD_TYPE=Release ..
 # leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
 git submodule update --init
 make -j4
 sudo make install

To install the HELICS Python 3 bindings:

::

 pip3 install helics==2.5.2

Test that HELICS and FNCS start:

::

 sudo ldconfig
 helics_player --version
 helics_recorder --version
 fncs_broker --version # look for the program to start, then exit with error

Then test HELICS from Python 3:

::

 python3
 >>> import helics
 >>> helics.helicsGetVersion()
 >>> quit()

GridLAB-D
~~~~~~~~~

To build the KLU solver:

::

 cd ~/src/KLU_DLL
 mkdir build
 cd build
 cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$TESP_INSTALL ..
 # replace $TESP_INSTALL with /usr/local if using the default
 sudo cmake --build . --target install

To link with both FNCS and HELICS, and run the autotest suite:

::

 cd ~/src/gridlab-d
 autoreconf -isf

 # in the following, --with-fncs and --with-helics can not be left blank, so use either $TESP_INSTALL or /usr/local for both
 # leave off --prefix if using the default /usr/local
 ./configure --prefix=$TESP_INSTALL --with-fncs=$TESP_INSTALL --with-helics=$TESP_INSTALL --enable-silent-rules 'CFLAGS=-w -O2' 'CXXFLAGS=-w -O2 -std=c++14' 'LDFLAGS=-w'
 # for debugging use 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -std=c++14 -g -O0' and 'LDFLAGS=-w -g -O0'

 make
 sudo make install
 gridlabd --validate 

EnergyPlus
~~~~~~~~~~

These following instructions install EnergyPlus with FNCS linkage and key portions of the retail v9.3 installation.

::

 cd ~/src/EnergyPlus
 mkdir build
 cd build
 cmake -DCMAKE_INSTALL_PREFIX=$TESP_INSTALL -DBUILD_FORTRAN=ON -DBUILD_PACKAGE=ON -DENABLE_INSTALL_REMOTE=OFF ..
 # leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
 make -j4
 sudo make install

Build eplus_agent
~~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/src/energyplus
 # the following steps are also in go.sh
 autoheader
 aclocal
 automake --add-missing
 autoconf
 ./configure --prefix=$TESP_INSTALL --with-fncs=$TESP_INSTALL 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2'
 # leave off --prefix and --with-fncs if using the default /usr/local
 make
 sudo make install

Build EnergyPlus Weather File Utility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/support/weather/TMY2EPW/source_code
 sudo make

Build ns3 with HELICS
~~~~~~~~~~~~~~~~~~~~~

First, in order to build ns-3 with Python bindings, we need to install the Python
binding generator that it uses, and then manually patch one of the ns-3 build files.

::
 
 pip3 install pybindgen --upgrade
 pip3 show pybindgen
 # edit line 17 of ~/src/ns-3-dev/bindings/python/wscript to specify the correct matching version, for example:
 REQUIRED_PYBINDGEN_VERSION = '0.21.0'

Then, we can build ns-3, install that into the same location as other parts of TESP, and test it:

::

 cd ~/src/ns-3-dev
 git clone -b feature/13b https://github.com/GMLC-TDC/helics-ns3 contrib/helics
 # --with-helics may not be left blank, so use either $TESP_INSTALL or /usr/local
 # --build-profile=optimized was used for TESP release, but it disables ns3 logging
 # ./waf configure --prefix=$TESP_INSTALL --with-helics=$TESP_INSTALL --build-profile=optimized --disable-werror --enable-examples --enable-tests
 ./waf distclean
 ./waf configure --prefix=$TESP_INSTALL --with-helics=$TESP_INSTALL --disable-werror --enable-examples --enable-tests
 ./waf build 
 sudo ./waf install
 ./test.py

Prepare for Testing
~~~~~~~~~~~~~~~~~~~

This command ensures Ubuntu will find all the new libraries, 
before you try :ref:`RunExamples`.

::

 # if using $TESP_INSTALL, edit the helper file tesp_ld.conf accordingly and then:
 sudo cp ~src/tesp/install/Linux/helpers/tesp_ld.conf /etc/ld.so.conf.d
 # then, regardless of whether the previous command was necessary:
 sudo ldconfig

In case you have both Python 2 and Python 3 installed, the TESP example
scripts and post-processing programs only invoke *python3*.

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

In order to build the documentation for ReadTheDocs:

::

 pip3 install recommonmark --upgrade
 pip3 install sphinx-jsonschema --upgrade
 pip3 install sphinx_rtd_theme --upgrade
 cd ~/src/tesp/doc
 make html

Changes can be previewed in ~/src/tesp/doc/_build/html/index.rst before
pushing them to GitHub. There is a trigger on ReadTheDocs that will
automatically rebuild public-facing documentation after the source
files on GitHub change.

Deployment - Ubuntu Installer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The general procedure will be:

#. Build TESP, installing to the default /opt/tesp
#. Clear the outputs from any earlier testing of the examples in your local repository
#. Deploy the shared files, which include examples, to /opt/tesp/share
#. Build opendsscmd to /opt/tesp/bin and liblinenoise.so to /opt/tesp/lib. (One source is the GridAPPS-D project repository under ~/src/CIMHub/distrib. Two copy commands are included in deploy.sh)
#. Make a sample user working directory, and auto-test the examples
#. Build and upload a Linux script installer using VMWare InstallBuilder. This is primarly based on the contents of /opt/tesp

Under ~/src/tesp/install/helpers, the following scripts may be helpful:

#. provision.sh; runs sudo apt-get for all packages needed for the build
#. gitclone.sh; clones all repositories need for the build
#. clean_outputs.sh; removes temporary output from the example directories
#. deploy.sh; copies redistributable files to /opt/tesp, invoking:

   #. deploy_ercot.sh; copies the ERCOT test system files to /opt/tesp

   #. deploy_examples.sh; copies the example files to /opt/tesp

   #. deploy_support.sh; copies the taxonomy feeder, reference building, sample weather, helper scripts and other support files to /opt/tesp

#. environment.sh; sets TESP_INSTALL and other environment variables
#. tesp_ld.conf; copy to /etc/ld.so.conf.d so Ubuntu fill find the shared libraries TESP installed
#. make_tesp_user_dir.sh; creates a working directory under the users home, and makes a copy of the shared examples and ERCOT test system.

Deployment - Docker Container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Windows and Mac OS X platforms are supported now through the Docker container *tesp_core*. 
As pre-requisites for building this container:

#. Install Docker on the build machine, following https://docs.docker.com/engine/install/ubuntu/
#. Build and test the Ubuntu installer as described in the previous subsection. By default, InstallBuilder puts the installer into *~/src/tesp/install/tesp_core*, which is the right place for a Docker build.

This Docker build process layers two images. The first image contains the required system and Python packages
for TESP, on top of Ubuntu 18.04, producing *tesp_foundation*. (In what follows, substitute your own DockerHub user name for *temcderm*)

::

 cd ~/src/tesp/install/tesp_foundation
 sudo docker build -t="temcderm/tesp_foundation:1.0.1" .

This process takes a while to complete. The second image starts from *tesp_foundation* and layers on the TESP components.
Primarily, it runs the Linux installer script inside the Docker container. It will check for current versions of the
packages just built into *tesp_foundation*, but these checks usually return quickly. The advantage of a two-step
image building process is that most new TESP versions can start from the existing *tesp_foundation*. The only exception
would be if some new TESP component introduces a new dependency.

::

 cd ~/src/tesp/install/tesp_core
 sudo docker build -t="temcderm/tesp_core:1.0.1" .

When complete, the layered image can be pushed up to Docker Hub.

::

 cd ~/src/tesp/install/tesp_core
 sudo docker push temcderm/tesp_core:1.0.1

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


