#!/bin/bash

# Copyright (C) 2021 Battelle Memorial Institute
# file: runhjava.sh


JAVAPATH=$INSTDIR/java

# Compile helicshed
javac -classpath ".:$JAVAPATH/helics.jar" helicshed.java

(exec helics_broker -f 2 --loglevel=warning --name=mainbroker &> broker.log &)
(exec gridlabd -D WANT_HELICS_NO_NS3 loadshed.glm &> gridlabd.log &)
(exec java -classpath ".:$JAVAPATH/helics.jar" -Djava.library.path="$JAVAPATH" helicshed &> java.log &)
