# Building Custom Docker Images with "user.Dockerfile"
Developers may need to customize the Docker images being used for a variety of reasons such as adding a new tool, trying out a new API, or even testing something new in the Docker image build process. For these purposes, we have included a "user.Dockerfile" which is intended to be an optional layer on top of the traditional TESP image stack (defined in "ubuntu.Dockerfile", "library.Dockerfile", and "build.Dockerfile"). This image is intended to be used to solve compatability problems and provide a customization layer.

## "user.Dockerfile" to Path Permissions Issues
The TESP Docker images have been set up to mount the locally-cloned TESP repository inside the Docker container such that all files in that folder outside the Docker container are visable and usable inside the Docker container. There can be permissions issues in these cases, though, due to the permissions of the "worker" account inside the container and the lack of permissions for that account outside the container. To patch this over, the "user" image can be used to set the permissions of the "worker" account inside the container to align them with the appropriate group outside the container.

1. Run `id` to find the group name and permissions for the user in the host OS - Amazingly, `id` provides the same response on macOS, WSL 2 (Windows) and Ubuntu Linux. The response to this command shows values for "gid". Note the numeric "gid" and corresponding group name.
2. Edit "tesp/scripts/docker/user.Dockerfile" to add these values - Change `ARG SIM_GID` to `ARG SIM_GID=<gid number>` and `ARG SIM_GRP` to `ARG SIM_GRP=<corresponding group name>`

## Build "user.Dockerfile"
1. Edit "build-images.sh" to include "user.Dockerfile" - Any Dockerfiles you have edited need to be re-built; this is done by setting the corresponding value ("ubuntu.Dockerfile", "library.Dockerfile", "build.Dockerfile", "user.Dockerfil") in "build-images.sh" to "1". If you only edited "user.Dockerfile" then set all the others to "0" and "build_user" to "1".
2. Rerun "build-images.sh"

## Updating "runtesp"
If you change "user.Dockerfile", to use those changes the "runtesp" shell (macOS and Ubuntu) or batch script (Windows) needs to be updated. This will call the "user" image instead of the "build" image when launching TESP in Docker.

1. Edit "tesp/scripts/helpers/runtesp" or "runtesp.bat" - Comment out the `IMAGE=pnnl/tesp:${docker_tag}` line and uncomment `IMAGE=cosim-user:tesp_${grid_ver}`. This will use the locally built "cosim-user" image instead of the Docker Hub hosted non-user image.
