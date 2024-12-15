#!/bin/bash

# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: push-images.sh

if [[ -z ${TESPDIR} ]]; then
  echo "Edit tesp.env in the TESP directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

tesp_ver=$(cat "${TESPDIR}/scripts/tesp_version")
grid_ver=$(cat "${TESPDIR}/scripts/grid_version")
docker_tag=${tesp_ver}_ubuntu_${grid_ver}

# you may need log out first `docker logout` ref. https://stackoverflow.com/a/53835882/248616
# docker login

# gives following response:

# USING WEB-BASED LOGIN
# To sign in with credentials on the command line, use 'docker login -u <username>'
#
# Your one-time device confirmation code is: BKXP-NSDM
# Press ENTER to open your browser or submit your device code here: https://login.docker.com/activate
#
# Waiting for authentication in the browser
# WARNING! Your password will be stored unencrypted in /home/d3j331/.docker/config.json.
# Configure a credential helper to remove this warning. See
# https://docs.docker.com/engine/reference/commandline/login/#credential-stores
#
# Login Succeeded

docker tag cosim-build:tesp_${grid_ver} pnnl/tesp:${docker_tag}
docker push pnnl/tesp:${docker_tag}
