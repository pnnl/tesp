ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:20.04

FROM ${UBUNTU}${UBUNTU_VERSION} AS ubuntu-base

ENV USER_NAME=tesp-user
ENV TESP_HOME=/home/${USER_NAME}

RUN export DEBIAN_FRONTEND=noninteractive && \
  export DEBCONF_NONINTERACTIVE_SEEN=true && \
  apt-get update && \
  echo "===== UPGRADING =====" && \
  apt-get upgrade -y && \
  echo "===== INSTALL STUFF =====" && \
  apt-get install -y \
  sudo \
  wget \
  pkgconf \
  git \
  build-essential \
  autoconf \
  libtool \
  libjsoncpp-dev \
  gfortran \
  cmake \
  subversion \
  unzip \
  # Java support
  openjdk-11-jdk \
  # for HELICS and FNCS
  libzmq5-dev \
  libczmq-dev \
  libboost-dev \
  # for GridLAB-D
  libxerces-c-dev \
  libhdf5-serial-dev \
  libsuitesparse-dev \
  # end users replace libsuitesparse-dev with libklu1, which is licensed LGPL
  # for solvers Ipopt/cbc used by AMES/Agents
  coinor-cbc \
  coinor-libcbc-dev \
  coinor-libipopt-dev \
  liblapack-dev \
  libmetis-dev \
  # Python support
  # if not using miniconda (avoid Python 3.7 on Ubuntu for now)
  python3-pip \
  python3-tk && \
  ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java && \
  echo "root:tesp" | chpasswd && \
  echo "<<<< Adding the TESP user >>>>" && \
  useradd -m -s /bin/bash ${USER_NAME} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${USER_NAME}:${USER_NAME}" | chpasswd && \
  usermod -aG sudo ${USER_NAME}

USER ${USER_NAME}
WORKDIR ${TESP_HOME}

FROM ubuntu-base AS tesp-production

ENV TESPDIR=${TESP_HOME}/tesp/repository/tesp
ENV INSTDIR=${TESP_HOME}/tesp/installed
ENV REPODIR=${TESP_HOME}/tesp/repository
ENV WAREDIR=${TESP_HOME}/tesp/software
ENV TESPBUILD=$TESPDIR/scripts/build
ENV TESPHELPR=$TESPDIR/scripts/helpers

ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
ENV FNCS_INCLUDE_DIR=$INSTDIR/include
ENV FNCS_LIBRARY=$INSTDIR/lib
ENV CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$INSTDIR/lib

# JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# PYHELICS_INSTALL
ENV PYHELICS_INSTALL=$INSTDIR

# PATH
ENV PATH=$PATH:$JAVA_HOME
ENV PATH=$PATH:$INSTDIR/bin
ENV PATH=$PATH:$INSTDIR/energyplus
ENV PATH=$PATH:$INSTDIR/energyplus/PreProcess
ENV PATH=$PATH:$INSTDIR/energyplus/PostProcess
ENV PATH=$PATH:$TESPHELPR

# PSST environment variables
ENV PSST_SOLVER=cbc
# 'PSST_SOLVER path' -- one of "cbc", "ipopt", "/ibm/cplex/bin/x86-64_linux/cplexamp"
ENV PSST_WARNING=ignore

