#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . environment
fi

echo
echo ++++++++++++++  GridLAB-D  ++++++++++++++
echo
cd "${REPODIR}/gridlab-d" || exit
autoreconf -isf
# for ARM/'constance' processer needs libtinfo.a,   edit 'ax_with_curses.m4'  lines 206,219,325,338  add -ltinfo
./configure --prefix="${INSTDIR}" --with-fncs="${INSTDIR}" --with-hdf5=yes --enable-silent-rules \
            'CFLAGS=-w -O2' 'CXXFLAGS=-w -O2 -std=c++14' 'LDFLAGS=-w'
# in configure --with-fncs and --with-helics can not be left blank, so use either $INSTDIR or /usr/local for both
# leave off --prefix if using the default /usr/local
# for debugging use 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -std=c++14 -g -O0' and 'LDFLAGS=-w -g -O0'
if [[ $1 == "clean" ]]; then
  make clean
fi
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install
#gridlabd --validate