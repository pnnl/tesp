#!/bin/bash

#max minus one dockers can run
max=3
usr="oste814"
sims="/mnt/simdata/ready"

hostname > $sims/$(hostname).log

#while true
#do
  for dir in $sims/$1*
  do
    if [ -d "$dir" ]
    then
      cnt=$(docker ps -a | wc -l)
      if [ $cnt -lt $max ]
      then
        FILE=$dir/hostname
        if [ -f "$FILE" ]
        then
          echo "Taken" $dir >> $sims/$(hostname).log
#          rm $FILE
        else
          echo "Running" $dir >> $sims/$(hostname).log
          echo "Running" $(basename $dir)
          hostname > $dir/hostname
          yes | cp -rf $dir .
#          rm -rf $sims/$dir
          sudo chown -R $usr:sim_group ../../*
          cd $(basename $dir)
          ./docker-run.sh
          cd ..
        fi
      else
        echo "Passing" $dir >> $sims/$(hostname).log
#        sleep 5m
      fi
    fi
  done
#  echo "Sleep Sims" >> $sims/$(hostname).log
#  sleep 15m
#done
