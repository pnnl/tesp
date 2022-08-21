#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: ruh8500volt.sh

(exec helics_broker -f 3 --loglevel=warning --name=mainbroker &> broker8500_volt.log &)
(exec gridlabd  -D USE_HELICS -D INV_MODE=CONSTANT_PF -D METRICS_ROOT=inv8500_volt inv8500.glm &> gridlabd8500_volt.log &)
(exec helics_player --input=prices.player --local --time_units=ns --stop 86400s &> player8500_volt.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.precool_loop(24, 'inv8500_volt', 'inv8500', response='Voltage', helicsConfig='inv8500_precool.json')" &> precool8500_volt.log &)
