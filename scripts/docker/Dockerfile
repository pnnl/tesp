ARG UBUNTU=ubuntu
ARG UBUNTU_VERSION=:20.04

FROM ${UBUNTU}${UBUNTU_VERSION} AS ubuntu-base

# TESP user name and work directory
ENV USER_NAME=worker
ENV USER_HOME=/home/$USER_NAME

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
  lsof \
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
  python3.8 \
  python3.8-venv \
  python3-pip \
  python3-tk \
  python3-pil.imagetk && \
  ln -s /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/default-java && \
  echo "root:tesp" | chpasswd && \
  echo "<<<< Adding the TESP user >>>>" && \
  useradd -m -s /bin/bash ${USER_NAME} && \
  echo "<<<< Changing new user password >>>>" && \
  echo "${USER_NAME}:${USER_NAME}" | chpasswd && \
  usermod -aG sudo ${USER_NAME}

USER ${USER_NAME}
WORKDIR ${USER_HOME}

FROM ubuntu-base AS tesp-production

# TESP exports
ENV TESPDIR=${USER_HOME}/tesp
ENV INSTDIR=${USER_HOME}/tesp/tenv
ENV REPODIR=${USER_HOME}/tesp/repository
ENV TESPBUILD=$TESPDIR/scripts/build
ENV TESPHELPR=$TESPDIR/scripts/helpers

# COMPILE exports
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYHELICS_INSTALL=$INSTDIR
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
ENV CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial
ENV FNCS_INCLUDE_DIR=$INSTDIR/include
ENV FNCS_LIBRARY=$INSTDIR/lib
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$INSTDIR/lib
ENV LD_RUN_PATH=$INSTDIR/lib

# PATH
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$PATH
ENV PATH=$PATH:$INSTDIR/energyplus
ENV PATH=$PATH:$INSTDIR/energyplus/PreProcess
ENV PATH=$PATH:$INSTDIR/energyplus/PostProcess
ENV PATH=$PATH:$TESPHELPR

# PSST exports
ENV PSST_SOLVER=cbc
# 'PSST_SOLVER path' -- one of "cbc", "ipopt", "/ibm/cplex/bin/x86-64_linux/cplexamp"
ENV PSST_WARNING=ignore

RUN git config --global user.name "${USER_NAME}" && \
  git config --global user.email "${USER_NAME}@${USER_NAME}.com" && \
  echo "User .name=${USER_NAME} and .email=${USER_NAME}@${USER_NAME}.com have been set for git repositories!" && \
  git config --global credential.helper store && \
  echo "Clone directory structure for TESP" && \
  cd ${HOME} || exit && \
  echo "++++++++++++++ TESP" && \
  git clone -b main https://github.com/pnnl/tesp.git && \
  cd ${TESPDIR} || exit && \
  mkdir -p repository && \
  mkdir -p tenv && \
  python3.8 -m pip install virtualenv && \
  "${HOME}/.local/bin/virtualenv" venv --prompt TESP && \
  echo "Copy TESP environment variables to $HOME/tespEnv" && \
  cp ${TESPDIR}/scripts/tespEnv "$HOME/" && \
  echo "Activate the python virtual environment" && \
  . ${TESPDIR}/venv/bin/activate && \
  echo "Download all relevant repositories..." && \
  cd ${REPODIR} || exit && \
  echo "++++++++++++++ PSST" && \
  git clone -b master https://github.com/ames-market/AMES-V5.0.git && \
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
  git clone -b main https://github.com/GMLC-TDC/helics-ns3 ns-3-dev/contrib/helics && \
  "${TESPBUILD}"/patch.sh ns-3-dev/contrib/helics helics-ns3 && \
  echo "++++++++++++++ KLU SOLVER" && \
  svn export https://github.com/gridlab-d/tools/branches/klu-build-update/solver_klu/source/KLU_DLL && \
  cd ${TESPDIR}/scripts && \
  echo "++++++++++++++  Compiling and Installing TESP software is starting!  ++++++++++++++" && \
  # Install all pip libraries
  echo "Installing Python Libraries..." && \
  pip3 install --upgrade pip > "${TESPBUILD}/tesp_pypi.log" && \
  pip3 install -r "${TESPDIR}/requirements.txt" >> "${TESPBUILD}/tesp_pypi.log" && \
  #develop tesp api
  echo "Installing Python TESP API..." && \
  cd "${TESPDIR}/src/tesp_support" || exit && \
  pip3 install -e . > "${TESPBUILD}/tesp_api.log" && \
  #develop psst api
  echo "Installing Python PSST..." && \
  cd "${REPODIR}/AMES-V5.0/psst" || exit && \
  pip3 install -e . > "${TESPBUILD}/AMES-V5.0.log" && \
  cd "${TESPBUILD}" && \
  echo "Compiling and Installing FNCS..." && \
  ./fncs_b.sh clean > fncs.log 2>&1 && \
  echo "Compiling and Installing FNCS for Java..." && \
  ./fncs_j_b.sh clean > fncs_j.log 2>&1 && \
  /bin/rm -r ${REPODIR}/fncs && \
  echo "Compiling and Installing HELICS..." && \
  ./HELICS-src_b.sh clean > HELICS-src.log 2>&1 && \
  /bin/rm -r  ${REPODIR}/HELICS-src && \
  echo "Compiling and Installing KLU..." && \
  ./KLU_DLL_b.sh clean > KLU_DLL.log 2>&1 && \
  /bin/rm -r ${REPODIR}/KLU_DLL && \
  echo "Compiling and Installing Gridlabd..." && \
  ./gridlab-d_b.sh clean > gridlab-d.log 2>&1 && \
  /bin/rm -r ${REPODIR}/gridlab-d && \
  echo "Compiling and Installing EnergyPlus..." && \
  ./EnergyPlus_b.sh clean > EnergyPlus.log 2>&1 && \
  /bin/rm -r ${REPODIR}/EnergyPlus && \
  echo "Compiling and Installing EnergyPlus for Java..." && \
  ./EnergyPlus_j_b.sh clean > EnergyPlus_j.log 2>&1 && \
  echo "Compiling and Installing NS-3..." && \
  ./ns-3-dev_b.sh clean > ns-3-dev.log 2>&1 && \
  /bin/rm -r ${REPODIR}/ns-3-dev && \
  echo "Compiling and Installing Ipopt with ASL and Mumps..." && \
  ./ipopt_b.sh clean > ipopt.log 2>&1 && \
  /bin/rm -r ${REPODIR}/Ipopt && \
  /bin/rm -r ${REPODIR}/ThirdParty-ASL && \
  /bin/rm -r ${REPODIR}/ThirdParty-Mumps && \
  echo "Compiling and Installing TMY3toTMY2_ansi..." && \
  cd "${TESPDIR}/data/weather/TMY2EPW/source_code" || exit && \
  gcc TMY3toTMY2_ansi.c -o TMY3toTMY2_ansi && \
  /bin/mv TMY3toTMY2_ansi "${INSTDIR}/bin" && \
  cd "${TESPBUILD}" || exit && \
  echo "Installing HELICS Python bindings..." && \
  ./HELICS-py.sh clean > HELICS-py.log 2>&1 && \
  echo "${USER_NAME}" | sudo -S ldconfig && \
  cd "${TESPBUILD}" || exit && \
  ./versions.sh