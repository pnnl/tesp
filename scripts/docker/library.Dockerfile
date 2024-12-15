ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# Build runtime image
FROM cosim-ubuntu:tesp_$TAG AS cosim-library

ARG SIM_GID
ARG SIM_GRP
ARG SIM_UID
ARG SIM_USER

RUN echo "===== Building CoSim Library =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
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
  cmake \
  subversion && \
  echo "root:${SIM_USER}" | chpasswd && \
  addgroup --gid ${SIM_GID} ${SIM_GRP} && \
  useradd -m -s /bin/bash -u ${SIM_UID} ${SIM_USER} && \
  echo "<<<< Changing '${SIM_USER}' password >>>>" && \
  echo "${SIM_USER}:${SIM_USER}" | chpasswd && \
  usermod -aG sudo,${SIM_GRP} ${SIM_USER}
