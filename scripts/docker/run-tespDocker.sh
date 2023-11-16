#!/bin/bash

DOCKER_NAME="tesp-docker"
#IMAGE_NAME="ubuntu:20.04"
#IMAGE_NAME="tesp-$(cat $TESPDIR/scripts/version):latest"
#IMAGE_NAME="tesp-helics:latest"
#IMAGE_NAME="tesp-gridlabd:latest"
#IMAGE_NAME="tesp-eplus:latest"
#IMAGE_NAME="tesp-ns3:latest"
#IMAGE_NAME="tesp-python:latest"
IMAGE_NAME="tesp-tespapi:latest"


clear
docker run -it --rm \
           --name ${DOCKER_NAME} ${IMAGE_NAME} bash