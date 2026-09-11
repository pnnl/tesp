#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

IPOPT_VERSION=3.14.19
ASL_VERSION=2.1.0

if [[ $1 == "clean" ]]; then
  cd "${REPO_DIR}" || exit
  rm -rf Ipopt
  rm -rf ThirdParty-ASL

  wget --no-check-certificate https://github.com/coin-or/Ipopt/archive/refs/tags/releases/${IPOPT_VERSION}.zip
  unzip ${IPOPT_VERSION}.zip
  mv Ipopt-releases-${IPOPT_VERSION} Ipopt
  rm "${IPOPT_VERSION}.zip"

  wget --no-check-certificate https://github.com/coin-or-tools/ThirdParty-ASL/archive/refs/tags/releases/${ASL_VERSION}.zip
  unzip ${ASL_VERSION}.zip
  mv ThirdParty-ASL-releases-${ASL_VERSION} ThirdParty-ASL
  rm "${ASL_VERSION}.zip"
fi

echo
echo "===== Make coin-or's third party ASL ====="
cd "${REPO_DIR}/ThirdParty-ASL" || exit
sed -i "s:wgetcmd=\"wget\":wgetcmd=\"wget --no-check-certificate\":g" ./get.ASL
./get.ASL
./configure --prefix="${INSTDIR}"
make -j "$(nproc)"
make install

echo
echo "===== Make Ipopt ====="
cd "${REPO_DIR}/Ipopt" || exit
./configure --prefix="${INSTDIR}"  --with-lapack="-llapack" --with-mumps-cflags=-I/usr/include/mumps_seq --with-mumps-lflags=-ldmumps_seq
make -j "$(nproc)"
make test
make install
