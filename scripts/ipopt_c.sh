#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . environment
fi

echo
echo ++++++++++++++  Ipopt  ++++++++++++++
echo
IPOPT_VERSION=3.13.2
ASL_VERSION=2.0
MUMPS_VERSION=2.1

if [[ $1 == "clean" ]]; then
  cd "${WAREDIR}"
  sudo rm -r Ipopt
  sudo rm -r ThirdParty-ASL
  sudo rm -r ThirdParty-Mumps
  
  wget https://www.coin-or.org/download/source/Ipopt/Ipopt-${IPOPT_VERSION}.tgz
  tar -xzf Ipopt-${IPOPT_VERSION}.tgz
  mv Ipopt-releases-${IPOPT_VERSION} Ipopt
  rm "Ipopt-${IPOPT_VERSION}.tgz"

  wget https://github.com/coin-or-tools/ThirdParty-ASL/archive/stable/${ASL_VERSION}.zip
  unzip ${ASL_VERSION}.zip
  mv ThirdParty-ASL-stable-${ASL_VERSION} ThirdParty-ASL
  rm "${ASL_VERSION}.zip"

  wget https://github.com/coin-or-tools/ThirdParty-Mumps/archive/stable/${MUMPS_VERSION}.zip
  unzip ${MUMPS_VERSION}.zip
  mv ThirdParty-Mumps-stable-${MUMPS_VERSION} ThirdParty-Mumps
  rm "${MUMPS_VERSION}.zip"
fi

echo
echo "===== Make coin-or's third party ASL ====="
cd "${WAREDIR}/ThirdParty-ASL" || exit
./get.ASL
./configure --prefix="${INSTDIR}"
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install

echo
echo "===== Make coin-or's third party Mumps ====="
cd "${WAREDIR}/ThirdParty-Mumps" || exit
./get.Mumps
./configure --prefix="${INSTDIR}"
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install

echo
echo "===== Make Ipopt ====="
cd "${WAREDIR}/Ipopt" || exit
./configure --prefix="${INSTDIR}"
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make test
sudo make install
