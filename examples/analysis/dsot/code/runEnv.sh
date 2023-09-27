#!/bin/bash

cat $TESPDIR/scripts/version > tesp_version
IMAGE_NAME="tesp-$(cat $TESPDIR/scripts/version):latest"
docker images -q $IMAGE_NAME > docker_version
hostname > hostname

WORKING_DIR="/data/tesp/examples/analysis/dsot/code"
ARCHIVE_DIR="/mnt/simdata/done"
USER_ID=oste814

docker run \
       -e LOCAL_USER_ID="$(id -u $USER_ID)" \
       -it \
       --rm \
       --network=none \
       --mount type=bind,source="$TESPDIR",destination="/data/tesp" \
       --mount type=bind,source="$ARCHIVE_DIR",destination="/mnt/simdata/done" \
       -w=${WORKING_DIR} \
       $IMAGE_NAME \
       /bin/bash
#        "export PSST_SOLVER=/opt/ibm/cplex/bin/x86-64_linux/cplexamp; \
#       pip install --user -e /data/tesp/src/tesp_support/;"
