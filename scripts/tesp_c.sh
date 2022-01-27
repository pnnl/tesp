#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: tesp_c.sh

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

echo
echo "++++++++++++++  Compiling and Installing TESP software is starting!  ++++++++++++++"
echo
# Install all pip libraries
echo "Installing Python Libraries..."
#pip3 install wheel colorama glm seaborn matplotlib networkx==2.3 numpy pandas pulp pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py xlrd
pip3 install wheel colorama glm seaborn matplotlib networkx numpy pandas pulp pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py xlrd > "${TESPDIR}/scripts/build/pylib.log" 2>&1

#develop tesp api
echo "Installing Python TESP API..."
cd "${TESPDIR}/src/tesp_support" || exit
pip3 install -e . > "${TESPDIR}/scripts/build/tespapi.log" 2>&1

#develop psst api
echo "Installing Python PSST..."
#cd "${REPODIR}/psst" || exit
cd "${REPODIR}/AMES-V5.0/psst" || exit
pip3 install -e . > "${TESPDIR}/scripts/build/AMES-V5.0.log" 2>&1

#  pip3 install tesp_support --upgrade
#  pip3 install psst --upgrade

cd "${TESPDIR}/scripts/build" || exit
if [[ $1 == "develop" ]]; then

  echo "Installing Python Sphinx for documentation..."
  pip3 install recommonmark sphinx-jsonschema sphinx_rtd_theme sphinxcontrib-bibtex >> "${TESPDIR}/scripts/build/pylib.log" 2>&1
  #  ./docs_b.sh clean > docs.log 2>&1

  echo "Compiling and Installing FNCS..."
  ./fncs_b.sh clean > fncs.log 2>&1

  echo "Compiling and Installing FNCS for Java..."
  ./fncs_j_b.sh clean > fncs_j.log 2>&1

  echo "Compiling and Installing HELICS..."
  ./HELICS-src_b.sh clean > HELICS-src.log 2>&1

  echo "Compiling and Installing KLU..."
  ./KLU_DLL_b.sh clean > KLU_DLL.log 2>&1

  echo "Compiling and Installing Gridlabd..."
  ./gridlab-d_b.sh clean > gridlab-d.log 2>&1

  echo "Compiling and Installing EnergyPlus..."
  ./EnergyPlus_b.sh clean > EnergyPlus.log 2>&1

  echo "Compiling and Installing EnergyPlus for Java..."
  ./EnergyPlus_j_b.sh clean > EnergyPlus_j.log 2>&1

  echo "Compiling and Installing NS-3..."
  ./ns-3-dev_b.sh clean > ns-3-dev.log 2>&1

  echo "Compiling and Installing Ipopt with ASL and Mumps..."
  ./ipopt_b.sh clean > ipopt.log 2>&1

else

  echo "Installing HELICS, FNCS, GridLabD, EnergyPlus, NS3, and solver binaries..."
  cd "${INSTDIR}" || exit
  wget --no-check-certificate https://mepas.pnnl.gov/FramesV1/Install/tesp_binaries.zip
  unzip tesp_binaries.zip > "${TESPDIR}/scripts/build/tesp_binaries.log" 2>&1
  rm tesp_binaries.zip
fi

echo
echo "Installation logs are found in '${TESPDIR}/scripts/build'"

# creates the necessary links and cache to the most recent shared libraries found
# in the directories specified on the command line, in the file /etc/ld.so.conf,
# and in the trusted directories (/lib and /usr/lib).
sudo ldconfig

cd "${TESPDIR}/scripts/build" || exit
./versions.sh

