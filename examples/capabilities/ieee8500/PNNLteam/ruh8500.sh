#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: ruh8500.sh

(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker8500.log &)
(exec gridlabd  -D USE_HELICS -D INV_MODE=CONSTANT_PF -D METRICS_ROOT=inv8500 inv8500.glm &> gridlabd8500.log &)
(exec helics_player --input=prices.player --local --time_units=ns --stop 86400s &> player8500.log &)
(exec python3 -c "import tesp_support.original.precool as tesp;tesp.precool_loop(24, 'inv8500', 'inv8500', response='PriceVoltage', helicsConfig='inv8500_precool.json')" &> precool8500.log &)
