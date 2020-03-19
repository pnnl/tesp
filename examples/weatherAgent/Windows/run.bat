set FNCS_FATAL=yes
set FNCS_LOG_STDOUT=yes
set FNCS_LOG_LEVEL=DEBUG2
set FNCS_TRACE=yes

set FNCS_CONFIG_FILE=
start /b cmd /c fncs_broker 3 ^>broker.log 2^>^&1

set FNCS_CONFIG_FILE=tracer.yaml
start /b cmd /c fncs_tracer 1d tracer.out ^>tracer.log 2^>^&1
set FNCS_CONFIG_FILE=

start /b cmd /c gridlabd weatherTester.glm ^>gridlabd.log 2^>^&1

set WEATHER_CONFIG=WeatherConfig.json
start /b cmd /c python weatherAgentTest.py weather.dat ^>weather.log 2^>^&1

