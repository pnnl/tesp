#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

cd "${REPODIR}/fncs" || exit
autoreconf -isf
./configure 'CXXFLAGS=-w -O2 -std=c++14' 'CFLAGS=-w -O2' --prefix="${INSTDIR}"
# leave off --prefix if using the /usr/local
if [[ $1 == "clean" ]]; then
  make clean
fi
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make install
