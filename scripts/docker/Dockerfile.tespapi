# Build runtime image
FROM tesp-python:latest AS tesp-run

# TESP user name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV TESPDIR=$USER_HOME/tesp
ENV INSTDIR=$TESPDIR/tenv

# Copy Binaries
# COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/
COPY --from=tesp-build:latest $TESPDIR/requirements.txt $TESPDIR
COPY --from=tesp-build:latest $TESPDIR/data/ $TESPDIR/data/
COPY --from=tesp-build:latest $TESPDIR/repository/AMES-V5.0/README.rst $TESPDIR
COPY --from=tesp-build:latest $TESPDIR/repository/AMES-V5.0/psst/ $TESPDIR/psst/

RUN echo "===== BUILD RUN TESP API =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
# Ipopt cbc solver support libraries
  coinor-cbc \
  coinor-libcbc-dev \
  coinor-libipopt-dev \
  liblapack-dev \
  libmetis-dev && \
# Install Python Libraries
  pip3 install -r "$TESPDIR/requirements.txt" > "$TESPDIR/tesp_pypi.log" && \
  cd $TESPDIR/psst || exit && \
  pip3 install -e . >> "$TESPDIR/tesp_pypi.log"
