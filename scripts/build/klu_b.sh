#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . environment
fi

echo
echo ++++++++++++++  KLU solver  ++++++++++++++
echo
cd "${REPODIR}/KLU_DLL" || exit
if [[ $1 == "clean" ]]; then
  sudo rm -r build
fi
mkdir -p build
cd build || exit
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="${INSTDIR}" ..
# replace $INSTDIR with /usr/local if using the default
sudo cmake --build . --target install