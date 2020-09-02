# need to have made ems*.idf in the local directory, with bHELICS=True

declare -r TESP_SUPPORT=$TESP_INSTALL/share/support
#declare -r TESP_SUPPORT=../../support

declare -r BUILDING=$1
declare -r STARTDATE=$2
declare -r ENDDATE=$3
declare -r TARGET=$4
declare -r STEPS=$5
declare -r METRICS=eplus_${TARGET}_metrics.json
#declare -r EPWFILE=$TESP_SUPPORT/energyplus/USA_IN_Indianapolis.Intl.AP.724380_TMY3.epw
declare -r EPWFILE=$TESP_SUPPORT/energyplus/2A_USA_TX_HOUSTON.epw

echo $BUILDING, $TARGET, $STARTDATE, $ENDDATE

python3 -c "import tesp_support.api as tesp;tesp.merge_idf('$TESP_SUPPORT/energyplus/$BUILDING.idf','ems$BUILDING.idf', '$STARTDATE', '$ENDDATE', '$TARGET.idf', '$STEPS')"

#(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker.log &)
#(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w $EPWFILE -d out$TARGET -r $TARGET.idf &> eplus$TARGET.log &)
#(export FNCS_LOG_STDOUT=yes && exec fncs_player 2d prices.txt &> player.log &)
#(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus_agent.yaml && exec eplus_agent 2d 5m $TARGET $METRICS 0.10 50 6 6 &> eplus_agent$TARGET.log &)

(exec helics_broker -f 3 --name=mainbroker &> broker.log &)
(export HELICS_CONFIG_FILE=eplusH.json && exec energyplus -w $EPWFILE -d out$TARGET -r $TARGET.idf &> eplus$TARGET.log &)
(exec helics_player --input=prices.txt --local --time_units=ns --stop 172800s &> playerH.log &)
(exec eplus_agent_helics 172800s 300s $TARGET $METRICS  0.10 50 6 6 eplus_agentH.json &> eplus_agent$TARGET.log &)

sleep 2
pid=$(pidof eplus_agent_helics)
echo $pid
tail --pid=$pid -f /dev/null
#wait < tesp.pid

