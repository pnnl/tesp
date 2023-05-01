#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runh.sh

declare -r EPLUS_PATH=$TESPDIR/data/energyplus
declare -r EPWFILE=$EPLUS_PATH/USA_IN_Indianapolis.Intl.AP.724380_TMY3.epw

python3 -c "import tesp_support.api.proces as tesp;tesp.merge_idf('SchoolBase.idf','./forSchoolBase/emsSchoolBaseH.idf', '2013-08-01 00:00:00', '2013-08-03 00:00:00', 'Merged.idf', '12')"

(exec helics_broker -f 4 --name=mainbroker &> broker.log &)
(export HELICS_CONFIG_FILE=eplusH.json && exec energyplus -w $EPWFILE -d output Merged.idf &> eplusH.log &)
(exec helics_player --input=prices.txt --local --time_units=ns --stop 172800s &> playerH.log &)
(exec eplus_agent_helics 172800s 300s SchoolDualController eplus_eplus_metrics.json  0.10 25 4 4 eplus_agentH.json &> eplus_agentH.log &)
(exec helics_recorder --input=helicsRecorder.json --timedelta 1s --period 300s --stop 172800s &> tracerH.log &)
