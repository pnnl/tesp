  exec docker run \
 	  --name estimation \
          --user=root \
	  --detach=false \
	  -e DISPLAY=${DISPLAY} \
	  -v /tmp/.X11-unix:/tmp/.X11-unix \
	  --rm \
	  -v `pwd`:/mnt/shared \
	  -i \
          -t \
	  estimation_master /bin/bash -c "cd /mnt/shared && python /mnt/shared/develop/w_energyplus/workflow.py && rm -rf eplustofmu"
    exit $?
