ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# Build runtime image
FROM cosim-build:tesp_$TAG AS cosim-user

ARG SIM_GID
ARG SIM_GRP
ARG SIM_UID
ARG SIM_USER

USER root
# SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN echo "<<<< Changing the '${SIM_GID}' group id for '${SIM_GRP} >>>>" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  groupdel ${SIM_GRP} && \
  groupadd --gid ${SIM_GID} ${SIM_GRP} && \
  usermod -aG sudo,${SIM_GRP} ${SIM_USER}

# Switch to '$SIM_USER'
USER ${SIM_USER}
WORKDIR /home/${SIM_USER}
