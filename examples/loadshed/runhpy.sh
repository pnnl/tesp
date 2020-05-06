#!/bin/bash
#(exec helics_broker -f 3 --loglevel=4 --name=mainbroker &> broker.log & jobs -p > tesp.pid)
#(exec helics_recorder --input=helicsRecorder.txt --timedelta 1s --verbose --mapfile map.out --period 1s --marker 900s --stop 21600s &> recorder.log &)
#(exec helics_recorder --input=helicsRecorder.txt --period 1s --stop 21600s &> recorder.log & jobs -p >> tesp.pid)
#(exec helics_recorder --config-file=helicsRecorder.json --input=recorderSources.json &> recorder.log & jobs -p >> tesp.pid)
#(exec helics_recorder --input=recorderSources.json --period 60s --stop 21600s &> recorder.log & jobs -p >> tesp.pid)
#(export 'NS_LOG=loadshedCommNetwork:HelicsApplication:HelicsFilterApplication:HelicsIdTag:HelicsSimulatorImpl:HelicsStaticSinkApplication:HelicsStaticSourceApplication=level_all|prefix_func|prefix_time' && exec loadshedCommNetwork --helicsConfigFile=loadshedCommNetworkConfig.json --simulationRunTime=21600.0 &> network.log & jobs -p >> tesp.pid)
#(exec gridlabd -D NEW_ISLANDING -D WANT_HELICS_NS3 loadshed.glm &> gridlabd.log & jobs -p >> tesp.pid)
#(exec python3 helicshed.py &> loadshed.log & jobs -p >> tesp.pid)

(exec helics_broker -f 3 --loglevel=4 --name=mainbroker &> broker.log &)
#(export 'NS_LOG=loadshedCommNetwork:HelicsApplication:HelicsFilterApplication:HelicsIdTag:HelicsSimulatorImpl:HelicsStaticSinkApplication:HelicsStaticSourceApplication=level_all|prefix_func|prefix_time' && exec loadshedCommNetwork --helicsConfigFile=loadshedCommNetworkConfig.json --simulationRunTime=21600.0 &> network.log &)
(exec loadshedCommNetwork --helicsConfigFile=loadshedCommNetworkConfig.json --simulationRunTime=21600.0 &> network.log &)
(exec gridlabd -D NEW_ISLANDING -D WANT_HELICS_NS3 loadshed.glm &> gridlabd.log &)
(exec python3 helicshed.py &> loadshed.log &)

