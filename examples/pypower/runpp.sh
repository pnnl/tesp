#!/bin/bash
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 2 &> broker.log &)
(export FNCS_CONFIG_FILE=pptracer.yaml && exec fncs_tracer 2d pptracer.out &> pptracer.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python -c "import tesp_support.api as tesp;tesp.pypower_loop('ppcase.json','ppcase')" &> pypower.log &)
