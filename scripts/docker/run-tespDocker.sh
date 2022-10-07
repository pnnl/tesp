#!/bin/bash

IMAGE_NAME="tesp-v1.1.5:latest"
DOCKER_NAME="tesp-docker"

docker run -it --rm \
           --name ${DOCKER_NAME} ${IMAGE_NAME} bash