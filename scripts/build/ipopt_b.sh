#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

IPOPT_VERSION=3.13.2
ASL_VERSION=2.0
MUMPS_VERSION=2.1

if [[ $1 == "clean" ]]; then
  cd "${REPO_DIR}" || exit
  rm -rf Ipopt
  rm -rf ThirdParty-ASL
  rm -rf ThirdParty-Mumps
  
  wget --no-check-certificate https://www.coin-or.org/download/source/Ipopt/Ipopt-${IPOPT_VERSION}.tgz
  tar -xzf Ipopt-${IPOPT_VERSION}.tgz
  mv Ipopt-releases-${IPOPT_VERSION} Ipopt
  rm "Ipopt-${IPOPT_VERSION}.tgz"

  wget --no-check-certificate https://github.com/coin-or-tools/ThirdParty-ASL/archive/stable/${ASL_VERSION}.zip
  unzip ${ASL_VERSION}.zip
  mv ThirdParty-ASL-stable-${ASL_VERSION} ThirdParty-ASL
  rm "${ASL_VERSION}.zip"

  wget --no-check-certificate https://github.com/coin-or-tools/ThirdParty-Mumps/archive/stable/${MUMPS_VERSION}.zip
  unzip ${MUMPS_VERSION}.zip
  mv ThirdParty-Mumps-stable-${MUMPS_VERSION} ThirdParty-Mumps
  rm "${MUMPS_VERSION}.zip"
fi

echo
echo "===== Make coin-or's third party ASL ====="
cd "${REPO_DIR}/ThirdParty-ASL" || exit
sed -i "s:wgetcmd=\"wget\":wgetcmd=\"wget --no-check-certificate\":g" ./get.ASL
./get.ASL
./configure --prefix="${INSTDIR}"
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make install

echo
echo "===== Make coin-or's third party Mumps ====="
cd "${REPO_DIR}/ThirdParty-Mumps" || exit
sed -i "s:wgetcmd=\"wget\":wgetcmd=\"wget --no-check-certificate\":g" ./get.Mumps
./get.Mumps
./configure --prefix="${INSTDIR}"
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make install

echo
echo "===== Make Ipopt ====="
cd "${REPO_DIR}/Ipopt" || exit
./configure --prefix="${INSTDIR}"
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make test
make install
