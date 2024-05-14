# Build runtime image
FROM cosim-ubuntu:tesp_1_22.04 AS cosim-library

ARG SIM_UID
ARG COSIM_USER

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
  echo "root:${COSIM_USER}" | chpasswd && \
  echo "<<<< Adding the '${COSIM_USER}' user >>>>" && \
  useradd -m -s /bin/bash -u $SIM_UID ${COSIM_USER} && \
  echo "<<<< Changing ${COSIM_USER} password >>>>" && \
  echo "${COSIM_USER}:${COSIM_USER}" | chpasswd && \
  usermod -aG sudo ${COSIM_USER}
