#!/bin/bash

# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: runhjava.sh

declare -r JAVAPATH=$INSTDIR/java

# Compile helicshed
javac -classpath ".:$JAVAPATH/helics.jar" helicshed.java

(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker.log &)
(exec helics_recorder --config-file helicsRecorder.json --timedelta 1s --period 1s --stop 21600s &> tracer.log &)
(exec gridlabd -D WANT_HELICS_NO_NS3 loadshed.glm &> gridlabd.log &)
(exec java -classpath ".:$JAVAPATH/helics.jar" -Djava.library.path="$JAVAPATH" helicshed &> java.log &)
