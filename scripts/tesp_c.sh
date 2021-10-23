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
  cd "${TESPDIR}/src/tesp_support" || exit
  pip3 install -e .
  #develop psst api
  cd "${REPODIR}/psst" || exit
  pip3 install -e .

else
  pip3 install tesp_support --upgrade
  pip3 install psst --upgrade
fi
opf

cd "${TESPDIR}/scripts/build" || exit
./fncs_b.sh clean
./fncs_java_b.sh clean
./helics2_b.sh clean
./klu_b.sh clean
./gridlabd_b.sh clean
./energyplus_b.sh clean
./energyplusj_b.sh clean
./ns-3_b.sh clean
./ipopt_b.sh clean

# creates the necessary links and cache to the most recent shared libraries found
# in the directories specified on the command line, in the file /etc/ld.so.conf,
# and in the trusted directories (/lib and /usr/lib).
sudo ldconfig

echo
echo ++++++++++++++  Build and compile TESP is complete!  ++++++++++++++
echo
./versions.sh