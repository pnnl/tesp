#!/bin/bash

if [[ -z ${SIM_DATA} ]]; then
  echo "Mounting point for sims has not been set!"
  echo "  Edit 'sim_data' in this files directory and"
  echo "  run 'source sim_data' in that same directory."
  exit
fi

#max minus one dockers can run
max=2
target_cases="$SIM_DATA/cases"

hostname > "$target_cases/$(hostname).log"

#while true
#do
  for dir in $target_cases/$1*
  do
    if [ -d "$dir" ]
    then
      case_name=$(basename $dir)
      cnt=$(docker ps --filter "name=$1" | wc -l)
      if [ $cnt -lt $max ]
      then
        FILE=$dir/hostname
        if [ -f "$FILE" ]
        then
          echo "Taken $dir" >> "$target_cases/$(hostname).log"
        else
          echo "Running $dir" >> "$target_cases/$(hostname).log"
          echo "Running $(basename $dir)"
          hostname > $dir/hostname
          yes | cp -rf $dir .
          cd "$(basename $dir)" || exit
          sed -i "s:--rm:--rm --name $case_name:g" "docker-run.sh"
          ./docker-run.sh
          cd ..
        fi
      else
        echo "Passing $dir" >> "$target_cases/$(hostname).log"
#        sleep 5m
      fi
    fi
  done
#  echo "Sleep Sims" >> "$target_cases/$(hostname).log"
#  sleep 15m
#done
