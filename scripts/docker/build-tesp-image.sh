#!/bin/bash

DOCKERFILE="Dockerfile"
TES_REP="tesp-v1.1.5"
TES_TAG=":latest"
CONTEXT="./"
clear
docker build --no-cache --rm --progress=plain \
             --network=host \
             -f ${DOCKERFILE} \
             -t ${TES_REP}${TES_TAG} ${CONTEXT}