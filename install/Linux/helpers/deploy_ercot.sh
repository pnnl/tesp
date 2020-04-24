# update contents of /opt/tesp/share/ercot
rm -rf /opt/tesp/share/ercot
mkdir /opt/tesp/share/ercot
cp ../../../ercot/*.* /opt/tesp/share/ercot

mkdir /opt/tesp/share/ercot/case8
cp ../../../ercot/case8/*.* /opt/tesp/share/ercot/case8
mkdir /opt/tesp/share/ercot/case8/dsostub
cp ../../../ercot/case8/dsostub/*.* /opt/tesp/share/ercot/case8/dsostub

mkdir /opt/tesp/share/ercot/bulk_system
cp ../../../ercot/bulk_system/*.* /opt/tesp/share/ercot/bulk_system

mkdir /opt/tesp/share/ercot/dist_system
cp ../../../ercot/dist_system/*.* /opt/tesp/share/ercot/dist_system


