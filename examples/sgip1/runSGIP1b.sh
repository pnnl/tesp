#!/bin/bash
# (export FNCS_LOG_LEVEL=DEBUG4 && export FNCS_LOG_STDOUT=yes && exec fncs_broker 36 &> broker.log &)
(exec fncs_broker 761 &> broker.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w ../energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../energyplus/SchoolDualController.idf &> eplus.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m School_DualController eplus_SGIP1b_metrics.json &> eplus_json.log &)
(export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 2d tracer.out &> tracer.log &)
(exec ./launch_SGIP1b_agents.sh &)
(export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec ./run_fncsMATPOWER.sh SGIP1b.m real_power_demand_case9_T.txt 171800 "2013-07-01 00:00:00" SGIP1b &> matpower.log &)

