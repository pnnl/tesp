set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=
set FNCS_TRACE=no
set FNCS_TIME_DELTA=

set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 5 ^>broker0.log 2^>^&1

rem set FNCS_LOG_LEVEL=
set FNCS_CONFIG_FILE=eplus.yaml
start /b cmd /c energyplus -w ../../support/energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../../support/energyplus/SchoolDualController.idf ^>eplus0.log 2^>^&1

set FNCS_CONFIG_FILE=eplus_json.yaml
start /b cmd /c eplus_json 2d 5m SchoolDualController eplus_TE_Challenge0_metrics.json ^>eplus_json0.log 2^>^&1

set FNCS_CONFIG_FILE=pypower30.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.pypower_loop('te30_pp.json','TE_Challenge0')" ^>pypower0.log 2^>^&1

set FNCS_CONFIG_FILE=TE_Challenge_auction.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.auction_loop('TE_Challenge_agent_dict.json','TE_Challenge0','NoMarket')" ^>auction0.log 2^>^&1

set FNCS_CONFIG_FILE=
set FNCS_LOG_LEVEL=
set FNCS_LOG_STDOUT=yes
start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=TE_Challenge0_metrics.json TE_Challenge.glm ^>gridlabd0.log 2^>^&1 

