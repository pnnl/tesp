#!/bin/bash

mkdir -p PyomoTempFiles

# To run agents set with_market=1 else set with_market=0
with_market=1

#(exec python3 -c "import tesp_support.api.schedule_server as tesp;tesp.schedule_server('../../data/8_schedule_server_metadata.json', 5150)" &> ./schedule.log &)
# wait schedule server to populate
#sleep 60
(helics_broker -f 2 --loglevel=warning --name=mainbroker &> ./broker.log &)
cd weather_Substation_1
(export WEATHER_CONFIG=weather_Config.json && exec python3 -c "import tesp_support.weather.weather_agent as tesp;tesp.startWeatherAgent('weather.dat')" &> ./weather_Substation_1_weather.log &)
cd ..
cd Substation_1
(gridlabd -D USE_HELICS -D METRICS_FILE="./Substation_1_metrics_" Substation_1.glm &> ./Substation_1_gridlabd.log &)
cd ..
#cd DSO_1
#(exec python3 -c "import tesp_support.dsot.substation as tesp;tesp.dso_loop('Substation_1',$with_market)" &> ./DSO_1_substation.log &)
#cd ..
#(exec python3 -c "import tesp_support.api.tso_psst as tesp;tesp.tso_psst_loop('./generate_case_config')" &> ./tso.log &)
#(exec python3 -c "import tesp_support.api.player as tesp;tesp.load_player_loop('./generate_case_config', 'genMn')" &> ./gen_player.log &)
#(exec python3 -c "import tesp_support.api.player as tesp;tesp.load_player_loop('./generate_case_config', 'genForecastHr')" &> ./alt_player.log &)
#(exec python3 -c "import tesp_support.api.player as tesp;tesp.load_player_loop('./generate_case_config', 'indLoad')" &> ./ind_player.log &)
#(exec python3 -c "import tesp_support.api.player as tesp;tesp.load_player_loop('./generate_case_config', 'gldLoad')" &> ./gld_player.log &)
#(exec python3 -c "import tesp_support.api.player as tesp;tesp.load_player_loop('./generate_case_config', 'refLoadMn')" &> ./ref_player.log &)
