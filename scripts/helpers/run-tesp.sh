#!/bin/bash

IMAGE=cosim-build:tesp_1_22.04

#       -e LOCAL_USER_ID="$(id -u)" \\

docker run -it --rm \\
       --network=none \\
       --mount type=bind, source="$TESPDIR", destination="$DOCKER_HOME/tesp" \\
       -w=$DOCKER_HOME \\
       $IMAGE \\
       bash -c "pip install --user -e $DOCKER_HOME/tesp/src/tesp_support/;"