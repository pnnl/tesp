#!/bin/bash

# Copyright (C) 2021 Battelle Memorial Institute
# file: runjava.sh


JAVAPATH=$INSTDIR/java

# Compile loadshed 
javac -classpath ".:$JAVAPATH/fncs.jar" loadshed.java

(export FNCS_TRACE=yes && export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec gridlabd -D WANT_FNCS=1 loadshed.glm &> gridlabd.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec fncs_player 6h loadshed.player &> player.log &)
(export FNCS_CONFIG_FILE=loadshed.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec java -classpath ".:$JAVAPATH/fncs.jar" -Djava.library.path="$JAVAPATH" loadshed 21600 &> java.log &)
