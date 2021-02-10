declare -r TESP_SUPPORT=$TESP_INSTALL/share/support/energyplus
#declare -r TESP_SUPPORT=../../support/energyplus

energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSchoolBase SchoolBase.idf

energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outFullServiceRestaurant $TESP_SUPPORT/FullServiceRestaurant.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outHospital $TESP_SUPPORT/Hospital.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outLargeHotel $TESP_SUPPORT/LargeHotel.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outLargeOffice $TESP_SUPPORT/LargeOffice.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outMediumOffice $TESP_SUPPORT/MediumOffice.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outMidriseApartment $TESP_SUPPORT/MidriseApartment.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outOutPatient $TESP_SUPPORT/OutPatient.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outPrimarySchool $TESP_SUPPORT/PrimarySchool.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outQuickServiceRestaurant $TESP_SUPPORT/QuickServiceRestaurant.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSecondarySchool $TESP_SUPPORT/SecondarySchool.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSmallHotel $TESP_SUPPORT/SmallHotel.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSmallOffice $TESP_SUPPORT/SmallOffice.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outStandaloneRetail $TESP_SUPPORT/StandaloneRetail.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outStripMall $TESP_SUPPORT/StripMall.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outSuperMarket $TESP_SUPPORT/SuperMarket.idf
energyplus -w $TESP_SUPPORT/2A_USA_TX_HOUSTON.epw -d outWarehouse $TESP_SUPPORT/Warehouse.idf

