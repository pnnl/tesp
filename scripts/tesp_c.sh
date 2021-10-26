#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . environment
fi

echo
echo ++++++++++++++  Compiles all TESP software and libraries  ++++++++++++++
echo
# Install all pip libraries
#pip3 install wheel colorama glm seaborn matplotlib networkx==2.3 numpy pandas pulp pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py xlrd
pip3 install wheel colorama glm seaborn matplotlib networkx numpy pandas pulp pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py xlrd 2> pylib.log

#develop tesp api
cd "${TESPDIR}/src/tesp_support" || exit
pip3 install -e . 2> tespapi.log
#develop psst api
cd "${REPODIR}/psst" || exit
pip3 install -e . 2> psst.log

#  pip3 install tesp_support --upgrade
#  pip3 install psst --upgrade

cd "${TESPDIR}/scripts/build" || exit
if [[ $1 == "develop" ]]; then

  echo Compiling and Installing FNCS
  ./fncs_b.sh clean 2> fncs.log
  echo Compiling and Installing FNCS for Java
  ./fncs_java_b.sh clean 2> fava_java.log
  echo Compiling and Installing HELICS
  ./helics2_b.sh clean 2> helics2.log
  echo Compiling and Installing KLU
  ./klu_b.sh clean 2> klu.log
  echo Compiling and Installing Gridlabd
  ./gridlabd_b.sh clean 2> gridlabd.log
  echo Compiling and Installing EnegryPlus
  ./energyplus_b.sh clean 2> energyplus.log
  echo Compiling and Installing EnergryPlus for Java
  ./energyplusj_b.sh clean 2> energyplusj.log
  echo Compiling and Installing NS-3
  ./ns-3_b.sh clean 2> ns3.log
  echo Compiling and Installing Ipopt with ASL and Mumps
  ./ipopt_b.sh clean 2> ipopt.log
else

  wget https://mepas.pnnl.gov/FramesV1/Install/tesp_binaries.zip
  cd "${INSTDIR}" exit
  unzip tesp_binaries.zip .
fi

# creates the necessary links and cache to the most recent shared libraries found
# in the directories specified on the command line, in the file /etc/ld.so.conf,
# and in the trusted directories (/lib and /usr/lib).
sudo ldconfig

echo
echo ++++++++++++++  Build and compile TESP is complete!  ++++++++++++++
echo
./versions.sh