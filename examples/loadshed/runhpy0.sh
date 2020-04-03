#!/bin/bash
(exec helics_broker -f 3 --loglevel=7 --name=mainbroker &> broker.log &)
(exec gridlabd -D WANT_HELICS_NO_NS3 loadshed.glm &> gridlabd.log &)
(exec helics_recorder --input=helicsRecorder0.txt --timedelta 1s --verbose --mapfile map.out --period 1s --marker 900s --stop 21600s &> recorder.log &)
(exec python3 helicshed0.py &> loadshed.log &)

