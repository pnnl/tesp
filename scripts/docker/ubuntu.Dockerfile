# Build runtime image
ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:22.04

FROM ${UBUNTU}${UBUNTU_VERSION} AS cosim-ubuntu

RUN echo "===== Building TESP Ubuntu =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
# misc utilities
  git \
  wget \
  lsof \
  unzip \
# java support
  openjdk-11-jdk \
# message support
  libzmq5-dev \
  libczmq-dev \
# misc libraries
  libboost-dev \
  libxerces-c-dev \
  libhdf5-serial-dev \
# solver libraries
  libsuitesparse-dev \
  coinor-cbc \
  coinor-libcbc-dev \
  coinor-libipopt-dev \
  liblapack-dev \
  libmetis-dev \
# python support
  python3-pip \
  python3-pil.imagetk && \
  ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java
