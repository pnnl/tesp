#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runhpp.sh


(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.tso_pypower_loop('ppcase.json','ppcase',helicsConfig='pypowerConfig.json')" &> pypower.log &)
(exec helics_recorder --input=helicsRecorder.txt --stop 172801s &> recorder.log &)
(exec helics_player --input=helics_loads.txt --local --time_units=s --stop 172800s &> helics_player.log &)
