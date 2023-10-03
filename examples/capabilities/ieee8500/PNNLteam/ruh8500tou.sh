#!/bin/bash

# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: ruh85000tou.sh

(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker8500_tou.log &)
(exec gridlabd  -D USE_HELICS -D INV_MODE=CONSTANT_PF -D METRICS_ROOT=inv8500_tou inv8500.glm &> gridlabd8500_tou.log &)
(exec helics_player prices.player -n player --local --time_units=ns --stop 86400s &> player8500_tou.log &)
(exec python3 -c "import tesp_support.original.precool as tesp;tesp.precool_loop(24, 'inv8500_tou', 'inv8500', response='Price', helicsConfig='inv8500_precool.json')" &> precool8500_tou.log &)
