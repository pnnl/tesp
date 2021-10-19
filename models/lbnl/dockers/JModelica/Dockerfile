FROM ubuntu:16.04
MAINTAINER xxx

# Set environment variables
ENV SRC_DIR /usr/local/src
ENV MODELICAPATH /usr/local/JModelica/ThirdParty/MSL

# Avoid warnings
# debconf: unable to initialize frontend: Dialog
# debconf: (TERM is not set, so the dialog frontend is not usable.)
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

# Install required packages
RUN apt-get update && \
    apt-get install -y \
    g++ \
    subversion \
    gfortran \
    ipython \
    cmake \
    swig \
    python-dev \
    python-numpy \
    python-scipy \
    python-matplotlib \
    cython \
    python-lxml \
    python-nose \
    python-jpype \
    zlib1g-dev \
    libboost-dev \
    ant \
    python-pip \
    default-jdk \
    openjdk-8-jdk \
    jcc \
    wget \
    autoconf \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

# Avoid warning Matplotlib is building the font cache using fc-list. This may take a moment.
RUN python -c "import matplotlib.pyplot"

# Install jcc-3.0 to avoid error in python -c "import jcc"
RUN pip install --upgrade pip
RUN ln -s /usr/lib/jvm/java-8-openjdk-amd64 /usr/lib/jvm/java-8-oracle && \
    pip install --upgrade jcc

RUN export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
RUN export JCC_JDK=/usr/lib/jvm/java-8-openjdk-amd64

# Get Install Ipopt and JModelica, and delete source code with is more than 1GB large
RUN cd $SRC_DIR && \
    wget wget -O - http://www.coin-or.org/download/source/Ipopt/Ipopt-3.12.4.tgz | tar xzf - && \
    cd $SRC_DIR/Ipopt-3.12.4/ThirdParty/Blas && \
    ./get.Blas && \
    cd $SRC_DIR/Ipopt-3.12.4/ThirdParty/Lapack && \
    ./get.Lapack && \
    cd $SRC_DIR/Ipopt-3.12.4/ThirdParty/Mumps && \
    ./get.Mumps && \
    cd $SRC_DIR/Ipopt-3.12.4/ThirdParty/Metis && \
    ./get.Metis && \
    cd $SRC_DIR/Ipopt-3.12.4 && \
    ./configure --prefix=/usr/local/Ipopt-3.12.4 && \
    make install && \
    cd $SRC_DIR && \
    svn export https://svn.jmodelica.org/trunk JModelica && \
    cd $SRC_DIR/JModelica/external && \
    rm -rf $SRC_DIR/JModelica/external/Assimulo && \
    svn export https://svn.jmodelica.org/assimulo/trunk Assimulo && \
    cd $SRC_DIR/JModelica && \
    rm -rf build && \
    mkdir build && \
    cd $SRC_DIR/JModelica/build && \
    ../configure --with-ipopt=/usr/local/Ipopt-3.12.4 --prefix=/usr/local/JModelica && \
    make install && \
    make casadi_interface && \
    rm -rf $SRC_DIR

# Replace 1000 with your user / group id
RUN export uid=1000 gid=1000 && \
    mkdir -p /home/developer && \
    mkdir -p /etc/sudoers.d && \
    echo "developer:x:${uid}:${gid}:Developer,,,:/home/developer:/bin/bash" >> /etc/passwd && \
    echo "developer:x:${uid}:" >> /etc/group && \
    echo "developer ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/developer && \
    chmod 0440 /etc/sudoers.d/developer && \
    chown ${uid}:${gid} -R /home/developer

USER developer
ENV HOME /home/developer
