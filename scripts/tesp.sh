#!/bin/bash

# From termial in the VM, enter the these lines to build
#   cd
#	  wget https://raw.githubusercontent.com/pnnl/tesp/evolve/scripts/tesp.sh
# if vpn is used --no-check-certificate in wget command line
#	  chmod 755 tesp.sh
# Set the the first and second parameter on the command line:
#	  ./tesp.sh username username@email


# If you want to run as shh this has to be installed and configured
#  sudo -get -y install openssh-server
#  sudo nano /etc/ssh/sshd_config
# Once you open the file, find and change the uncomment line: # Port 22 
#  sudo service ssh start
#  sudo systemctl status ssh


#alternatives command line for java or python
#sudo update-alternatives --config java


# build tools
sudo apt-get update
sudo apt-get -y upgrade
sudo apt-get -y install git
sudo apt-get -y install build-essential
sudo apt-get -y install autoconf
sudo apt-get -y install libtool
sudo apt-get -y install libjsoncpp-dev
sudo apt-get -y install gfortran
sudo apt-get -y install cmake
sudo apt-get -y install subversion
sudo apt-get -y install unzip

# Java support
sudo apt-get -y install openjdk-11-jdk
sudo ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java

# for HELICS and FNCS
sudo apt-get -y install libzmq5-dev
sudo apt-get -y install libczmq-dev
sudo apt-get -y install libboost-dev

# for GridLAB-D
sudo apt-get -y install libxerces-c-dev
sudo apt-get -y install libhdf5-serial-dev
sudo apt-get -y install libsuitesparse-dev
# end users replace libsuitesparse-dev with libklu1, which is licensed LGPL

# for solvers Ipopt/cbc used by AMES/Agents
sudo apt-get -y install coinor-cbc
sudo apt-get -y install coinor-libcbc-dev
sudo apt-get -y install coinor-libipopt-dev
sudo apt-get -y install liblapack-dev
sudo apt-get -y install libmetis-dev

# Python support
# if not using miniconda (avoid Python 3.7 on Ubuntu for now)
sudo apt-get -y install python3-pip
sudo apt-get -y install python3-tk


echo
echo "Set create directory structure for TESP"
cd $HOME
mkdir -p grid
cd grid || exit
mkdir -p repository
mkdir -p installed
mkdir -p software
# Download all relevant repositories
cd repository || exit

echo
if [[ -z $1 && -z $2 ]]; then
  echo "No user name set for git repositories!"
else
  git config --global user.name $1
  git config --global user.email $2
  echo "User name $1 set for git repositories!"
fi
git config --global credential.helper store

echo
echo ++++++++++++++ FNCS
git clone -b develop https://github.com/FNCS/fncs.git

echo
echo ++++++++++++++ HELICS
git clone -b helics2 https://github.com/GMLC-TDC/HELICS-src
#git clone -b main https://github.com/GMLC-TDC/HELICS-src

echo
echo ++++++++++++++ GRIDLAB
#develop - dec21 commit number for dsot
#ENV GLD_VERSION=6c983d8daae8c6116f5fd4d4ccb7cfada5f8c9fc
git clone -b develop https://github.com/gridlab-d/gridlab-d.git

echo
echo ++++++++++++++ ENERGYPLUS
git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git

echo
echo ++++++++++++++ TESP
git clone -b evolve https://github.com/pnnl/tesp.git
# need for back port of DSOT
# git clone -b master https://stash.pnnl.gov/scm/tesp/tesp-private.git

echo
echo ++++++++++++++ NS3
git clone https://gitlab.com/nsnam/ns-3-dev.git
cd ns-3-dev || exit
git clone -b feature/13b https://github.com/GMLC-TDC/helics-ns3 contrib/helics
cd ..
git clone https://github.com/gjcarneiro/pybindgen.git

echo
echo ++++++++++++++ PSST
git clone https://github.com/ames-market/psst.git

echo
echo ++++++++++++++ KLU SOLVER
svn export https://github.com/gridlab-d/tools/branches/klu-build-update/solver_klu/source/KLU_DLL

# Install snap Pycharm IDE for python
# sudo snap install pycharm-community --classic

# to Run pycharm
# pycharm-community &> ~/charm.log&

# Compile all relevant executables
cd tesp/scripts 
./tesp_c.sh
