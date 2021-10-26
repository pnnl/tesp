declare -r CWD=$pwd
cd ../../../examples/loadshed
./clean.sh
make clean
cd ../energyplus
./clean.sh
cd ../te30
./clean.sh
cd ../pypower
./clean.sh
cd ../sgip1
./clean.sh
cd ../weatherAgent
./clean.sh
cd ../ieee8500
./clean.sh
cd PNNLteam
./clean.sh
cd ../../comm
rm -rf CombinedCase
rm -rf Nocomm_Base
rm -rf Eplus_Restaurant
rm -rf SummerTest
rm -rf Eplus_Comm
cd ../../ercot/case8
./clean.sh
rm -f *.glm
cd dsostub
./clean.sh
cd ../../bulk_system
./clean.sh
cd ../dist_system
./clean.sh
cd $CWD
