#!/bin/bash

mkdir -p ../data
if [[ $1 == "200" ]]; then
  rm -f data200.zip
  wget https://mepas.pnnl.gov/FramesV1/Install/data200.zip
  unzip data200.zip -d ..
else
  rm -f data8.zip
  wget https://mepas.pnnl.gov/FramesV1/Install/data8.zip
  unzip data8.zip -d ..
fi
