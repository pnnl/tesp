# Project: Transactive Energy  #
## Creating a Docker container for a TESP scenario ##
***************************************
_Author: **Laurentiu Dan Marinovici**_

Copyright (C) 2018, Battelle Memorial Institute
Updated 09/07/2018
***************************************
## Documenting Docker container installation and image creation ##

## **Ubuntu** ##
The TESP docker image has been created and tested on a virtual machine (Oracle VM VirtualBox on Windows) running Ubuntu 16.04.4 LTS. After being pushed to the docker hub, it has been cloned and tested on a similar Ubuntu VM.

### Pre-requisites ###

In order to enable the graphical user interface (GUI) of TESP within its Docker container, X server is used on the Ubuntu host computer (VM). Detailed information can be found at [Using GUI's with Docker](http://wiki.ros.org/docker/Tutorials/GUI "GUI in Docker Container"), and [Running a GUI application in a Docker container](https://linuxmeerkat.wordpress.com/2014/10/17/running-a-gui-application-in-a-docker-container/ "Running GUI app in Docker container"). Therefore, first X server needs to be installed on the host computer(VM).

Run
```bash
which Xvfb
```
or
```bash
apt-cache search Xvfb
```
to check if host has X server installed. If not, run
```bash
sudo apt-get install xvfb
```
to install it. To check some of the X server settings, one could run
```bash
ps aux | grep X
```
or, to see the *DISPLAY* environment variable
```bash
echo $DISPLAY
```
which should return *:0* as default.

### Install Docker Community Edition ###
  - File [Script to install Docker CE on Ubuntu](https://github.com/GRIDAPPSD/gridappsd-docker/blob/master/docker_install_ubuntu.sh "Run this script."), which presents what the docker installation site shows at [Docker installation](https://docs.docker.com/install/linux/docker-ce/ubuntu/ "Online Docker documentation").
  ```
  #!/bin/bash

  # Environment variables you need to set so you don't have to edit the script below.
  DOCKER_CHANNEL=stable
  DOCKER_COMPOSE_VERSION=1.18.0

  # Update the apt package index.
  sudo apt-get update

  # Install packages to allow apt to use a repository over HTTPS.
  sudo apt-get install -y \
      apt-transport-https \
      ca-certificates \
      curl \
      software-properties-common \
      vim

  # Add Docker's official GPG key.
  curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | sudo apt-key add -

  # Verify the fingerprint.
  sudo apt-key fingerprint 0EBFCD88

  # Pick the release channel.
  sudo add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") \
    $(lsb_release -cs) \
    ${DOCKER_CHANNEL}"

  # Update the apt package index.
  sudo apt-get update

  # Install the latest version of Docker CE.
  sudo apt-get install -y docker-ce

  # Allow your user to access the Docker CLI without needing root.
  sudo /usr/sbin/usermod -aG docker $USER

  # Install Docker Compose.
  curl -L https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-`uname -s`-`uname -m` -o /tmp/docker-compose
  sudo mv /tmp/docker-compose /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  sudo chown root:root /usr/local/bin/docker-compose
  ```
  - The script also installs Docker Composer, used to define and run a multi-container Docker application. See [Compose overview](https://docs.docker.com/compose/overview/).
  - __Warning.__ To be able to run the Docker CLI without needing root, you need a reboot.

### For the TESP-image **creators** - How to build a docker image ###
  - To build an image we need a Dockerfile configuration file.

  All files described below are available at the [TESP GitHub](https://github.com/pnnl/tesp/tree/master/examples/te30/dockerSetupFiles "TESP docker setup files").

  <font style="color:blue">As the platform has undergone many changes and updates, there have been several Docker images created. Each image has been built incrementally from a previously built image. Therefore, there are several different Docker set-up files and scripts to run them. As of 09/06/2018, the latest version is version 5.</font>

  Here is the Dockerfile *<Dockerfile.tesp_full>* written to create the TESP image from a host computer containing the sources for the necessary software packages, that is FNCS, GridLAB-D, PyPower, Energy Plus, Energy Plus JSON and the python TE agents.
  ```bash
  ARG PYTHON=python
  ARG PYTHON_VERSION=:3

  FROM ${PYTHON}${PYTHON_VERSION}

  RUN apt-get update && \
      apt-get install -y \
      wget \
      git \
      automake \
      autoconf \
      make \
      cmake \
      g++ \
      gcc \
      libtool \
      ca-certificates \
      openssl \
      lsof \
      psmisc && \
      rm -rf /var/lib/apt/lists/* && \
      rm -rf /var/cache/apt/archives/* && \
      echo "===== PYTHON VERSION =====" && \
      python --version && \
      echo "===== PIP VERSION =====" && \
      pip --version && \
      echo "===== UPGRADE PIP =====" && \
      pip install --upgrade pip && \
      echo "===== install NUMPY =====" && \
      pip install numpy && \
      echo "===== install MATPLOTLIB =====" && \
      pip install matplotlib && \
      echo "===== install SCIPY =====" && \
      pip install scipy && \
      echo "===== install PYPOWER =====" && \
      pip install pypower && \
      echo "===== current PIP3 modules =====" && \
      pip list --format=columns

  # -----------------------------------------------------
  # Environment variables giving the location where TESP
  # related software will be installed.
  # -----------------------------------------------------
  ENV TESP=/tesp
  ENV FNCS_INSTALL=${TESP}/FNCSInstall
  ENV GLD_INSTALL=${TESP}/GridLABD1048Install
  ENV EPLUS_INSTALL=${TESP}/EnergyPlusInstall
  ENV EPLUSJSON_INSTALL=${TESP}/EPlusJSONInstall
  ENV PYPOWER_INSTALL=${TESP}/PyPowerInstall
  ENV AGENTS_INSTALL=${TESP}/AgentsInstall

  # ----------------------------------------------------
  # Because I want to use the software versions I already have
  # installed on the current Dragonstone VM, I am going to use
  # directly the downloads and repositories I have, letting aside
  # the commands that are performing the actual downloads, and 
  # repository cloning.
  # Hence, from the context of the folder where I have all my downloads
  # and clones, I only add the needed ones.
  # I am running the image building script from inside the folder where
  # all repositories have been already cloned in the source folders below.
  # --------------------------------------------------------------
  ENV CZMQ_VERSION 3.0.2
  ENV ZMQ_VERSION 4.1.6
  ENV CZMQ_SOURCE=czmq-${CZMQ_VERSION}
  ENV ZMQ_SOURCE=zeromq-${ZMQ_VERSION}
  # -------------------------------
  # FNCS branch = feature/transactiveEnergyApi
  ENV FNCS_SOURCE=fncs
  # -------------------------------
  # GridLAB-D branch = feature/1048
  ENV GLD_SOURCE=gridlab-d
  # -------------------------------
  # Energy Plus branch = fncs-v8.3.0
  ENV EPLUS_SOURCE=EnergyPlus
  ENV EPLUS_POSTPROC="EPLUS/EnergyPlus-8-3-0/PostProcess/ReadVarsESO"
  ENV EPLUSJSON_SOURCE=EnergyPlusJSON
  # -------------------------------
  # PYPOWER has only 2 main executable scripts
  # however, fncs.py has a hardcoded path that I need to be careful about
  ENV PYPOWER_SOURCE=TESP-pypower
  # -------------------------------
  ENV AG_SOURCE=TESP-agents
  # The folder on the image where all source files will be copied to,
  # so that installation can proceed.
  ENV SOURCE_DIR=/tmp/sources

  # --------------------------------------------------------------
  # Environment variables needed for the package installation
  # --------------------------------------------------------------
  ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${FNCS_INSTALL}/lib
  ENV FNCS_LIBRARY=${FNCS_INSTALL}/lib
  ENV FNCS_INCLUDE_DIR=${FNCS_INSTALL}/include
  ENV PATH="${PATH}:${FNCS_INSTALL}"
  # default values
  ENV FNCS_LOG_FILE=no
  ENV FNCS_LOG_STDOUT=no
  ENV FNCS_LOG_TRACE=no
  ENV FNCS_LOG_LEVEL=DEBUG4

  # ------------------------------------------------------------------
  # Adding the host source folders to the Docker image source folders
  # ------------------------------------------------------------------
  ADD ${ZMQ_SOURCE} ${SOURCE_DIR}/${ZMQ_SOURCE}
  ADD ${CZMQ_SOURCE} ${SOURCE_DIR}/${CZMQ_SOURCE}
  ADD ${FNCS_SOURCE} ${SOURCE_DIR}/${FNCS_SOURCE}
  ADD ${GLD_SOURCE} ${SOURCE_DIR}/${GLD_SOURCE}
  ADD ${EPLUS_SOURCE} ${SOURCE_DIR}/${EPLUS_SOURCE}
  ADD ${EPLUS_POSTPROC} ${SOURCE_DIR}
  ADD ${EPLUSJSON_SOURCE} ${SOURCE_DIR}/${EPLUSJSON_SOURCE}
  ADD ${PYPOWER_SOURCE} ${SOURCE_DIR}/${PYPOWER_SOURCE}
  ADD ${AG_SOURCE} ${SOURCE_DIR}/${AG_SOURCE}

  RUN mkdir -p ${SOURCE_DIR}

  # ----------------------------------------------------
  # INSTALL ZMQ and BINDINGS for c++
  # ----------------------------------------------------
  RUN cd ${SOURCE_DIR}/${ZMQ_SOURCE} && \
      ./configure --prefix=${FNCS_INSTALL} && \
      make && \
      make install && \
      cd ${SOURCE_DIR} && \
      /bin/rm -r ${SOURCE_DIR}/${ZMQ_SOURCE}

  RUN cd ${SOURCE_DIR}/${CZMQ_SOURCE} && \
      ./configure --prefix=${FNCS_INSTALL} --with-libzmq=${FNCS_INSTALL} && \
      make && \
      make install && \
      cd /tmp && \
      /bin/rm -r ${SOURCE_DIR}/${CZMQ_SOURCE}

  # ----------------------------------------------------
  # INSTALL FNCS
  # ----------------------------------------------------
  RUN cd ${SOURCE_DIR}/${FNCS_SOURCE} && \
      autoreconf -if && \
      ./configure --prefix=${FNCS_INSTALL} --with-zmq=${FNCS_INSTALL} && \
      make && \
      make install && \
      cd /tmp && \
      /bin/rm -r ${SOURCE_DIR}/${FNCS_SOURCE}

  # ----------------------------------------------------
  # INSTALL GridLAB-D
  # ----------------------------------------------------
  RUN cd ${SOURCE_DIR}/${GLD_SOURCE} && \
      cd ${SOURCE_DIR}/${GLD_SOURCE}/third_party && \
      tar -xzf xerces-c-3.1.1.tar.gz && \
      cd ${SOURCE_DIR}/${GLD_SOURCE}/third_party/xerces-c-3.1.1 && \
      ./configure && \
      make && \
      make install && \
      chmod u=rwx ${SOURCE_DIR}/${GLD_SOURCE}/build-aux/version.sh && \
      cd ${SOURCE_DIR}/${GLD_SOURCE} && \
      autoreconf -if && \
      ./configure --prefix=${GLD_INSTALL} --with-fncs=${FNCS_INSTALL} --enable-silent-rules \
      'CFLAGS=-g -O0 -w' 'CXXFLAGS=-g -O0 -w' 'LDFLAGS=-g -O0 -w' && \
      make && \
      make install && \
      cd /tmp && \
      /bin/rm -r ${SOURCE_DIR}/${GLD_SOURCE}
  ENV PATH="${PATH}:${GLD_INSTALL}/bin"
  ENV GLMPATH="${GLD_INSTALL}/lib/gridlabd:${GLD_INSTALL}/share/gridlabd"

  # ----------------------------------------------------
  # INSTALL Energy Plus
  # ----------------------------------------------------
  ENV CMAKE_INSTALL_PREFIX=${EPLUS_INSTALL}

  RUN mkdir ${EPLUS_INSTALL} && \
      cd ${EPLUS_INSTALL} && \
      cmake -DCMAKE_INSTALL_PREFIX:PATH=${EPLUS_INSTALL} \
            -DCMAKE_PREFIX_PATH=${FNCS_INSTALL} \
            ${SOURCE_DIR}/${EPLUS_SOURCE} && \
      make && \
      make install && \
      cd /tmp

  # ----------------------------------------------------
  # Extra installation needed for Energy Plus
  # Copy the ReadVarsESO file needed for postprocessing
  # from a version of EPLUS ready for installation
  # ----------------------------------------------------
  RUN mkdir -p ${EPLUS_INSTALL}/Products/PostProcess && \
      cd ${SOURCE_DIR} && \
      /bin/cp ReadVarsESO ${EPLUS_INSTALL}/Products/PostProcess && \
      cd /tmp && \
      /bin/rm ${SOURCE_DIR}/ReadVarsESO

  # ----------------------------------------------------
  # INSTALL Energy Plus JSON
  # ----------------------------------------------------
  RUN cd ${SOURCE_DIR}/${EPLUSJSON_SOURCE} && \
      autoheader && \
      aclocal && \
      automake --add-missing && \
      autoreconf -if && \
      ./configure --prefix=${EPLUSJSON_INSTALL} --with-fncs=${FNCS_INSTALL} && \
      make && \
      make install && \
      cd /tmp && \
      /bin/rm -r ${SOURCE_DIR}/${EPLUSJSON_SOURCE}

  # ----------------------------------------------------
  # INSTALL PYPOWER
  # Actually simply copying the necessary files
  # ----------------------------------------------------
  RUN mkdir ${PYPOWER_INSTALL} && \
      cd ${SOURCE_DIR}/${PYPOWER_SOURCE} && \
      /bin/cp *.* ${PYPOWER_INSTALL} && \
      /bin/cp fncs.py.DockerVersion ${PYPOWER_INSTALL}/fncs.py && \
      cd /tmp && \
      /bin/rm -r ${SOURCE_DIR}/${PYPOWER_SOURCE}

  # ----------------------------------------------------
  # INSTALL TE AGENTS
  # Actually simply copying the necessary files
  # ----------------------------------------------------
  RUN mkdir ${AGENTS_INSTALL} && \
      cd ${SOURCE_DIR}/${AG_SOURCE} && \
      /bin/cp *.* ${AGENTS_INSTALL} && \
      /bin/cp fncs.py.DockerVersion ${AGENTS_INSTALL}/fncs.py && \
      cd /tmp && \
      /bin/rm -r ${SOURCE_DIR}/${AG_SOURCE} && \
      /bin/rm -r ${SOURCE_DIR}
  ```
  
  - To build the Docker image, simply run
  ```bash
  docker build .
  ```
  or
  ```shell
  docker build -f <Docker config file> -t <Docker tag> .
  ```
  __Warning!__ Yes, the full-stop at the end represents the context of the Docker image build.

  To build a TESP image, a script similar to the one below could be used *<build-tespbuild-tespFullPython3Image.sh>*
  ```bash
  #!/bin/bash

  DOCKERFILE="Dockerfile.tesp_full"
  TESP_REP="tesp/full"
  TESP_TAG=":V1"
  clear
  docker build --no-cache \
              --network=host \
              -f ${DOCKERFILE} \
              -t ${TESP_REP}${TESP_TAG} .
  ```
  which will build an image based on a Python 3 distribution, with all the software installed based on the Dockerfile. As of this point, the access to the image will be as root.

  - To add a user to the already existing image *tesp/full:V1*, a new image *tesp/full:V2* is going to be created. To do so write a new Dockerfile *Dockerfile_fullUser* as below, where user *tesp_user* is added, and given root access to the TESP folder *${TESP}*.
  ```bash
  ARG REPOSITORY="tesp/full"
  ARG TAG="V1"

  FROM ${REPOSITORY}:${TAG}

  RUN useradd -m -s /bin/bash tesp-user && \
      chown -R tesp-user ${TESP}

  USER tesp-user
  WORKDIR ${TESP}
  ```
  then run the new script *build-tespFullPython3ImageUser.sh*, which looks like
  ```bash
  #!/bin/bash

  DOCKERFILE="Dockerfile.tesp_fullUser"
  TESP_REP="tesp/full"
  TESP_TAG=":V2"
  clear
  docker build --no-cache \
              --network=host \
              -f ${DOCKERFILE} \
              -t ${TESP_REP}${TESP_TAG} .
  ```

  * To view a list of the docker images
  ```bash
	docker images
	```
  * To view a list of all docker containers
  ```bash
  docker ps -a
  ```

  - On [hub.docker.com](hub.docker.com "hub.docker.com"), a new repository has been created *laurmarinovici/tesp*, and made public. In order to be able to load the local Docker image to the hub under the created repository name, I had to re-tag it
  ```bash
  docker tag tesp/full:V2 laurmarinovici/tesp
  ```
  Then, run
  ```bash
  docker login
  docker push laurmarinovici/tesp
  ```

  - As of <font style="color:red">2018/05/16</font>, a new auction agent has been developed (new algorithm for demand curve, and consolidation of controller agents under one auction agent), and some updates to the PYPOWER wrapper have been performed. Hence, a new image has been created called *laurmarinovici/tesp:V2*. Also, new scripts and input files have been created for the TE30 scenario to accommodate for these changes. These newly created files have been denoted by appending date (*20180516* or higher) to the file names.
  - As of <font style="color:red">2018/08/07</font>, the Docker image has reached version 5, that is *laurmarinovici/tesp:V5*, and contains the following updates:
    - GridLAB-D has been updated to the latest version supporting the transactive energy features;
    - Eplus-JSON has been updated to the latest version that accounts for an augmented set of input arguments, that includes a reference price, a degree per price unit increase ramp, and the upper and lower temperature bandwidths;
    - PYPOWER and TESP-SUPPORT are integrated as modules for the PYTHON distribution and can easily be installed and upgraded using PYTHON commands:
      ```bash
      pip install PYPOWER
      pip install tesp-support
      ```
      and
      ```bash
      pip install --upgrade PYPOWER
      pip install --upgrade tesp-support
      ```
    - Also, the support and example files now come through the installation of a release kit that can be downloaded from [TESP releases](https://github.com/pnnl/tesp/releases "TESP releases"). In order to run it, it needs to be executable and ran under super user mode.

### For the **users** of the TESP docker container on Ubuntu and MacOS ###
After installing Docker according to the above-mentioned procedure, to pull the latest Docker image, run
```bash
docker pull laurmarinovici/tesp:V5
```
Then, to start one of the TE examples, specifically the TE30 challenge, go to the folder _TESP-Docker-Inputs_ (which users might be provided or download from [TESP GitHub page](https://github.com/pnnl/tesp/tree/master/install/Docker/TESP-Docker-Inputs)) at your machine terminal, and run
```bash
./runTESP-V5-Container-TE30-0.1.sh
```
This script is presented below.
```bash
#!/bin/bash
clear
# 
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":V5"
TESP_CONT="tespV5"
HOST_FOLDER="$PWD"

#
docker images

# 
if (docker inspect -f {{.State.Running}} ${TESP_CONT} &> /dev/null); then
  echo "===== Container ${TESP_CONT} is already running, so I will close and remove it first. ====="
  docker stop ${TESP_CONT}
  docker rm ${TESP_CONT}
fi

echo "===== Create container ${TESP_CONT}."
docker container run --name ${TESP_CONT} \
                      -dit --env="DISPLAY" \
                      --env="QT_X11_NO_MITSHM=1" \
                      --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
                      --volume="${HOST_FOLDER}:/tmp/scenarioData:rw" \
                      ${TESP_REP}${TESP_TAG}
export CONTAINER_ID=$(docker ps -l -q)
xhost +local:`docker inspect --format='{{ .Config.Hostname}}' ${CONTAINER_ID}`

echo "===== List of containers on the machine."
docker ps -a
docker container start ${TESP_CONT}
echo "===== Container ${TESP_CONT} has been started."

# =================== TE30 Challenge Support and example files ====================================================
echo "===== Setting up support and example folders, and the running scripts."
docker container exec ${TESP_CONT} /bin/bash -c 'whoami && \
  PATH=$PATH:/tesp/FNCSInstall/bin:/tesp/EnergyPlusInstall:/tesp/EPlusJSONInstall/bin && \
  export PATH && \
  echo $PATH && \
  cd ${TESP} && mkdir TESP-support && \
  cp -r /tmp/scenarioData/TESP-support/support ${TESP}/TESP-support && \
  cd ${TESP}/TESP-support && mkdir examples && \
  cp -r /tmp/scenarioData/TESP-support/examples/te30 ${TESP}/TESP-support/examples && \
  cp -r /tmp/scenarioData/TESP-support/examples/players ${TESP}/TESP-support/examples && \
  cp /tmp/scenarioData/Running-TE30-Scripts/runGUI-TE30-0.2.sh ${TESP}/TESP-support && \
  cp /tmp/scenarioData/Running-TE30-Scripts/runTE30-0.2.sh ${TESP}/TESP-support && \
  chmod u+x ${TESP}/TESP-support/runGUI-TE30-0.2.sh && \
  chmod u+x ${TESP}/TESP-support/runTE30-0.2.sh && \
  echo $PATH'

# =================== FNCS settings =========================================================
echo "===== Setting up FNCS paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${FNCS_INSTALL}/bin/outputFiles; then rmdir ${FNCS_INSTALL}/bin/outputFiles; mkdir ${FNCS_INSTALL}/bin/outputFiles; else mkdir ${FNCS_INSTALL}/bin/outputFiles; fi'

# ================== GridLAB-D settings ============================================================
echo "===== Setting up GridLAB-D paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${GLD_INSTALL}/bin/outputFiles; then rmdir ${GLD_INSTALL}/bin/outputFiles; mkdir ${GLD_INSTALL}/bin/outputFiles; else mkdir ${GLD_INSTALL}/bin/outputFiles; fi'

# =================== Energy Plus settings =========================================================
echo "===== Settting up Energy Plus paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUS_INSTALL}/outputFiles; then rmdir ${EPLUS_INSTALL}/outputFiles; mkdir ${EPLUS_INSTALL}/outputFiles; else mkdir ${EPLUS_INSTALL}/outputFiles; fi'

# =================== Energy Plus JSON settings =========================================================
echo "===== Setting up Energy Plus JSON paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUSJSON_INSTALL}/outputFiles; then rmdir ${EPLUSJSON_INSTALL}/outputFiles; mkdir ${EPLUSJSON_INSTALL}/outputFiles; else mkdir ${EPLUSJSON_INSTALL}/outputFiles; fi'

echo "=========================================================================================="

# =================== Prepare the TE30 Challenge ===================================================================
echo "===== Preparing the TE30 scenario."
docker container exec ${TESP_CONT} /bin/bash -c 'cd ${TESP}/TESP-support/examples/te30 && \
  python3 prepare_case.py'

docker container exec -it ${TESP_CONT} /bin/bash -c 'stty cols 200 rows 60 && bash'
```
It performs the following main and important actions:
- starts a docker container tagged _tespV5_ from the docker image _laurmarinovici/tesp:V5_;
- sets some environment variables for the Docker container to make sure the executables are correctly found; (__WARNING!__ I believe this aspect does not quite work, in the sense that though the commands run, the PATH does not get fixed once the container has started; therefore, the PATH environment is set again in the simulation start script)
- copies the corresponding support and example files from the TESP release installation folder; (__WARNING!__ It is recommended that, in order for the script to work, the data files that come with the TESP release should be under the folder _TESP-support_ in the same folder as _TESP-Docker-Inputs_.)
- copies the specific example running scripts from the local _Running-TE30-Scripts_ folder, that is _runTE30-0.2.sh_ to run the example without a GUI, and _runGUI-TE30-0.2.sh_ to invoke the GUI;
- creates output folders for each simulator;
- prepares the TE30 scenario by running the corresponding PYTHON script;
- returns to the Docker container Ubuntu prompt.
To make sure all transactive energy support files are up-to-date, from the Ubuntu Docker container prompt, you can run
```bash
pip install --upgrade pip
pip install --upgrade PYPOWER
pip install --upgrade tesp-support
```
Then, to start the TE30 scenario simulation,
```bash
cd TESP-support
./runGUI-TE30-0.2.sh
```
This will open the GUI running this example. The next steps are:
- Click on _Open..._ and navigate to */examples/te30* to select the file _tesp_monitor.json_;
- Click on _Start All_.
The evolution of the simulation can be followed through the displayed graphs.

## **Mac OS** ##

### Pre-requisites ###

Same as in the Ubuntu case, in order to enable the graphical user interface (GUI) of TESP within its Docker container, the X server MacOS counterpart needs to be installed on the computer running it, that is [XQuartz](https://www.xquartz.org/ "Click to get the dmg"). Once XQuartz is installed, run it at the terminal with
```
open -a XQuartz
```
and in X11 Preferences under Security tab, make sure "Allow connections from network clients" is checked.

Also, _socat_ ([Netcat on steroids :)](http://www.dest-unreach.org/socat/)) needs to be installed. And it will be done using the _brew_ ([Homebrew](https://docs.brew.sh/Installation)), which I have installed using
```
ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)" /dev/null
```
Run
```
brew install socat
socat TCP-LISTEN:6000,reuseaddr,fork UNIX-CLIENT:\"$DISPLAY\"
```
to install _socat_, and then give access to the host display.

At the Mac terminal, start XQuartz with
```
open -a xquartz& 
```
and on the X11 terminal, run
```
IP=$(ifconfig en1 | grep inet | awk '$1=="inet" {print $2}')
xhost + $IP
export IP
```
to get the IP and add it to the access control list.

__WARNING.__
  - If on WiFi, _en0_ might need to be used instead of _en1_.
  - If network is changed, this command needs to be rerun to get the correct IP.

On MacOS, the script that starts the Docker container and sets the scenario simulation environment (_runTESP-V5-MacContainer-TE30-0.1.sh_) is similar to the one on Ubuntu, except the part that sets the X Server environment, which is highlighted below.
```
...........

# 
if (docker inspect -f {{.State.Running}} ${TESP_CONT} &> /dev/null); then
  echo "Container ${TESP_CONT} is already running."
else
  echo "===== Create container ${TESP_CONT}."
  docker container run --name ${TESP_CONT} \
                        -dit --env="DISPLAY" \
                        --env="QT_X11_NO_MITSHM=1" \
                        --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
                        --volume="${HOST_FOLDER}:/tmp/scenarioData:rw" \
                        ${TESP_REP}${TESP_TAG}
  export CONTAINER_ID=$(docker ps -l -q)
  xhost +local:`docker inspect --format='{{ .Config.Hostname}}' ${CONTAINER_ID}`
fi

...........
```
After running it in a similar fashion as in the Ubuntu case, from the XQuartz terminal prompt, follow the same steps as previously mentioned to start the TE30 simulation.

**Lessons learnt**

While setting the scripts for MacOS, some challenges occurred while using _docker cp_ command to copy the scenario input files and running scripts from host to container before being able to run the simulation inside the container. It turned out that doing so from MacOS would copy the files under different UID:GID on the container, which made it impossible to run _chmod_ and set the running scripts as executable. Therefore, I have adopted a different method, that is mounting the folder that contains the files on a folder on the container, and then copy them to the simulation folder. The same method was then adopted for the Ubuntu case as well.
