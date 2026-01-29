ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# ============================================================
# Base: Environment setup
# ============================================================
FROM tesp-library:tesp_$TAG AS base
ARG SIM_USER
ARG SIM_GRP
ENV SIM_HOME=/home/$SIM_USER
ENV SIM_EMAIL=pnnl.com
ENV TESPDIR=$SIM_HOME/tesp
ENV INSTDIR=$SIM_HOME/tenv
ENV REPO_DIR=$SIM_HOME/repo
ENV BUILD_DIR=$SIM_HOME/build
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYHELICS_INSTALL=$INSTDIR
ENV GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
ENV CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial:$INSTDIR/include
ENV FNCS_INCLUDE_DIR=$INSTDIR/include
ENV FNCS_LIBRARY=$INSTDIR/lib
ENV LD_LIBRARY_PATH=$INSTDIR/lib
ENV LD_RUN_PATH=$INSTDIR/lib
ENV PATH=$JAVA_HOME:$INSTDIR/bin:$SIM_HOME/.local/bin:$PATH
ENV PATH=$PATH:$INSTDIR/energyplus:$INSTDIR/energyplus/PreProcess:$INSTDIR/energyplus/PostProcess
ENV PATH=$PATH:$TESPDIR/scripts/helpers
ENV PSST_SOLVER=cbc
ENV PSST_WARNING=ignore
USER $SIM_USER
WORKDIR $SIM_HOME

# ============================================================
# Setup and clone all repositories
# ============================================================
FROM base AS tesp-clone
ARG SIM_USER
ARG SIM_GRP
COPY . ${BUILD_DIR}
RUN mkdir -p tenv repo tesp && \
    echo "$SIM_USER" | sudo -S chown -hR $SIM_USER:$SIM_GRP ${SIM_HOME} && \
    echo "$SIM_USER" | sudo -S chmod -R g+rwX ${SIM_HOME} && \
    git config --global user.name "${SIM_USER}" && \
    git config --global user.email "${SIM_USER}@${SIM_EMAIL}" && \
    git config --global credential.helper store && \
    cd ${REPO_DIR} && \
    git clone -b develop https://github.com/pnnl/tesp.git && \
    mv tesp/src tesp/data tesp/DISCLAIMER.txt tesp/LICENSE tesp/README.md tesp/requirements.txt ${TESPDIR}/ && \
    git clone -b master https://github.com/ames-market/AMES-V5.0.git && \
    ${BUILD_DIR}/patch.sh AMES-V5.0 AMES-V5.0 && \
    mv AMES-V5.0/README.rst . && \
    mv AMES-V5.0/psst . && \
    git clone -b feature/opendss https://github.com/FNCS/fncs.git && \
    ${BUILD_DIR}/patch.sh fncs fncs && \
    git clone -b main https://github.com/GMLC-TDC/HELICS-src && \
    ${BUILD_DIR}/patch.sh HELICS-src HELICS-src && \
    git clone -b develop https://github.com/gridlab-d/gridlab-d.git && \
    ${BUILD_DIR}/patch.sh gridlab-d gridlab-d && \
    git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git && \
    ${BUILD_DIR}/patch.sh EnergyPlus EnergyPlus && \
    git clone https://gitlab.com/nsnam/ns-3-dev.git && \
    ${BUILD_DIR}/patch.sh ns-3-dev ns-3-dev && \
    git clone -b main https://github.com/GMLC-TDC/helics-ns3 ns-3-dev/contrib/helics && \
    ${BUILD_DIR}/patch.sh ns-3-dev/contrib/helics helics-ns3 && \
    unzip -q ${BUILD_DIR}/KLU_DLL.zip -d ./KLU_DLL

# ============================================================
# FNCS
# ============================================================
FROM tesp-clone AS build-fncs
RUN cd ${BUILD_DIR} && \
    ./fncs_b.sh clean > fncs.log 2>&1 && \
    ./fncs_j_b.sh clean > fncs_j.log 2>&1

# ============================================================
# HELICS
# ============================================================
FROM build-fncs AS build-helics
RUN cd ${BUILD_DIR} && \
    ./HELICS-src_b.sh clean > HELICS-src.log 2>&1

# ============================================================
# KLU
# ============================================================
FROM build-helics AS build-klu
RUN cd ${BUILD_DIR} && \
    ./KLU_DLL_b.sh clean > KLU_DLL.log 2>&1

# ============================================================
# GridLAB-D
# ============================================================
FROM build-klu AS build-gridlabd
RUN cd ${BUILD_DIR} && \
    ./gridlab-d_b.sh clean > gridlab-d.log 2>&1

# ============================================================
# EnergyPlus
# ============================================================
FROM build-gridlabd AS build-energyplus
RUN cd ${BUILD_DIR} && \
    ./EnergyPlus_b.sh clean > EnergyPlus.log 2>&1

# ============================================================
# NS-3
# ============================================================
FROM build-energyplus AS build-ns3
RUN cd ${BUILD_DIR} && \
    ./ns-3-dev_b.sh clean 

# ============================================================
# Ipopt
# ============================================================
FROM build-ns3 AS build-ipopt
RUN cd ${BUILD_DIR} && \
    ./ipopt_b.sh clean > ipopt.log 2>&1

# ============================================================
# TESP Agents
# ============================================================
FROM build-ipopt AS build-tesp-agents
RUN cd ${BUILD_DIR} && \
    ./tesp_b.sh clean > tesp.log 2>&1

# ============================================================
# Cleanup and Python packages
# ============================================================
FROM build-tesp-agents AS build-python
RUN cd ${REPO_DIR} && \
    rm -rf tesp AMES-V5.0 fncs HELICS-src KLU_DLL gridlab-d EnergyPlus ns-3-dev Ipopt ThirdParty-ASL ThirdParty-Mumps && \
    pip install --no-warn-script-location --break-system-packages --upgrade pip > "${BUILD_DIR}/pypi.log" && \
    pip install --no-warn-script-location --break-system-packages --no-cache-dir -r ${TESPDIR}/requirements.txt >> "${BUILD_DIR}/pypi.log" && \
    pip install --no-warn-script-location --break-system-packages --no-cache-dir helics[cli] >> "${BUILD_DIR}/pypi.log" && \
    pip install --no-warn-script-location --break-system-packages --no-cache-dir -e ${REPO_DIR}/psst >> "${BUILD_DIR}/pypi.log" && \
    pip install --no-warn-script-location --break-system-packages --no-cache-dir -e ${TESPDIR}/src/tesp_support >> "${BUILD_DIR}/pypi.log"

# ============================================================
# Final image
# ============================================================
FROM build-python AS tesp-build
ARG SIM_USER
USER root
RUN ldconfig
USER $SIM_USER
RUN ${BUILD_DIR}/versions.sh && \
    gridlabd --version && \
    helics_broker --version && \
    energyplus --version && \
    fncs_broker --help > /dev/null && \
    python3 -c "import tesp_support; print('tesp_support OK')"