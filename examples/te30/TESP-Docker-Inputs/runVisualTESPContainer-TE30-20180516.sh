#!/bin/bash
clear
# 
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":V2"
TESP_CONT="tespV2"
HOST_FOLDER="$PWD"

#
docker images

# 
if (docker inspect -f {{.State.Running}} ${TESP_CONT} &> /dev/null); then
  echo "Container ${TESP_CONT} is already running."
else
  echo "===== Create container ${TESP_CONT}."
  docker container run --name ${TESP_CONT} \
                        -dit --env="DISPLAY" \
                        --env="QT_X11_NO_MITSHM=1" \
                        --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
                        --volume="${HOST_FOLDER}:/tmp/scenarioData:rw" \
                        ${TESP_REP}${TESP_TAG}
  export CONTAINER_ID=$(docker ps -l -q)
  xhost +local:`docker inspect --format='{{ .Config.Hostname}}' ${CONTAINER_ID}`
fi

echo "===== List of containers on the machine."
docker ps -a
docker container start ${TESP_CONT}
echo "===== Container ${TESP_CONT} has been started."

# =================== TE30 Challenge Running scripts ====================================================
echo "===== Setting up running scripts folder."
docker container exec ${TESP_CONT} /bin/bash -c 'RUN_SCR_DIR=RunningScripts && cd ${TESP} && mkdir ${RUN_SCR_DIR} && \
  cp /tmp/scenarioData/RunningScripts-20180516/tespTE30.py ${TESP}/${RUN_SCR_DIR} && \
  cp /tmp/scenarioData/RunningScripts-20180516/tespTE30_20180521.yaml ${TESP}/${RUN_SCR_DIR} && \
  cp /tmp/scenarioData/RunningScripts-20180516/fncs.py.DockerVersion ${TESP}/${RUN_SCR_DIR}/fncs.py && \
  cp /tmp/scenarioData/RunningScripts-20180516/runTE30_ChallengePYPOWER_20180516.sh ${TESP}/${RUN_SCR_DIR} && \
  cp /tmp/scenarioData/RunningScripts-20180516/runGUITE30Challenge.sh ${TESP}/${RUN_SCR_DIR} && \
  chmod u+x ${TESP}/${RUN_SCR_DIR}/runTE30_ChallengePYPOWER_20180516.sh && \
  chmod u+x ${TESP}/${RUN_SCR_DIR}/runGUITE30Challenge.sh'

# =================== FNCS settings =========================================================
echo "===== Setting up FNCS paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${FNCS_INSTALL}/bin/playerFiles; then rmdir ${FNCS_INSTALL}/bin/playerFiles; mkdir ${FNCS_INSTALL}/bin/playerFiles; else mkdir ${FNCS_INSTALL}/bin/playerFiles; fi && \
  if test -e ${FNCS_INSTALL}/bin/outputFiles; then rmdir ${FNCS_INSTALL}/bin/outputFiles; mkdir ${FNCS_INSTALL}/bin/outputFiles; else mkdir ${FNCS_INSTALL}/bin/outputFiles; fi'

# ================== GridLAB-D settings ============================================================
echo "===== Setting up GridLAB-D paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${GLD_INSTALL}/bin/modelFiles; then rmdir ${GLD_INSTALL}/bin/modelFiles; mkdir ${GLD_INSTALL}/bin/modelFiles; else mkdir ${GLD_INSTALL}/bin/modelFiles; fi && \
  if test -e ${GLD_INSTALL}/bin/inputFilesTE30; then rmdir ${GLD_INSTALL}/bin/inputFilesTE30; mkdir ${GLD_INSTALL}/bin/inputFilesTE30; else mkdir ${GLD_INSTALL}/bin/inputFilesTE30; fi && \
  if test -e ${GLD_INSTALL}/bin/outputFiles; then rmdir ${GLD_INSTALL}/bin/outputFiles; mkdir ${GLD_INSTALL}/bin/outputFiles; else mkdir ${GLD_INSTALL}/bin/outputFiles; fi && \
  cp /tmp/scenarioData/GridLABD/modelFiles-20180516/* ${GLD_INSTALL}/bin/modelFiles && \
  cp -R /tmp/scenarioData/GridLABD/inputFilesTE30/ ${GLD_INSTALL}/bin/'

# =================== Energy Plus settings =========================================================
echo "===== Settting up Energy Plus paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUS_INSTALL}/outputFiles; then rmdir ${EPLUS_INSTALL}/outputFiles; mkdir ${EPLUS_INSTALL}/outputFiles; else mkdir ${EPLUS_INSTALL}/outputFiles; fi && \
  cp /tmp/scenarioData/EnergyPlus/eplus.yaml ${EPLUS_INSTALL} && \
  cp /tmp/scenarioData/EnergyPlus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw ${EPLUS_INSTALL} && \
  cp /tmp/scenarioData/EnergyPlus/SchoolDualController.idf ${EPLUS_INSTALL}'

