#!/bin/bash

cd case8 || exit
./clean.sh
rm -f ./*.glm
cd dsostub || exit
./clean.sh
cd ../../bulk_system || exit
./clean.sh
cd ../dist_system || exit
./clean.sh
cd ..