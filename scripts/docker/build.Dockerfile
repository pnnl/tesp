ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# Build runtime image
FROM cosim-library:tesp_$TAG AS cosim-build

ARG SIM_USER

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

RUN echo "===== Building CoSim Build =====" && \
  echo "Configure name and email for git" && \
  git config --global user.name "${SIM_USER}" && \
  git config --global user.email "${SIM_USER}@${SIM_EMAIL}" && \
  git config --global credential.helper store && \
  echo "Directory structure for build" && \
  mkdir -p tenv && \
  mkdir -p repo && \
  mkdir -p tesp

# Copy the build instructions
COPY . ${BUILD_DIR}
USER root
RUN chown -hR $SIM_USER:$SIM_USER ${BUILD_DIR}

USER $SIM_USER
WORKDIR $SIM_HOME

RUN echo "Cloning or download all relevant repositories..." && \
  cd "${REPO_DIR}" || exit && \
  echo "++++++++++++++ TESP" && \
  git clone -b develop https://github.com/pnnl/tesp.git && \
#  ${BUILD_DIR}/patch.sh tesp tesp && \
  echo "++++++++++++++ PSST" && \
  git clone -b master https://github.com/ames-market/AMES-V5.0.git && \
  ${BUILD_DIR}/patch.sh AMES-V5.0 AMES-V5.0 && \
  mv AMES-V5.0/README.rst . && \
  mv AMES-V5.0/psst . && \
  rm -rf AMES-V5.0 && \
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
  echo "++++++++++++++  Compiling and Installing TESP software is starting!  ++++++++++++++" && \
  cd ${BUILD_DIR} || exit && \
  echo "Compiling and Installing FNCS..." && \
  ./fncs_b.sh clean > fncs.log 2>&1 && \
  echo "Compiling and Installing FNCS for Java..." && \
  ./fncs_j_b.sh clean > fncs_j.log 2>&1 && \
  /bin/rm -r ${REPO_DIR}/fncs && \
  echo "Compiling and Installing HELICS..." && \
  ./HELICS-src_b.sh clean > HELICS-src.log 2>&1 && \
  /bin/rm -r ${REPO_DIR}/HELICS-src && \
  echo "Compiling and Installing KLU..." && \
  ./KLU_DLL_b.sh clean > KLU_DLL.log 2>&1 && \
  /bin/rm -r ${REPO_DIR}/KLU_DLL && \
  echo "Compiling and Installing Gridlabd..." && \
  ./gridlab-d_b.sh clean > gridlab-d.log 2>&1 && \
  /bin/rm -r ${REPO_DIR}/gridlab-d && \
  echo "Compiling and Installing EnergyPlus..." && \
  ./EnergyPlus_b.sh clean > EnergyPlus.log 2>&1 && \
  /bin/rm -r ${REPO_DIR}/EnergyPlus && \
  echo "Compiling and Installing NS-3..." && \
  ./ns-3-dev_b.sh clean > ns-3-dev.log 2>&1 && \
  /bin/rm -r ${REPO_DIR}/ns-3-dev && \
  echo "Compiling and Installing Ipopt with ASL and Mumps..." && \
  ./ipopt_b.sh clean > ipopt.log 2>&1 && \
  /bin/rm -r ${REPO_DIR}/Ipopt && \
  /bin/rm -r ${REPO_DIR}/ThirdParty-ASL && \
  /bin/rm -r ${REPO_DIR}/ThirdParty-Mumps && \
  echo "Compiling and Installing TESP EnergyPlus agents and TMY converter..." && \
  cp -r ${REPO_DIR}/tesp/src ${TESPDIR} && \
  cp -r ${REPO_DIR}/tesp/data ${TESPDIR} && \
  cp ${REPO_DIR}/tesp/README.md ${TESPDIR} && \
  cp ${REPO_DIR}/tesp/LICENSE ${TESPDIR} && \
  cp ${REPO_DIR}/tesp/requirements.txt ${TESPDIR} && \
  /bin/rm -r ${REPO_DIR}/tesp && \
  ./tesp_b.sh clean > tesp.log 2>&1 && \
  echo "Install TESP and Misc. Python Libraries..." && \
  pip install --no-warn-script-location --upgrade pip  > "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir -r ${TESPDIR}/requirements.txt  >> "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir helics[cli]  >> "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir -e ${REPO_DIR}/psst  >> "pypi.log" && \
  pip install --no-warn-script-location --no-cache-dir -e ${TESPDIR}/src/tesp_support  >> "pypi.log" && \
  echo "${SIM_USER}" | sudo -S ldconfig && \
  ./versions.sh
