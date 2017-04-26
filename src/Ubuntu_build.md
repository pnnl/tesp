Xterm setup
===========

# I did this via console terminal before XQuartz worked ... may not be necessary
sudo apt-get install xauth

# This is what works for Mac OS X via XQuartz, (i.e. -X fails)
# the MobaXterm connection is similar.
ssh -Y admsuser@172.20.128.10

Prep Steps - Python and some other tools
========================================

sudo apt-get install git
sudo apt-get install build-essential

cd /opt
# may need sudo on the following steps to install for all users
wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux_x86_64.sh
conda update conda
conda install matplotlib
conda install scipy
conda install pandas

Checkout PNNL repositories from github
======================================

mkdir ~/src
cd ~/src
git config --global (user.name, user.email, color.ui)

git clone https://github.com/FNCS/fncs.git
cd fncs
git checkout -b transactiveEnergyApi

cd ..
git clone https://github.com/gridlab-d/gridlab-d.git
cd gridlab-d
git checkout -b develop

cd ..
git clone https://github.com/FNCS/EnergyPlus.git
cd EnergyPlus
git checkout -b fncs-v8.3.0

cd ..
git clone https://github.com/pnnl/tesp.git
cd tesp
git checkout -b master

FNCS with Prerequisites (installed to /usr/local)
=================================================

cd ~/src
wget --no-check-certificate http://download.zeromq.org/zeromq-4.1.3.tar.gz
tar -xzf zeromq-4.1.3.tar.gz
cd zeromq-4.1.3
./configure --without-libsodium
make
sudo make install

cd ..
wget --no-check-certificate http://download.zeromq.org/czmq-3.0.2.tar.gz
tar -xzf czmq-3.0.2.tar.gz
cd ../czmq-3.0.2
./configure
make
sudo make install

cd ../fncs
./configure
make
sudo make install

GridLAB-D with Prerequisites (installed to /usr/local)
======================================================

sudo apt install autoconf
sudo apt install libtool
cd ~/src/gridlab-d
autoreconf -isf
cd third_party
bash install_xercesc  # many warnings about changing permissions ... not important?
./configure --with-fncs=/usr/local
make
sudo make install

EnergyPlus with Prerequisites (installed to /usr/local)
=======================================================

sudo apt install cmake
sudo apt-get install libjsoncpp-dev
mkdir build
cd build
cmake ..
make
# Before installing, we need components of the public version as explained in Chad's readme
# So, the public version was installed from https://github.com/NREL/EnergyPlus/releases/tag/v8.3.0

# Similar to the experience with Mac and Windows, this installation step wrongly puts
#  the build products in /usr/local instead of /usr/local/bin and /usr/local/lib
#  Before copying the files and symlinks down to ./bin and ./lib, I noticed that the
#  build version appeared to be 8.4.0 instead of 8.3.0.  Need to investigate the reason.
#  It could be something in the Cmake file, because "git status" verifies the correct branch.
#  We do know that fncs-v8.3.0 is the only branch that works properly.

sudo make install

TODO: build eplus_json
======================

- some problem with automake process, which I am not very familiar with. Makefile could be better.s

TODO: MATPOWER, MCR and wrapper
===============================

- not attempted

TODO: Organize Python and Example files for execution
=====================================================

- see the stash repository files models/matpower/runSGIP1b.sh,
  or models/pypower/run30.sh for how it was done befoe

