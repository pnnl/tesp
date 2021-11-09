#!/bin/bash

EPLUS_PATH=$TESPDIR/data/energyplus

cp $EPLUS_PATH/emsHELICS/*.idf .

./run_seasonal_cases.sh "FullServiceRestaurant"
./run_seasonal_cases.sh "Hospital"
./run_seasonal_cases.sh "LargeHotel"
./run_seasonal_cases.sh "LargeOffice"
./run_seasonal_cases.sh "MediumOffice"
./run_seasonal_cases.sh "MidriseApartment"
./run_seasonal_cases.sh "OutPatient"
./run_seasonal_cases.sh "PrimarySchool"
./run_seasonal_cases.sh "QuickServiceRestaurant"
./run_seasonal_cases.sh "SecondarySchool"
./run_seasonal_cases.sh "SmallHotel"
./run_seasonal_cases.sh "SmallOffice"
./run_seasonal_cases.sh "StandaloneRetail"
./run_seasonal_cases.sh "StripMall"
./run_seasonal_cases.sh "SuperMarket"
./run_seasonal_cases.sh "Warehouse"

#./run_seasonal_cases.sh "SchoolBase"

