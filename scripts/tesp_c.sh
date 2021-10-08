#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . environment
fi

echo
echo ++++++++++++++  Compiles all TESP software and libraries  ++++++++++++++
echo
# Install all pip libraries
pip3 install wheel colorama glm seaborn matplotlib networkx==2.3 numpy pandas pulp pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py xlrd

./fncs_c.sh
./fncs_java_c.sh
./helics2_c.sh
./klu_c.sh
./gridlabd_c.sh
./energyplus_c.sh
./energyplusj_c.sh
./ns-3_c.sh
./ipopt_c.sh clean

# creates the necessary links and cache to the most recent shared libraries found
# in the directories specified on the command line, in the file /etc/ld.so.conf,
# and in the trusted directories (/lib and /usr/lib).
sudo ldconfig