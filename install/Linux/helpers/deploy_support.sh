# update contents of /opt/tesp/share/support
rm -rf /opt/tesp/share/support
mkdir /opt/tesp/share/support

mkdir /opt/tesp/share/support/energyplus
cp ../../../support/energyplus/*.* /opt/tesp/share/support/energyplus
mkdir /opt/tesp/share/support/energyplus/emsFNCS
cp ../../../support/energyplus/emsFNCS/*.* /opt/tesp/share/support/energyplus/emsFNCS
mkdir /opt/tesp/share/support/energyplus/emsHELICS
cp ../../../support/energyplus/emsHELICS/*.* /opt/tesp/share/support/energyplus/emsHELICS

mkdir /opt/tesp/share/support/feeders
cp ../../../support/feeders/*.* /opt/tesp/share/support/feeders

mkdir /opt/tesp/share/support/misc
cp ../../../support/misc/*.* /opt/tesp/share/support/misc

mkdir /opt/tesp/share/support/pypower
cp ../../../support/pypower/*.* /opt/tesp/share/support/pypower

mkdir /opt/tesp/share/support/schedules
cp ../../../support/schedules/*.* /opt/tesp/share/support/schedules

mkdir /opt/tesp/share/support/weather
cp ../../../support/weather/*.* /opt/tesp/share/support/weather

