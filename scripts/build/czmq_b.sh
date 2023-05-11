#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

if [[ $1 == "clean" ]]; then
  cd "${REPODIR}" || exit
  rm -rf czmq

  wget --no-check-certificate https://github.com/zeromq/czmq/releases/download/v4.2.1/czmq-4.2.1.tar.gz
  tar -xzf czmq-4.2.1.tar.gz
  mv czmq-4.2.1 czmq
  rm czmq-4.2.1.tar.gz
fi

cd "${REPODIR}/czmq" || exit
# edit two lines of c:/msys64/mingw64/lib/pkgconfig/libzmq.pc so they read
#    Libs: -L${libdir} -lzmq -lws2_32 -liphlpapi -lpthread -lrpcrt4
#    Libs.private: -lstdc++
./configure --prefix="${INSTDIR}" --with-liblz4=no 'CXXFLAGS=-O2 -w -std=gnu++14' 'CFLAGS=-O2 -w'
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make install
