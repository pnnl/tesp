declare -r TESP_SUPPORT=$TESP_INSTALL/share/support/energyplus
#declare -r TESP_SUPPORT=../../support/energyplus

energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSchoolBase -r SchoolBase.idf

energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outFullServiceRestaurant -r $TESP_SUPPORT/FullServiceRestaurant.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outHospital -r $TESP_SUPPORT/Hospital.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outLargeHotel -r $TESP_SUPPORT/LargeHotel.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outLargeOffice -r $TESP_SUPPORT/LargeOffice.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outMediumOffice -r $TESP_SUPPORT/MediumOffice.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outMidriseApartment -r $TESP_SUPPORT/MidriseApartment.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outOutPatient -r $TESP_SUPPORT/OutPatient.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outPrimarySchool -r $TESP_SUPPORT/PrimarySchool.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outQuickServiceRestaurant -r $TESP_SUPPORT/QuickServiceRestaurant.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSecondarySchool -r $TESP_SUPPORT/SecondarySchool.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSmallHotel -r $TESP_SUPPORT/SmallHotel.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSmallOffice -r $TESP_SUPPORT/SmallOffice.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outStandaloneRetail -r $TESP_SUPPORT/StandaloneRetail.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outStripMall -r $TESP_SUPPORT/StripMall.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSuperMarket -r $TESP_SUPPORT/SuperMarket.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outWarehouse -r $TESP_SUPPORT/Warehouse.idf

