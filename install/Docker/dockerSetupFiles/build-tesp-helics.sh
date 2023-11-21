#!/bin/bash

# Copyright (c) 2021-2023 Battelle Memorial Institute
# file: build-tesp-helics.sh

DOCKERFILE="Dockerfile.tesp_helics"
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":helics"
clear
docker build --no-cache --rm\
             --network=host \
             -f ${DOCKERFILE} \
             -t ${TESP_REP}${TESP_TAG} ../../downloads/
