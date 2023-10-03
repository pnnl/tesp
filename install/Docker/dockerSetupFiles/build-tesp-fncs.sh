#!/bin/bash

# Copyright (c) 2021-2023 Battelle Memorial Institute
# file: build-tesp-fncs.sh

DOCKERFILE="Dockerfile.tesp_fncs"
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":fncs"
CONTEXT="/Users/mari009/PNNL_Projects/GitHubRepositories" # this is the context on Mac
clear
docker build --no-cache --rm=true \
             --network=host \
             -f ${DOCKERFILE} \
             -t ${TESP_REP}${TESP_TAG} ${CONTEXT}
