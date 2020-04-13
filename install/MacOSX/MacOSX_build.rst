.. _BuildingOnMacOSX:

Building on Mac OS X
--------------------

This procedure builds all components from scratch. If you've already
built GridLAB-D on your machine, please take note of the specific
GitHub branch requirements for TESP:

- feature/1173 for GridLAB-D
- develop for FNCS
- fncs-v8.3.0 for EnergyPlus

The Mac OS X build procedure is very similar to that for Linux,
and should be executed from the Terminal. For consistency among
platforms, this procedure uses gcc rather than clang. It's also
assumed that Homebrew has been installed.

It may also be necessary to disable system integrity protection (SIP),
in order to modify contents under */usr*. Workarounds to set the
*LD_LIBRARY_PATH* and *DYLD_LIBRARY_PATH* environment variables 
have not been tested successfully.

When you finish the build, try :ref:`RunExamples`.

Build GridLAB-D
~~~~~~~~~~~~~~~

Follow these directions:

::

 http://gridlab-d.shoutwiki.com/wiki/Mac_OSX/Setup

Install Python Packages, Java, updated GCC
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 # install Python 3.7+ from Conda
 # tesp_support, including verification of PYPOWER dependency
 pip install tesp_support
 opf

 brew install gcc-9

 # also need Java, Cmake, autoconf, libtool

Checkout PNNL repositories from github
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 mkdir ~/src
 cd ~/src
 git config --global (specify user.name, user.email, color.ui)
 git clone -b develop https://github.com/FNCS/fncs.git
 git clone -b feature/1173 https://github.com/gridlab-d/gridlab-d.git
 git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git
 git clone -b develop https://github.com/pnnl/tesp.git
 git clone -b master https://github.com/GMLC-TDC/HELICS-src

FNCS with Prerequisites (installed to /usr/local)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your Java version may have removed *javah*.  If that's the case, use *javac -h* instead.

::

 brew install zeromq
 brew install czmq

 cd ../fncs
 autoreconf -isf
 ./configure --with-zmq=/usr/local --with-czmq=/usr/local 'CPP=gcc-9 -E' 'CXXPP=g++-9 -E' 'CC=gcc-9' 'CXX=g++-9' 'CXXFLAGS=-w -O2 -mmacosx-version-min=10.12' 'CFLAGS=-w -O2 -mmacosx-version-min=10.12'
 make
 sudo make install

 cd java
 mkdir build
 cd build
 cmake -DCMAKE_C_COMPILER="gcc-9" -DCMAKE_CXX_COMPILER="g++-9" ..
 make
 # copy jar and jni library to  tesp/examples/loadshed/java

HELICS (installed to /usr/local, build with gcc9)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To build HELICS:

::

 cd ~/src/HELICS-src
 rm -r build
 mkdir build
 cd build
 cmake -DCMAKE_INSTALL_PREFIX="/usr/local" -DBUILD_PYTHON_INTERFACE=ON -DBUILD_JAVA_INTERFACE=ON -DBUILD_SHARED_LIBS=ON -DJAVA_AWT_INCLUDE_PATH=NotNeeded -DHELICS_DISABLE_BOOST=ON -DCMAKE_C_COMPILER=/usr/local/bin/gcc-9 -DCMAKE_CXX_COMPILER=/usr/local/bin/g++-9 ../
 make clean
 make -j 4
 sudo make install

To test HELICS:

 helics_player --version
 helics_recorder --version
 ipython
 import helics
 helics.helicsGetVersion()
 quit

Add this to .bash_profile

::

 export PYTHONPATH=/usr/local/python:$PYTHONPATH

GridLAB-D with Prerequisites (installed to /usr/local)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you encounter build errors with GridLAB-D, please try
adding *-std=c++14* to *CXXFLAGS*.

::

 brew install xerces-c

 cd ~/src/gridlab-d
 autoreconf -isf

 ./configure --with-fncs=/usr/local --with-helics=/usr/local --enable-silent-rules 'CPP=gcc-9 -E' 'CXXPP=g++-9 -E' 'CC=gcc-9' 'CXX=g++-9' 'CXXFLAGS=-O2 -w -std=c++14' 'CFLAGS=-O2 -w' LDFLAGS='-w'

 sudo make
 sudo make install
 # TODO - set the GLPATH?
 gridlabd --validate 

ns-3 with HELICS
~~~~~~~~~~~~~~~~

::

 # consider -g flags on CXX, C and LD if debugging
 cd ~/src
 git clone https://gitlab.com/nsnam/ns-3-dev.git
 cd ns-3-dev
 git clone https://github.com/GMLC-TDC/helics-ns3 contrib/helics
 ./waf configure --with-helics=/usr/local --disable-werror --enable-examples --enable-tests 'CPP=gcc-9 -E' 'CXXPP=g++-9 -E' 'CC=gcc-9' 'CXX=g++-9' 'CXXFLAGS=-w -std=c++14' 'CFLAGS=-w' LDFLAGS='-w'
 ./waf build

EnergyPlus with Prerequisites (installed to /usr/local)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src/EnergyPlus
 mkdir build
 cd build
 cmake -DCMAKE_C_COMPILER="gcc-9" -DCMAKE_CXX_COMPILER="g++-9" ..
 make

 # Before installing, we need components of the public version, including but not limited 
 #   to the critical Energy+.idd file
 # The compatible public version is at https://github.com/NREL/EnergyPlus/releases/tag/v8.3.0
 # That public version should be installed to /usr/local/EnergyPlus-8-3-0 before going further

 sudo make install

 # Similar to the experience with Linux and Windows, this installation step wrongly puts
 #  the build products in /usr/local instead of /usr/local/bin and /usr/local/lib
 #  the following commands will copy FNCS-compatible EnergyPlus over the public version
 cd /usr/local
 cp energyplus-8.3.0 bin
 cp libenergyplusapi.8.3.0.dylib lib

 # if ReadVarsESO not found at the end of a simulation, try this
 /usr/local/EnergyPlus-8-3-0$ sudo ln -s PostProcess/ReadVarsESO ReadVarsESO

Build eplus_agent
~~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/src/energyplus
 # the following steps are also in go.sh
 autoheader
 aclocal
 automake --add-missing
 # edit configure.ac to use g++-9 on Mac
 autoconf
 ./configure --prefix=/usr/local --with-zmq=/usr/local --with-czmq=/usr/local
 make
 sudo make install


