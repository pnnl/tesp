set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
rem set FNCS_LOG_LEVEL=DEBUG2
rem set FNCS_TRACE=yes
set FNCS_TIME_DELTA=

set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 5 ^>broker1ex.log 2^>^&1

set FNCS_CONFIG_FILE=eplus.yaml
start /b cmd /c energyplus -w ../../support/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../../support/energyplus/SchoolDualController.idf ^>eplus1ex.log 2^>^&1

set FNCS_CONFIG_FILE=eplus_json.yaml
start /b cmd /c eplus_json 2d 5m SchoolDualController eplus_SGIP1ex_metrics.json ^>eplus_json1ex.log 2^>^&1

set FNCS_CONFIG_FILE=pypower.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.pypower_loop('sgip1_pp.json','SGIP1ex')" ^>pypower1ex.log 2^>^&1

set FNCS_CONFIG_FILE=
start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=SGIP1ex_metrics.json SGIP1e.glm ^>gridlabd1ex.log 2^>^&1 

set FNCS_CONFIG_FILE=SGIP1e_substation.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.substation_loop('SGIP1e_agent_dict.json','SGIP1ex',flag='NoMarket')" ^>substation1ex.log 2^>^&1

