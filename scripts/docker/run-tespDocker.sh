#!/bin/bash

IMAGE_NAME="tesp-evolve-v1.0.2:20220321"
DOCKER_NAME="tesp-docker-101"

docker run -it --rm \
           --name ${DOCKER_NAME} ${IMAGE_NAME} bash