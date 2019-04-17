#!/bin/bash

DOCKERFILE="Dockerfile.tesp_helics"
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":helics"
clear
docker build --no-cache --rm\
             --network=host \
             -f ${DOCKERFILE} \
             -t ${TESP_REP}${TESP_TAG} ../../downloads/
