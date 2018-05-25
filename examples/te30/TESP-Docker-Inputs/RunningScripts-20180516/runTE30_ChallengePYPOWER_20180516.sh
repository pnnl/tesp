#!/bin/bash

clear
scenarioName="TE30_ChallengePYPOWER"
SIM_ROOT="/tesp"
# ==================================================== setting up the FNCS environment ================================================
# FNCS broker
fncsBroker="tcp://*:5570"
# FNCS installation folder
fncsDir="${SIM_ROOT}/FNCSInstall/bin"
FNCSROOT="${SIM_ROOT}/FNCSInstall"
echo "---------------------------------------------"
if test -z $LD_LIBRARY_PATH
then
  LD_LIBRARY_PATH=.:$FNCSROOT/lib
else
  LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$FNCSROOT/lib
fi    
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$FNCSROOT/bin
export LD_LIBRARY_PATH
echo $LD_LIBRARY_PATH
echo "======================================================"
# set FNCS to print or not at the standard output
fncsSTDOUTlog="yes"
# set FNCS to log or not the outputs for FNCS broker
fncsFILElog="no"
fncsLogFile="$fncsDir/fncs_broker.log" # I believe this is a default name
# number of simulators
# simNum=5
# FNCS output file (if wanted)
fncsOutFile="$fncsDir/outputFiles/fncs${simNum}Sims.out"
# FNCS logging level
fncsLOGlevel="DEBUG4"

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
gldModels=("$gldDir/modelFiles/TE30_ChallengePYPOWER.glm")
# get the number of GridLAB-D models
gldNum=${#gldModels[@]}
echo "There are $gldNum GridLAB-D instances."
# GridLAB-D logging level
gldLOGlevel="DEBUG4"

# ===================================================== setting up the PYPOWER environment ====================================================
# PYPOWER installation folder
ppDir="${SIM_ROOT}/PyPowerInstall"
# FNCS broker setting for PYPOWER; this could also be set up in the YAML file
fncsBrMP="tcp://localhost:5570"
# set FNCS to print or not at standard output for PYPOWER
ppSTDOUTlog="yes"
# set FNCS to log or not the outputs for FNCS broker
ppFILElog="no"
# PYPOWER configuration file for FNCS
ppFNCSConfig="$ppDir/pypowerConfig_TE30dispload.yaml"
# PYPOWER case
ppCase="$ppDir/ppcasefile.py"
# caseNum="9"
# Total number of substations; could be different than the number running under this scripts
gldTotalNum="1"
# mpCase="./caseFiles/case${caseNum}_${gldTotalNum}Subst_2GenAtBus2.m"
# real load profile file
# realLoadFile="$ppDir/inputFiles/real_power_demand_CCSI.txt"
# reactive load profile file
# reactiveLoadFile="$ppDir/inputFiles/reactive_power_demand_CCSI.txt"
# clearing market time/interval between OPF calculations
ppMarketTime=300
# stop time for MATPOWER simulation in seconds
ppStopTime=172800
# presumed starting time of simulation
# needs to be double quoted when used becase the string has spaces
ppStartTime="2012-01-01 00:00:00 PST"
# load metrics file output
ppLoadMetricsFile="$ppDir/metricFiles/loadBus_metrics.json"
# dispatchable load metrics file output
ppDispLoadMetricsFile="$ppDir/metricFiles/dispLoadBus_metrics.json"
# generator metrics file output
ppGeneratorMetricsFile="$ppDir/metricFiles/generatorBus_metrics.json"
# output file
ppOutFile="$ppDir/outputFiles/pp${gldTotalNum}Subst.out"
# PYPOWER logging level
ppLOGlevel="DEBUG4"
# ppLOGlevel="LMACTIME"

# ====================================================== setting up the Energy Plus environment ==============================================================
# Energy Plus installation folder
epDir="${SIM_ROOT}/EnergyPlusInstall"
epRunDir="${epDir}/Products"
# FNCS broker setting for Energy Plus; this could also be set up in the ZPL file
fncsBrEP="tcp://localhost:5570"
# set FNCS to print or not at standard output for Energy Plus
epSTDOUTlog="yes"
# set FNCS to log or not the outputs for Energy Plus
epFILElog="no"
epLOGlevel="DEBUG4"
# set the configuration file for Energy Plus
epCONFfile="${epDir}/eplus.yaml"
# set Energy Plus weather file
epWEATHERfile="${epDir}/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw"
# Energy Plus reference file
epREFfile="${epDir}/SchoolDualController.idf"
# output info file
epOutFile="$epDir/outputFiles/eplus_${scenarioName}_PYPOWER.out"

# ======================================================== setting up the Energy Plus JSON environment ===========================================================
# Energy Plus JSON installation folder
epjDir="${SIM_ROOT}/EPlusJSONInstall"
epjRunDir="${epjDir}/bin"
# FNCS broker setting for Energy Plus JSON; this could also be set up in the ZPL file
fncsBrEPJ="tcp://localhost:5570"
# set FNCS to print or not at standard output for Energy Plus JSON
epjSTDOUTlog="yes"
# set FNCS to log or not the outputs for Energy Plus JSON
epjFILElog="no"
epjLOGlevel="DEBUG4"
# set the configuration file for Energy Plus
epjCONFfile="${epjDir}/eplus_json.yaml"
# set Energy Plus JSON stop time - mandatory parameter
epjSTOPtime="172800s" # "2d"
# set Energy Plus JSON aggregation time for results - mandatory parameter
epjAGGtime="5m"
# set Energy Plus JSON building ID
epjBUILDid="School_DualController"
# set Energy Plus output file
epjMetricsFile="$epjDir/outputFiles/eplus_${scenarioName}_metrics.json"
# output info file
epjOutFile="$epjDir/outputFiles/eplus_json_${scenarioName}.out"

# ========================================================= setting up AGENTS configurations ========================================================================
# TE AGENTS installation folder
agentSTDOUTlog="yes"
agentFILElog="no"
agentLOGlevel="DEBUG4"
agentDir="${SIM_ROOT}/AgentsInstall"
agentCONFfile="${agentDir}/inputFiles/${scenarioName}_auction.yaml"
agentDICTfile="${agentDir}/inputFiles/${scenarioName}_agent_dict.json"
agentOutFile="${agentDir}/outputFiles/${scenarioName}_auction.out"

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

export FNCS_LOG_LEVEL=$fncsLOGlevel && export FNCS_BROKER=$fncsBroker && export FNCS_LOG_STDOUT=$fncsSTDOUTlog && export FNCS_LOG_FILE=$fncsFILElog && cd $fncsDir && ./fncs_broker $simNum &
> $fncsOutFile &

# ================================================ starting PYPOWER ==================================================================
if test -e $ppOutFile
then
  echo "$ppOutFile exists, so I will remove it."
  rm $ppOutFile
fi

export FNCS_CONFIG_FILE=$ppFNCSConfig && export FNCS_LOG_STDOUT=$ppSTDOUTlog && export FNCS_LOG_FILE=$ppFILElog && export FNCS_LOG_LEVEL=$fncsLOGlevel && export PYPOWER_LOG_LEVEL=$ppLOGlevel && cd $ppDir && python3 ./fncsPYPOWER.py $scenarioName &> $ppOutFile &
# $ppCase "$mpStartTime" $mpStopTime $mpMarketTime

# ================================================ starting GridLAB-D ===============================================================
for ((i=0; i<$gldNum; i++)); do
   # output file for each GridLAB-D instance
   echo ${gldModels[${i}]}
   gldOutFile="$gldDir/outputFiles/gld$((${i}+1))_${gldTotalNum}Subst.out"
   if test -e $gldOutFile
   then
     echo "$gldOutFile exists, so I will remove it."
     rm $gldOutFile
   fi
   export FNCS_LOG_STDOUT=$gldSTDOUTlog && export FNCS_LOG_FILE=$gldFILElog && export FNCS_LOG_LEVEL=$gldLOGlevel && cd $gldDir && ./gridlabd -D USE_FNCS -D METRICS_FILE=TE30_ChallengePYPOWER_metrics.json ${gldModels[${i}]} &> $gldOutFile &
done

# ================================================ starting TE Agents ============================================================
export FNCS_LOG_STDOUT=${agentSTDOUTlog} && export FNCS_LOG_FILE=${agentFILElog} && export FNCS_LOG_LEVEL=$agentLOGlevel && export FNCS_CONFIG_FILE=${agentCONFfile} && export FNCS_FATAL=NO && cd $agentDir && exec python3 auction.py ${agentDICTfile} ${scenarioName} &> ${agentOutFile} &

# ================================================ starting Energy Plus ============================================================
if test -e $epOutFile
then
  echo "$epOutFile exists, so I will remove it."
  rm $epOutFile
fi

export FNCS_BROKER=$fncsBrEP && export FNCS_LOG_STDOUT=$epSTDOUTlog && export FNCS_LOG_FILE=$epFILElog && export FNCS_CONFIG_FILE=$epCONFfile && export FNCS_LOG_LEVEL=$epLOGlevel && cd $epRunDir && ./energyplus -w $epWEATHERfile -d output -r $epREFfile &> $epOutFile &

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

export FNCS_BROKER=$fncsBrEPJ && export FNCS_LOG_STDOUT=$epjSTDOUTlog && export FNCS_LOG_FILE=$epjFILElog && export FNCS_CONFIG_FILE=$epjCONFfile && export FNCS_LOG_LEVEL=$epjLOGlevel && cd $epjRunDir && ./eplus_json $epjSTOPtime $epjAGGtime $epjBUILDid $epjMetricsFile  &> $epjOutFile &

exit 0
