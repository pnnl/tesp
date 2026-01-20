ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# ============================================================
# Base stage: Common setup
# ============================================================
FROM cosim-library:tesp_$TAG AS base
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
ENV PSST_SOLVER=cbc
ENV PSST_WARNING=ignore

USER $SIM_USER
WORKDIR $SIM_HOME

# ============================================================
# Stage: Setup directories and clone TESP
# ============================================================
FROM base AS tesp-clone
ARG SIM_USER
ARG SIM_GRP
COPY . ${BUILD_DIR}

RUN echo "===== Setup & TESP Clone =====" && \
    git config --global user.name "${SIM_USER}" && \
    git config --global user.email "${SIM_USER}@${SIM_EMAIL}" && \
    git config --global credential.helper store && \
    mkdir -p tenv repo tesp && \
    echo "$SIM_USER" | sudo -S chown -hR $SIM_USER:$SIM_GRP ${SIM_HOME} && \
    echo "$SIM_USER" | sudo -S chmod -R g+rwX ${SIM_HOME} && \
    cd ${REPO_DIR} && \
    git clone -b develop https://github.com/pnnl/tesp.git && \
    mv tesp/src ${TESPDIR} && \
    mv tesp/data ${TESPDIR} && \
    mv tesp/DISCLAIMER.txt ${TESPDIR} && \
    mv tesp/LICENSE ${TESPDIR} && \
    mv tesp/README.md ${TESPDIR} && \
    mv tesp/requirements.txt ${TESPDIR} && \
    rm -rf tesp

# ============================================================
# Stage: Python dependencies (no native build dependencies)
# ============================================================
FROM tesp-clone AS python-deps
ARG BUILD_TESP=yes
ARG BUILD_PSST=yes

RUN echo "===== Python Dependencies =====" && \
    pip install --no-warn-script-location --break-system-packages --upgrade pip > "${BUILD_DIR}/pypi.log" && \
    pip install --no-warn-script-location --break-system-packages --no-cache-dir -r ${TESPDIR}/requirements.txt >> "${BUILD_DIR}/pypi.log"

RUN if [ "${BUILD_TESP}" = "yes" ]; then \
      echo "===== TESP Python Package =====" && \
      pip install --no-warn-script-location --break-system-packages --no-cache-dir -e ${TESPDIR}/src/tesp_support >> "${BUILD_DIR}/pypi.log" ; \
    fi

RUN if [ "${BUILD_PSST}" = "yes" ]; then \
      echo "===== PSST =====" && \
      cd ${REPO_DIR} && \
      git clone -b master https://github.com/ames-market/AMES-V5.0.git && \
      ${BUILD_DIR}/patch.sh AMES-V5.0 AMES-V5.0 && \
      mv AMES-V5.0/README.rst . && \
      mv AMES-V5.0/psst . && \
      rm -rf AMES-V5.0 && \
      pip install --no-warn-script-location --break-system-packages --no-cache-dir -e ${REPO_DIR}/psst >> "${BUILD_DIR}/pypi.log" ; \
    fi

# ============================================================
# INDEPENDENT BUILD: KLU (no dependencies)
# Can run in parallel with FNCS
# ============================================================
FROM python-deps AS build-klu
ARG BUILD_KLU=yes

RUN if [ "${BUILD_KLU}" = "yes" ]; then \
      echo "===== Building KLU =====" && \
      cd ${REPO_DIR} && \
      unzip -q ${BUILD_DIR}/KLU_DLL.zip -d ./KLU_DLL && \
      cd ${BUILD_DIR} && \
      ./KLU_DLL_b.sh clean > KLU_DLL.log 2>&1 && \
      cd ${REPO_DIR} && \
      rm -rf KLU_DLL ; \
    fi

# ============================================================
# INDEPENDENT BUILD: Ipopt (no dependencies)
# Can run in parallel with FNCS, KLU
# ============================================================
FROM python-deps AS build-ipopt
ARG BUILD_IPOPT=yes

RUN if [ "${BUILD_IPOPT}" = "yes" ]; then \
      echo "===== Building Ipopt =====" && \
      cd ${BUILD_DIR} && \
      ./ipopt_b.sh clean > ipopt.log 2>&1 && \
      cd ${REPO_DIR} && \
      rm -rf Ipopt ThirdParty-ASL ThirdParty-Mumps ; \
    fi

# ============================================================
# BUILD: FNCS (no dependencies, but others depend on it)
# Can run in parallel with KLU, Ipopt
# ============================================================
FROM python-deps AS build-fncs
ARG BUILD_FNCS=yes

RUN if [ "${BUILD_FNCS}" = "yes" ]; then \
      echo "===== Building FNCS =====" && \
      cd ${REPO_DIR} && \
      git clone -b feature/opendss https://github.com/FNCS/fncs.git && \
      ${BUILD_DIR}/patch.sh fncs fncs && \
      cd ${BUILD_DIR} && \
      ./fncs_b.sh clean > fncs.log 2>&1 && \
      ./fncs_j_b.sh clean > fncs_j.log 2>&1 && \
      cd ${REPO_DIR} && \
      rm -rf fncs ; \
    fi

