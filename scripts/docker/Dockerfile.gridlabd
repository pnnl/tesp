# Build runtime image
FROM tesp-helics:latest AS tesp-run

# TESP user name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV TESPDIR=$USER_HOME/tesp
ENV INSTDIR=$TESPDIR/tenv

# Compile exports
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd

# Copy Binaries
# COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/

RUN echo "===== BUILD RUN GridLabD =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
# GridLAB-D support libraries
  libxerces-c-dev \
  libhdf5-serial-dev \
  libsuitesparse-dev
