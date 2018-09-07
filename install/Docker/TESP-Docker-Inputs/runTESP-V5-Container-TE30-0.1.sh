#!/bin/bash
clear
# 
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":V5"
TESP_CONT="tespV5"
HOST_FOLDER="$PWD"

#
docker images

# 
if (docker inspect -f {{.State.Running}} ${TESP_CONT} &> /dev/null); then
  echo "===== Container ${TESP_CONT} is already running, so I will close and remove it first. ====="
  docker stop ${TESP_CONT}
  docker rm ${TESP_CONT}
fi

echo "===== Create container ${TESP_CONT}."
docker container run --name ${TESP_CONT} \
                      -dit --env="DISPLAY" \
                      --env="QT_X11_NO_MITSHM=1" \
                      --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
                      --volume="${HOST_FOLDER}:/tmp/scenarioData:rw" \
                      ${TESP_REP}${TESP_TAG}
export CONTAINER_ID=$(docker ps -l -q)
xhost +local:`docker inspect --format='{{ .Config.Hostname}}' ${CONTAINER_ID}`

echo "===== List of containers on the machine."
docker ps -a
docker container start ${TESP_CONT}
echo "===== Container ${TESP_CONT} has been started."

# =================== TE30 Challenge Support and example files ====================================================
echo "===== Setting up support and example folders, and the running scripts."
docker container exec ${TESP_CONT} /bin/bash -c 'whoami && \
  PATH=$PATH:/tesp/FNCSInstall/bin:/tesp/EnergyPlusInstall:/tesp/EPlusJSONInstall/bin && \
  export PATH && \
  echo $PATH && \
  cd ${TESP} && mkdir TESP-support && \
  cp -r /tmp/scenarioData/TESP-support/support ${TESP}/TESP-support && \
  cd ${TESP}/TESP-support && mkdir examples && \
  cp -r /tmp/scenarioData/TESP-support/examples/te30 ${TESP}/TESP-support/examples && \
  cp -r /tmp/scenarioData/TESP-support/examples/players ${TESP}/TESP-support/examples && \
  cp /tmp/scenarioData/Running-TE30-Scripts/runGUI-TE30-0.2.sh ${TESP}/TESP-support && \
  cp /tmp/scenarioData/Running-TE30-Scripts/runTE30-0.2.sh ${TESP}/TESP-support && \
  chmod u+x ${TESP}/TESP-support/runGUI-TE30-0.2.sh && \
  chmod u+x ${TESP}/TESP-support/runTE30-0.2.sh && \
  echo $PATH'

# =================== FNCS settings =========================================================
echo "===== Setting up FNCS paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${FNCS_INSTALL}/bin/outputFiles; then rmdir ${FNCS_INSTALL}/bin/outputFiles; mkdir ${FNCS_INSTALL}/bin/outputFiles; else mkdir ${FNCS_INSTALL}/bin/outputFiles; fi'

# ================== GridLAB-D settings ============================================================
echo "===== Setting up GridLAB-D paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${GLD_INSTALL}/bin/outputFiles; then rmdir ${GLD_INSTALL}/bin/outputFiles; mkdir ${GLD_INSTALL}/bin/outputFiles; else mkdir ${GLD_INSTALL}/bin/outputFiles; fi'

# =================== Energy Plus settings =========================================================
echo "===== Settting up Energy Plus paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUS_INSTALL}/outputFiles; then rmdir ${EPLUS_INSTALL}/outputFiles; mkdir ${EPLUS_INSTALL}/outputFiles; else mkdir ${EPLUS_INSTALL}/outputFiles; fi'

# =================== Energy Plus JSON settings =========================================================
echo "===== Setting up Energy Plus JSON paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUSJSON_INSTALL}/outputFiles; then rmdir ${EPLUSJSON_INSTALL}/outputFiles; mkdir ${EPLUSJSON_INSTALL}/outputFiles; else mkdir ${EPLUSJSON_INSTALL}/outputFiles; fi'

echo "=========================================================================================="

# =================== Prepare the TE30 Challenge ===================================================================
echo "===== Preparing the TE30 scenario."
docker container exec ${TESP_CONT} /bin/bash -c 'cd ${TESP}/TESP-support/examples/te30 && \
  python3 prepare_case.py'

docker container exec -it ${TESP_CONT} /bin/bash -c 'stty cols 200 rows 60 && bash'