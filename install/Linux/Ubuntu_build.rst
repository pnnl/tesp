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
- the first step of *sudo apt-get install git* is not necessary
- when building the Java 10 binding for FNCS, you have to manually copy the fncs.jar and libFNCSjni.so to the correct place. The paths are different because of how WSL integrates the Windows and Linux file systems
- for HELICS bindings, add PYTHONPATH and JAVAPATH to *~/.profile* instead of *~/.bashrc*

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
 # end users need only libklu1, which is licensed LGPL
 # if not using miniconda (avoid Python 3.7 on Ubuntu for now)
 sudo apt-get -y install python3-pip
 sudo apt-get -y install python3-tk

Preparation - Python 3 and Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, download and execute a Linux install script for Miniconda (Python*3.7*+) 
from https://docs.conda.io/en/latest/miniconda.html  The script should not be
run as root, otherwise, you won't have permission to install Python packages.
After the script configures Conda and you re-open the Ubuntu terminal as instructed:

::

 pip3 install tesp_support --upgrade
 opf 

Checkout PNNL repositories from github
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As noted above, we suggest *mkdir usrc* instead of *mkdir ~/src* on WSL.

::

 mkdir ~/src
 cd ~/src
 git config --global user.name "your user name"
 git config --global user.email "your email"
 git config --global credential.helper store
 git clone -b develop https://github.com/FNCS/fncs.git
 git clone -b master https://github.com/GMLC-TDC/HELICS-src
 git clone -b feature/1173 https://github.com/gridlab-d/gridlab-d.git
 git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git
 git clone -b develop https://github.com/pnnl/tesp.git
 git clone https://gitlab.com/nsnam/ns-3-dev.git
 svn export https://github.com/gridlab-d/tools/branches/klu-build-update/solver_klu/source/KLU_DLL

Choosing and Configuring the Install Directories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These instructions assume you have administrative permissions on /usr/local, and only
need to maintain one version of the build products.  If that's not the case, you
can define an environment variable, e.g., *$TESP_INSTALL*, and use that in place of
/usr/local for installation directories. The following examples are for Ubuntu; 
other flavors of Linux may differ.

For Ubuntu in a *virtual machine*, first edit or replace the */etc/environment* file.
This is not a script file, and it doesn't support the $variable replacement syntax. If using
$TESP_INSTALL, it has to be spelled out on each line, e.g.:

::

 TESP_INSTALL="/opt/tesp"
 PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/tesp/bin:/opt/tesp:/opt/tesp/PreProcess:/opt/tesp/PostProcess"
 GLPATH="/opt/tesp/lib/gridlabd:/opt/tesp/share/gridlabd"
 CXXFLAGS="-I/opt/tesp/share/gridlabd"
 PYTHONPATH="/opt/tesp/python"
 JAVAPATH="/opt/tesp/java"

If not using $TESP_INSTALL explicitly, it defaults to /usr/local

::

 # add the following four lines
 GLPATH="/usr/local/lib/gridlabd:/usr/local/share/gridlabd"
 CXXFLAGS="-I/usr/local/share/gridlabd"
 PYTHONPATH="/usr/local/python"
 JAVAPATH="/usr/local/java"

For Ubuntu in *WSL*, all changes are made to *~/.profile*.

::

 # optionally, export TESP_INSTALL="somePath"
 # then use $TESP_INSTALL instead of /usr/local in the following exports
 export GLPATH="/usr/local/lib/gridlabd:/usr/local/share/gridlabd"
 export CXXFLAGS="-I/usr/local/share/gridlabd"
 # set up Python and Java to run with HELICS
 export PYTHONPATH="/usr/local/python:$PYTHONPATH"
 export JAVAPATH="/usr/local/java:$JAVAPATH"

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
 make install

The *make install* step may not work on WSL. A manual example is *cp fncs.jar ../../tesp/examples/loadshed/java*

These instructions install HELICS to /usr/local. Use the graphical version of CMake 
for configuring a build with $TESP_INSTALL.

::

 cd ~/src/HELICS-src
 mkdir build
 cd build
 cmake -DBUILD_PYTHON_INTERFACE=ON -DBUILD_JAVA_INTERFACE=ON -DBUILD_SHARED_LIBS=ON \
       -DJAVA_AWT_INCLUDE_PATH=NotNeeded -DHELICS_DISABLE_BOOST=ON \
       -DCMAKE_INSTALL_PREFIX=$TESP_INSTALL -DCMAKE_BUILD_TYPE=Release ..
 # leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
 make -j4
 sudo make install

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

These following instructions install EnergyPlus with FNCS linkage and key portions of the retail v8.3 installation.

::

 cd ~/src/EnergyPlus
 mkdir build
 cd build
 cmake -DCMAKE_INSTALL_PREFIX=$TESP_INSTALL -DBUILD_FORTRAN=ON -DBUILD_PACKAGE=ON -DENABLE_INSTALL_REMOTE=OFF ..
 # leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
 make -j4
 sudo make install

Build eplus_json
~~~~~~~~~~~~~~~~

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

Build ns3 with HELICS
~~~~~~~~~~~~~~~~~~~~~

First, in order to build ns-3 with Python bindings, we need to install the Python
binding generator that it uses, and then manually patch one of the ns-3 build files.

::
 
 pip3 install pybindgen
 pip3 show pybindgen
 # edit line 17 of ~/src/ns-3-dev/bindings/python/wscript to specify the correct matching version, for example:
 REQUIRED_PYBINDGEN_VERSION = '0.20.1'

Then, we can build ns-3, install that into the same location as other parts of TESP, and test it:

::

 cd ~/src/ns-3-dev
 git clone https://github.com/GMLC-TDC/helics-ns3 contrib/helics
 # --with-helics may not be left blank, so use either $TESP_INSTALL or /usr/local
 ./waf configure --build-profile=optimized --prefix=$TESP_INSTALL --with-helics=$TESP_INSTALL --disable-werror --enable-examples --enable-tests
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


