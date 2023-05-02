#!/bin/bash

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: make_all_ems.sh

declare -r EPLUS_PATH=$TESPDIR/data/energyplus
declare -r EPLUS_OUTDIR=.
declare -r FOR_HELICS=$1

python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outFullServiceRestaurant','$EPLUS_PATH/FullServiceRestaurant.idf','emsFullServiceRestaurant.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outHospital','$EPLUS_PATH/Hospital.idf','emsHospital.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outLargeHotel','$EPLUS_PATH/LargeHotel.idf','emsLargeHotel.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outLargeOffice','$EPLUS_PATH/LargeOffice.idf','emsLargeOffice.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outMediumOffice','$EPLUS_PATH/MediumOffice.idf','emsMediumOffice.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outMidriseApartment','$EPLUS_PATH/MidriseApartment.idf','emsMidriseApartment.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outOutPatient','$EPLUS_PATH/OutPatient.idf','emsOutPatient.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outPrimarySchool','$EPLUS_PATH/PrimarySchool.idf','emsPrimarySchool.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outQuickServiceRestaurant','$EPLUS_PATH/QuickServiceRestaurant.idf','emsQuickServiceRestaurant.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outSecondarySchool','$EPLUS_PATH/SecondarySchool.idf','emsSecondarySchool.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outSmallHotel','$EPLUS_PATH/SmallHotel.idf','emsSmallHotel.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outSmallOffice','$EPLUS_PATH/SmallOffice.idf','emsSmallOffice.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outStandaloneRetail','$EPLUS_PATH/StandaloneRetail.idf','emsStandaloneRetail.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outStripMall','$EPLUS_PATH/StripMall.idf','emsStripMall.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outSuperMarket','$EPLUS_PATH/SuperMarket.idf','emsSuperMarket.idf',bHELICS=$FOR_HELICS)"
python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('$EPLUS_OUTDIR/outWarehouse','$EPLUS_PATH/Warehouse.idf','emsWarehouse.idf',bHELICS=$FOR_HELICS)"

python3 -c "import tesp_support.api.make_ems as tesp;tesp.make_ems('./forSchoolBase','SchoolBase.idf','emsSchoolBase.idf',bHELICS=$FOR_HELICS)"