# =================== Energy Plus JSON settings =========================================================
echo "===== Setting up Energy Plus JSON paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUSJSON_INSTALL}/outputFiles; then rmdir ${EPLUSJSON_INSTALL}/outputFiles; mkdir ${EPLUSJSON_INSTALL}/outputFiles; else mkdir ${EPLUSJSON_INSTALL}/outputFiles; fi && \
  cp /tmp/scenarioData/EnergyPlusJSON-20180516/eplus_json.yaml ${EPLUSJSON_INSTALL}'

# =================== PyPower settings =========================================================
echo "===== Settting up PyPower paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${PYPOWER_INSTALL}/outputFiles; then rmdir ${PYPOWER_INSTALL}/outputFiles; mkdir ${PYPOWER_INSTALL}/outputFiles; else mkdir ${PYPOWER_INSTALL}/outputFiles; fi && \
  cp /tmp/scenarioData/PyPower-20180516/NonGLDLoad.txt ${PYPOWER_INSTALL} && \
  cp /tmp/scenarioData/PyPower-20180516/ppcasefile.py ${PYPOWER_INSTALL} && \
  cp /tmp/scenarioData/PyPower-20180516/pypowerConfig_TE30dispload.yaml ${PYPOWER_INSTALL} && \
  cp /tmp/scenarioData/PyPower-20180516/TE30_ChallengePYPOWER_m_dict.json ${PYPOWER_INSTALL}'

# =================== Agents settings =========================================================
echo "===== Settting up Agents paths and folders."
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${AGENTS_INSTALL}/inputFiles; then rmdir ${AGENTS_INSTALL}/inputFiles; mkdir ${AGENTS_INSTALL}/inputFiles; else mkdir ${AGENTS_INSTALL}/inputFiles; fi && \
  if test -e ${AGENTS_INSTALL}/outputFiles; then rmdir ${AGENTS_INSTALL}/outputFiles; mkdir ${AGENTS_INSTALL}/outputFiles; else mkdir ${AGENTS_INSTALL}/outputFiles; fi && \
  cp -R /tmp/scenarioData/Agents-20180516/inputFiles ${AGENTS_INSTALL}'


# =================== Run TE30 =========================================================
# echo "===== Run script to simulate."
# docker container exec -i ${TESP_CONT} /bin/bash -c 'export TERM=xterm && echo "===== TERM = ${TERM}" && export FNCS_LOG_STDOUT=no && echo "===== FNCS_LOG_STDOUT = ${FNCS_LOG_STDOUT}" && cd ${TESP}/${RUN_SCR_DIR} && python tespTE30.py&'
# docker container exec ${TESP_CONT} /bin/sh -c "export TERM=xterm && cd /tesp/ && ./runTE30ChallengeDocker.sh > te30DockerRun.log &"
# docker container exec ${TESP_CONT} /bin/sh -c "tail -f ${GLD_INSTALL}/bin/outputFiles/gld1_1Subst.out"

# echo "===== Done with running use case. Copying the post processing scripts to the container."
# docker cp ${HOME}/work/CoSimulation/TESP-pypower/outputFiles/process_pypower.py ${TESP_CONT}:${PYPOWER_INSTALL}outputFiles/
# docker cp ${HOME}/work/CoSimulation/TESP-GridLABD1048install/bin/outputFiles/process_gld.py ${TESP_CONT}:${GLD_INSTALL}/bin/outputFiles/
# docker cp ${HOME}/work/CoSimulation/ENERGYPLUS_JSONinstall/outputFiles/process_eplus.py ${TESP_CONT}:${EPLUSJSON_INSTALL}outputFiles/
# docker cp ${HOME}/work/CoSimulation/Agents/outputFiles/TE30_Challenge_PYPOWER_agent_dict.json ${TESP_CONT}:/tesp/AgentsInstall
# docker cp ${HOME}/work/CoSimulation/Agents/outputFiles/process_agents.py ${TESP_CONT}:/tesp/AgentsInstall/
# echo "===== Transferred post-processing files. Let's run."

# USE_CASE="TE30_Challenge_PYPOWER" 

echo "=========================================================================================="

# echo "===== STOP ALL CONTAINERS."
# docker stop $(docker ps -a -q)
# echo "===== REMOVE ALL CONTAINERS."
# docker rm $(docker ps -a -q)
# echo "===== List of containers."
# docker ps -a
#echo "===== Running bash in the container."
docker container exec -it ${TESP_CONT} /bin/bash -c 'stty cols 200 rows 60 && bash'
