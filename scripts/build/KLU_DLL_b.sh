#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

cd "${REPODIR}/KLU_DLL" || exit
if [[ $1 == "clean" ]]; then
  rm -rf build
fi
mkdir -p build
cd build || exit
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="${INSTDIR}" ..
# replace $INSTDIR with /usr/local if using the default
cmake --build . --target install