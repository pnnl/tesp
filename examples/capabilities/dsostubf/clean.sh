#!/bin/bash

for dir in *; do
  if [ -d "$dir" ]; then
    [ "$dir" = "data" ] && continue
    rm -rf "$dir"
  fi
done
