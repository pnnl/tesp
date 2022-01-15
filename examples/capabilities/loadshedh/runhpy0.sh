#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runhpy0.sh

(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker.log &)
(exec gridlabd -D WANT_HELICS_NO_NS3 loadshed.glm &> gridlabd.log &)
(exec helics_recorder --input=helicsRecorder0.json --timedelta 1s --period 1s --stop 21600s &> tracer.log &)
(exec python3 helicshed0.py &> loadshed.log &)
