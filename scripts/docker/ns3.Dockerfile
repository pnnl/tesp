# Build runtime image
FROM tesp-helics:latest AS tesp-run

# TESP user name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV TESPDIR=$USER_HOME/tesp
ENV INSTDIR=$TESPDIR/tenv

# Copy Binaries
# COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/

RUN echo "===== BUILD RUN NS3 =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y
