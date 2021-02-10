set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=
set FNCS_TRACE=no
set FNCS_TIME_DELTA=

set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 3 ^>broker30.log 2^>^&1
start /b cmd /c fncs_player 48h prices.player ^>player30.log 2^>^&1

set FNCS_CONFIG_FILE=inv30_precool.yaml
start /b cmd /c python -c "import tesp_support.api as tesp;tesp.precool_loop(48,'inv30')" ^>precool30.log 2^>^&1

set FNCS_CONFIG_FILE=
set FNCS_LOG_LEVEL=
set FNCS_LOG_STDOUT=yes
start /b cmd /c gridlabd -D USE_FNCS inv30.glm ^>gridlabd30.log 2^>^&1 

