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
cd ../../ercot/case8
./clean.sh
rm *.glm
cd $CWD
