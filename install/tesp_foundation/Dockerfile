FROM ubuntu:18.04
LABEL maintainer="Thomas.McDermott@pnnl.gov"
RUN apt-get update;apt-get dist-upgrade -y
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y --no-install-recommends apt-utils
RUN apt-get install -y libjsoncpp-dev 
RUN apt-get install -y libxerces-c-dev
RUN apt-get install -y libzmq5-dev
RUN apt-get install -y libczmq-dev
RUN apt-get install -y libklu1
RUN apt-get install -y coinor-cbc
RUN apt-get install -y openjdk-11-jre-headless 
RUN apt-get install -y openjdk-11-jdk-headless
RUN apt-get install -y python3-pip
RUN apt-get install -y python3-tk
RUN pip3 install tesp_support --upgrade
RUN pip3 install psst --upgrade

