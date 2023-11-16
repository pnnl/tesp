#!/bin/bash

usr="oste814"
sims="/mnt/simdata/done"

hostname > "$sims/$(hostname).log"
echo "Running $1" >> "$sims/$(hostname).log"
dir=$(basename "$1")
echo "Running $dir"
hostname > "$1/hostname"
yes | cp -rf "$1" .
sed -i "s:./clean.sh; ./run.sh; ./monitor.sh:./postprocess.sh:g" "$dir/docker-run.sh"
sudo chown -R $usr:sim_group ../../*
cd "$dir" || exit
./docker-run.sh
