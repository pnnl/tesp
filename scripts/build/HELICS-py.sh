#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

# Install HELICS Python3 bindings for a version that exactly matches the local build
ver=$(helics_recorder --version)
#ver='1.2.33-main5675'
#ver='1.2.33 (1-12-20)'
# replace points, split into array
a=( ${ver//./ } )
# trim element 2 by increment and decrement to trim remain string
((a[2]++))
((a[2]--))
ver="${a[0]}.${a[1]}.${a[2]}"

pip3 install helics=="${ver}"
# pip3 install helics-apps=="${ver}"
# pip3 install git+https://github.com/GMLC-TDC/helics-cli.git@main
pip3 install helics[cli]