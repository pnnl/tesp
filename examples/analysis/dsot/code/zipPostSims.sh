#!/bin/bash

if [[ -z ${SIM_DATA} ]]; then
  echo "Mounting point for sims has not been set!"
  echo "  Edit 'sim_data' in this files directory and"
  echo "  run 'source sim_data' in that same directory."
  exit
fi

echo "This script will zip the results from $1 case(s) to"
echo "  $SIM_DATA/data"
echo "and will zip the post processing results in another from $1 case(s) to"
echo "  $SIM_DATA/post"

for dir in "$1"*
do
  if [ -d "$dir" ]
  then
    FILE=$dir/tesp_version
    FILE=$dir/docker_id
    if [ -f "$FILE" ]
    then
      echo "$(cat "$FILE")"
      target_data=$SIM_DATA/data
      target_post=$SIM_DATA/post
      echo "Zip simulation $dir to target_data"
      sudo mkdir -p "$target_data"
      sudo mkdir -p "$target_post"

      # remove Pyomo temperary files
      sudo rm -rf $dir/Pyomo*

      sudo zip -r "$target_post/$dir.zip" \
        $dir/plots $dir/*csv $dir/*log $dir/*json $dir/*h5 ./$FILE

      for i in 1 2 3 4 5 6 7 8; do
        sudo zip "$target_post/$dir.zip" \
          $dir/Substation_$i/*_baseline_demand*.h5 \
          $dir/Substation_$i/*profiles.h5 \
          $dir/Substation_$i/*amenity_log.csv \
          $dir/Substation_$i/*_data* \
          $dir/DSO_$i/*_dict.*
      done
      sudo zip -r -9 -q "$target_data/$dir.zip" "$dir"
    fi
  fi
done
