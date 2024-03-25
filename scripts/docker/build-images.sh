#!/bin/bash

# build_<image_name>: 0 - skip; 1 - build image; <image_name> must be in sync with names array below
build_ubuntu=0
build_library=0
build_build=0
build_helics=0
build_tespapi=0

if [[ -z ${TESPDIR} ]]; then
  echo "Edit tesp.env in the TESP directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

paths=(
  "./"
  "./"
  "${TESPDIR}/scripts/build/"
  "./"
  "./"
)

names=(
  "ubuntu"
  "library"
  "build"
  "helics"
  "tespapi"
)

# Dynamically build the 'builds' array based on the configuration
builds=()
for name in "${names[@]}"; do
  var="build_$name"
  builds+=( "${!var}" ) # Indirect variable reference
done

cd "$DOCKER_DIR" || exit
export BUILDKIT_PROGRESS=plain

for i in "${!names[@]}"; do
  CONTEXT="${paths[$i]}"
  IMAGE_NAME="cosim-${names[$i]}:latest"
  DOCKERFILE="${names[$i]}.Dockerfile"

  if [ "${builds[$i]}" -eq 1 ]; then
    echo "========"
    echo "Creating ${IMAGE_NAME} from ${DOCKERFILE}"
    image1=$(docker images -q "${IMAGE_NAME}")
    docker build --no-cache --rm \
                 --build-arg COSIM_USER="${COSIM_USER}" \
                 --build-arg SIM_HOST="${SIM_HOST}" \
                 --build-arg SIM_USER="${SIM_USER}" \
                 --build-arg SIM_UID=$SIM_UID \
                 --network=host \
                 -f "${DOCKERFILE}" \
                 -t "${IMAGE_NAME}" "${CONTEXT}"
    image2=$(docker images -q "${IMAGE_NAME}")
    if [ "$image1" != "$image2" ]; then
      echo "Deleting old image Id: $image1"
      docker rmi "${image1}"
    fi
    echo
  fi
done
