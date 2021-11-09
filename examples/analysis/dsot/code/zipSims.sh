# !/bin/bash

# if you have to remount the dsot share drive
#sudo mount -t cifs //pnnlfs07.pnl.gov/sharedata09$/DSOT  /mnt/dsot -o username=d3j331

# this script will copy results from eioc host(boomer,tapteal...) /mnt/simdata/done/[tesp version]/[case]/ 
# to the pnl share drive \\pnl\projects\DSOT\run_outputs\DER\[tesp version]\zip\

share="/mnt/dsot/run_outputs/DER"

for dir in $1*
do
  if [ -d "$dir" ]
  then
    FILE=$dir/tesp_version
    if [ -f "$FILE" ]
    then
      target=$share/$(cat $FILE)/zip
      echo "Zip simulation" $dir "to" $target
      sudo mkdir -p $target
      sudo zip -r -9 -q $target/$dir.zip $dir
    fi
  fi
done
