ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# Build runtime image
FROM cosim-library:tesp_$TAG AS cosim-build

ARG SIM_USER
ARG SIM_GRP

ENV SIM_HOME=/home/$SIM_USER
ENV SIM_EMAIL=pnnl.com

USER $SIM_USER
WORKDIR $SIM_HOME

# CoSim exports
ENV TESPDIR=$SIM_HOME/tesp
ENV INSTDIR=$SIM_HOME/tenv
ENV REPO_DIR=$SIM_HOME/repo
ENV BUILD_DIR=$SIM_HOME/build

# COMPILE exports
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYHELICS_INSTALL=$INSTDIR
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
ENV CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial:$INSTDIR/include
ENV FNCS_INCLUDE_DIR=$INSTDIR/include
ENV FNCS_LIBRARY=$INSTDIR/lib
ENV LD_LIBRARY_PATH=$INSTDIR/lib
ENV LD_RUN_PATH=$INSTDIR/lib

# PATH
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$SIM_HOME/.local/bin:$PATH
ENV PATH=$PATH:$INSTDIR/energyplus
ENV PATH=$PATH:$INSTDIR/energyplus/PreProcess
ENV PATH=$PATH:$INSTDIR/energyplus/PostProcess
ENV PATH=$PATH:$TESPDIR/scripts/helpers

# PSST exports
ENV PSST_SOLVER=cbc
# 'PSST_SOLVER path' -- one of "cbc", "ipopt", "/ibm/cplex/bin/x86-64_linux/cplexamp"
ENV PSST_WARNING=ignore
# 'PSST_WARNING action' -- one of "error", "ignore", "always", "default", "module", or "once"

COPY . ${BUILD_DIR}

RUN echo "===== Building TESP Build =====" && \
  echo "Configure name and email for git" && \
  git config --global user.name "${SIM_USER}" && \
  git config --global user.email "${SIM_USER}@${SIM_EMAIL}" && \
  git config --global credential.helper store && \
  echo "Directory structure for build" && \
  mkdir -p tenv && \
  mkdir -p repo && \
  mkdir -p tesp && \
  echo "$SIM_USER" | sudo -S chown -hR $SIM_USER:$SIM_GRP ${SIM_HOME} && \
  echo "$SIM_USER" | sudo -S chmod -R g+rwX ${SIM_HOME} && \
  echo "Cloning or download all relevant repositories..." && \
  cd ${REPO_DIR} || exit && \
  echo "++++++++++++++ TESP" && \
  git clone -b develop https://github.com/pnnl/tesp.git && \
  mv tesp/src ${TESPDIR} && \
  mv tesp/data ${TESPDIR} && \
  mv tesp/DISCLAIMER.txt ${TESPDIR} && \
  mv tesp/LICENSE ${TESPDIR} && \
  mv tesp/README.md ${TESPDIR} && \
  mv tesp/requirements.txt ${TESPDIR} && \
  echo "++++++++++++++ PSST" && \
  git clone -b master https://github.com/ames-market/AMES-V5.0.git && \
  ${BUILD_DIR}/patch.sh AMES-V5.0 AMES-V5.0 && \
  mv AMES-V5.0/README.rst . && \
  mv AMES-V5.0/psst . && \
  echo "++++++++++++++ FNCS" && \
  git clone -b feature/opendss https://github.com/FNCS/fncs.git && \
  ${BUILD_DIR}/patch.sh fncs fncs && \
  echo "++++++++++++++ HELICS" && \
  git clone -b main https://github.com/GMLC-TDC/HELICS-src && \
  ${BUILD_DIR}/patch.sh HELICS-src HELICS-src && \
  echo "++++++++++++++ GRIDLAB" && \
  git clone -b develop https://github.com/gridlab-d/gridlab-d.git && \
  ${BUILD_DIR}/patch.sh gridlab-d gridlab-d && \
  echo "++++++++++++++ ENERGYPLUS" && \
  git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git && \
  ${BUILD_DIR}/patch.sh EnergyPlus EnergyPlus && \
  echo "++++++++++++++ NS-3" && \
  git clone https://gitlab.com/nsnam/ns-3-dev.git && \
  ${BUILD_DIR}/patch.sh ns-3-dev ns-3-dev && \
  echo "++++++++++++++ HELICS-NS-3" && \
  git clone -b main https://github.com/GMLC-TDC/helics-ns3 ns-3-dev/contrib/helics && \
  ${BUILD_DIR}/patch.sh ns-3-dev/contrib/helics helics-ns3 && \
  echo "++++++++++++++ KLU SOLVER" && \
  unzip -q ${BUILD_DIR}/KLU_DLL.zip -d ./KLU_DLL && \
  echo "++++++++++++++  Compiling and Installing grid software is starting!  ++++++++++++++" && \
  cd ${BUILD_DIR} || exit && \
  echo "Compiling and Installing FNCS..." && \
  ./fncs_b.sh clean > fncs.log 2>&1 && \
  echo "Compiling and Installing FNCS for Java..." && \
  ./fncs_j_b.sh clean > fncs_j.log 2>&1 && \
  echo "Compiling and Installing HELICS..." && \
  ./HELICS-src_b.sh clean > HELICS-src.log 2>&1 && \
  echo "Compiling and Installing KLU..." && \
  ./KLU_DLL_b.sh clean > KLU_DLL.log 2>&1 && \
  echo "Compiling and Installing Gridlabd..." && \
  ./gridlab-d_b.sh clean > gridlab-d.log 2>&1 && \
  echo "Compiling and Installing EnergyPlus..." && \
  ./EnergyPlus_b.sh clean > EnergyPlus.log 2>&1 && \
  echo "Compiling and Installing NS-3..." && \
  ./ns-3-dev_b.sh clean > ns-3-dev.log 2>&1 && \
  echo "Compiling and Installing Ipopt with ASL and Mumps..." && \
  ./ipopt_b.sh clean > ipopt.log 2>&1 && \
  echo "Compiling and Installing TESP EnergyPlus agents and TMY converter..." && \
  ./tesp_b.sh clean > tesp.log 2>&1 && \
  echo "Remove all repositories..." && \
  cd ${REPO_DIR} || exit && \
  rm -r tesp && \
  rm -r AMES-V5.0 && \
  rm -r fncs && \
  rm -r HELICS-src && \
  rm -r KLU_DLL && \
  rm -r gridlab-d && \
  rm -r EnergyPlus && \
  rm -r ns-3-dev && \
  rm -r Ipopt && \
  rm -r ThirdParty-ASL && \
  rm -r ThirdParty-Mumps && \
  echo "Install Python Libraries and TESP pypi..." && \
  pip install --no-warn-script-location --upgrade pip  > "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir -r ${TESPDIR}/requirements.txt  >> "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir helics[cli]  >> "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir -e ${REPO_DIR}/psst  >> "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir -e ${TESPDIR}/src/tesp_support  >> "pypi.log" && \
  echo "${SIM_USER}" | sudo -S ldconfig && \
  ${BUILD_DIR}/versions.sh
