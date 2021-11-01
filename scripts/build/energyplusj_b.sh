#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . ~/environment
fi

cd "${TESPDIR}/src/energyplus" || exit
# the following steps are also in go.sh
autoheader
aclocal
automake --add-missing
autoconf
./configure --prefix="${INSTDIR}"  --with-fncs="${INSTDIR}" 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2'
if [[ $1 == "clean" ]]; then
  make clean
fi
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install
