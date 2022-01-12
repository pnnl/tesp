#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runfh_bridge.sh

EPLUS_PATH=$TESPDIR/data/energyplus
EPWFILE=$EPLUS_PATH/USA_IN_Indianapolis.Intl.AP.724380_TMY3.epw

#python3 -c "import tesp_support.api as tesp;tesp.merge_idf('$EPLUS_PATH/FullServiceRestaurant.idf','emsFullServiceRestaurant.idf', '2013-08-01 00:00:00', '2013-08-03 00:00:00', 'Merged.idf', '12')"
python3 -c "import tesp_support.api as tesp;tesp.merge_idf('SchoolBase.idf','./forSchoolBase/emsSchoolBase.idf', '2013-08-01 00:00:00', '2013-08-03 00:00:00', 'Merged.idf', '12')"

# FNCS federation is energyplus with agent, and a recorder
(export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> fncs_broker.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w $EPWFILE -d output Merged.idf &> eplus.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus_agent.yaml && exec eplus_agent 2d 5m SchoolDualController eplus_eplus_metrics.json  0.10 50 6 6 bridge_eplus_agent.json &> eplus_agent.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 2d tracer.out &> fncs_tracer.log &)

# HELICS federation is the pricing with agent, and a recorder; the agent was already started as part of the FNCS federation
(exec helics_broker -f 3 --loglevel=4 --name=mainbroker &> helics_broker.log &)
(exec helics_player --input=prices.txt --local --time_units=ns --stop 172800s &> helics_player.log &)
(exec helics_recorder --input=helicsRecorder.txt --timedelta 1s --period 300s --stop 172800s &> helics_recorder.log &)
