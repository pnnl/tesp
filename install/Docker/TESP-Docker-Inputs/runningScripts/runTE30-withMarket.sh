#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runTE30-withMarket.sh

clear
scenarioFolder="te30"
scenarioName="TE_Challenge"
scenarioType="WithMarket"
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
simNum=5
# FNCS output file (if wanted)
fncsOutFile="${OUT_DIR}/fncs${simNum}Sims.out"
# FNCS logging level
fncsLOGlevel="INFO"

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
gldModels=("${SCEN_ROOT}/TE_Challenge.glm")
# get the number of GridLAB-D models
gldNum=${#gldModels[@]}
echo "There are $gldNum GridLAB-D instances."
# GridLAB-D metrics file
gldMetricsfile="${scenarioName}_${scenarioType}_metrics.json"
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
ppFNCSConfig="${SCEN_ROOT}/pypower30.yaml"
# Total number of substations; could be different than the number running under this scripts
gldTotalNum="1"
# output file
ppOutFile="${OUT_DIR}/pp${gldTotalNum}Subst_${scenarioType}.out"
# PYPOWER logging level
ppLOGlevel="INFO"
# ppLOGlevel="LMACTIME"

# ====================================================== setting up the Energy Plus environment ==============================================================
# FNCS broker setting for Energy Plus; this could also be set up in the ZPL file
fncsBrEP="tcp://localhost:5570"
# set FNCS to print or not at standard output for Energy Plus
epSTDOUTlog="yes"
# set FNCS to log or not the outputs for Energy Plus
epFILElog="no"
epLOGlevel="INFO"
# set the configuration file for Energy Plus
epCONFfile="${SCEN_ROOT}/eplus.yaml"
# set Energy Plus weather file
epWEATHERfile="${SUPPORT_ROOT}/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw"
# Energy Plus reference file
epREFfile="${SUPPORT_ROOT}/energyplus/SchoolDualController.idf"
# output info file
epOutFile="${OUT_DIR}/eplus_${scenarioName}_${scenarioType}.out"

# ======================================================== setting up the Energy Plus JSON environment ===========================================================
# FNCS broker setting for Energy Plus JSON; this could also be set up in the ZPL file
fncsBrEPJ="tcp://localhost:5570"
# set FNCS to print or not at standard output for Energy Plus JSON
epjSTDOUTlog="yes"
# set FNCS to log or not the outputs for Energy Plus JSON
epjFILElog="no"
epjLOGlevel="INFO"
# set the configuration file for Energy Plus
epjCONFfile="${SCEN_ROOT}/eplus_json.yaml"
# set Energy Plus JSON stop time - mandatory parameter
epjSTOPtime="172800s" # "2d"
# set Energy Plus JSON aggregation time for results - mandatory parameter
epjAGGtime="5m"
# set Energy Plus JSON building ID
epjBUILDid="SchoolDualController"
# reference price [$/MW]
epjBasePrice=0.02
# price ramp [defF/price]
epjTempRamp=25
# high delta temperature
epjLimitHi=4
# low delta temperature
epjLimitLo=4
# set Energy Plus output file
epjMetricsFile="eplus_${scenarioName}_${scenarioType}_metrics.json"
# output info file
epjOutFile="${OUT_DIR}/eplus_json_${scenarioName}_${scenarioType}.out"

# ========================================================= setting up AGENTS configurations ========================================================================
# TE AGENTS installation folder
agentSTDOUTlog="yes"
agentFILElog="no"
agentLOGlevel="INFO"
agentCONFfile="${SCEN_ROOT}/TE_Challenge_substation.yaml"
agentDICTfile="${SCEN_ROOT}/TE_Challenge_agent_dict.json"
agentOutFile="${OUT_DIR}/substation_${scenarioName}_${scenarioType}.out"

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

# ================================================ starting PYPOWER ==================================================================
if test -e $ppOutFile
then
  echo "$ppOutFile exists, so I will remove it."
  rm $ppOutFile
fi

export FNCS_CONFIG_FILE=$ppFNCSConfig && \
export FNCS_LOG_STDOUT=$ppSTDOUTlog \
&& export FNCS_LOG_FILE=$ppFILElog && \
export FNCS_LOG_LEVEL=$fncsLOGlevel && \
export PYPOWER_LOG_LEVEL=$ppLOGlevel && \
cd ${SCEN_ROOT} && \
python -c "import tesp_support.api as tesp;tesp.tso_pypower_loop_f('te30_pp.json','${scenarioName}_${scenarioType}')" &> $ppOutFile &

# ================================================ starting GridLAB-D ===============================================================
for ((i=0; i<$gldNum; i++)); do
   # output file for each GridLAB-D instance
   echo ${gldModels[${i}]}
   gldOutFile="${OUT_DIR}/gld$((${i}+1))_${gldTotalNum}Subst_${scenarioType}.out"
   if test -e $gldOutFile
   then
     echo "$gldOutFile exists, so I will remove it."
     rm $gldOutFile
   fi
   export FNCS_LOG_STDOUT=$gldSTDOUTlog && \
   export FNCS_LOG_FILE=$gldFILElog && \
   export FNCS_LOG_LEVEL=$gldLOGlevel && \
   cd ${SCEN_ROOT} && \
   gridlabd -D USE_FNCS -D METRICS_FILE=${gldMetricsfile} ${gldModels[${i}]} &> $gldOutFile &
done

# ================================================ starting TE Agents ============================================================
export FNCS_LOG_STDOUT=${agentSTDOUTlog} && \
export FNCS_LOG_FILE=${agentFILElog} && \
export FNCS_LOG_LEVEL=$agentLOGlevel && \
export FNCS_CONFIG_FILE=${agentCONFfile} && \
export FNCS_FATAL=NO && \
cd ${SCEN_ROOT} && \
python -c "import tesp_support.api as tesp;tesp.substation_loop('${agentDICTfile}','${scenarioName}_${scenarioType}',flag='${scenarioType}')" &> ${agentOutFile} &

# ================================================ starting Energy Plus ============================================================
if test -e $epOutFile
then
  echo "$epOutFile exists, so I will remove it."
  rm $epOutFile
fi

export FNCS_BROKER=$fncsBrEP && \
export FNCS_LOG_STDOUT=$epSTDOUTlog && \
export FNCS_LOG_FILE=$epFILElog && \
export FNCS_CONFIG_FILE=$epCONFfile && \
export FNCS_LOG_LEVEL=$epLOGlevel && \
cd ${SCEN_ROOT} && energyplus -w $epWEATHERfile -d ${OUT_DIR} -r $epREFfile &> $epOutFile &

# ================================================ starting Energy Plus JSON =======================================================
if test -e $epjOutFile
then
  echo "$epjOutFile exists, so I will remove it."
  rm $epjOutFile
fi

if test -e $epjMetricsFile
then
  echo "$epjMetricsFile exists, so I will remove it."
  rm $epjMetricsFile
fi

export FNCS_BROKER=$fncsBrEPJ && \
export FNCS_LOG_STDOUT=$epjSTDOUTlog && \
export FNCS_LOG_FILE=$epjFILElog && \
export FNCS_CONFIG_FILE=$epjCONFfile && \
export FNCS_LOG_LEVEL=$epjLOGlevel && \
cd ${SCEN_ROOT} && \
eplus_json $epjSTOPtime $epjAGGtime $epjBUILDid $epjMetricsFile ${epjBasePrice} ${epjTempRamp} ${epjLimitHi} ${epjLimitLo}  &> $epjOutFile &

exit 0
