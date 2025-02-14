# Building, Updating, and Publishing Docker Images For Release
The instructions on this page for building the TESP Docker images are primarily intended to be used when generating new images for release. There may be other reasons for building new Docker images such as the integration of a new tool in TESP or experimenting with some other change to TESP itself. See the ["Custom Docker Images"](./Custom_Docker_images.md) for how to set-up and build Docker images in that case.

## Preparing build environment
1. - `git clone https://github.com/pnnl/tesp`  All the tooling to support building Docker images exists in the TESP repository so the first step to building the images is cloning in repository. The default branch contains the released version of the build tooling but for development purposes you may need to work from an alternative branch. If so, be sure to `git checkout <branch name>`.
2. (conda only)`conda deactivate` - TESP uses the Python virtual environment (`venv`) tool to manage the environment and we have seen some challenges when working inside conda. If you have conda installed it installs itself in such a way that all new terminal sessions start out in the "base" environment (_e.g._ `(base) $`). Deactivate this environment with `conda deactivate`.
3. `source tesp.env`d - This sets up the build environment, primarily through defining a bunch of environment variables.


## Building the images
1. `cd tesp/scripts/docker` - The scripts to build the Docker images are found in this folder.
2. (optional) Edit  "build-images.sh" to only build some of the images - If a previous attempt to build the Docker images was partially successful, it is not necessary to rebuild images that already exist. You can use `docker images` to see a list of local image and when they were last built. Any that show up there can be deactivated in the `build-images.sh` script but setting "build_ubuntu", "build_library" or "build_build" to "0".
3. (optional) Set group ID in "user.Dockerfile" - 
4. Run "build-images.sh" - At a terminal run "build-images.sh"
5. Confirm built images with `docker images` looking for "cosim-ubuntu", "cosim-library" and "cosim-build".


## Publishing Docker Images
1. Get permission to push images - Only Docker Hub users that are members of the "pnnl/tesp" channel can push images.
2. Login to Docker Hub - `docker login -u <Docker Hub username>` - You can authenticate with a previously defined personal access token.
3. Push up images to Docker Hub - Run "push-images.sh" to push the images up to the Docker Hub registry.






