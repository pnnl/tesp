set FNCS_CONFIG_FILE=
set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=DEBUG1
rem set FNCS_TRACE=yes
start /b cmd /c fncs_broker 3 ^>broker.log 2^>^&1
start /b cmd /c gridlabd loadshed.glm ^>gridlabd.log 2^>^&1
start /b cmd /c fncs_player 6h loadshed.player ^>player.log 2^>^&1
set FNCS_CONFIG_FILE=loadshed.yaml
start /b cmd /c python loadshed.py 21600 ^>loadshed.log 2^>^&1