RUN git config --global user.name "${USER_NAME}" && \
  git config --global user.email "${USER_NAME}@${USER_NAME}.com" && \
  echo "User .name=${USER_NAME} and .email=${USER_NAME}@${USER_NAME}.com have been set for git repositories!" && \
  git config --global credential.helper store && \
  echo "Create directory structure for TESP" && \
  cd ${HOME} && \
  mkdir -p tesp && \
  cd tesp && \
  mkdir -p repository && \
  mkdir -p installed && \
  mkdir -p software && \
  cd repository && \
  echo "++++++++++++++ TESP" && \
  git clone -b main https://github.com/pnnl/tesp.git && \
  echo "Download all relevant repositories..." && \
  echo "++++++++++++++ PSST" && \
  git clone https://github.com/ames-market/AMES-V5.0.git && \
  echo "Applying the patch for AMES...... from ${TESPBUILD}" && \
  ${TESPBUILD}/patch.sh AMES-V5.0 AMES-V5.0 && \
  echo "++++++++++++++ FNCS" && \
  git clone -b feature/opendss https://github.com/FNCS/fncs.git && \
  ${TESPBUILD}/patch.sh fncs fncs && \
  echo "++++++++++++++ HELICS" && \
  git clone -b main https://github.com/GMLC-TDC/HELICS-src && \
  "${TESPBUILD}"/patch.sh HELICS-src HELICS-src && \
  echo "++++++++++++++ GRIDLAB" && \
  git clone -b develop https://github.com/gridlab-d/gridlab-d.git && \
  "${TESPBUILD}"/patch.sh gridlab-d gridlab-d && \
  echo "++++++++++++++ ENERGYPLUS" && \
  git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git && \
  "${TESPBUILD}"/patch.sh EnergyPlus EnergyPlus && \
  echo "++++++++++++++ NS-3" && \
  git clone https://gitlab.com/nsnam/ns-3-dev.git && \
  "${TESPBUILD}"/patch.sh ns-3-dev ns-3-dev && \
  echo "++++++++++++++ HELICS-NS-3" && \
  cd ns-3-dev && \
  git clone -b helics3-update-v2 https://github.com/GMLC-TDC/helics-ns3 contrib/helics && \
  cd .. && \
  echo "++++++++++++++ KLU SOLVER" && \
  svn export https://github.com/gridlab-d/tools/branches/klu-build-update/solver_klu/source/KLU_DLL && \
  cd ${TESPDIR}/scripts && \
  echo "++++++++++++++  Compiling and Installing TESP software is starting!  ++++++++++++++" && \
  # Install all pip libraries
  echo "Installing Python Libraries..." && \
  echo "${USER_NAME}" | sudo -S -H pip3 install wheel colorama glm seaborn matplotlib networkx numpy pandas pulp xlrd pkgconfig && \
  echo "${USER_NAME}" | sudo -S -H pip3 install pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py && \
  #develop tesp api
  echo "Installing Python TESP API..." && \
  cd "${TESPDIR}/src/tesp_support" && \
  echo "${USER_NAME}" | sudo -S -H pip3 install -e . && \
  #develop psst api
  echo "Installing Python PSST..." && \
  cd "${REPODIR}/AMES-V5.0/psst" && \
  echo "${USER_NAME}" | sudo -S -H pip3 install -e . && \
  cd "${TESPBUILD}" && \
  echo "Compiling and Installing FNCS..." && \
  ./fncs_b.sh clean && \
  echo "Compiling and Installing FNCS for Java..." && \
  ./fncs_j_b.sh clean && \
  /bin/rm -r ${REPODIR}/fncs && \
  echo "Compiling and Installing HELICS..." && \
  ./HELICS-src_b.sh clean && \
  /bin/rm -r  ${REPODIR}/HELICS-src && \
  echo "${USER_NAME}" | sudo -S -H pip3 install helics && \
  echo "============ HELICS CLI ==================" && \
  echo "${USER_NAME}" | sudo -S -H pip3 install git+https://github.com/GMLC-TDC/helics-cli.git@main && \
  # HELICS APPS
  echo "============ HELICS APPS ==================" && \
  echo "${USER_NAME}" | sudo -S -H pip3 install --upgrade helics-apps && \
  echo "Compiling and Installing KLU..." && \
  ./KLU_DLL_b.sh clean && \
  /bin/rm -r ${REPODIR}/KLU_DLL && \
  echo "Compiling and Installing Gridlabd..." && \
  ./gridlab-d_b.sh clean && \
  /bin/rm -r ${REPODIR}/gridlab-d && \
  echo "Compiling and Installing EnergyPlus..." && \
  ./EnergyPlus_b.sh clean && \
  /bin/rm -r ${REPODIR}/EnergyPlus && \
  echo "Compiling and Installing EnergyPlus for Java..." && \
  ./EnergyPlus_j_b.sh clean && \
  echo "Compiling and Installing NS-3..." && \
  ./ns-3-dev_b.sh clean && \
  /bin/rm -r ${REPODIR}/ns-3-dev && \
  echo "Compiling and Installing Ipopt with ASL and Mumps..." && \
  ./ipopt_b.sh clean && \
  /bin/rm -r ${WAREDIR} && \
  echo "Compiling and Installing TMY3toTMY2_ansi..." && \
  cd "${TESPDIR}/data/weather/TMY2EPW/source_code" && \
  gcc TMY3toTMY2_ansi.c -o TMY3toTMY2_ansi && \
  /bin/mv TMY3toTMY2_ansi "${INSTDIR}/bin" && \
  echo "${USER_NAME}" | sudo -S ldconfig && \
  cd "${TESPBUILD}" && \
  ./versions.sh