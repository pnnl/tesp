ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# Build runtime image
FROM cosim-build:tesp_$TAG AS cosim-user

ARG SIM_UID
ARG SIM_USER

ARG COSIM_UID=$SIM_UID
ARG COSIM_USER=$SIM_USER

ARG SIM_UID=1004
ARG SIM_USER=d3j331
ENV OTESPDIR=$TESPDIR

ENV SIM_HOME=/home/$SIM_USER
ENV TESPDIR=$SIM_HOME/tesp
ENV INSTDIR=$SIM_HOME/tenv
ENV BUILD_DIR=$COSIM_HOME/build
ENV REPO_DIR=$SIM_HOME/repo

# COMPILE exports
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYHELICS_INSTALL=$INSTDIR
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
ENV CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial:$INSTDIR/include
ENV FNCS_INCLUDE_DIR=$INSTDIR/include
ENV FNCS_LIBRARY=$INSTDIR/lib
ENV LD_LIBRARY_PATH=$INSTDIR/lib
ENV LD_RUN_PATH=$INSTDIR/lib

# PATH
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$SIM_HOME/.local/bin:$PATH
ENV PATH=$PATH:$INSTDIR/energyplus
ENV PATH=$PATH:$INSTDIR/energyplus/PreProcess
ENV PATH=$PATH:$INSTDIR/energyplus/PostProcess
ENV PATH=$PATH:$TESPDIR/scripts/helpers

USER root
# SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN echo "<<<< Adding the '${SIM_USER}' user, '${SIM_UID} id >>>>" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
#
  useradd -m -s /bin/bash -u $SIM_UID ${SIM_USER} && \
  echo "<<<< Changing '${SIM_USER}' password >>>>" && \
  echo "${SIM_USER}:${SIM_USER}" | chpasswd && \
#
  echo "<<<< Adding the '${SIM_GID}' to user '${SIM_USER}' >>>>" && \
  addgroup --SIM_GID ${SIM_GID} ${SIM_GRP} && \
  usermod -aG sudo,${SIM_GRP} ${SIM_USER} && \
#
  echo "<<<< Adding the 'copy' to '${SIM_USER}' user >>>>" && \
  mv /home/${COSIM_USER}/repo /home/${SIM_USER} && \
  mv /home/${COSIM_USER}/tenv /home/${SIM_USER} && \
  mv /home/${COSIM_USER}/tesp /home/${SIM_USER} && \
  chown -R ${SIM_USER}:${SIM_GRP} /home/${SIM_USER}

# Switch to '$SIM_USER'
USER ${SIM_USER}
WORKDIR /home/${SIM_USER}

RUN echo "Install TESP and Misc. Python Libraries..." && \
  pip install --no-warn-script-location --upgrade pip  > "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir -r ${TESPDIR}/requirements.txt  >> "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir helics[cli]  >> "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir -e ${REPO_DIR}/psst  >> "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir -e ${TESPDIR}/src/tesp_support  >> "pypi.log"
