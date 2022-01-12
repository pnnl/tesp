#!/bin/bash
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run.sh

#(exec helics_broker -f 4 --loglevel=7 --name=mainbroker &> broker.log &)
#(export HELICS_CONFIG_FILE=eplus.json && exec /home/xcosmos/src/energyPlus/EnergyPlus/build/Products/energyplus -w Test.epw -d output -r Mergedh.idf &> eplus.log &)
#(exec helics_player --input=prices.txt --local --time_units=ns --stop 172800s --loglevel=7 &> player.log &)
#(exec eplus_agent_helics 172800s 300s SchoolDualController eplus_eplus_metrics.json  0.10 25 4 4 helics_eplus_agent2.json &> eplus_agent.log &)
#(exec helics_recorder --input=helicsRecorder.json --timedelta 1s --period 300s --stop 172800s --loglevel=7 &> tracer.log &)

EPLUS_PATH=$TESPDIR/data/energyplus
EPWFILE=$EPLUS_PATH/USA_IN_Indianapolis.Intl.AP.724380_TMY3.epw

(exec helics_broker -f 4 --name=mainbroker &> broker.log &)
(export HELICS_CONFIG_FILE=eplus.json && exec energyplus -w $EPWFILE -d output -r Mergedh.idf &> eplus.log &)
(exec helics_player --input=prices.txt --local --time_units=ns --stop 172800s &> player.log &)
(exec eplus_agent_helics 172800s 300s SchoolDualController eplus_eplus_metrics.json  0.10 25 4 4 helics_eplus_agent2.json &> eplus_agent.log &)
(exec helics_recorder --input=helicsRecorder.json --timedelta 1s --period 300s --stop 172800s &> tracer.log &)
