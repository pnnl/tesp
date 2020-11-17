declare -r TESP_SUPPORT=$TESP_INSTALL/share/support/energyplus
declare -r EPLUS_OUTDIR=$HOME/tesp_working/examples/energyplus

#declare -r TESP_SUPPORT=../../support/energyplus
#declare -r EPLUS_OUTDIR=.

declare -r FOR_HELICS=True

python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outFullServiceRestaurant','$TESP_SUPPORT/FullServiceRestaurant.idf','emsFullServiceRestaurant.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outHospital','$TESP_SUPPORT/Hospital.idf','emsHospital.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outLargeHotel','$TESP_SUPPORT/LargeHotel.idf','emsLargeHotel.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outLargeOffice','$TESP_SUPPORT/LargeOffice.idf','emsLargeOffice.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outMediumOffice','$TESP_SUPPORT/MediumOffice.idf','emsMediumOffice.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outMidriseApartment','$TESP_SUPPORT/MidriseApartment.idf','emsMidriseApartment.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outOutPatient','$TESP_SUPPORT/OutPatient.idf','emsOutPatient.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outPrimarySchool','$TESP_SUPPORT/PrimarySchool.idf','emsPrimarySchool.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outQuickServiceRestaurant','$TESP_SUPPORT/QuickServiceRestaurant.idf','emsQuickServiceRestaurant.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outSecondarySchool','$TESP_SUPPORT/SecondarySchool.idf','emsSecondarySchool.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outSmallHotel','$TESP_SUPPORT/SmallHotel.idf','emsSmallHotel.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outSmallOffice','$TESP_SUPPORT/SmallOffice.idf','emsSmallOffice.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outStandaloneRetail','$TESP_SUPPORT/StandaloneRetail.idf','emsStandaloneRetail.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outStripMall','$TESP_SUPPORT/StripMall.idf','emsStripMall.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outSuperMarket','$TESP_SUPPORT/SuperMarket.idf','emsSuperMarket.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api as tesp;tesp.make_ems('$EPLUS_OUTDIR/outWarehouse','$TESP_SUPPORT/Warehouse.idf','emsWarehouse.idf',bHELICS=$FOR_HELICS)"

python3 -c "import tesp_support.api as tesp;tesp.make_ems('./forSchoolBase','SchoolBase.idf','emsSchoolBase.idf',bHELICS=$FOR_HELICS)"

