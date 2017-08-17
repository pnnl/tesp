The Mac OS X build procedure is very similar to that for Linux,
and should be executed from the Terminal. For consistency among
platforms, this procedure uses gcc rather than clang.

Xterm setup for Mac OS X (XQuartz) and Windows (MobaXterm)
==========================================================

# This may be necessary for XQuartz
sudo apt-get install xauth

# This is what works for Mac OS X via XQuartz, (i.e. -X fails)
# the MobaXterm connection is similar.
ssh -Y admsuser@tesp-ubuntu.pnl.gov

Build GridLAB-D
===============

http://gridlab-d.shoutwiki.com/wiki/Mac_OSX/Setup

Install Python, Java and some other tools
=========================================

cd /opt
# may need sudo on the following steps to install for all users
wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh
conda update conda
conda install matplotlib
conda install scipy
conda install pandas

brew install gcc

# Java, Cmake, autoconf, libtool

Checkout PNNL repositories from github
======================================

mkdir ~/src
cd ~/src
git config --global (specify user.name, user.email, color.ui)

git clone -b feature/transactiveEnergyApi https://github.com/FNCS/fncs.git

git clone -b feature/1048 https://github.com/gridlab-d/gridlab-d.git

git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git

git clone -b master https://github.com/pnnl/tesp.git

FNCS with Prerequisites (installed to /usr/local)
=================================================

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
./configure 'CPP=gcc-7 -E' 'CXXPP=g++-7 -E' 'CC=gcc-7' 'CXX=g++-7' 'CXXFLAGS=-w' 'CFLAGS=-w'
make
sudo make install

cd java
mkdir build
cd build
cmake -DCMAKE_C_COMPILER="gcc-7" -DCMAKE_CXX_COMPILER="g++-7" ..
make
# copy jar and jni library to  tesp/src/java

GridLAB-D with Prerequisites (installed to /usr/local)
======================================================

cd ~/src/gridlab-d
autoreconf -isf

cd third_party
tar -xvzf xerces-c-3.1.1.tar.gz
cd xerces-c-3.1.1
./configure 'CPP=gcc-7 -E' 'CXXPP=g++-7 -E' 'CC=gcc-7' 'CXX=g++-7' 'CXXFLAGS=-w' 'CFLAGS=-w'
make
sudo make install
cd ../..

./configure --with-fncs=/usr/local 'CPP=gcc-7 -E' 'CXXPP=g++-7 -E' 'CC=gcc-7' 'CXX=g++-7' 'CXXFLAGS=-w' 'CFLAGS=-w'

sudo make
sudo make install
# TODO - set the GLPATH?
gridlabd --validate 

EnergyPlus with Prerequisites (installed to /usr/local)
=======================================================

sudo apt-get install libjsoncpp-dev
cd ~/src/EnergyPlus
mkdir build
cd build
cmake -DCMAKE_C_COMPILER="gcc-7" -DCMAKE_CXX_COMPILER="g++-7" ..
make

# Before installing, we need components of the public version, including but not limited to the critical Energy+.idd file
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
================

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

PYPOWER
=======

pip install pypower
opf # Should run correctly

TESP Uses TCP/IP port 5570 for communication
============================================
1.	"lsof -i :5570" will show all processes connected to port 5570; use this or "ls -al *.log", "ls -al *.json", "ls -al *.csv" to show progress of a case solution
2.	"./kill5570.sh" will terminate all processes connected to port 5570; if you have to do this, make sure "lsof -i :5570" shows nothing before attempting another case

TestCase1 - verifies GridLAB-D and Python over FNCS 
===================================================
1.  cd ~/src/tesp/examples/loadshed
2.	python glm_dict.py loadshed
3.	./run.sh
4.	python plot_loadshed.py loadshed

TestCase1j - verifies GridLAB-D and Java over FNCS
==================================================
same as TestCase1, except
3.  ./runjava.sh

TestCase2 - verifies EnergyPlus over FNCS
=========================================
1.  cd ~/src/tesp/examples/energyplus
2.	./run.sh
3.	python process_eplus.py eplus

TestCase3 - verifies PYPOWER over FNCS
======================================
1.  cd ~/src/tesp/examples/pypower
2.	./runpp.sh
3.	python process_pypower.py ppcase

TestCase4 - 30 houses, 1 school, 4 generators over FNCS
=======================================================
1.  cd ~/src/tesp/examples/te30
2.	python prep_agents.py TE_Challenge
3.	python glm_dict.py TE_Challenge
4.	./run30.sh
5.  # the simulation takes about 10 minutes, use "cat TE*.csv" to show progress up to 172800 seconds
6.	python process_eplus.py te_challenge
7.	python process_pypower.py te_challenge
8.	python process_agents.py te_challenge
9.	python process_gld.py te_challenge

SGIP1b - 1594 houses, 1 school, 4 generators over FNCS
======================================================
1.  cd ~/src/tesp/examples/sgip1
2.	python prep_agents.py SGIP1b
3.	python glm_dict.py SGIP1b
4.	./runSGIP1b.sh
5.  # the simulation takes about 120 minutes, use "cat SGIP*.csv" to show progress up to 172800 seconds
6.	python process_eplus.py SGIP1b
7.	python process_pypower.py SGIP1b
8.	python process_agents.py SGIP1b
9.	python process_gld.py SGIP1b


