#!/bin/bash
clear
# 
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":latest"
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
                        ${TESP_REP}${TESP_TAG}
  export CONTAINER_ID=$(docker ps -l -q)
  xhost +local:`docker inspect --format='{{ .Config.Hostname}}' ${CONTAINER_ID}`
fi

echo "===== List of containers on the machine."
docker ps -a
docker container start ${TESP_CONT}
echo "===== Container ${TESP_CONT} has been started."

# =================== TE30 Challenge Running scripts ====================================================
echo "===== Create running scripts folder."
docker container exec ${TESP_CONT} /bin/sh -c 'cd ${TESP} && mkdir runScripts'
echo "===== Copy running scripts."
docker cp ${HOST_FOLDER}/RunningScripts/tespTE30.py ${TESP_CONT}:/tesp/runScripts
docker cp ${HOST_FOLDER}/RunningScripts/tespTE30.yaml ${TESP_CONT}:/tesp/runScripts
docker cp ${HOST_FOLDER}/RunningScripts/fncs.py.DockerVersion ${TESP_CONT}:/tesp/runScripts/fncs.py
docker cp ${HOST_FOLDER}/RunningScripts/runVisualTE30ChallengeDocker.sh ${TESP_CONT}:/tesp/runScripts
docker container exec ${TESP_CONT} /bin/sh -c 'chmod u+x ${TESP}/runScripts/runVisualTE30ChallengeDocker.sh'

# =================== FNCS settings =========================================================
echo "===== Set-up FNCS paths and folders."
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${FNCS_INSTALL}/bin/playerFiles; then rmdir ${FNCS_INSTALL}/bin/playerFiles; mkdir ${FNCS_INSTALL}/bin/playerFiles; else mkdir ${FNCS_INSTALL}/bin/playerFiles; fi'
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${FNCS_INSTALL}/bin/outputFiles; then rmdir ${FNCS_INSTALL}/bin/outputFiles; mkdir ${FNCS_INSTALL}/bin/outputFiles; else mkdir ${FNCS_INSTALL}/bin/outputFiles; fi'
# docker cp ${HOME}/work/CoSimulation/FNCSinstall/bin/playerFiles/ ${TESP_CONT}:/tesp/FNCSInstall/bin/
# docker cp ${HOME}/work/CoSimulation/FNCSinstall/bin/outputFiles/ ${TESP_CONT}:/tesp/FNCSInstall/bin/

# ================== GridLAB-D settings ============================================================
echo "===== Set-up GridLAB-D paths and folders."
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${GLD_INSTALL}/bin/modelFiles; then rmdir ${GLD_INSTALL}/bin/modelFiles; mkdir ${GLD_INSTALL}/bin/modelFiles; else mkdir ${GLD_INSTALL}/bin/modelFiles; fi'
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${GLD_INSTALL}/bin/inputFilesTE30; then rmdir ${GLD_INSTALL}/bin/inputFilesTE30; mkdir ${GLD_INSTALL}/bin/inputFilesTE30; else mkdir ${GLD_INSTALL}/bin/inputFilesTE30; fi'
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${GLD_INSTALL}/bin/outputFiles; then rmdir ${GLD_INSTALL}/bin/outputFiles; mkdir ${GLD_INSTALL}/bin/outputFiles; else mkdir ${GLD_INSTALL}/bin/outputFiles; fi'
docker cp ${HOST_FOLDER}/GridLABD/modelFiles/ ${TESP_CONT}:/tesp/GridLABD1048Install/bin/
docker cp ${HOST_FOLDER}/GridLABD/inputFilesTE30/ ${TESP_CONT}:/tesp/GridLABD1048Install/bin/
# docker cp ${HOST_FOLDER}/GridLABD//outputFiles/ ${TESP_CONT}:/tesp/GridLABD1048Install/bin/

# =================== Energy Plus settings =========================================================
echo "===== Set-up Energy Plus paths and folders."
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${EPLUS_INSTALL}/outputFiles; then rmdir ${EPLUS_INSTALL}/outputFiles; mkdir ${EPLUS_INSTALL}/outputFiles; else mkdir ${EPLUS_INSTALL}/outputFiles; fi'
docker cp ${HOST_FOLDER}/EnergyPlus/eplus.yaml ${TESP_CONT}:/tesp/EnergyPlusInstall/
docker cp ${HOST_FOLDER}/EnergyPlus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw ${TESP_CONT}:/tesp/EnergyPlusInstall/
docker cp ${HOST_FOLDER}/EnergyPlus/SchoolDualController.idf ${TESP_CONT}:/tesp/EnergyPlusInstall/

