# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: Dockerfile

FROM ubuntu:20.04
LABEL maintainer="Thomas.McDermott@pnnl.gov"
RUN apt-get update;apt-get dist-upgrade -y
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y --no-install-recommends apt
RUN apt-get update
RUN apt-get install -y libjsoncpp-dev libxerces-c-dev libzmq5-dev libczmq-dev libklu1 coinor-cbc \
 openjdk-11-jre-headless  openjdk-11-jdk-headless python3-pip python3-tk cmake
RUN pip3 install tesp_support --upgrade
RUN pip3 install psst --upgrade
RUN pip3 install helics==2.6.1

