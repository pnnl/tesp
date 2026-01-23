#!/bin/bash

if [[ -z ${SIM_DATA} ]]; then
  echo "Mounting point for sims has not been set!"
  echo "  Edit 'sim_data' in this files directory and"
  echo "  run 'source sim_data' in that same directory."
  exit
fi

echo "This script will copy $1 case(s) to"
echo "  $SIM_DATA/cases"

# change the ready folder
target_cases=$SIM_DATA/cases

# cd to directory where the cases
for dir in $1*
do
  if [ -d "$dir" ]
  then
#    FILE=$dir/tso.yaml
    FILE=$dir/tso_h.json
    if [ -f "$FILE" ]
    then
      echo "Submit simulation $dir"
      rm -rf "$target_cases/$dir"
      cp -r "$dir" "$target_cases"
      rm -rf "$dir"
    fi
  fi
done
