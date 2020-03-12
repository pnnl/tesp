declare -r CWD=$pwd
cd ../../../examples/loadshed
./clean.sh
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
cd $CWD
