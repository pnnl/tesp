ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# Build runtime image
FROM cosim-ubuntu:tesp_$TAG AS cosim-library

ARG SIM_GID
ARG SIM_GRP
ARG SIM_UID
ARG SIM_USER

RUN echo "===== Building TESP Library =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
  sudo \
  pkgconf \
  build-essential \
  autoconf \
  libtool \
  libjsoncpp-dev \
  gfortran \
  cmake && \
  echo "root:${SIM_USER}" | chpasswd && \
  addgroup --gid ${SIM_GID} ${SIM_GRP} && \
  useradd -m -s /bin/bash -g ${SIM_GRP} -G sudo,${SIM_GRP} -u ${SIM_UID} ${SIM_USER} && \
  echo "${SIM_USER}:${SIM_USER}" | chpasswd
