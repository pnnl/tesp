#!/bin/bash

clear

# setting up the FNCS environment
# FNCS broker
fncsBroker="tcp://*:5570"
# FNCS installation folder
fncsDir="/home/laurentiu/work/CoSimulation/FNCSinstall/bin"
# set FNCS to print or not at the standard output
fncsSTDOUTlog="no"
# set FNCS to log or not the outputs for FNCS broker
fncsFILElog="no"
# number of simulators
simNum=2
# FNCS output file (if wanted)
fncsOutFile="fncs${simNum}Sims.out"
# FNCS logging level
fncsLOGlevel="DEBUG4"

# setting up the PLAYER environment
# PLAYER installation folder
playerDir="/home/laurentiu/work/CoSimulation/FNCSinstall/bin"
# FNCS broker setting for PLAYER; this could also be set up in the ZPL file
fncsBrPlayer="tcp://localhost:5570"
# set FNCS to print or not at standard output for PLAYER
playerSTDOUTlog="no"
# set FNCS to log or not the outputs for FNCS broker
playerFILElog="no"
# stop time for PLAYER simulation in seconds
playerStopTime="420s"
# input file
playerInFile="matpowerPlayer.player"
# output file
playerOutFile="playerLog.out"
# player name
playerName="matpowerPlayer"
# player logging level
playerLOGlevel="DEBUG4"

# setting up the GridLAB-D environment
# FNCS broker for GridLAB-D
# this need to be set in GLM file also, or is it enough in only one place?
fncsBrGLD="tcp://localhost:5570"
# set FNCS to print or not at standard output for GridLAB-D
gldSTDOUTlog="no"
# set FNCS to log or not the outputs for FNCS broker
gldFILElog="no"
# GridLAB-D installation folder
gldDir="/home/laurentiu/work/CoSimulation/GridLABDinstall/bin"
# GridLAB-D models array
gldModels=('TBusNum_5_R1_1247_1_t0_TESP.glm')
# get the number of GridLAB-D models
gldNum=${#gldModels[@]}
echo $gldNum

# setting up the MATPOWER environment
# MATPOWER installation folder
mpDir="/home/laurentiu/work/CoSimulation/CCSI28-MATPOWERinstall"
# FNCS broker setting for MATPOWER; this could also be set up in the ZPL file
fncsBrMP="tcp://localhost:5570"
# set FNCS to print or not at standard output for MATPOWER
mpSTDOUTlog="no"
# set FNCS to log or not the outputs for FNCS broker
mpFILElog="no"
# MATPOWER case
caseNum="9"
# Total number of substations; could be different than the number running under this scripts
gldTotalNum="1"
mpCase="case${caseNum}_${gldTotalNum}Subst_2GenAtBus2.m"
# real load profile file
realLoadFile="real_power_demand.txt"
# reactive load profile file
reactiveLoadFile="reactive_power_demand.txt"
# MATPOWER configuration file for FNCS
mpFNCSConfig="matpowerSubsWithPlayer.yaml"
# clearing market time/interval between OPF calculations
mpMarketTime=300
# stop time for MATPOWER simulation in seconds
mpStopTime=420
# presumed starting time of simulation
# needs to be double quoted when used becase the string has spaces
mpStartTime="2012-01-01 00:00:00 PST"
# load metrics file output
mpLoadMetricsFile="loadBus_case${caseNum}_metrics.json"
# dispatchable load metrics file output
mpDispLoadMetricsFile="dispLoadBus_case${caseNum}_metrics.json"
# generator metrics file output
mpGeneratorMetricsFile="generatorBus_case${caseNum}_metrics.json"
# output file
mpOutFile="mp${gldTotalNum}Subst.out"
# MATPOWER logging level
mpLOGlevel="DEBUG4"

# starting FNCS broker
export FNCS_LOG_LEVEL=$fncsLOGlevel && export FNCS_BROKER=$fncsBroker && export FNCS_LOG_STDOUT=$fncsSTDOUTlog && export FNCS_LOG_FILE=$fncsFILElog && cd $fncsDir && ./fncs_broker $simNum &
#> $fncsOutFile &

# starting the FNCS player to help with testing the MATPOWER wrapper code
# related to fully integration of wholesale and retail markets integration
export FNCS_NAME=$playerName && export FNCS_LOG_LEVEL=$playerLOGlevel && export FNCS_BROKER=$fncsBrPlayer && export FNCS_LOG_STDOUT=$playerSTDOUTlog && export FNCS_LOG_FILE=$playerFILElog && cd $playerDir && ./fncs_player $playerStopTime $playerInFile &> $playerOutFile &

# starting GridLAB-D
# for ((i=0; i<$gldNum; i++)); do
   # output file for each GridLAB-D instance
#    echo ${gldModels[${i}]}
#    gldOutFile="gld$((${i}+1))_${gldTotalNum}Subst.out"
#    export FNCS_LOG_STDOUT=$gldSTDOUTlog && export FNCS_LOG_FILE=$gldFILElog && cd $gldDir && ./gridlabd ${gldModels[${i}]} &> $gldOutFile &
# done

# starting MATPOWER
export FNCS_CONFIG_FILE=$mpFNCSConfig && export FNCS_LOG_STDOUT=$mpSTDOUTlog && export FNCS_LOG_FILE=$mpFILElog && export FNCS_LOG_LEVEL=$fncsLOGlevel && export MATPOWER_LOG_LEVEL=$mpLOGlevel && cd $mpDir && ./start_MATPOWER $mpCase $realLoadFile $reactiveLoadFile $mpStopTime $mpMarketTime "$mpStartTime" $mpLoadMetricsFile $mpDispLoadMetricsFile $mpGeneratorMetricsFile &> $mpOutFile &

exit 0
