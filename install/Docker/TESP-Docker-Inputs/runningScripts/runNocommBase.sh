#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runNocommBase.sh

clear
scenarioFolder="comm/Nocomm_Base"
scenarioName="Nocomm_Base"
scenarioType="WithMarket" # it is by default; do not add to the metrics (JSON) and output (OUT) file names
SIM_ROOT="${WORK_DIR}/tesp-platform"
SUPPORT_ROOT="${WORK_DIR}/TESP-support/support"
SCEN_ROOT="${WORK_DIR}/TESP-support/examples/${scenarioFolder}"
OUT_DIR="${SCEN_ROOT}/output"

cd ${WORK_DIR}/TESP-support/support/weather/TMY2EPW/source_code/ && \
echo "Compiling the TMY3 to TMY2 converter ..... " && \
gcc TMY3toTMY2_ansi.c -o Tmy3toTMY2_ansi
if test ! -d ${SIM_ROOT}/tesp-support
then
  echo "=== The folder for the extra support executables, such as TMY3-to-TMY2 converters, does not exist. ==="
  mkdir ${SIM_ROOT}/tesp-support
else
  echo "=== The folder for the extra support executables, such as TMY3-to-TMY2 converters, already exists. ==="
fi
echo "Moving converter to TESP platform support fodler .... " && \
mv Tmy3toTMY2_ansi ${SIM_ROOT}/tesp-support/ && \
echo "Adding the TESPplatform support folder to the path .... " && \
export PATH=${SIM_ROOT}/tesp-support:$PATH && \
echo "Making the Nocomm_base scenario ... " && \
cd ${WORK_DIR}/TESP-support/examples/comm && python make_comm_base.py && \
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
# GridLAB-D installation folder
gldDir="${SIM_ROOT}/GridLABD1048Install/bin"
# GridLAB-D models array
gldModels=("${SCEN_ROOT}/${scenarioName}.glm")
# get the number of GridLAB-D models
gldNum=${#gldModels[@]}
echo "There are $gldNum GridLAB-D instances."
# GridLAB-D metrics file
gldMetricsfile="${scenarioName}_metrics.json"
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
ppFNCSConfig="${SCEN_ROOT}/pypower.yaml"
# Total number of substations; could be different than the number running under this scripts
gldTotalNum="1"
# output file
ppOutFile="${OUT_DIR}/pp${gldTotalNum}Subst.out"
# PYPOWER logging level
ppLOGlevel="INFO"
# ppLOGlevel="LMACTIME"

# ========================================================= setting up AGENTS configurations ========================================================================
# TE AGENTS installation folder
agentSTDOUTlog="yes"
agentFILElog="no"
agentLOGlevel="INFO"
agentCONFfile="${SCEN_ROOT}/${scenarioName}_substation.yaml"
agentDICTfile="${SCEN_ROOT}/${scenarioName}_agent_dict.json"
agentOutFile="${OUT_DIR}/substation_${scenarioName}.out"

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
cd ${SCEN_ROOT} && \
python -c "import tesp_support.api as tesp;tesp.pypower_loop('${scenarioName}_pp.json','${scenarioName}')" > $ppOutFile 2>&1 &

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
   cd ${SCEN_ROOT} && \
   gridlabd -D USE_FNCS -D METRICS_FILE=${gldMetricsfile} ${gldModels[${i}]} > $gldOutFile 2>&1 &
done

# ================================================ starting TE Agents ============================================================
export FNCS_LOG_STDOUT=${agentSTDOUTlog} && \
export FNCS_LOG_FILE=${agentFILElog} && \
export FNCS_LOG_LEVEL=$agentLOGlevel && \
export FNCS_CONFIG_FILE=${agentCONFfile} && \
export FNCS_FATAL=YES && \
cd ${SCEN_ROOT} && \
python -c "import tesp_support.api as tesp;tesp.substation_loop('${agentDICTfile}','${scenarioName}',flag='${scenarioType}')" > ${agentOutFile} 2>&1 &

exit 0
