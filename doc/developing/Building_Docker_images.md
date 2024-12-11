# Building, Updating, and Publishing Docker Images

Generally only need to rebuild images in preparation for release

Might use it as a way to hotfix a bug (have user build and use local images rather than waiting for a fix to make it to Docker Hub)

## Preparing build environment


## Building the images
go to tesp/scripts/docker
./build-images.sh (macOS and Linux)

Confirm images have been built with `docker images`; look for TODO

## Publishing Docker Images
Run /tesp/scripts/docker/push-images.sh

Only Docker Hub users that are members of the "pnnl/tesp" channel can push images.






