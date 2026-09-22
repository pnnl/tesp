#!/bin/bash

if [[ -z ${SIM_DATA} ]]; then
  echo "Mounting point for sims has not been set!"
  echo "  Edit 'sim_data' in this files directory and"
  echo "  run 'source sim_data' in that same directory."
  exit
fi

echo "This script will zip the results from $1 case(s) to"
echo "  $SIM_DATA/data"

target_data="$SIM_DATA/data"

for dir in "$1"*
do
  if [ -d "$dir" ]
  then
    FILE=$dir/tesp_version
#    FILE=$dir/docker_id
    if [ -f "$FILE" ]
    then
      echo "Zip simulation $dir to $target_data"
      sudo mkdir -p "$target_data"
      sudo zip -r -9 -q "$target_data/$dir.zip" "$dir"
    fi
  fi
done
