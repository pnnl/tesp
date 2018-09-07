#!/bin/bash

DOCKERFILE="Dockerfile.tesp_fullUserV5"
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":V5"
clear
docker build --no-cache \
             --network=host \
             -f ${DOCKERFILE} \
             -t ${TESP_REP}${TESP_TAG} ../../downloads/
