#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runhpy.sh

declare -r ns3=
#Errorlevel for ns3-helics loadshedCommNetwork, uncomment next three lines for debugging
#ns3=loadshedCommNetwork:HelicsApplication:HelicsFilterApplication
#ns3=$ns3:HelicsIdTag:HelicsSimulatorImpl:HelicsStaticSinkApplication
#ns3=$ns3:HelicsStaticSourceApplication=level_all|prefix_func|prefix_time


#(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker.log & jobs -p > tesp.pid)
#(exec gridlabd -D NEW_ISLANDING -D WANT_HELICS_NS3 loadshed.glm &> gridlabd.log & jobs -p >> tesp.pid)
#(export NS_LOG=$ns3 && exec loadshedCommNetwork --helicsConfigFile=loadshedCommNetworkConfig.json --simulationRunTime=21600.0 &> network.log & jobs -p >> tesp.pid)
#(exec python3 helicshed.py &> loadshed.log & jobs -p >> tesp.pid)


(exec helics_broker -f 4 --loglevel=warning --dumplog --name=mainbroker &> broker.log &)
(exec helics_recorder --input=helicsRecorder.json --timedelta 1s --period 1s --stop 21600s &> tracer.log &)
(exec gridlabd -D WANT_HELICS_NS3 loadshed.glm &> gridlabd.log &)
(export NS_LOG=$ns3 && exec ./loadshedCommNetwork --helicsConfigFile=loadshedCommNetworkConfig.json --simulationRunTime=21600.0 &> network.log &)
(exec python3 helicshed.py &> loadshed.log &)
