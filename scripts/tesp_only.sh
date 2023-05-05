#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: tesp_only.sh

# From terminal in the VM, enter the these lines to build
#   cd
#	  wget --no-check-certificate https://raw.githubusercontent.com/pnnl/tesp/main/scripts/tesp_only.sh
#	  chmod 755 tesp.sh
#   ./tesp_only.sh

# If you would to use and IDE here's to install snap Pycharm IDE for python
#   sudo snap install pycharm-community --classic
# Here is how to start pycharm and capture pycharm log for any errors
#   pycharm-community &> ~/charm.log&

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


sudo apt-get -y install python3.8
sudo apt-get -y install python3.8-venv
sudo apt-get -y install python3-pip
sudo apt-get -y install ${tk}
sudo apt-get -y install python3-pil.imagetk

echo
echo "Create directory structure for TESP"
cd "${HOME}" || exit
mkdir -p tesp
cd tesp || exit

echo "Install a virtual python environment to $HOME/tesp/venv"
python3.8 -m pip install --upgrade pip
python3.8 -m pip install virtualenv
"${HOME}/.local/bin/virtualenv" venv --prompt TESP

echo "Install executables environment to $HOME/tesp/tenv"
mkdir -p tenv
echo "Install repositories to $HOME/tesp/repository"
mkdir -p repository
cd repository || exit
echo
echo "Download all relevant repositories..."

echo
echo ++++++++++++++ TESP
git clone -b main https://github.com/pnnl/tesp.git
echo "Copy TESP environment variables to $HOME/tespEnv for shell scripts"
cp tesp/scripts/tespEnv "$HOME/"
. "${HOME}/tespEnv"

echo "Installing Python Libraries..."
which python > "${TESPBUILD}/tesp_pypi.log" 2>&1
pip3 install --upgrade pip >> "${TESPBUILD}/tesp_pypi.log" 2>&1
pip3 install -r "${TESPDIR}/requirements.txt" >> "${TESPBUILD}/tesp_pypi.log" 2>&1

echo "Installing Python TESP API..."
cd "${TESPDIR}/src/tesp_support" || exit
pip3 install -e . > "${TESPBUILD}/tesp_api.log" 2>&1

echo
echo "TESP installation logs are found in ${TESPBUILD}"
echo "No third parties are installed, like GridLabD, or Energyplus "
echo "If you want install them run tesp.sh in the 'scripts' directory"
echo "++++++++++++++  Installing TESP software is complete!  ++++++++++++++"
echo