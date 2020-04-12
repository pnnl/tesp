declare -r TESP_SUPPORT=$TESP_INSTALL/share/support

declare -r BUILDING=$1
declare -r STARTDATE=$2
declare -r ENDDATE=$3
declare -r TARGET=$4
declare -r STEPS=$5
declare -r METRICS=eplus_${TARGET}_metrics.json
declare -r EPWFILE=$TESP_SUPPORT/energyplus/USA_IN_Indianapolis.Intl.AP.724380_TMY3.epw

echo $BUILDING, $TARGET, $STARTDATE, $ENDDATE

python3 -c "import tesp_support.api as tesp;tesp.merge_idf('$TESP_SUPPORT/energyplus/$BUILDING.idf','ems$BUILDING.idf', '$STARTDATE', '$ENDDATE', '$TARGET.idf', '$STEPS')"

(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w $EPWFILE -d out$TARGET -r $TARGET.idf &> eplus$TARGET.log &)
(export FNCS_LOG_STDOUT=yes && exec fncs_player 2d prices.txt &> player.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 15m $TARGET $METRICS 0.10 50 6 6 &> eplus_json$TARGET.log &)

sleep 2
pid=$(pidof eplus_json)
echo $pid
tail --pid=$pid -f /dev/null
#wait < tesp.pid

