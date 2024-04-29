# Build runtime image
FROM cosim-ubuntu:latest AS cosim-helics

# User name and work directory
ARG SIM_UID
ARG COSIM_USER
ENV COSIM_HOME=/home/$COSIM_USER

ENV INSTDIR=$COSIM_HOME/tenv

# Compile exports
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYHELICS_INSTALL=$INSTDIR
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
# ENV CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial:$INSTDIR/include
# ENV FNCS_INCLUDE_DIR=$INSTDIR/include
# ENV FNCS_LIBRARY=$INSTDIR/lib
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$INSTDIR/lib
# ENV LD_RUN_PATH=$INSTDIR/lib

# PATH
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$PATH
ENV PATH=$PATH:$INSTDIR/energyplus
ENV PATH=$PATH:$INSTDIR/energyplus/PreProcess
ENV PATH=$PATH:$INSTDIR/energyplus/PostProcess

RUN echo "===== Building CoSim HELICS =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
# protect images by changing root password
  echo "root:${COSIM_USER}" | chpasswd && \
  echo "<<<< Adding the '${COSIM_USER}' user >>>>" && \
  useradd -m -s /bin/bash -u $SIM_UID ${COSIM_USER} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${COSIM_USER}:${COSIM_USER}" | chpasswd && \
  usermod -aG sudo ${COSIM_USER}

#Add cplex
#COPY $COSIM_HOME/cplex_studio129.linux-x86-64.bin
#RUN cd $COSIM_HOME || exit && \
#CPLEX_BIN=cplex_studio129.linux-x86-64.bin && \
#chmod a+x ${CPLEX_BIN} && \
#./cplex_studio129.linux-x86-64.bin -i silent -DLICENSE_ACCEPTED=TRUE -DUSER_INSTALL_DIR=$INSTDIR/ibm \

# Copy Binaries
COPY --from=cosim-build:latest $INSTDIR/ $INSTDIR/
RUN chown -hR $COSIM_USER:$COSIM_USER $COSIM_HOME

# Set as user
USER $COSIM_USER
WORKDIR $COSIM_HOME
