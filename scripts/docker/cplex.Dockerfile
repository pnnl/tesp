ARG DOCKER_VER
ARG TAG=$DOCKER_VER

# Build runtime image
FROM cosim-build:tesp_$TAG AS cosim-cplex

ARG SIM_USER
ARG SIM_GRP
ARG CPLEX_BIN=cplex_studio129.linux-x86-64.bin

ENV PSST_SOLVER=$INSTDIR/ibm/cplex/bin/x86-64_linux/cplexamp

COPY "./$CPLEX_BIN" /home/$SIM_USER/repo/

RUN echo "===== Building TESP Cplex =====" && \
    cd $REPO_DIR && \
    echo $SIM_USER | sudo -S chown -hR $SIM_USER:$SIM_GRP "$CPLEX_BIN" && \
    chmod a+x "$CPLEX_BIN" && \
    "./$CPLEX_BIN" -i silent -DLICENSE_ACCEPTED=TRUE -DUSER_INSTALL_DIR=$INSTDIR/ibm && \
    rm "$REPO_DIR/$CPLEX_BIN"
