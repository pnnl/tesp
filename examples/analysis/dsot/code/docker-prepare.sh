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

git describe > tesp_version
docker images -q tesp_private:latest > docker_version

REPO="tesp_private"
LOCAL_TESP="$HOME/projects/dsot/code/tesp-private"
WORKING_DIR="/data/tesp/examples/dsot_v3"
#BASHCMD="pip install --user -e /data/tesp/src/tesp_support/; python3 prepare_case_dsot_f.py"
#BASHCMD="pip install --user -e /data/tesp/src/tesp_support/; python3 prepare_case_dsot_f.py $1 $2 $3 $4 $5 $6"
BASHCMD="pip install --user -e /data/tesp/src/tesp_support/; python3 generate_case.py"

docker run \
       -e LOCAL_USER_ID="$(id -u)" \
       -it \
       --rm \
       --network=none \
       --ipc=none \
       --mount type=bind,source="$LOCAL_TESP/examples",destination="/data/tesp/examples" \
       --mount type=bind,source="$LOCAL_TESP/support",destination="/data/tesp/support" \
       --mount type=bind,source="$LOCAL_TESP/ercot",destination="/data/tesp/ercot" \
       --mount type=bind,source="$LOCAL_TESP/src",destination="/data/tesp/src" \
       -w=${WORKING_DIR} \
       $REPO:latest \
       /bin/bash -c "$BASHCMD"
