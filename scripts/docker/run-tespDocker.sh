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

USER_NAME=worker
USER_HOME=/home/$USER_NAME


clear
docker run -it --rm \
           -e LOCAL_USER_ID="$(id -u d3j331)" \
           -w=${USER_HOME} \
           --name ${DOCKER_NAME} ${IMAGE_NAME} bash