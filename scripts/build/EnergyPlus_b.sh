#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

cd "${INSTDIR}" || exit
mkdir -p energyplus
cd "${REPO_DIR}/EnergyPlus" || exit
if [[ $1 == "clean" ]]; then
  rm -rf build
fi

myoption="Unix Makefiles"
if [ ${MSYSTEM_PREFIX} ]; then
  myoption=MSYS\ Makefiles
fi

mkdir -p build
cd build || exit
cmake -DCMAKE_INSTALL_PREFIX="${INSTDIR}/energyplus" -DCMAKE_PREFIX_PATH="${INSTDIR}" \
      -DCMAKE_BUILD_TYPE=Release -DBUILD_FORTRAN=ON -DBUILD_PACKAGE=ON -DENABLE_INSTALL_REMOTE=OFF -G "$myoption" ..
# leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
if [[ $1 == "clean" ]]; then
  make clean
fi
make -j $(grep -c "^processor" /proc/cpuinfo)
make install
