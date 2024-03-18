#!/bin/bash

# Copyright (c) 2021-2023 Battelle Memorial Institute
# file: tesp.sh


# You should get familiar with the command line to have good success with TESP
# As such, you may want to run in remote shh terminal.
# Here is to how to install and configured ssh server
#   sudo apt-get -y install openssh-server
#   sudo nano /etc/ssh/sshd_config
# Once you open the file, find and change the uncomment line: # Port 22
#   sudo service ssh start
#   sudo systemctl status ssh


# From terminal in the VM, enter the these lines to build
#   cd
#	  wget --no-check-certificate https://raw.githubusercontent.com/pnnl/tesp/main/scripts/tesp.sh
# if vpn is used --no-check-certificate in wget command line
#	  chmod 755 tesp.sh
# Set the the first and second parameter on the command line:
#	  ./tesp.sh username username@email

# If you would to use and IDE here's to install snap Pycharm IDE for python
#   sudo snap install pycharm-community --classic
# Here is how to start pycharm and capture pycharm log for any errors
#   pycharm-community &> ~/charm.log&


#alternatives command line for java or python
#sudo update-alternatives --config java

# repo for git
# sudo add-apt-repository ppa:git-core/ppa

while true; do
    # shellcheck disable=SC2162
    read -p "Do you wish to build the binaries? " yn
    case $yn in
        [Yy]* ) binaries="develop"; break;;
        [Nn]* ) binaries="copy"; break;;
        * ) echo "Please answer [y]es or [n]o.";;
    esac
done

# repo for git
# sudo add-apt-repository ppa:git-core/ppa

# Some support depends on linux version
lv=( $(cat /etc/issue) )
lv=( ${lv[1]//./ } )
if [[ ${lv[0]} -eq 18 ]]; then
  sudo apt-get update
  tk="python3-tk"
elif [[ ${lv[0]} -eq 20 ]]; then
  sudo apt-get update
  tk="python3-tk"
elif [[ ${lv[0]} -eq 22 ]]; then
  sudo add-apt-repository ppa:deadsnakes/ppa -y
  sudo apt-get update
  tk="python3.8-tk"
else
  echo "**************************************************"
  echo "$(cat /etc/issue), not supported for TESP"
  echo "**************************************************"
  exit
fi

# build tools
sudo apt-get -y upgrade
sudo apt-get -y install pkgconf
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
sudo ln -sf /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java

# for HELICS and FNCS
sudo apt-get -y install libzmq5-dev
sudo apt-get -y install libczmq-dev
sudo apt-get -y install libboost-dev

# for GridLAB-D
sudo apt-get -y install libxerces-c-dev
sudo apt-get -y install libhdf5-serial-dev

# for solvers used by AMES/Agents/GridLAB-D
# needed for KLU
sudo apt-get -y install libsuitesparse-dev
# end users replace libsuitesparse-dev with libklu1, which is licensed LGPL
# needed for Ipopt/cbc
sudo apt-get -y install coinor-cbc
sudo apt-get -y install coinor-libcbc-dev
sudo apt-get -y install coinor-libipopt-dev
sudo apt-get -y install liblapack-dev
sudo apt-get -y install libmetis-dev

sudo apt-get -y install python3.8
sudo apt-get -y install python3.8-venv
sudo apt-get -y install python3-pip
sudo apt-get -y install ${tk}
sudo apt-get -y install python3-pil.imagetk

echo
if [[ -z $1 && -z $2 ]]; then
  echo "No user name set for git repositories!"
else
  git config --global user.name "$1"
  git config --global user.email "$2"
  echo "User .name=$1 and .email=$2 have been set for git repositories!"
fi
git config --global credential.helper store

echo
echo "Clone directory structure for TESP"
echo ++++++++++++++ TESP
git clone -b main https://github.com/pnnl/tesp.git
echo "Copy TESP environment variables to $HOME/tespEnv for shell scripts"
cp tesp/scripts/tespEnv "$HOME/"
. "${HOME}/tespEnv"
cd tesp || exit

echo "Install a virtual python environment to $HOME/tesp/venv"
python3.8 -m pip install --upgrade pip
python3.8 -m pip install virtualenv
"${HOME}/.local/bin/virtualenv" venv --prompt TESP

echo "Install executables environment to $HOME/tesp/tenv"
mkdir -p tenv
if [[ ${lv[0]} -eq 18 ]]; then
  if [[ $binaries == "develop" ]]; then
    # To compile with helics>=3.1 gridlabd>=5.0 need to upgrade cmake and g++-9 for ubuntu 18.04
    wget --no-check-certificate https://github.com/Kitware/CMake/releases/download/v3.24.2/cmake-3.24.2-linux-x86_64.sh
    chmod 755 cmake-3.24.2-linux-x86_64.sh
    ./cmake-3.24.2-linux-x86_64.sh --skip-license --prefix="$HOME/tesp/tenv"
    rm -f cmake-3.24.2-linux-x86_64.sh
  fi
  sudo add-apt-repository ppa:ubuntu-toolchain-r/test -y
  sudo apt-get update
  sudo apt-get -y install gcc-9 g++-9
  sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9
  sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 60 --slave /usr/bin/g++ g++ /usr/bin/g++-7
fi

echo "Install repositories to $HOME/tesp/repository"
mkdir -p repository
cd repository || exit
echo
echo "Download all relevant repositories..."

echo
echo ++++++++++++++ PSST
# git clone https://github.com/ames-market/psst.git
git clone -b master https://github.com/ames-market/AMES-V5.0.git
"${TESPBUILD}/patch.sh" AMES-V5.0 AMES-V5.0

if [[ $binaries == "develop" ]]; then
  echo
  echo ++++++++++++++ FNCS
  git clone -b feature/opendss https://github.com/FNCS/fncs.git
  #For dsot
  #git clone -b develop https://github.com/FNCS/fncs.git
  "${TESPBUILD}/patch.sh" fncs fncs

  echo
  echo ++++++++++++++ HELICS
  git clone -b main https://github.com/GMLC-TDC/HELICS-src
  "${TESPBUILD}/patch.sh" HELICS-src HELICS-src

  echo
  echo ++++++++++++++ GRIDLAB
  #develop - dec21 commit number for dsot
  #ENV GLD_VERSION=6c983d8daae8c6116f5fd4d4ccb7cfada5f8c9fc
  git clone -b master https://github.com/gridlab-d/gridlab-d.git
  "${TESPBUILD}/patch.sh" gridlab-d gridlab-d

  echo
  echo ++++++++++++++ ENERGYPLUS
  git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git
  "${TESPBUILD}/patch.sh" EnergyPlus EnergyPlus

  echo
  echo ++++++++++++++ NS-3
  git clone -b master https://gitlab.com/nsnam/ns-3-dev.git
  "${TESPBUILD}/patch.sh" ns-3-dev ns-3-dev

  echo
  echo ++++++++++++++ HELICS-NS-3
  git clone -b main https://github.com/GMLC-TDC/helics-ns3 ns-3-dev/contrib/helics
  "${TESPBUILD}/patch.sh" ns-3-dev/contrib/helics helics-ns3

  echo
  echo ++++++++++++++ KLU SOLVER
  svn export https://github.com/gridlab-d/tools/solver_klu/source/KLU_DLL
fi

# Compile all relevant executables
cd "${TESPBUILD}" || exit
./tesp_c.sh $binaries
