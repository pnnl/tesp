#!/bin/bash

# Copyright (C) 2021 - 2022 Battelle Memorial Institute
# file: ruh30.glm

declare -r SCHED_PATH=$TESPDIR/data/schedules

(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker30.log &)
(exec gridlabd -D SCHED_PATH=$SCHED_PATH -D INV_MODE=CONSTANT_PF -D USE_HELICS inv30.glm &> gridlabd30.log &)
(exec helics_player --input=prices.player --local --time_units=ns --stop 172800s &> player30.log &)
(exec python3 -c "import tesp_support.original.precool as tesp;tesp.precool_loop(48, 'inv30', 'inv30', helicsConfig='inv30_precool.json')" &> precool30.log &)
