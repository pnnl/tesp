#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

cd "${REPODIR}/HELICS-src" || exit
if [[ $1 == "clean" ]]; then
  rm -rf build
fi
mkdir -p build
cd build || exit
cmake -DHELICS_BUILD_JAVA_INTERFACE=ON -DBUILD_SHARED_LIBS=ON -DHELICS_BUILD_CXX_SHARED_LIB=ON \
      -DJAVA_AWT_INCLUDE_PATH=NotNeeded -DHELICS_DISABLE_BOOST=ON -DCMAKE_CXX_EXTENSIONS=ON \
      -DCMAKE_INSTALL_PREFIX="${INSTDIR}" -DCMAKE_BUILD_TYPE=Release ..
# leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
git submodule update --init

if [[ $1 == "clean" ]]; then
  make clean
  pip3 uninstall -y helics
fi
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make install

# Install HELICS Python3 bindings for a version that exactly matches the local build
# ver=$(helics_recorder --version)

#version='1.2.33-main5675'
#version='1.2.33 (1-12-20)'
# replace points, split into array
# a=( ${ver//./ } )
# trim element 2  by increment and decrement
# ((a[2]++))
# ((a[2]--))

# ver="${a[0]}.${a[1]}.${a[2]}"
# pip3 install helics=="${ver}"