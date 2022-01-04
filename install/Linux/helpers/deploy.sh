# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: deploy.sh

cp ../../../LICENSE /opt/tesp
cp ../../../autotest.py /opt/tesp/share
cp ../../../autotest_long.py /opt/tesp/share
cp environment /opt/tesp/share
cp tesp_ld.conf /opt/tesp/share
cp tesp_envar.sh /opt/tesp/share
cp provision.sh /opt/tesp/share
cp gitclone.sh /opt/tesp/share
cp make_tesp_user_dir.sh /opt/tesp/bin
cp tesp_to_current_dir.sh /opt/tesp/bin
cp ../../../../CIMHub/distrib/opendsscmd /opt/tesp/bin
cp ../../../../CIMHub/distrib/liblinenoise.so /opt/tesp/lib
cp ../../../../CIMHub/distrib/libklusolve.so /opt/tesp/lib
cp ../../../../fncs/java/fncs.jar /opt/tesp/java
cp ../../../../fncs/java/fncs.jar /opt/tesp/java
./deploy_ercot.sh
./deploy_examples.sh
./deploy_support.sh

