#!/bin/bash

# Copyright (c) 2021-2023 Battelle Memorial Institute
# file: runInvTi30.sh

clear
scenarioFolder="ieee8500/PNNLteam"
scenarioName="invti30"
SIM_ROOT="${WORK_DIR}/tesp-platform"
SUPPORT_ROOT="${WORK_DIR}/TESP-support/support"
SCEN_ROOT="${WORK_DIR}/TESP-support/examples/${scenarioFolder}"
OUT_DIR="${SCEN_ROOT}/output"
if test ! -d ${OUT_DIR}
then
  echo "==== Simulation output folder does not exist yet. ===="
  mkdir ${OUT_DIR}
else
  echo "==== Simulation output folder already exists. ===="
fi
# ==================================================== setting up the FNCS environment ================================================
# FNCS broker
fncsBroker="tcp://*:5570"
# FNCS installation folder
FNCS_DIR="${SIM_ROOT}/FNCSInstall/bin"
FNCS_ROOT="${SIM_ROOT}/FNCSInstall"
echo "---------------------------------------------"
if test -z $LD_LIBRARY_PATH
then
  LD_LIBRARY_PATH=.:$FNCS_ROOT/lib
else
  LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$FNCS_ROOT/lib
fi    
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$FNCS_ROOT/bin
export LD_LIBRARY_PATH
echo $LD_LIBRARY_PATH
echo "======================================================"
# set FNCS to print or not at the standard output
fncsSTDOUTlog="yes"
# set FNCS to log or not the outputs for FNCS broker
fncsFILElog="no"
fncsLogFile="$FNCS_DIR/fncs_broker.log" # I believe this is a default name
# number of simulators
simNum=3
# FNCS output file (if wanted)
fncsOutFile="${OUT_DIR}/fncs${simNum}Sims.out"
# FNCS logging level
fncsLOGlevel="DEBUG1"

# =================================================== setting up the GridLAB-D environment ==================================================
# FNCS broker for GridLAB-D
# this need to be set in GLM file also, or is it enough in only one place?
fncsBrGLD="tcp://localhost:5570"
# set FNCS to print or not at standard output for GridLAB-D
gldSTDOUTlog="yes"
# set FNCS to log or not the outputs for FNCS broker
gldFILElog="no"
# GridLAB-D models array
gldModels=("${SCEN_ROOT}/${scenarioName}.glm")
# get the number of GridLAB-D models
gldNum=${#gldModels[@]}
echo "There are $gldNum GridLAB-D instances."
# GridLAB-D metrics file
gldMetricsfile="${scenarioName}_metrics.json"
# GridLAB-D logging level
gldLOGlevel="INFO"

# ===================================================== setting up the PLAYER environment ====================================================
# set FNCS to print or not at standard output for player
playerSTDOUTlog="yes"
# set FNCS to log or not the outputs for FNCS broker
playerFILElog="no"
# player configuration file for FNCS
playerFNCSConfig="${SCEN_ROOT}/prices.player"
# output file
playerOutFile="${OUT_DIR}/player.out"
# player logging level
playerLOGlevel="INFO"
# player pre_colling time
playerTime="48h"

# ========================================================= setting up AGENTS configurations ========================================================================
# TE AGENTS installation folder
agentTime="48"
agentSTDOUTlog="yes"
agentFILElog="no"
agentLOGlevel="INFO"
agentCONFfile="${SCEN_ROOT}/${scenarioName}_precool.yaml"
agentDICTfile="${SCEN_ROOT}/${scenarioName}_agent_dict.json"
agentOutFile="${OUT_DIR}/agent_${scenarioName}.out"

cd ${SCEN_ROOT} && pwd && python prepare_cases.py &

# ================================================ starting FNCS broker ===========================================================
if test -e $fncsLogFile
then
  echo "$fncsLogFile exists, so I will remove it."
  rm $fncsLogFile
fi

if test -e $fncsOutFile
then
  echo "$fncsOutFile exists, so I will remove it."
  rm $fncsOutFile
fi

export FNCS_LOG_LEVEL=$fncsLOGlevel && \
export FNCS_BROKER=$fncsBroker && \
export FNCS_LOG_STDOUT=$fncsSTDOUTlog && \
export FNCS_LOG_FILE=$fncsFILElog && \
cd ${SCEN_ROOT} && \
fncs_broker $simNum &> $fncsOutFile &

# ================================================ starting player ==================================================================
if test -e $playerOutFile
then
  echo "$playerOutFile exists, so I will remove it."
  rm $playerOutFile
fi

export FNCS_CONFIG_FILE=$playerFNCSConfig && \
export FNCS_LOG_STDOUT=$playerSTDOUTlog && \
export FNCS_LOG_FILE=$playerFILElog && \
export FNCS_LOG_LEVEL=$fncsLOGlevel && \
export PLAYER_LOG_LEVEL=$playerLOGlevel && \
export FNCS_FATAL=YES && \
cd ${SCEN_ROOT} && \
fncs_player ${playerTime} ${playerFNCSConfig} &> $playerOutFile &

# ================================================ starting GridLAB-D ===============================================================
for ((i=0; i<$gldNum; i++)); do
   # output file for each GridLAB-D instance
   echo ${gldModels[${i}]}
   gldOutFile="${OUT_DIR}/gld$((${i}+1))_${gldTotalNum}Subst_${scenarioName}.out"
   if test -e $gldOutFile
   then
     echo "$gldOutFile exists, so I will remove it."
     rm $gldOutFile
   fi
   export FNCS_LOG_STDOUT=$gldSTDOUTlog && \
   export FNCS_LOG_FILE=$gldFILElog && \
   export FNCS_LOG_LEVEL=$gldLOGlevel && \
   export FNCS_FATAL=YES && \
   cd ${SCEN_ROOT} && \
   gridlabd -D USE_FNCS -D METRICS_FILE=${gldMetricsfile} --lock ${gldModels[${i}]} &> $gldOutFile &
done

# ================================================ starting TE Agents ============================================================
if test -e ${agentOutFile}
then
  echo "${agentOutFile} exists, so I will remove it."
  rm ${agentOutFile}
fi
export FNCS_LOG_STDOUT=${agentSTDOUTlog} && \
export FNCS_LOG_FILE=${agentFILElog} && \
export FNCS_LOG_LEVEL=$agentLOGlevel && \
export FNCS_CONFIG_FILE=${agentCONFfile} && \
export FNCS_FATAL=YES && \
cd ${SCEN_ROOT} && \
python -c "import tesp_support.original.precool as tesp;tesp.precool_loop(${agentTime},'${scenarioName}')" &> ${agentOutFile} &

exit 0