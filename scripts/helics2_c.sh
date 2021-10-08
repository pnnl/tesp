#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . environment
fi

echo
echo ++++++++++++++  HELICS  ++++++++++++++
echo
cd "${REPODIR}/HELICS-src" || exit
if [[ $1 == "clean" ]]; then
  sudo rm -r build
fi
mkdir build
cd build || exit
cmake -DBUILD_JAVA_INTERFACE=ON -DBUILD_SHARED_LIBS=ON \
      -DJAVA_AWT_INCLUDE_PATH=NotNeeded -DHELICS_DISABLE_BOOST=ON \
      -DCMAKE_INSTALL_PREFIX="${INSTDIR}" -DCMAKE_BUILD_TYPE=Release ..
# leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
git submodule update --init
if [[ $1 == "clean" ]]; then
  make clean
fi
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install
# Install HELICS Python 3 bindings for a version that exactly matches the local build
ver=$(helics_recorder --version)
pip3 install helics==${ver% *}