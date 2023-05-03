#!/bin/bash
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: runcombinedh.sh

(exec helics_broker -f 4 --loglevel=warning --name=mainbroker &> broker.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=CombinedCaseH_metrics.json CombinedCase.glm &> gld_7.log &)
(exec python3 -c "import tesp_support.original.substation as tesp;tesp.substation_loop('CombinedCase_agent_dict.json','CombinedCaseH',helicsConfig='CombinedCase_substation.json')"  &> sub_7.log &)
(exec python3 -c "import tesp_support.api.tso_PYPOWER as tesp;tesp.tso_pypower_loop('Feeder1_pp.json','CombinedCaseH',helicsConfig='pypower.json')"  &> pypower.log &)
(export WEATHER_CONFIG=Feeder1_weather.json && exec python3 -c "import tesp_support.api.weather_agent as tesp;tesp.startWeatherAgent('weather.dat')"  &> weather.log &)
