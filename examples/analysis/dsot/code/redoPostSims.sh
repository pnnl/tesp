#!/bin/bash

#sudo mount -t cifs -o file_mode=0777,dir_mode=0777,username=?,password=? //pnnlfs09.pnl.gov/sharedata37_op$/DSOT  /mnt/dsot
#sudo mount -t cifs -o file_mode=0777,dir_mode=0777,username=?,password=? //pnnlfs09.pnl.gov/sharedata13_op$/TSP_Rates  /mnt/post

# sub="dsot"
# sub="flat-rate"
sub="time-of-use"
# sub="rob-don"
share="/mnt/dsot/run_outputs/Rates_Scenario/$sub"
target_post="/mnt/post/Rates_Scenario/$sub/post"

for j in 04; do
  d1=8_2016_$j\_pv_bt_fl_ev

  unzip -q "$share/$d1.zip"
  cd "$d1" || exit
#  python3 ../run_case_postprocessing.py > postprocessing.log
  cd .. || exit

  for i in 1 2 3 4 5 6 7 8; do
    echo "$target_post/$d1.zip" $d1/Substation_$i/*_baseline_demand*.h5
    zip "$target_post/$d1.zip" $d1/Substation_$i/*_baseline_demand*.h5
  done

#  rm -rf $d1
done
#
#hostname > "$sims/$(hostname).log"
#echo "Running $1" >> "$sims/$(hostname).log"
#dir=$(basename "$1")
#echo "Running $dir"
#hostname > "$1/hostname"
#yes | cp -rf "$1" .
#sed -i "s:./clean.sh; ./run.sh; ./monitor.sh:./postprocess.sh:g" "$dir/docker-run.sh"
#sudo chown -R $usr:sim_group ../../*
#cd "$dir" || exit
#./docker-run.sh
