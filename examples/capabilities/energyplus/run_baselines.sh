#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: run_baselines.sh

declare -r EPLUS_PATH=$TESPDIR/data/energyplus

energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outSchoolBase SchoolBase.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outFullServiceRestaurant $EPLUS_PATH/FullServiceRestaurant.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outHospital $EPLUS_PATH/Hospital.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outLargeHotel $EPLUS_PATH/LargeHotel.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outLargeOffice $EPLUS_PATH/LargeOffice.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outMediumOffice $EPLUS_PATH/MediumOffice.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outMidriseApartment $EPLUS_PATH/MidriseApartment.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outOutPatient $EPLUS_PATH/OutPatient.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outPrimarySchool $EPLUS_PATH/PrimarySchool.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outQuickServiceRestaurant $EPLUS_PATH/QuickServiceRestaurant.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outSecondarySchool $EPLUS_PATH/SecondarySchool.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outSmallHotel $EPLUS_PATH/SmallHotel.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outSmallOffice $EPLUS_PATH/SmallOffice.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outStandaloneRetail $EPLUS_PATH/StandaloneRetail.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outStripMall $EPLUS_PATH/StripMall.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outSuperMarket $EPLUS_PATH/SuperMarket.idf
energyplus -w $EPLUS_PATH/2A_USA_TX_HOUSTON.epw -d outWarehouse $EPLUS_PATH/Warehouse.idf
