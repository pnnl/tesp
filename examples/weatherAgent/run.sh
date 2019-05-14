#!/bin/bash
(export FNCS_TRACE=yes && export FNCS_LOG_STDOUT=yes && exec fncs_broker 3 &> broker.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec gridlabd weatherTester.glm &> gridlabd.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 1d tracer.out &> tracer.log &)
(export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && export WEATHER_CONFIG=WeatherConfig.json && exec python3 weatherAgentTest.py weather.dat &> weather.log &)

