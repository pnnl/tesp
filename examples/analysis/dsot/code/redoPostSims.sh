#!/bin/bash

if [[ -z ${SIM_DATA} ]]; then
  echo "Mounting point for sims has not been run!"
  echo "Edit 'mount.sh' in this files directory and"
  echo "then run './mount.sh' in that same directory"
  exit
fi

echo "This script will unzip the results from $1 case(s) to current directory"
echo "and then run post processing code after that the shell will zip the"
echo "post processing results to $SIM_DATA/post and then remove the case(s)"

target_data="$SIM_DATA/data"
target_post="$SIM_DATA/post"

for j in 04; do
  d1=8_2016_$j\_pv_bt_fl_ev

  unzip -q "$target_data/$d1.zip"
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
