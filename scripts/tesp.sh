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
# Here is how to start the environment and pycharm and capture pycharm log for any errors
#   source ~/grid/tesp/tesp.env
#   pycharm-community &> ~/charm.log&

#alternatives command line for java or python
#sudo update-alternatives --config java

# repo for git
# sudo add-apt-repository ppa:git-core/ppa

while true; do
    # shellcheck disable=SC2162
    read -p "Do you wish to build the binaries? (Yy/Nn)" yn
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
#if [[ ${lv[0]} -eq 18 ]]; then
#  sudo apt-get update
#  tk="python3-tk"
#elif [[ ${lv[0]} -eq 20 ]]; then
#  sudo apt-get update
#  tk="python3-tk"
#elif [[ ${lv[0]} -eq 22 ]]; then
#  sudo add-apt-repository ppa:deadsnakes/ppa -y
#  sudo apt-get update
#  tk="python3.8-tk"
#else
#  echo "**************************************************"
#  echo "$(cat /etc/issue), not supported for TESP"
#  echo "**************************************************"
#  exit
#fi

# add build tools for compiling
sudo apt-get -y upgrade
sudo apt-get -y install pkgconf \
git \
build-essential \
autoconf \
libtool \
libjsoncpp-dev \
gfortran \
install cmake \
subversion \
unzip

# add tools/libs for Java support, HELICS, FNCS, GridLAB-D, Ipopt/cbc
sudo apt-get -y install openjdk-11-jdk \
libzmq5-dev \
libczmq-dev \
libboost-dev \
libxerces-c-dev \
libhdf5-serial-dev \
libsuitesparse-dev \
coinor-cbc \
coinor-libcbc-dev \
coinor-libipopt-dev \
liblapack-dev \
libmetis-dev \
python3-venv \
python3-pip \
python3-tk \
python3-pil.imagetk
#sudo apt-get -y install python3.8
#sudo apt-get -y install python3.8-venv
#sudo apt-get -y install python3-pip
#sudo apt-get -y install ${tk}
#sudo apt-get -y install python3-pil.imagetk

sudo ln -sf /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java

echo
if [[ -z $1 && -z $2 ]]; then
  echo "No user name set for git repositories!"
else
  git config --global user.name "$1"
  git config --global user.email "$2"
  echo "User .name=$1 and .email=$2 have been set for git repositories!"
fi
git config --global credential.helper store

cd "${HOME}" || exit
echo "Install environment to $HOME/grid"
mkdir -p grid
cd grid || exit

echo
echo "Install a virtual python environment to $HOME/grid/venv"
python3 -m pip install --upgrade pip
python3 -m pip install virtualenv
"${HOME}/.local/bin/virtualenv" venv --prompt GRID

echo
echo "Install executables environment to $HOME/grid/tenv"
mkdir -p tenv

if [[ ${lv[0]} -eq 18 ]]; then
  if [[ $binaries == "develop" ]]; then
    # To compile with helics>=3.1 gridlabd>=5.0 need to upgrade cmake and g++-9 for ubuntu 18.04
    wget --no-check-certificate https://github.com/Kitware/CMake/releases/download/v3.24.2/cmake-3.24.2-linux-x86_64.sh
    chmod 755 cmake-3.24.2-linux-x86_64.sh
    ./cmake-3.24.2-linux-x86_64.sh --skip-license --prefix="$HOME/grid/tenv"
    rm -f cmake-3.24.2-linux-x86_64.sh
  fi
  sudo add-apt-repository ppa:ubuntu-toolchain-r/test -y
  sudo apt-get update
  sudo apt-get -y install gcc-9 g++-9
  sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60 --slave /usr/bin/g++ g++ /usr/bin/g++-9
  sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 60 --slave /usr/bin/g++ g++ /usr/bin/g++-7
fi

echo "Clone directory structure for TESP"
echo ++++++++++++++ TESP
if [[ ! -d "$HOME/grid/tesp" ]]; then
  git clone -b main https://github.com/pnnl/tesp.git
fi

echo "Activate Virtual Environment..."
. tesp/tesp.env

# The rest of the build/install depends on the exports in the tespEnv file
which python > "${BUILD_DIR}/tesp_pypi.log" 2>&1

echo "Install grid applications software to $HOME/grid/repo"
mkdir -p repo
cd repo || exit

echo
echo "Download all relevant repositories..."
echo
echo ++++++++++++++ PSST
if [[ ! -d "${REPO_DIR}/AMES-V5.0" ]]; then
  # git clone -b master https://github.com/ames-market/psst.git
  # For dsot
  git clone -b master https://github.com/ames-market/AMES-V5.0.git
  "${BUILD_DIR}/patch.sh" AMES-V5.0 AMES-V5.0
fi

if [[ $binaries == "develop" ]]; then
  echo
  echo ++++++++++++++ FNCS
  if [[ ! -d "${REPO_DIR}/fncs" ]]; then
    git clone -b feature/opendss https://github.com/FNCS/fncs.git
    # For different calling no cpp
    # git clone -b develop https://github.com/FNCS/fncs.git
    "${BUILD_DIR}/patch.sh" fncs fncs
  fi

  echo
  echo ++++++++++++++ HELICS
  if [[ ! -d "${REPO_DIR}/HELICS-src" ]]; then
    git clone -b main https://github.com/GMLC-TDC/HELICS-src
    "${BUILD_DIR}/patch.sh" HELICS-src HELICS-src
  fi

  echo
  echo ++++++++++++++ GRIDLAB
  if [[ ! -d "${REPO_DIR}/gridlab-d" ]]; then
    git clone -b master https://github.com/gridlab-d/gridlab-d.git
    "${BUILD_DIR}/patch.sh" gridlab-d gridlab-d
  fi

  echo
  echo ++++++++++++++ ENERGYPLUS
  if [[ ! -d "${REPO_DIR}/EnergyPlus" ]]; then
    git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git
    "${BUILD_DIR}/patch.sh" EnergyPlus EnergyPlus
  fi

  echo
  echo ++++++++++++++ NS-3
  if [[ ! -d "${REPO_DIR}/ns-3-dev" ]]; then
    git clone -b master https://gitlab.com/nsnam/ns-3-dev.git
    "${BUILD_DIR}/patch.sh" ns-3-dev ns-3-dev
  fi

  echo
  echo ++++++++++++++ HELICS-NS-3
  if [[ ! -d "${REPO_DIR}/ns-3-dev/contrib/helics" ]]; then
    git clone -b main https://github.com/GMLC-TDC/helics-ns3 ns-3-dev/contrib/helics
    "${BUILD_DIR}/patch.sh" ns-3-dev/contrib/helics helics-ns3
  fi

  echo
  echo ++++++++++++++ KLU SOLVER
  if [[ ! -d "${REPO_DIR}/KLU_DLL" ]]; then
    unzip -q "${BUILD_DIR}/KLU_DLL.zip" -d ./KLU_DLL
  fi
fi

# Compile all relevant executables
cd "${BUILD_DIR}" || exit
./build_c.sh $binaries
