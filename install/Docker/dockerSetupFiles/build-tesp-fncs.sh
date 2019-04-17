#!/bin/bash

DOCKERFILE="Dockerfile.tesp_fncs"
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":fncs"
CONTEXT="/Users/mari009/PNNL_Projects/GitHubRepositories" # this is the context on Mac
clear
docker build --no-cache --rm=true \
             --network=host \
             -f ${DOCKERFILE} \
             -t ${TESP_REP}${TESP_TAG} ${CONTEXT}
