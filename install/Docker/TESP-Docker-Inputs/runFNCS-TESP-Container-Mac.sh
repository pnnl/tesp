#!/bin/bash
# Copyright (c) 2021-2023 Battelle Memorial Institute
# file: runFNCS-TESP-Container-Mac.sh

clear
# 
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":fncs"
TESP_CONT="tespFNCS"
HOST_FOLDER="$PWD"
HOST_SCRIPTS="$PWD/runningScripts"
TESP_USER="tesp-user"
HOST_EXAMPLE="/Users/mari009/PNNL_Projects/GitHubRepositories/TESP_github/examples"
HOST_SUPPORT="/Users/mari009/PNNL_Projects/GitHubRepositories/TESP_github/support"
HOST_ERCOT="/Users/mari009/PNNL_Projects/GitHubRepositories/TESP_github/ercot"
HOST_AGENTS="/Users/mari009/PNNL_Projects/GitHubRepositories/TESP_github/src/tesp_support/tesp_support"
TESP_SUPPORT="/home/${TESP_USER}/TESP-support/support"
TESP_EXAMPLE="/home/${TESP_USER}/TESP-support/examples"
TESP_ERCOT="/home/${TESP_USER}/TESP-support/ercot"
TESP_AGENTS="/home/${TESP_USER}/TESP-support/TESP-agents"
TESP_SCRIPTS="/home/${TESP_USER}/runningScripts"

#
docker images

# 
if (docker inspect -f {{.State.Running}} ${TESP_CONT} &> /dev/null); then
  echo "===== Container ${TESP_CONT} is already running, so I will close and remove it first. ====="
  docker stop ${TESP_CONT}
  docker rm ${TESP_CONT}
fi

echo "===== Create container ${TESP_CONT}."

docker run --name ${TESP_CONT} \
                      -dit --rm \
                      -e DISPLAY=$IP:0 \
                      --mount type=bind,source=${HOST_EXAMPLE},destination=${TESP_EXAMPLE} \
                      --mount type=bind,source=${HOST_ERCOT},destination=${TESP_ERCOT} \
                      --mount type=bind,source=${HOST_SUPPORT},destination=${TESP_SUPPORT} \
                      --mount type=bind,source=${HOST_SCRIPTS},destination=${TESP_SCRIPTS} \
                      --mount type=bind,source=${HOST_AGENTS},destination=${TESP_AGENTS} \
                      --mount type=bind,source=/tmp/.X11-unix,destination=/tmp/.X11-unix \
                      --net=host --ipc=host --user=${TESP_USER} \
                      ${TESP_REP}${TESP_TAG}
export CONTAINER_ID=$(docker ps -l -q)
xhost +local:`docker inspect --format='{{ .Config.Hostname}}' ${CONTAINER_ID}`

echo "===== List of containers on the machine."
docker ps -a
docker container start ${TESP_CONT}
echo "===== Container ${TESP_CONT} has been started."

# =================== FNCS settings =========================================================
echo "===== Setting up FNCS paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${FNCS_INSTALL}/bin/outputFiles; then rmdir ${FNCS_INSTALL}/bin/outputFiles; mkdir ${FNCS_INSTALL}/bin/outputFiles; else mkdir ${FNCS_INSTALL}/bin/outputFiles; fi'

# ================== GridLAB-D settings ============================================================
echo "===== Setting up GridLAB-D paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${GLD_INSTALL}/bin/outputFiles; then rmdir ${GLD_INSTALL}/bin/outputFiles; mkdir ${GLD_INSTALL}/bin/outputFiles; else mkdir ${GLD_INSTALL}/bin/outputFiles; fi'

# =================== Energy Plus settings =========================================================
echo "===== Setting up Energy Plus paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUS_INSTALL}/outputFiles; then rmdir ${EPLUS_INSTALL}/outputFiles; mkdir ${EPLUS_INSTALL}/outputFiles; else mkdir ${EPLUS_INSTALL}/outputFiles; fi'

# =================== Energy Plus JSON settings =========================================================
echo "===== Setting up Energy Plus JSON paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUSJSON_INSTALL}/outputFiles; then rmdir ${EPLUSJSON_INSTALL}/outputFiles; mkdir ${EPLUSJSON_INSTALL}/outputFiles; else mkdir ${EPLUSJSON_INSTALL}/outputFiles; fi'

echo "=========================================================================================="

# =================== Prepare the TE30 Challenge ===================================================================
# echo "===== Preparing the TE30 scenario."
#docker container exec ${TESP_CONT} /bin/bash -c 'cd /${WORK_DIR}/TESP-support/examples/te30 && \
#  python prepare_case.py'

docker container exec -it ${TESP_CONT} /bin/bash -c 'stty cols 200 rows 60 && bash && echo "Updating tesp-support Python package." && pip install --upgrade tesp-support'