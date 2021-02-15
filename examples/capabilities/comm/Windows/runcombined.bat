set FNCS_FATAL=yes
set FNCS_TIME_DELTA=
set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 4 ^>broker.log 2^>^&1
set FNCS_CONFIG_FILE=
start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=CombinedCase_metrics.json CombinedCase.glm ^>gridlabd.log 2^>^&1
set FNCS_CONFIG_FILE=CombinedCase_substation.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.substation_loop('CombinedCase_agent_dict.json','CombinedCase')" ^>substation.log 2^>^&1
set FNCS_CONFIG_FILE=pypower.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.pypower_loop('Feeder1_pp.json','CombinedCase')" ^>pypower.log 2^>^&1
set FNCS_CONFIG_FILE=
set WEATHER_CONFIG=Feeder1_Weather_Config.json
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" ^>weather.log 2^>^&1
