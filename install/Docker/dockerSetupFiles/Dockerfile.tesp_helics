ARG DOCKER_IMG=laurmarinovici/tesp
ARG DOCKER_IMG_VERSION=:base

FROM ${DOCKER_IMG}${DOCKER_IMG_VERSION} AS tesp-helics-builder
# -----------------------------------------------------
# Environment variables giving the location where TESP
# related software will be installed on the Docker container.
# -----------------------------------------------------
ENV TESP=${WORK_DIR}/tesp-platform
ENV HELICS_INSTALL=${TESP}/HELICSInstall
ENV GLD_INSTALL=${TESP}/GridLABDInstall
ENV NS3_INSTALL=${TESP}/ns3Install

# ----------------------------------------------------
# Because I want to use the software versions I already have
# installed on the current VM, I am going to use
# directly the downloads and repositories I have, letting aside
# the commands that are performing the actual downloads, and 
# repository cloning.
# Hence, from the context of the folder where I have all my downloads
# and clones, I only add the needed ones.
# I am running the image building script from inside the folder where
# all repositories have been already cloned in the source folders below.
# --------------------------------------------------------------
# HELICS branch = develop
ENV HELICS_SOURCE="HELICS-src"
# -------------------------------
# GridLAB-D branch = feature/1146
ENV GLD_SOURCE="gridlab-d"
# -------------------------------
# ns3 branch = ns-3-dev
# with helics-ns3 and fnss-ns3
ENV NS3_SOURCE="ns-3-dev"
# The folder on the image where all source files will be copied to,
# so that installation can proceed.
ENV SOURCE_DIR="${WORK_DIR}/sources/"

# --------------------------------------------------------------
# Environment variables needed for the package installation
# --------------------------------------------------------------
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${HELICS_INSTALL}/lib
ENV HELICS_LIBRARY=${HELICS_INSTALL}/lib
ENV HELICS_INCLUDE_DIR=${HELICS_INSTALL}/include
ENV PATH=${PATH}:${HELICS_INSTALL}/bin:${GLD_INSTALL}/bin
ENV GLPATH="${GLD_INSTALL}/lib/gridlabd:${GLD_INSTALL}/share/gridlabd"
# default values
ENV HELICS_LOG_FILE=no
ENV HELICS_LOG_STDOUT=no
ENV HELICS_LOG_TRACE=no
ENV HELICS_LOG_LEVEL=DEBUG4

# ------------------------------------------------------------------
# Adding the host source folders to the Docker image source folders
# ------------------------------------------------------------------
COPY --chown=tesp-user:tesp-user ./ ${SOURCE_DIR}

RUN mkdir -p ${SOURCE_DIR} && \
    mkdir -p ${TESP} && \
# ----------------------------------------------------
# INSTALL HELICS
# ----------------------------------------------------
    cd ${SOURCE_DIR}${HELICS_SOURCE} && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=${HELICS_INSTALL} -DBUILD_PYTHON_INTERFACE=ON -DCMAKE_CXX_FLAGS="-O2" -DCMAKE_C_FLAGS="-O2" ../ && \
    make -j 2 && \
    make install && \
    /bin/rm -r ${SOURCE_DIR}${HELICS_SOURCE} && \
    export PYTHONPATH=${HELICS_INSTALL}/python:$PYTHONPATH && \
# ----------------------------------------------------
# INSTALL GridLAB-D
# ----------------------------------------------------
    cd ${SOURCE_DIR}${GLD_SOURCE} && \
    autoreconf -isf && \
    ./configure --prefix=${GLD_INSTALL} --with-helics=${HELICS_INSTALL} --enable-silent-rules \
    'CPP=gcc -E' 'CXXPP=g++ -E' 'CC=gcc' 'CXX=g++' \ 
    'CFLAGS=-w -O3 -fno-inline-functions' 'CXXFLAGS=-w -O3 -fno-inline-functions -std=c++14' 'LDFLAGS=-w -O3' && \
    make && \
    make install && \
    /bin/rm -r ${SOURCE_DIR}${GLD_SOURCE} && \
# -----------------------------------------------------
# INSTALL ns3-helics
# -----------------------------------------------------
    cd ${SOURCE_DIR}${NS3_SOURCE} && \
    ./waf configure --disable-werror --with-helics=${HELICS_INSTALL} --prefix=${NS3_INSTALL} && \
    ./waf install

FROM ${DOCKER_IMG}${DOCKER_IMG_VERSION} AS tesp-helics-production
# -----------------------------------------------------
# Environment variables giving the location where TESP
# related software will be installed on the Docker container.
# -----------------------------------------------------
ENV TESP=${WORK_DIR}/tesp-platform
ENV HELICS_INSTALL=${TESP}/HELICSInstall
ENV GLD_INSTALL=${TESP}/GridLABDInstall
ENV NS3_INSTALL=${TESP}/ns3Install
# --------------------------------------------------------------
# Environment variables needed for the package installation
# --------------------------------------------------------------
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${HELICS_INSTALL}/lib
ENV HELICS_LIBRARY=${HELICS_INSTALL}/lib
ENV HELICS_INCLUDE_DIR=${HELICS_INSTALL}/include
ENV PATH=${PATH}:${HELICS_INSTALL}/bin:${GLD_INSTALL}/bin
ENV GLPATH=${GLD_INSTALL}/lib/gridlabd:${GLD_INSTALL}/share/gridlabd
ENV PYTHONPATH=${HELICS_INSTALL}/python:$PYTHONPATH
COPY --from=tesp-helics-builder --chown=tesp-user ${WORK_DIR} ${WORK_DIR} 