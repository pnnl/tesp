#!/bin/bash

sims="/mnt/simdata/ready"

for dir in $1*
do
  if [ -d "$dir" ]
  then
    FILE=$dir/tso.yaml
    if [ -f "$FILE" ]
    then
      echo "Submit simulation" $dir
      rm -rf $sims/$dir
      cp -r $dir $sims
      rm -rf $dir
    fi
  fi
done

