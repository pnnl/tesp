#!/bin/bash

for dir in *; do
  if [ -d "$dir" ]
  then
    if [ "$dir" != "plots" ] && [ "$dir" != "post_processing" ]
    then
      rm -rf "$dir"
    fi
  fi
done
