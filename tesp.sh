#!/bin/bash


#sudo apt-get -y install openssh-server
#sudo nano /etc/ssh/sshd_config
#Once you open the file, find and change the uncomment line: # Port 22 

# build tools
sudo apt-get -y install apt-utils
sudo apt-get -y install git
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
sudo apt-get -y install libhdf5-serial-dev
sudo apt-get -y install libsuitesparse-dev
# end users replace libsuitesparse-dev with libklu1, which is licensed LGPL

# for AMES market simulator
sudo apt-get -y install coinor-cbc
#need ipopt support

# Python support
# if not using miniconda (avoid Python 3.7 on Ubuntu for now)
sudo apt-get -y install python3-pip
sudo apt-get -y install python3-tk

#              coinor-libcbc-dev \
##              default-jdk \
##              default-jre \
#              gosu \
##              libboost-dev \
##              libboost-filesystem-dev \
##              libboost-program-options-dev \
##              libboost-signals-dev \
##              libboost-test-dev \
#              libmetis-dev \
#              libxerces-c-dev \
#              lsof \
#              make \
#              pkg-config \
#              python-minimal \
#              python-pip \
#              python3 \
#              python3-dev \
##              swig \
#              unzip \
#              uuid-dev \
#              wget \

# Install all pip libraries
pip install wheel colorama glm seaborn matplotlib networkx==2.3 numpy pandas pulp pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py xlrd

# Set create directory structure for grid repository and installed software
mkdir grid
cd grid
mkdir repository
mkdir installed
mkdir software

# Download all relevant repositories
cd repository
# Set your name and email address
#git config --global user.name "your user name"
#git config --global user.email "your email"
#git config --global credential.helper store
#develop for dsot
git clone -b develop https://github.com/FNCS/fncs.git
#feature/opendss for tesp
#git clone -b feature/opendss https://github.com/FNCS/fncs.git
git clone -b main https://github.com/GMLC-TDC/HELICS-src
# develop - dec21 commit number for dsot
# ENV GLD_VERSION=6c983d8daae8c6116f5fd4d4ccb7cfada5f8c9fc
git clone -b develop https://github.com/gridlab-d/gridlab-d.git
git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git
git clone -b master https://stash.pnnl.gov/scm/tesp/tesp-private.git
git clone -b develop https://github.com/pnnl/tesp.git
git clone https://gitlab.com/nsnam/ns-3-dev.git
#git clone https://github.com/ames-market/psst.git
svn export https://github.com/gridlab-d/tools/branches/klu-build-update/solver_klu/source/KLU_DLL

# Install snap Pycharm IDE for python
# sudo snap install pycharm-community --classic

# to Run pycharm
# pycharm-community &> ~/charm.log&

# Compile all relevant executables
./tespCompile.sh