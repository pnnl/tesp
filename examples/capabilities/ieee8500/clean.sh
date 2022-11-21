rm -f *.out
rm -f *.log
rm -f *.xml
rm -f *.json
rm -f bill.csv
git checkout climate.csv &> /dev/null
git checkout house_*.csv &> /dev/null
git checkout main_regulator.csv &> /dev/null
git checkout substation_load.csv &> /dev/null
cd PNNLteam || exit
./clean.sh
cd ..