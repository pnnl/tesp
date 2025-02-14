#!/bin/bash

if [[ -z ${SIM_DATA} ]]; then
  echo "Mounting point for sims has not been run!"
  echo "Edit 'mount.sh' in this files directory and"
  echo "then run './mount.sh' in that same directory"
  exit
fi

echo "This script will unzip the case results from command line argument"
echo "and then run post processing code after that the shell will zip the"
echo "post processing results to $SIM_DATA/post and then remove the case"

target_data=$SIM_DATA/data

if [ -f "$target_data/$1.zip" ]
then
  hostname > "$target_data/$(hostname).log"
  echo "Running $1" >> "$target_data/$(hostname).log"
  echo "Running $1"
  #yes | cp -rf "$target_data/$1" .
  echo "$target_data/$1.zip"
  yes | unzip -q "$target_data/$1.zip"
  sed -i "s:./clean.sh; ./run.sh; ./monitor.sh:./postprocess.sh:g" "$1/docker-run.sh"
  sudo chown -R $USER:sim_group ../../*
  cd "$1" || exit
  ./docker-run.sh
else
  echo "$target_data/$1.zip is not file!"
fi