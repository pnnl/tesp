ARG DOCKER_IMG=laurmarinovici/tesp
ARG DOCKER_IMG_VERSION=:base

FROM ${DOCKER_IMG}${DOCKER_IMG_VERSION} AS tesp-fncs-builder
# -----------------------------------------------------
# Environment variables giving the location where TESP
# related software will be installed on the Docker container.
# -----------------------------------------------------
ENV TESP=${WORK_DIR}/tesp-platform
ENV FNCS_INSTALL=${TESP}/FNCSInstall
ENV GLD_INSTALL=${TESP}/GridLABDInstall
ENV EPLUS_INSTALL=${TESP}/EnergyPlusInstall
ENV EPLUSJSON_INSTALL=${TESP}/EPlusJSONInstall

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
# FNCS branch = develop
ENV FNCS_SOURCE="fncs"
# -------------------------------
# GridLAB-D branch = feature/1146
ENV GLD_SOURCE="gridlab-d"
# -------------------------------
# Energy Plus branch = fncs-v8.3.0
ENV EPLUS_SOURCE="EnergyPlus"
# EnergyPlusJSON copied from TESP sources to the context first
ENV EPLUSJSON_SOURCE="EnergyPlusJSON"
# -------------------------------
# The folder on the image where all source files will be copied to,
# so that installation can proceed.
ENV SOURCE_DIR="${WORK_DIR}/sources/"

# --------------------------------------------------------------
# Environment variables needed for the package installation
# --------------------------------------------------------------
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${FNCS_INSTALL}/lib
ENV FNCS_LIBRARY=${FNCS_INSTALL}/lib
ENV FNCS_INCLUDE_DIR=${FNCS_INSTALL}/include
ENV PATH=${PATH}:${FNCS_INSTALL}/bin:${GLD_INSTALL}/bin:${EPLUS_INSTALL}:${EPLUS_INSTALL}/PreProcess:${EPLUS_INSTALL}/PostProcess:${EPLUSJSON_INSTALL}/bin
ENV GLPATH="${GLD_INSTALL}/lib/gridlabd:${GLD_INSTALL}/share/gridlabd"
# default values
ENV FNCS_LOG_FILE=no
ENV FNCS_LOG_STDOUT=no
ENV FNCS_LOG_TRACE=no
ENV FNCS_LOG_LEVEL=DEBUG4

# ------------------------------------------------------------------
# Adding the host source folders to the Docker image source folders
# ------------------------------------------------------------------
COPY --chown=tesp-user:tesp-user ./ ${SOURCE_DIR}

RUN mkdir -p ${SOURCE_DIR} && \
    mkdir -p ${TESP} && \
# ----------------------------------------------------
# INSTALL FNCS
# ----------------------------------------------------
    cd ${SOURCE_DIR}/${FNCS_SOURCE} && \
    autoreconf -if && \
    ./configure --prefix=${FNCS_INSTALL} && \
    make && \
    make install && \
    /bin/rm -r ${SOURCE_DIR}/${FNCS_SOURCE} && \
# ----------------------------------------------------
# INSTALL GridLAB-D
# ----------------------------------------------------
    cd ${SOURCE_DIR}${GLD_SOURCE} && \
    autoreconf -isf && \
    ./configure --prefix=${GLD_INSTALL} --with-fncs=${FNCS_INSTALL} --enable-silent-rules \
    'CPP=gcc -E' 'CXXPP=g++ -E' 'CC=gcc' 'CXX=g++' \ 
    'CFLAGS=-w -O3 -fno-inline-functions' 'CXXFLAGS=-w -O3 -fno-inline-functions -std=c++14' 'LDFLAGS=-w -O3' && \
    make && \
    make install && \
    /bin/rm -r ${SOURCE_DIR}${GLD_SOURCE} && \
# ----------------------------------------------------
# INSTALL Energy Plus
# ----------------------------------------------------
    cd ${SOURCE_DIR}/${EPLUS_SOURCE} && \
    mkdir build && \
    cd ./build && \
    cmake -DCMAKE_INSTALL_PREFIX:PATH=${EPLUS_INSTALL} \
          -DCMAKE_PREFIX_PATH=${FNCS_INSTALL} \
          -DBUILD_FORTRAN=ON -DBUILD_PACKAGE=ON -DENABLE_INSTALL_REMOTE=OFF \
          ${SOURCE_DIR}/${EPLUS_SOURCE} && \
    make -j 4 && \
    make install && \
    /bin/rm -r ${SOURCE_DIR}/${EPLUS_SOURCE} && \
# ----------------------------------------------------
# INSTALL Energy Plus JSON
# ----------------------------------------------------
    cd ${SOURCE_DIR}/${EPLUSJSON_SOURCE} && \
    autoheader && \
    aclocal && \
    automake --add-missing && \
    autoreconf -if && \
    ./configure --prefix=${EPLUSJSON_INSTALL} --with-fncs=${FNCS_INSTALL} && \
    make && \
    make install && \
    /bin/rm -r ${SOURCE_DIR}/${EPLUSJSON_SOURCE} && \
    /bin/rm -r ${SOURCE_DIR}

FROM ${DOCKER_IMG}${DOCKER_IMG_VERSION} AS tesp-fncs-production
# -----------------------------------------------------
# Environment variables giving the location where TESP
# related software will be installed on the Docker container.
# -----------------------------------------------------
ENV TESP=${WORK_DIR}/tesp-platform
ENV FNCS_INSTALL=${TESP}/FNCSInstall
ENV GLD_INSTALL=${TESP}/GridLABDInstall
ENV EPLUS_INSTALL=${TESP}/EnergyPlusInstall
ENV EPLUSJSON_INSTALL=${TESP}/EPlusJSONInstall
# --------------------------------------------------------------
# Environment variables needed for the package installation
# --------------------------------------------------------------
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${FNCS_INSTALL}/lib
ENV FNCS_LIBRARY=${FNCS_INSTALL}/lib
ENV FNCS_INCLUDE_DIR=${FNCS_INSTALL}/include
ENV PATH=${PATH}:${FNCS_INSTALL}/bin:${GLD_INSTALL}/bin:${EPLUS_INSTALL}:${EPLUS_INSTALL}/PreProcess:${EPLUS_INSTALL}/PostProcess:${EPLUSJSON_INSTALL}/bin
ENV GLPATH=${GLD_INSTALL}/lib/gridlabd:${GLD_INSTALL}/share/gridlabd
COPY --from=tesp-fncs-builder --chown=tesp-user ${WORK_DIR} ${WORK_DIR} 