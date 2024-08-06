#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

cd "${REPO_DIR}/KLU_DLL" || exit
if [[ $1 == "clean" ]]; then
  rm -rf build
fi
mkdir -p build
cd build || exit
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="${INSTDIR}" ..
# replace $INSTDIR with /usr/local if using the default
cmake --build . --target install