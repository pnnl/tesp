#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . environment
fi

cd "${INSTDIR}" || exit
mkdir -p energyplus
cd "${REPODIR}/EnergyPlus" || exit
if [[ $1 == "clean" ]]; then
  sudo rm -rf build
fi
mkdir -p build
cd build || exit
cmake -DCMAKE_INSTALL_PREFIX="${INSTDIR}/energyplus" -DCMAKE_PREFIX_PATH="${INSTDIR}" \
      -DBUILD_FORTRAN=ON -DBUILD_PACKAGE=ON -DENABLE_INSTALL_REMOTE=OFF ..
# leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
if [[ $1 == "clean" ]]; then
  make clean
fi
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install
