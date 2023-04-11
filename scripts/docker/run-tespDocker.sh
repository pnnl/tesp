#!/bin/bash

IMAGE_NAME="tesp-$(cat $TESPDIR/scripts/version):latest"
DOCKER_NAME="tesp-docker"

docker run -it --rm \
           --name ${DOCKER_NAME} ${IMAGE_NAME} bash