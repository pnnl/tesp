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

 brew install python3
 pip install pandas
 # tesp_support, including verification of PYPOWER dependency
 pip install tesp_support
 opf

 brew install gcc

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

 cd ~/src
 wget --no-check-certificate http://download.zeromq.org/zeromq-4.1.3.tar.gz
 tar -xzf zeromq-4.1.3.tar.gz
 cd zeromq-4.1.3
 ./configure --without-libsodium 'CPP=gcc-7 -E' 'CXXPP=g++-7 -E' 'CC=gcc-7' 'CXX=g++-7'
 make
 sudo make install

 cd ..
 wget --no-check-certificate http://download.zeromq.org/czmq-3.0.2.tar.gz
 tar -xzf czmq-3.0.2.tar.gz
 cd czmq-3.0.2
 ./configure 'CPP=gcc-7 -E' 'CXXPP=g++-7 -E' 'CC=gcc-7' 'CXX=g++-7' 'CPPFLAGS=-Wno-format-truncation'
 make
 sudo make install

 cd ../fncs
 autoreconf -if
 ./configure 'CPP=gcc-7 -E' 'CXXPP=g++-7 -E' 'CC=gcc-7' 'CXX=g++-7' 'CXXFLAGS=-w -mmacosx-version-min=10.12' 'CFLAGS=-w -mmacosx-version-min=10.12'
 make
 sudo make install

 cd java
 mkdir build
 cd build
 cmake -DCMAKE_C_COMPILER="gcc-7" -DCMAKE_CXX_COMPILER="g++-7" ..
 make
 # copy jar and jni library to  tesp/examples/loadshed/java

Boost and HELICS (installed to /usr/local, build with gcc7)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Based on https://github.com/GMLC-TDC/HELICS-src/issues/641#issuecomment-470663933

Build zmq 4.1.6 and czmq 4.2.0

::

 cd ~/src
 tar -xzf boost_1_64_0.tar.gz
 cd boost_1_64_0
 ./bootstrap.sh --with-libraries=program_options,filesystem,system,test

Modify project_config.jam as directed at https://solarianprogrammer.com/2018/08/07/compiling-boost-gcc-clang-macos/

For example, using gcc 7.3 instead of 8.1, part of the file should look like this:

::

 # if ! darwin in [ feature.values <toolset> ]
 # {
 #     using darwin ; 
 # }

 # project : default-build <toolset>darwin ;
 using gcc : 7.3 : /usr/local/bin/g++-7 ;

Then issue the following commands to build and test:

::

 sudo ./b2 cxxflags=-std=c++14 install
 g++-7 -std=c++14 test.cpp -o test -lboost_system -lboost_filesystem
 ./test

To build HELICS:

::

 brew install swig
 cd ~/src/HELICS-src
 rm -r build
 mkdir build
 cd build
 cmake -DCMAKE_INSTALL_PREFIX="/usr/local" -DBOOST_ROOT="/usr/local" -DBUILD_PYTHON_INTERFACE=ON -DUSE_BOOST_STATIC_LIBS=ON -DCMAKE_C_COMPILER=/usr/local/bin/gcc-7 -DCMAKE_CXX_COMPILER=/usr/local/bin/g++-7 ../
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

 cd ~/src/gridlab-d
 autoreconf -isf

 cd third_party
 tar -xvzf xerces-c-3.2.0.tar.gz
 cd xerces-c-3.2.0
 ./configure 'CPP=gcc-7 -E' 'CXXPP=g++-7 -E' 'CC=gcc-7' 'CXX=g++-7' 'CXXFLAGS=-w' 'CFLAGS=-w'
 make
 sudo make install
 cd ../..

 ./configure --with-fncs=/usr/local --with-helics=/usr/local --enable-silent-rules 'CPP=gcc-7 -E' 'CXXPP=g++-7 -E' 'CC=gcc-7' 'CXX=g++-7' 'CXXFLAGS=-w -std=c++14' 'CFLAGS=-w' LDFLAGS='-g -w'

 sudo make
 sudo make install
 # TODO - set the GLPATH?
 gridlabd --validate 

ns-3 with HELICS
~~~~~~~~~~~~~~~~

::

 cd ~/src
 git clone https://gitlab.com/nsnam/ns-3-dev.git
 cd ns-3-dev
 git clone https://github.com/GMLC-TDC/helics-ns3 contrib/helics
 ./waf configure --with-helics=/usr/local --disable-werror --enable-examples --enable-tests 'CPP=gcc-7 -E' 'CXXPP=g++-7 -E' 'CC=gcc-7' 'CXX=g++-7' 'CXXFLAGS=-w -std=c++14' 'CFLAGS=-w' LDFLAGS='-g -w'
 ./waf build

EnergyPlus with Prerequisites (installed to /usr/local)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 sudo apt-get install libjsoncpp-dev
 cd ~/src/EnergyPlus
 mkdir build
 cd build
 cmake -DCMAKE_C_COMPILER="gcc-7" -DCMAKE_CXX_COMPILER="g++-7" ..
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

Build eplus_json
~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/src/energyplus
 # the following steps are also in go.sh
 autoheader
 aclocal
 automake --add-missing
 autoconf
 # edit configure.ac to use g++-7 on Mac
 ./configure
 make
 sudo make install


