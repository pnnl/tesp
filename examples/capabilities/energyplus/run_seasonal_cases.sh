#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run_seasonal_cases.sh

EPLUS_PATH=$TESPDIR/data/energyplus
EPWFILE=$EPLUS_PATH/2A_USA_TX_HOUSTON.epw

declare -r WINTER_START="2013-01-03 00:00:00"
declare -r WINTER_END="2013-01-05 00:00:00"
declare -r SUMMER_START="2013-08-01 00:00:00"
declare -r SUMMER_END="2013-08-03 00:00:00"
declare -r BUILDING=$1

python3 -c "import tesp_support.api as tesp;tesp.merge_idf('$EPLUS_PATH/$BUILDING.idf','ems$BUILDING.idf', '$SUMMER_START', '$SUMMER_END', 'Summer$BUILDING.idf', '12')"
python3 -c "import tesp_support.api as tesp;tesp.merge_idf('$EPLUS_PATH/$BUILDING.idf','ems$BUILDING.idf', '$WINTER_START', '$WINTER_END', 'Winter$BUILDING.idf', '12')"

./run_ems_case.sh "Winter$BUILDING" "Winter_Mkt_$BUILDING" "50" "6" "$EPWFILE"
./run_ems_case.sh "Summer$BUILDING" "Summer_Mkt_$BUILDING" "50" "6" "$EPWFILE"
./run_ems_case.sh "Winter$BUILDING" "Winter_NoMkt_$BUILDING" "0.01" "0.01" "$EPWFILE"
./run_ems_case.sh "Summer$BUILDING" "Summer_NoMkt_$BUILDING" "0.01" "0.01" "$EPWFILE"

