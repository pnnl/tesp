#!/bin/bash

# with market
# (export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 760 &> broker.log &)
# (exec ./launch_SGIP1e_agents.sh &)

#without market
(export FNCS_BROKER="tcp://*:5570" && exec fncs_broker 6 &> broker.log &)
(export FNCS_FATAL=NO && exec gridlabd SGIP1e.glm &> gridlabd.log &)
(export FNCS_FATAL=NO && exec python double_auction.py input/auction_registration.json SGIP1e &> auction.log &)
(export FNCS_FATAL=NO && exec python house_controller.py input/controller_registration_house1_R1_12_47_1_tm_507_thermostat_controller.json &> control.log &)

# EnergyPlus and Pypower - 3 processes
(export FNCS_CONFIG_FILE=eplus.yaml && exec EnergyPlus -w ../energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../energyplus/SchoolDualController.idf &> eplus.log &)
(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m School_DualController eplus_SGIP1e_metrics.json &> eplus_json.log &)
(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py SGIP1e &> pypower.log &)

