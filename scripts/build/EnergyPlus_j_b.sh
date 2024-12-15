#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

cd "${TESPDIR}/src/energyplus" || exit
# the following steps are also in go.sh
autoheader
aclocal
automake --add-missing
autoconf
./configure --prefix="${INSTDIR}" --with-fncs="${INSTDIR}" 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2'
if [[ $1 == "clean" ]]; then
  make clean
fi
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make install
