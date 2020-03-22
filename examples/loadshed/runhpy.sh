#!/bin/bash
(exec helics_broker -f 3 --loglevel=3 --name=mainbroker &> broker.log &)
(exec gridlabd --lock -D WANT_HELICS_NS3 loadshed.glm &> gridlabd.log &)
(exec loadshedCommNetwork --helicsConfigFile=loadshedCommNetworkConfig.json --simulationRunTime=21600.0 &> network.log &)
(exec python3 helicshed.py &> loadshed.log &)


