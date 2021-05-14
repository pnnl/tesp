#!/bin/bash
#(exec helics_broker -f 3 --loglevel=4 --name=mainbroker &> broker.log & jobs -p > tesp.pid)
#(export 'NS_LOG=loadshedCommNetwork:HelicsApplication:HelicsFilterApplication:HelicsIdTag:HelicsSimulatorImpl:HelicsStaticSinkApplication:HelicsStaticSourceApplication=level_all|prefix_func|prefix_time' && exec loadshedCommNetwork --helicsConfigFile=loadshedCommNetworkConfig.json --simulationRunTime=21600.0 &> network.log & jobs -p >> tesp.pid)
#(exec gridlabd -D NEW_ISLANDING -D WANT_HELICS_NS3 loadshed.glm &> gridlabd.log & jobs -p >> tesp.pid)
#(exec python3 helicshed.py &> loadshed.log & jobs -p >> tesp.pid)

make
chmod +x loadshedCommNetwork

(exec helics_broker -f 4 --loglevel=4 --dumplog --name=mainbroker &> broker.log &)
(export 'NS_LOG=loadshedCommNetwork:HelicsApplication:HelicsFilterApplication:HelicsIdTag:HelicsSimulatorImpl:HelicsStaticSinkApplication:HelicsStaticSourceApplication=level_all|prefix_func|prefix_time' && exec ./loadshedCommNetwork --helicsConfigFile=loadshedCommNetworkConfig.json --simulationRunTime=21600.0 &> network.log &)
#(exec ./loadshedCommNetwork --helicsConfigFile=loadshedCommNetworkConfig.json --simulationRunTime=21600.0 &> network.log &)
(exec gridlabd -D NEW_ISLANDING -D WANT_HELICS_NS3 loadshed.glm &> gridlabd.log &)
(exec python3 helicshed.py &> loadshed.log &)
(exec helics_recorder --input=helicsRecorder.json --timedelta 1s --period 1s --stop 21600s &> tracer.log &)

