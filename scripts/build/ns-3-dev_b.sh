#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

cd "${REPODIR}/ns-3-dev" || exit
# first build: use the following command for HELICS interface to ns3:
# git clone -b feature/13b https://github.com/GMLC-TDC/helics-ns3 contrib/helics
# subsequent builds: use the following 3 commands to update HELICS interface code:
# cd contrib/helics
# git pull
# cd ../..
# then configure, build and test ns3 with the HELICS interface
# --with-helics may not be left blank, so use either $INSTDIR or /usr/local
if [[ $1 == "clean" ]]; then
  ./waf distclean
#  ./ns3 distclean
fi

./waf configure --prefix="${INSTDIR}" --with-helics="${INSTDIR}" --build-profile=optimized \
                --disable-werror --enable-logs --enable-build-version

#./ns3 configure --prefix="${INSTDIR}" --build-profile=optimized --disable-werror \
#                --enable-logs --enable-build-version
# To enable examples or tests add the respective --enable command to the waf configure command line
# --enable-examples --enable-tests

./waf build
# ./ns3 build

./waf install
# ./ns3 install
#./test.py
