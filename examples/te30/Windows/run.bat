set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=
set FNCS_TRACE=no
set FNCS_TIME_DELTA=

set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 6 ^>broker.log 2^>^&1

rem set FNCS_LOG_LEVEL=
set FNCS_CONFIG_FILE=eplus.yaml
start /b cmd /c energyplus -w ../../support/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../../support/energyplus/SchoolDualController.idf ^>eplus.log 2^>^&1

set FNCS_CONFIG_FILE=eplus_json.yaml
start /b cmd /c eplus_json 2d 5m SchoolDualController eplus_TE_Challenge_metrics.json ^>eplus_json.log 2^>^&1

set FNCS_CONFIG_FILE=pypower30.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.pypower_loop('te30_pp.json','TE_Challenge')" ^>pypower.log 2^>^&1

set FNCS_CONFIG_FILE=TE_Challenge_substation.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.substation_loop('TE_Challenge_agent_dict.json','TE_Challenge')" ^>substation.log 2^>^&1

set FNCS_CONFIG_FILE=
set WEATHER_CONFIG=TE_Challenge_Weather_Config.json
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.startWeatherAgent('weather.dat')" ^>weather.log 2^>^&1

set WEATHER_CONFIG=
set FNCS_CONFIG_FILE=
set FNCS_LOG_LEVEL=
set FNCS_LOG_STDOUT=yes
start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=TE_Challenge_metrics.json TE_Challenge.glm ^>gridlabd.log 2^>^&1 

