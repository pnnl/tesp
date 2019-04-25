#!/bin/bash

DOCKERFILE="Dockerfile.tesp_base"
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":base"
clear
docker build --no-cache --rm\
             --network=host \
             -f ${DOCKERFILE} \
             -t ${TESP_REP}${TESP_TAG} ./
