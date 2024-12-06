ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# Build runtime image
FROM cosim-build:tesp_$TAG AS cosim-user

ARG SIM_UID
ARG COSIM_USER

USER root
RUN echo "===== Building CoSim Library =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  echo "<<<< Adding the sim_group access >>>>" && \
  groupadd -g 1007 sim_group && \
  usermod -a -G sim_group worker && \
  echo "<<<< Adding the '${COSIM_USER}' user >>>>" && \
  useradd -m -s /bin/bash -u $SIM_UID ${COSIM_USER} && \
  echo "<<<< Changing ${COSIM_USER} password >>>>" && \
  echo "${COSIM_USER}:${COSIM_USER}" | chpasswd && \
  usermod -aG sudo ${COSIM_USER} && \
  usermod -aG sim_group ${COSIM_USER}
