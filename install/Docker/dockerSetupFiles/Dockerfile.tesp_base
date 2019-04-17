ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:18.04

FROM ${UBUNTU}${UBUNTU_VERSION} AS ubuntu-base

ENV TERM=xterm \
    DEBIAN_FRONTEND=noninteractive
ENV USER_NAME=tesp-user
ENV WORK_DIR=/home/${USER_NAME}

# -------------------------------------------------------------------
# By default, the docker image is built as ROOT.
# Updating, upgrading the distribution, and installing everything
# that needs to be installed with ROOT privileges
# -------------------------------------------------------------------
RUN apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y \
    sudo \
    gfortran \
    wget \
    git \
    automake \
    autoconf \
    make \
    cmake \
    cmake-curses-gui \
    libtool \
    ca-certificates \
    openssl \
    lsof \
    psmisc \
    nano \
    build-essential \
    libtool \
    libjsoncpp-dev \
    default-jre \
    default-jdk \
    libxerces-c-dev \
    libboost-dev \
    libboost-program-options-dev \
    libboost-test-dev \
    libboost-filesystem-dev \
    libboost-signals-dev \
    libzmq5-dev \
    libczmq-dev \
    swig \
    python3 \
    python3-dev \
    python3-pip \
    python3-tk && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /var/cache/apt/archives/* && \
    ln -fs python3 /usr/bin/python && \
    echo "===== PYTHON VERSION =====" && \
    python --version && \
    echo "===== PIP VERSION =====" && \
    pip3 --version && \
    echo "===== UPGRADE PIP =====" && \
    pip3 install --upgrade pip && \
    ln -fs /usr/local/bin/pip /usr/bin/pip && \
    pip --version && \
    echo "===== install NUMPY =====" && \
    pip install numpy && \
    echo "===== install MATPLOTLIB =====" && \
    pip install matplotlib && \
    echo "===== install SCIPY =====" && \
    pip install scipy && \
    echo "===== install PYPOWER =====" && \
    pip install pypower && \
    pip install networkx && \
    pip install tesp_support && \
    echo "===== current PIP3 modules =====" && \
    pip list --format=columns && \
    echo "root:tesp" | chpasswd && \
    useradd -m -s /bin/bash ${USER_NAME}

USER ${USER_NAME}
WORKDIR ${WORK_DIR}