# ============================================================
# BUILD: HELICS (depends on FNCS)
# ============================================================
FROM build-fncs AS build-helics
ARG BUILD_HELICS=yes
ARG BUILD_HELICS_PY=yes

RUN if [ "${BUILD_HELICS}" = "yes" ]; then \
      echo "===== Building HELICS =====" && \
      cd ${REPO_DIR} && \
      git clone -b main https://github.com/GMLC-TDC/HELICS-src && \
      ${BUILD_DIR}/patch.sh HELICS-src HELICS-src && \
      cd ${BUILD_DIR} && \
      ./HELICS-src_b.sh clean > HELICS-src.log 2>&1 && \
      cd ${REPO_DIR} && \
      rm -rf HELICS-src ; \
    fi

RUN if [ "${BUILD_HELICS_PY}" = "yes" ]; then \
      echo "===== HELICS Python =====" && \
      pip install --no-warn-script-location --break-system-packages --no-cache-dir helics[cli] >> "${BUILD_DIR}/pypi.log" ; \
    fi

# ============================================================
# BUILD: EnergyPlus (depends on FNCS)
# Can run in parallel with HELICS
# ============================================================
FROM build-fncs AS build-energyplus
ARG BUILD_ENERGYPLUS=yes
ARG BUILD_FNCS=yes

RUN if [ "${BUILD_ENERGYPLUS}" = "yes" ]; then \
      if [ "${BUILD_FNCS}" != "yes" ]; then echo "WARNING: EnergyPlus may require FNCS"; fi && \
      echo "===== Building EnergyPlus =====" && \
      cd ${REPO_DIR} && \
      git clone -b fncs_9.3.0 https://github.com/FNCS/EnergyPlus.git && \
      ${BUILD_DIR}/patch.sh EnergyPlus EnergyPlus && \
      cd ${BUILD_DIR} && \
      ./EnergyPlus_b.sh clean > EnergyPlus.log 2>&1 && \
      cd ${REPO_DIR} && \
      rm -rf EnergyPlus ; \
    fi

# ============================================================
# BUILD: NS-3 (depends on HELICS, which depends on FNCS)
# ============================================================
FROM build-helics AS build-ns3
ARG BUILD_NS3=yes
ARG BUILD_HELICS=yes

RUN if [ "${BUILD_NS3}" = "yes" ]; then \
      if [ "${BUILD_HELICS}" != "yes" ]; then echo "WARNING: NS-3 may require HELICS"; fi && \
      echo "===== Building NS-3 =====" && \
      cd ${REPO_DIR} && \
      git clone https://gitlab.com/nsnam/ns-3-dev.git && \
      ${BUILD_DIR}/patch.sh ns-3-dev ns-3-dev && \
      git clone -b main https://github.com/GMLC-TDC/helics-ns3 ns-3-dev/contrib/helics && \
      ${BUILD_DIR}/patch.sh ns-3-dev/contrib/helics helics-ns3 && \
      cd ${BUILD_DIR} && \
      ./ns-3-dev_b.sh clean > ns-3-dev.log 2>&1 && \
      cd ${REPO_DIR} && \
      rm -rf ns-3-dev ; \
    fi

# ============================================================
# MERGE: Combine KLU + HELICS for GridLAB-D
# (GridLAB-D depends on FNCS, HELICS, and KLU)
# ============================================================
FROM build-helics AS build-gridlabd-base
ARG SIM_USER
ARG SIM_GRP

# Copy KLU artifacts from parallel build
COPY --from=build-klu --chown=$SIM_USER:$SIM_GRP $SIM_HOME/tenv $SIM_HOME/tenv

# ============================================================
# BUILD: GridLAB-D (depends on FNCS, HELICS, KLU)
# ============================================================
FROM build-gridlabd-base AS build-gridlabd
ARG BUILD_GRIDLABD=yes
ARG BUILD_FNCS=yes
ARG BUILD_HELICS=yes
ARG BUILD_KLU=yes

RUN if [ "${BUILD_GRIDLABD}" = "yes" ]; then \
      if [ "${BUILD_FNCS}" != "yes" ]; then echo "WARNING: GridLAB-D may require FNCS"; fi && \
      if [ "${BUILD_HELICS}" != "yes" ]; then echo "WARNING: GridLAB-D may require HELICS"; fi && \
      if [ "${BUILD_KLU}" != "yes" ]; then echo "WARNING: GridLAB-D may require KLU"; fi && \
      echo "===== Building GridLAB-D =====" && \
      cd ${REPO_DIR} && \
      git clone -b develop https://github.com/gridlab-d/gridlab-d.git && \
      ${BUILD_DIR}/patch.sh gridlab-d gridlab-d && \
      cd ${BUILD_DIR} && \
      ./gridlab-d_b.sh clean > gridlab-d.log 2>&1 && \
      cd ${REPO_DIR} && \
      rm -rf gridlab-d ; \
    fi

