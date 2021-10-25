
git describe > tesp_version
docker images -q tesp_private:latest > docker_version
hostname > hostname

REPO="tesp_private"
LOCAL_TESP="$HOME/projects/dsot/code/tesp-private"
WORKING_DIR="/data/tesp/examples/dsot_v3"
ARCHIVE_DIR="/mnt/simdata/done"

docker run \
       -e LOCAL_USER_ID="$(id -u oste814)" \
       -it \
       --rm \
       --network=none \
       --mount type=bind,source="$LOCAL_TESP",destination="/data/tesp" \
       --mount type=bind,source="$ARCHIVE_DIR",destination="/mnt/simdata/done" \
       -w=${WORKING_DIR} \
       $REPO:latest \
       /bin/bash
#        "export PSST_SOLVER=/opt/ibm/cplex/bin/x86-64_linux/cplexamp; \
#       pip install --user -e /data/tesp/src/tesp_support/;"
