#!/bin/bash
# helics run --path helicsconfig.json
(exec helics_broker -f 2 --loglevel=3 --name=mainbroker &> broker.log &)
(exec gridlabd -D WANT_HELICS_NO_NS3 loadshed.glm &> gridlabd.log &)
# (exec fncs_player 6h loadshed.player &> player.log &)
(exec python3 helicshed0.py &> loadshed.log &)


