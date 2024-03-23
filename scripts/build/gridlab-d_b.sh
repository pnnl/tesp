#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

## using make for <5.0 GridLAB-D
#cd "${REPO_DIR}/gridlab-d" || exit
#autoreconf -isf
## for ARM/'constance' processer needs libtinfo.a,   edit 'ax_with_curses.m4'  lines 206,219,325,338  add -ltinfo
#./configure --prefix="${INSTDIR}" --with-fncs="${INSTDIR}" --with-helics="${INSTDIR}" --with-hdf5=yes --enable-silent-rules \
#            'CFLAGS=-w -O2' 'CXXFLAGS=-w -O2 -std=c++14' 'LDFLAGS=-w'
## in configure --with-fncs and --with-helics can not be left blank, so use either $INSTDIR or /usr/local for both
## leave off --prefix if using the default /usr/local
## for debugging use 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -std=c++14 -g -O0' and 'LDFLAGS=-w -g -O0'
#if [[ $1 == "clean" ]]; then
#  make clean
#fi
#make -j "$(grep -c "^processor" /proc/cpuinfo)"
#make install

# using cmake for >=5.0 GridLAB-D
cd "${REPO_DIR}/gridlab-d" || exit
if [[ $1 == "clean" ]]; then
  rm -rf build
  git submodule update --init
fi

mkdir build
cd build || exit
cmake -DCMAKE_INSTALL_PREFIX="${INSTDIR}" -DCMAKE_BUILD_TYPE=Release \
      -DGLD_USE_HDF5=ON \
      -DGLD_USE_FNCS=ON -DGLD_FNCS_DIR="${INSTDIR}" \
      -DGLD_USE_HELICS=ON -DGLD_HELICS_DIR="${INSTDIR}" ..

# Remove -DGLD_USE_FNCS=ON -DGLD_FNCS_DIR="${INSTDIR}" if you do not need to use FNCS

# Run the build system and install the application
cmake --build . -j $(grep -c "^processor" /proc/cpuinfo) --target install

# To validate the build
#gridlabd.sh -t 0 --validate
