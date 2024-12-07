#!/bin/bash
#
# This runs a dsot simulation within a docker container that waits until the sim
# completes before ending and removing itself.  Result files will persist outside
# the container if they land in the mounted local directories.
#
# TODO: double check that all this is necessary, since it may be overkill?
# before running, make sure (maybe we can check in this script??)
#   a) a group with gid=9001 exists on your local machine
#   b) your local user id is associated with gid=9001?
#   c) at least your 'examples' mounted dir has group owner gid=9001 on your local machine
#      - and that these files have same permissions shared between owner and group???
#        (this let's us not login with local user id, but created mounted files might appear weird on local system)

IMAGE="cosim-cplex:tesp_22.04.1"

git describe --tags > tesp_version
docker images -q ${IMAGE} > docker_version
hostname > hostname

WORKING_DIR="$SIM_HOME/tesp/examples/analysis/dsot/code/%s"
#BASHCMD="python3 prepare_case_dsot_f.py"
#BASHCMD="python3 prepare_case_dsot_f.py $1 $2 $3 $4 $5 $6"
BASHCMD="python3 generate_case.py"

docker run \
       -e LOCAL_USER_ID=$SIM_UID \
       -itd \
       --rm \
       --network=none \
       --ipc=none \
       --mount type=bind,source="$TESPDIR",destination="$SIM_HOME/tesp"
       -w=${WORKING_DIR} \
       ${IMAGE} \
       /bin/bash -c "$BASHCMD"
