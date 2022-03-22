#!/bin/bash

DOCKERFILE="Dockerfile"
TES_REP="tesp-evolve-v1.0.2"
TES_TAG=":20220321"
CONTEXT="./"
clear
docker build --no-cache --rm --progress=plain \
             --network=host \
             -f ${DOCKERFILE} \
             -t ${TES_REP}${TES_TAG} ${CONTEXT}