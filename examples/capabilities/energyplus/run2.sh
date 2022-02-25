#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run2.sh

declare -r EPLUS_PATH=$TESPDIR/data/energyplus
declare -r TMY_PATH=$TESPDIR/data/weather

#python3 -c "import tesp_support.api as tesp;tesp.merge_idf('$EPLUS_PATH/FullServiceRestaurant.idf','$EPLUS_PATH/ems/emsFullServiceRestaurant.idf', '2013-01-03 00:00:00', '2013-01-05 00:00:00', 'Merged.idf', '12')"
#python3 -c "import tesp_support.api as tesp;tesp.merge_idf('$EPLUS_PATH/FullServiceRestaurant.idf','$EPLUS_PATH/ems/emsFullServiceRestaurant.idf', '2013-07-01 00:00:00', '2013-07-03 00:00:00', 'Merged.idf', '12')"

#python3 -c "import tesp_support.api as tesp;tesp.merge_idf('SchoolBase.idf','./forSchoolBase/emsSchoolBase.idf', '2013-01-03 00:00:00', '2013-01-05 00:00:00', 'Merged.idf', '12')"
python3 -c "import tesp_support.api as tesp;tesp.merge_idf('SchoolBase.idf','./forSchoolBase/emsSchoolBase.idf', '2013-07-01 00:00:00', '2013-07-03 00:00:00', 'Merged.idf', '12')"

TMY3toTMY2_ansi $TMY_PATH/TX-Houston_Bush_Intercontinental.tmy3 > Test.tmy2
python3 -c "import tesp_support.api as tesp;tesp.convert_tmy2_to_epw('Test')"

(export FNCS_LOG_STDOUT=yes && exec fncs_broker 4 &> broker.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w Test.epw -d output Merged.idf &> eplus.log &)
(export FNCS_LOG_STDOUT=yes && exec fncs_player 2d prices.txt &> player.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=eplus_agent.yaml && exec eplus_agent 2d 5m SchoolDualController eplus_eplus_metrics.json  0.10 25 4 4 &> eplus_agent.log &)
(export FNCS_LOG_STDOUT=yes && export FNCS_CONFIG_FILE=tracer.yaml && exec fncs_tracer 2d tracer.out &> tracer.log &)
