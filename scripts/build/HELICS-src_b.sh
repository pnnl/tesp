#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

cd "${REPO_DIR}/HELICS-src" || exit
if [[ $1 == "clean" ]]; then
  rm -rf build
  git submodule update --init
fi

myoption="Unix Makefiles"
if [ ${MSYSTEM_PREFIX} ]; then
  myoption=MSYS\ Makefiles
fi

mkdir -p build
cd build || exit
cmake -DHELICS_BUILD_JAVA_INTERFACE=ON -DBUILD_SHARED_LIBS=ON -DHELICS_BUILD_CXX_SHARED_LIB=ON \
      -DJAVA_AWT_INCLUDE_PATH=NotNeeded -DHELICS_DISABLE_BOOST=ON -DCMAKE_CXX_EXTENSIONS=ON \
      -DCMAKE_INSTALL_PREFIX="${INSTDIR}" -DCMAKE_BUILD_TYPE=Release -G "$myoption" ..
# leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local

if [[ $1 == "clean" ]]; then
  make clean
  pip uninstall -y helics
fi
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make install
