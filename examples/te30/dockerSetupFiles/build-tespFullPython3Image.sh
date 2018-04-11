#!/bin/bash

DOCKERFILE="Dockerfile.tesp_full"
TESP_REP="tesp/full"
TESP_TAG=":V1"
clear
docker build --no-cache \
             --network=host \
             -f ${DOCKERFILE} \
             -t ${TESP_REP}${TESP_TAG} .
