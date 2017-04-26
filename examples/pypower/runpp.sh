#!/bin/bash
(export FNCS_LOG_STDOUT=yes && exec fncs_broker 2 &> ppbroker.log &)
(export FNCS_CONFIG_FILE=pptracer.yaml && exec fncs_tracer 2d pptracer.out &> pptracer.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py &> pypower.log &)

