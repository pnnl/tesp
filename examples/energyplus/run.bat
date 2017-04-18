set FNCS_FATAL=NO
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=DEBUG4

set FNCS_CONFIG_FILE
start /b cmd /c fncs_broker 4 ^>broker.log 2^>^&1

set FNCS_CONFIG_FILE=eplus.yaml
start /b cmd /c energyplus -w USA_IN_Indianapolis.Intl.AP.724380_TMY3.epw -d output -r SchoolDualController.idf ^>eplus.log 2^>^&1

set FNCS_CONFIG_FILE
start /b cmd /c fncs_player 1d prices.txt ^>player.log 2^>^&1

set FNCS_CONFIG_FILE=eplus_json.yaml
start /b cmd /c eplus_json 1d 5m School_DualController eplus.json ^>eplus_json.log 2^>^&1

set FNCS_CONFIG_FILE=tracer.yaml
start /b cmd /c fncs_tracer 1d tracer.out ^>tracer.log 2^>^&1

