cp ../../../LICENSE /opt/tesp
cp ../../../autotest.py /opt/tesp/share
cp environment /opt/tesp/share
cp tesp_ld.conf /opt/tesp/share
cp provision.sh /opt/tesp/share
cp gitclone.sh /opt/tesp/share
cp make_tesp_user_dir.sh /opt/tesp/bin
cp ../../../../fncs/java/fncs.jar /opt/tesp/java
cp ../../../../fncs/java/fncs.jar /opt/tesp/java
./deploy_ercot.sh
./deploy_examples.sh
./deploy_support.sh

