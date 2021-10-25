# !/bin/bash

for dir in $1*
do
  if [ -d "$dir" ]
  then
    FILE=$dir/docker_id
    if [ -f "$FILE" ]
    then
      id=$(cat $FILE)
      echo "Stopping simulation" $dir ", docker container id" $id
      docker stop $id
    fi
  fi
done
