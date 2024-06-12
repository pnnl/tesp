#!/bin/bash

docker images -q docker.artifactory.pnnl.gov/gpiq/gpiq_python:tesp_emissions_calc > docker_version
hostname > hostname

LOCAL_TESP="~/grid/tesp/examples/capabilities/dsostub/code"

docker run \
       -it \
       --mount type=bind,source="$LOCAL_TESP",destination="/tesp" \
       --entrypoint "//bin/bash" 74149bfda150
