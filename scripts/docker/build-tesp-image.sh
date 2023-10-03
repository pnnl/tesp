#!/bin/bash

IMAGE_NAME="tesp-$(cat "$TESPDIR/scripts/version"):latest"
DOCKERFILE="Dockerfile"
CONTEXT="./"

clear
docker build --no-cache --rm --progress=plain \
             --network=host \
             -f ${DOCKERFILE} \
             -t "${IMAGE_NAME}" ${CONTEXT}