# ============================================================
# BUILD: TESP agents (depends on EnergyPlus)
# ============================================================
FROM build-energyplus AS build-tesp-agents
ARG BUILD_TESP=yes

RUN if [ "${BUILD_TESP}" = "yes" ]; then \
      echo "===== Building TESP Agents =====" && \
      cd ${BUILD_DIR} && \
      ./tesp_b.sh clean > "${BUILD_DIR}/tesp.log" 2>&1 ; \
    fi

# ============================================================
# MERGE: Combine all build artifacts
# ============================================================
FROM python-deps AS build-complete
ARG SIM_USER
ARG SIM_GRP
ARG BUILD_GRIDLABD=yes
ARG BUILD_ENERGYPLUS=yes
ARG BUILD_NS3=yes
ARG BUILD_IPOPT=yes
ARG BUILD_FNCS=yes
ARG BUILD_HELICS=yes
ARG BUILD_KLU=yes

# Copy from all parallel branches
# Order matters - later COPY can overwrite earlier ones
COPY --from=build-ipopt --chown=$SIM_USER:$SIM_GRP $SIM_HOME/tenv $SIM_HOME/tenv
COPY --from=build-klu --chown=$SIM_USER:$SIM_GRP $SIM_HOME/tenv $SIM_HOME/tenv
COPY --from=build-gridlabd --chown=$SIM_USER:$SIM_GRP $SIM_HOME/tenv $SIM_HOME/tenv
COPY --from=build-ns3 --chown=$SIM_USER:$SIM_GRP $SIM_HOME/tenv $SIM_HOME/tenv
COPY --from=build-tesp-agents --chown=$SIM_USER:$SIM_GRP $SIM_HOME/tenv $SIM_HOME/tenv

# Copy Python packages from HELICS stage (includes helics[cli])
COPY --from=build-helics --chown=$SIM_USER:$SIM_GRP $SIM_HOME/.local $SIM_HOME/.local

# ============================================================
# Verification
# ============================================================
RUN echo "===== Build Verification =====" && \
    if [ "${BUILD_GRIDLABD}" = "yes" ]; then gridlabd --version || echo "GridLAB-D verification failed"; fi && \
    if [ "${BUILD_HELICS}" = "yes" ]; then helics_broker --version || echo "HELICS verification failed"; fi && \
    if [ "${BUILD_ENERGYPLUS}" = "yes" ]; then energyplus --version || echo "EnergyPlus verification failed"; fi && \
    if [ "${BUILD_NS3}" = "yes" ]; then command -v ns3 || echo "NS-3 verification failed"; fi && \
    if [ "${BUILD_FNCS}" = "yes" ]; then command -v fncs_broker || echo "FNCS verification failed"; fi && \
    if [ "${BUILD_KLU}" = "yes" ]; then ls "${INSTDIR}/lib" | grep -q klusolve || echo "KLU verification failed"; fi && \
    if [ "${BUILD_IPOPT}" = "yes" ]; then command -v ipopt || echo "Ipopt verification failed"; fi && \
    echo "${SIM_USER}" | sudo -S ldconfig

# ============================================================
# Final stage: Clean production image
# ============================================================
FROM cosim-library:tesp_$TAG AS cosim-build
ARG SIM_USER
ARG SIM_GRP
ENV SIM_HOME=/home/$SIM_USER
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
ENV PATH=$PATH:$INSTDIR/energyplus
ENV PATH=$PATH:$INSTDIR/energyplus/PreProcess
ENV PATH=$PATH:$INSTDIR/energyplus/PostProcess
ENV PATH=$PATH:$TESPDIR/scripts/helpers
ENV PSST_SOLVER=cbc
ENV PSST_WARNING=ignore

USER root

# Copy only the installed artifacts from build stage
COPY --from=build-complete --chown=$SIM_USER:$SIM_GRP $SIM_HOME/tenv $SIM_HOME/tenv
COPY --from=build-complete --chown=$SIM_USER:$SIM_GRP $SIM_HOME/tesp $SIM_HOME/tesp
COPY --from=build-complete --chown=$SIM_USER:$SIM_GRP $SIM_HOME/repo $SIM_HOME/repo
COPY --from=build-complete --chown=$SIM_USER:$SIM_GRP $SIM_HOME/.local $SIM_HOME/.local
COPY --from=build-complete --chown=$SIM_USER:$SIM_GRP $SIM_HOME/.gitconfig $SIM_HOME/.gitconfig

USER $SIM_USER
WORKDIR $SIM_HOME

RUN echo "${SIM_USER}" | sudo -S ldconfig

RUN echo "===== Final Verification =====" && \
    python3 --version && \
    pip --version || true