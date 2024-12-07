#!/bin/bash

# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: push-images.sh

if [[ -z ${TESPDIR} ]]; then
  echo "Edit tesp.env in the TESP directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

ver=$(cat "${TESPDIR}/scripts/grid_version")

docker tag cosim-build:tesp_${ver} pnnl/tesp:${ver}
docker push pnnl/tesp:${ver}
