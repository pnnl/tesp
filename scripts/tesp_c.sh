#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . environment
fi

echo
echo ++++++++++++++  Compiles all TESP software and libraries  ++++++++++++++
echo
# Install all pip libraries
#pip3 install wheel colorama glm seaborn matplotlib networkx==2.3 numpy pandas pulp pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py xlrd
pip3 install wheel colorama glm seaborn matplotlib networkx numpy pandas pulp pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py xlrd

if [[ $1 == "develop" ]]; then
  #develop tesp api
  cd "${TESPDIR}/src/tesp_spport" || exit
  pip3 install -e .
  #develop psst api
  cd "${REPODIR}/psst" || exit
  pip3 install -e .

  cd "${TESPDIR}/scripts" | exit
else
  pip3 install tesp_support --upgrade
  pip3 install psst --upgrade
fi
opf

./fncs_c.sh clean
./fncs_java_c.sh clean
./helics2_c.sh clean
./klu_c.sh clean
./gridlabd_c.sh clean
./energyplus_c.sh clean
./energyplusj_c.sh clean
./ns-3_c.sh clean
./ipopt_c.sh clean

# creates the necessary links and cache to the most recent shared libraries found
# in the directories specified on the command line, in the file /etc/ld.so.conf,
# and in the trusted directories (/lib and /usr/lib).
sudo ldconfig