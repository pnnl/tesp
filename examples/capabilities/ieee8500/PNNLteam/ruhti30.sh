#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: ruhti30.sh

declare -r SCHED_PATH=$TESPDIR/data/schedules

(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> brokerti30.log &)
(exec gridlabd -D SCHED_PATH=$SCHED_PATH -D INV_MODE=VOLT_VAR -D USE_HELICS invti30.glm &> gridlabdti30.log &)
(exec helics_player --input=prices.player --local --time_units=ns --stop 172800s &> playerti30.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.precool_loop(48, 'invti30', 'invti30', helicsConfig='invti30_precool.json')" &> precoolti30.log &)
