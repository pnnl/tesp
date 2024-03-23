# Declare arguments
ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:20.04

# Build runtime image
FROM ${UBUNTU}${UBUNTU_VERSION} AS tesp-run

# TESP user name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME
ENV TESPDIR=$USER_HOME/tesp
ENV INSTDIR=$TESPDIR/tenv

# Compile exports
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYHELICS_INSTALL=$INSTDIR

# PATH
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$PATH

# Copy Binaries
COPY --from=tesp-build:latest $INSTDIR/ $INSTDIR/

RUN echo "===== BUILD RUN HELICS =====" && \
  export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  echo "===== Install Libraries =====" && \
  apt-get update && \
  apt-get dist-upgrade -y && \
  apt-get install -y \
# Java libraries
  openjdk-11-jdk \
# HELICS and FNCS support libraries
  lsof \
  libzmq5-dev \
  libczmq-dev \
  libboost-dev && \
  ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java && \
# protect images by changing root password
  echo "root:tesp" | chpasswd && \
  echo "<<<< Adding the TESP user >>>>" && \
  useradd -m -s /bin/bash ${USER_NAME} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${USER_NAME}:${USER_NAME}" | chpasswd && \
  usermod -aG sudo ${USER_NAME}
