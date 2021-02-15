set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=
set FNCS_TRACE=no
set FNCS_TIME_DELTA=

set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 9 ^>broker.log 2^>^&1

start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=Bus1_metrics.json Bus1.glm ^>Bus1.log 2^>^&1 

start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=Bus2_metrics.json Bus2.glm ^>Bus2.log 2^>^&1

start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=Bus3_metrics.json Bus3.glm ^>Bus3.log 2^>^&1

start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=Bus4_metrics.json Bus4.glm ^>Bus4.log 2^>^&1 

start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=Bus5_metrics.json Bus5.glm ^>Bus5.log 2^>^&1 

start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=Bus6_metrics.json Bus6.glm ^>Bus6.log 2^>^&1 

start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=Bus7_metrics.json Bus7.glm ^>Bus7.log 2^>^&1

start /b cmd /c gridlabd -D USE_FNCS -D METRICS_FILE=Bus8_metrics.json Bus8.glm ^>Bus8.log 2^>^&1 

set FNCS_CONFIG_FILE=tso8.yaml
start /b cmd /c python fncsTSO.py ^>bulk.log 2^>^&1
