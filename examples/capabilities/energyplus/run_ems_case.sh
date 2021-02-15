# need to have made ems*.idf in the local directory, with bHELICS=True
# or cp ~/src/tesp/support/energyplus/emsHELICS/*.idf .

declare -r MERGED=$1
declare -r OUTPUT=$2
declare -r RAMP=$3
declare -r CAP=$4
declare -r EPWFILE=$5
declare -r METRICS=eplus_${OUTPUT}_metrics.json

echo $MERGED, $OUTPUT, $RAMP, $CAP, $METRICS

#(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker.log &)
#(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w $EPWFILE -d out$OUTPUT $MERGED.idf &> eplus$OUTPUT.log &)
#(export FNCS_LOG_STDOUT=yes && exec fncs_player 2d prices.txt &> player.log &)
#(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus_agent.yaml && exec eplus_agent 2d 5m $OUTPUT $METRICS 0.10 $RAMP $CAP $CAP &> eplus_agent$OUTPUT.log &)

(exec helics_broker -f 3 --name=mainbroker &> broker.log &)
(export HELICS_CONFIG_FILE=eplusH.json && exec energyplus -w $EPWFILE -d out$OUTPUT $MERGED.idf &> eplus$OUTPUT.log &)
(exec helics_player --input=prices.txt --local --time_units=ns --stop 172800s &> playerH.log &)
(exec eplus_agent_helics 172800s 300s $OUTPUT $METRICS  0.10 $RAMP $CAP $CAP eplus_agentH.json &> eplus_agent$OUTPUT.log &)

sleep 2
pid=$(pidof eplus_agent_helics)
echo $pid
tail --pid=$pid -f /dev/null
#wait < tesp.pid

