#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tesp.env in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

if [[ $1 == "clean" ]]; then
  cd "${REPO_DIR}" || exit
  rm -rf czmq-4.2.1

  wget --no-check-certificate https://github.com/zeromq/czmq/releases/download/v4.2.1/czmq-4.2.1.tar.gz
  tar -xzf czmq-4.2.1.tar.gz
  rm czmq-4.2.1.tar.gz
fi

# edit two lines of c:/msys64/ucrt64/lib/pkgconfig/libzmq.pc so they read
#    Libs: -L${libdir} -lzmq -lws2_32 -liphlpapi -lpthread -lrpcrt4
#    Libs.private: -lstdc++

cd /c/msys64/ucrt64/lib/pkgconfig
sed -i 's:Libs\: -L${libdir} -lzmq.*:Libs\: -L${libdir} -lzmq -lws2_32 -liphlpapi -lpthread -lrpcrt4:g' libzmq.pc
sed -i 's:Libs.private\: -lstdc++.*:Libs.private\: -lstdc++:g' libzmq.pc

cd "${REPO_DIR}/czmq-4.2.1" || exit
./configure --prefix="${INSTDIR}" --with-liblz4=no 'CXXFLAGS=-O2 -w -std=gnu++14' 'CFLAGS=-O2 -w'
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make install
