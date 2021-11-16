#!/bin/bash
# Copyright (C) 2021 Battelle Memorial Institute
# file: runcombinedh.sh

(exec helics_broker -f 4 --loglevel=4 --name=mainbroker &> helics_broker.log &)
(exec gridlabd -D USE_HELICS -D METRICS_FILE=CombinedCaseH_metrics.json CombinedCase.glm &> helics_gld1.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('CombinedCase_agent_dict.json','CombinedCaseH',helicsConfig='CombinedCase_HELICS_substation.json')"  &> helics_sub1.log &)
(exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('Feeder1_pp.json','CombinedCaseH',helicsConfig='pypowerConfig.json')"  &> helics_pypower.log &)
(export WEATHER_CONFIG=Feeder1_HELICS_Weather_Config.json && exec python3 -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')"  &> helics_weather.log &)