# =================== Energy Plus JSON settings =========================================================
echo "===== Set-up Energy Plus JSON paths and folders."
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${EPLUSJSON_INSTALL}/outputFiles; then rmdir ${EPLUSJSON_INSTALL}/outputFiles; mkdir ${EPLUSJSON_INSTALL}/outputFiles; else mkdir ${EPLUSJSON_INSTALL}/outputFiles; fi'
docker cp ${HOST_FOLDER}/EnergyPlusJSON/eplus_json.yaml ${TESP_CONT}:/tesp/EPlusJSONInstall/

# =================== PyPower settings =========================================================
echo "===== Set-up PyPower paths and folders."
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${PYPOWER_INSTALL}/outputFiles; then rmdir ${PYPOWER_INSTALL}/outputFiles; mkdir ${PYPOWER_INSTALL}/outputFiles; else mkdir ${PYPOWER_INSTALL}/outputFiles; fi'
docker cp ${HOST_FOLDER}/PyPower/NonGLDLoad.txt ${TESP_CONT}:/tesp/PyPowerInstall/
docker cp ${HOST_FOLDER}/PyPower/ppcasefile.py ${TESP_CONT}:/tesp/PyPowerInstall/
docker cp ${HOST_FOLDER}/PyPower/pypowerConfig_TE30dispload.yaml ${TESP_CONT}:/tesp/PyPowerInstall/

# =================== Agents settings =========================================================
echo "===== Set-up Agents paths and folders."
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${AGENTS_INSTALL}/inputFiles; then rmdir ${AGENTS_INSTALL}/inputFiles; mkdir ${AGENTS_INSTALL}/inputFiles; else mkdir ${AGENTS_INSTALL}/inputFiles; fi'
docker cp ${HOST_FOLDER}/Agents/inputFilesPP ${TESP_CONT}:/tesp/AgentsInstall/inputFilesPP
docker cp ${HOST_FOLDER}/Agents/launch_TE30_Challenge_PYPOWER_agents.sh.DockerVersion ${TESP_CONT}:/tesp/AgentsInstall/launch_TE30_Challenge_PYPOWER_agents.sh
docker container exec ${TESP_CONT} /bin/sh -c 'chmod u+x ${AGENTS_INSTALL}/launch_TE30_Challenge_PYPOWER_agents.sh'

# =================== Run TE30 =========================================================
echo "===== Run script to simulate."
docker container exec ${TESP_CONT} /bin/sh -c 'export TERM=xterm && echo "===== TERM = ${TERM}" && export FNCS_LOG_STDOUT=no && echo "===== FNCS_LOG_STDOUT = ${FNCS_LOG_STDOUT}" && cd /tesp/runScripts && python tespTE30.py&'
# docker container exec ${TESP_CONT} /bin/sh -c "export TERM=xterm && cd /tesp/ && ./runTE30ChallengeDocker.sh > te30DockerRun.log &"
# docker container exec ${TESP_CONT} /bin/sh -c "tail -f /tesp/GridLABD1048Install/bin/outputFiles/gld1_1Subst.out"

# echo "===== Done with running use case. Copying the post processing scripts to the container."
# docker cp ${HOME}/work/CoSimulation/TESP-pypower/outputFiles/process_pypower.py ${TESP_CONT}:/tesp/PyPowerInstall/outputFiles/
# docker cp ${HOME}/work/CoSimulation/TESP-GridLABD1048install/bin/outputFiles/process_gld.py ${TESP_CONT}:/tesp/GridLABD1048Install/bin/outputFiles/
# docker cp ${HOME}/work/CoSimulation/ENERGYPLUS_JSONinstall/outputFiles/process_eplus.py ${TESP_CONT}:/tesp/EPlusJSONInstall/outputFiles/
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
echo "===== Running bash in the container."
docker container exec -it ${TESP_CONT} /bin/bash
