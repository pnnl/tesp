#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runErcotCase8.sh

clear
scenarioFolder="ercot"
scenarioName="case8"
SIM_ROOT="${WORK_DIR}/tesp-platform"
SUPPORT_ROOT="${WORK_DIR}/TESP-support/support"
SCEN_ROOT="${WORK_DIR}/TESP-support/${scenarioFolder}"
OUT_DIR="${SCEN_ROOT}/output"

cd ${SCEN_ROOT}/dist_system && python populate_feeders.py && \
cd ${SCEN_ROOT}/case8 && python prepare_case.py && \
echo "============= Let's start do some calculations !!!!!!! =================="

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
simNum=9
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
# GridLAB-D installation folder
gldDir="${SIM_ROOT}/GridLABD1048Install/bin"
# GridLAB-D models array
gldModels=("${SCEN_ROOT}/${scenarioName}/Bus1.glm" \
           "${SCEN_ROOT}/${scenarioName}/Bus2.glm" \
           "${SCEN_ROOT}/${scenarioName}/Bus3.glm" \
           "${SCEN_ROOT}/${scenarioName}/Bus4.glm" \
           "${SCEN_ROOT}/${scenarioName}/Bus5.glm" \
           "${SCEN_ROOT}/${scenarioName}/Bus6.glm" \
           "${SCEN_ROOT}/${scenarioName}/Bus7.glm" \
           "${SCEN_ROOT}/${scenarioName}/Bus8.glm")
# get the number of GridLAB-D models
gldNum=${#gldModels[@]}
echo "There are $gldNum GridLAB-D instances."
# GridLAB-D metrics file
gldMetricsfile="${scenarioFolder}_${scenarioName}_metrics.json"
# GridLAB-D logging level
gldLOGlevel="INFO"

# ===================================================== setting up the PYPOWER environment ====================================================
# FNCS broker setting for PYPOWER; this could also be set up in the YAML file
fncsBrMP="tcp://localhost:5570"
# set FNCS to print or not at standard output for PYPOWER
ppSTDOUTlog="yes"
# set FNCS to log or not the outputs for FNCS broker
ppFILElog="no"
# PYPOWER configuration file for FNCS
ppFNCSConfig="${SCEN_ROOT}/${scenarioName}/tso8.yaml"
# Total number of substations; could be different than the number running under this scripts
gldTotalNum="1"
# output file
ppOutFile="${OUT_DIR}/pp${gldTotalNum}Subst.out"
# PYPOWER logging level
ppLOGlevel="INFO"
# ppLOGlevel="LMACTIME"

# ========================================================= setting up AGENTS configurations ========================================================================
# TE AGENTS installation folder
#agentSTDOUTlog="yes"
#agentFILElog="no"
#agentLOGlevel="INFO"
#agentCONFfile="${SCEN_ROOT}/${scenarioName}_substation.yaml"
#agentDICTfile="${SCEN_ROOT}/${scenarioName}_agent_dict.json"
#agentOutFile="${OUT_DIR}/substation_${scenarioName}.out"

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
cd ${SCEN_ROOT}/${scenarioName} && \
fncs_broker $simNum > $fncsOutFile 2>&1 &

# ================================================ starting PYPOWER ==================================================================
if test -e $ppOutFile
then
  echo "$ppOutFile exists, so I will remove it."
  rm $ppOutFile
fi

export FNCS_CONFIG_FILE=$ppFNCSConfig && \
export FNCS_LOG_STDOUT=$ppSTDOUTlog && \
export FNCS_LOG_FILE=$ppFILElog && \
export FNCS_LOG_LEVEL=$fncsLOGlevel && \
export PYPOWER_LOG_LEVEL=$ppLOGlevel && \
export FNCS_FATAL=YES && \
cd ${SCEN_ROOT}/${scenarioName} && \
python fncsTSO.py > $ppOutFile 2>&1 &

# ================================================ starting GridLAB-D ===============================================================
for ((i=0; i<$gldNum; i++)); do
   # output file for each GridLAB-D instance
   echo ${gldModels[${i}]}
   gldOutFile="${OUT_DIR}/gld$((${i}+1))_${gldTotalNum}Subst.out"
   if test -e $gldOutFile
   then
     echo "$gldOutFile exists, so I will remove it."
     rm $gldOutFile
   fi
   export FNCS_LOG_STDOUT=$gldSTDOUTlog && \
   export FNCS_LOG_FILE=$gldFILElog && \
   export FNCS_LOG_LEVEL=$gldLOGlevel && \
   export FNCS_FATAL=YES && \
   cd ${SCEN_ROOT}/${scenarioName} && \
   gridlabd -D USE_FNCS -D METRICS_FILE=${gldMetricsfile} ${gldModels[${i}]} > $gldOutFile 2>&1 &
done

# ================================================ starting TE Agents ============================================================
#export FNCS_LOG_STDOUT=${agentSTDOUTlog} && \
#export FNCS_LOG_FILE=${agentFILElog} && \
#export FNCS_LOG_LEVEL=$agentLOGlevel && \
#export FNCS_CONFIG_FILE=${agentCONFfile} && \
#export FNCS_FATAL=YES && \
#cd ${SCEN_ROOT} && \
#python -c "import tesp_support.substation as tesp;tesp.substation_loop('${agentDICTfile}','${scenarioName}',flag='${scenarioType}')" > ${agentOutFile} 2>&1 &

exit 0
