#!/bin/bash

# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: runhpy0.sh

(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker.log &)
(exec helics_recorder --config-file helicsRecorder.json --timedelta 1s --period 1s --stop 21600s &> tracer.log &)
(exec gridlabd -D WANT_HELICS_NO_NS3 loadshed.glm &> gridlabd.log &)
(exec python3 helicshed0.py &> loadshed.log &)
