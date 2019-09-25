#!/bin/bash
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 5 &> broker.log &)
(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w ../../support/EnergyPlus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../../support/energyplus/SchoolDualController.idf &> eplus1d.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m SchoolDualController eplus_SGIP1d_metrics.json &> eplus_json1d.log &)
(export FNCS_FATAL=YES && exec gridlabd -D USE_FNCS -D METRICS_FILE=SGIP1d_metrics.json SGIP1d.glm &> gridlabd1d.log &)
(export FNCS_CONFIG_FILE=SGIP1d_substation.yaml && export FNCS_FATAL=YES && exec python3 -c "import tesp_support.api as tesp;tesp.substation_loop('SGIP1d_agent_dict.json','SGIP1d')" &> substation1d.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=YES && export FNCS_LOG_STDOUT=yes && exec python3 -c "import tesp_support.api as tesp;tesp.pypower_loop('sgip1_pp.json','SGIP1d')" &> pypower1d.log &)

