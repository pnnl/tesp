# Project: Transactive Energy  #
## Creating a Docker container for a TESP scenario ##
***************************************
_Author: **Laurentiu Dan Marinovici**_

Copyright (C) 2018, Battelle Memorial Institute
***************************************
## Documenting docker container installation and creation on ##

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
  * File [Script to install Docker CE on Ubuntu](https://github.com/GRIDAPPSD/gridappsd-docker/blob/master/docker_install_ubuntu.sh "Run this script."), which presents what the docker installation site shows at [Docker installation](https://docs.docker.com/install/linux/docker-ce/ubuntu/ "Online Docker documentation").
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
  * The script also installs Docker Composer, used to define and run a multi-container Docker application. See [Compose overview](https://docs.docker.com/compose/overview/).
  * __Warning.__ To be able to run the Docker CLI without needing root, you need a reboot.

### For the TESP-image **creators** - How to build a docker image ###
  * To build an image we need a Dockerfile configuration file.

  All files described below are available at the [TESP GitHub](https://github.com/pnnl/tesp/tree/master/examples/te30/dockerSetupFiles "TESP docker setup files").

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
  
  * To build the Docker image, simply run
  ```bash
  docker build .
  ```
  or
  ```shell
  docker build -f <Docker config file> -t <Docker tag> .
  ```
  __Warning!__ Yes, the full-stop at the end is needed.

  To build the TESP image, the following script is used *<build-tespbuild-tespFullPython3Image.sh>*
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

  * To add a user to the already existing image *tesp/full:V1*, a new image *tesp/full:V2* is going to be created. To do so write a new Dockerfile *Dockerfile_fullUser* as below, where user *tesp_user* is added, and given root access to the TESP folder *${TESP}*.
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

  * On [hub.docker.com](hub.docker.com "hub.docker.com"), a new repository has been created *laurmarinovici/tesp*, and made public. In order to be able to load the local Docker image to the hub under the created repository name, I had to re-tag it
  ```bash
  docker tag tesp/full:V2 laurmarinovici/tesp
  ```
  Then, run
  ```bash
  docker login
  docker push laurmarinovici/tesp
  ```

  * As of 2018-05-16, a new auction agent has been developed (new algorithm for demand curve, and consolidation of controller agents under one auction agent), and some updates to the PYPOWER wrapper have been performed. Hence, a new image has been created called *laurmarinovici/tesp:V2*. Also, new scripts and input files have been created for the TE30 scenario to accommodate for these changes. These newly created files have been denoted by appending date (*20180516* or higher) to the file names.

### For the **users** of the TESP docker container ###
After installing Docker according to the above-mentioned procedure, run
```bash
docker pull laurmarinovici/tesp
```
and then, go to the folder *TESP-Docker-Inputs* (which users might be provided or download from [TESP GitHub page](https://github.com/pnnl/tesp/tree/master/examples/te30/TESP-Docker-Inputs)) at your Ubuntu terminal, and run
```bash
./runVisualTESPContainer-TE30.sh
```
This script should start a docker container tagged *tespV2*, copy all the needed files to run TE30 challenge on the corresponding folders, then start a *bash* session on the container in working folder *tesp*, under the user *tesp_user*. Once this point has been reached, run
```bash
export TERM=xterm && echo "===== TERM = ${TERM}" && export FNCS_LOG_STDOUT=no && echo "===== FNCS_LOG_STDOUT = ${FNCS_LOG_STDOUT}" && cd /tesp/runScripts && python tespTE30.py &
```
at the terminal prompt. Start simulation scenario by clicking **Start All**.

## **Mac OS** ##

### Pre-requisites ###

Same as in the Ubuntu case, in order to enable the graphical user interface (GUI) of TESP within its Docker container, the X server MacOS counterpart needs to be installed on the computer running it, that is [XQuartz](https://www.xquartz.org/ "Click to get the dmg"). Once XQuartz is installed, run it at the terminal with
```
open -a XQuartz
```
and in X11 Preferences under Security tab, make sure "Allow connections from network clients" is checked.

Also, _socat_ ([Netcat on steroids :)](http://www.dest-unreach.org/socat/)) needs to be installed. And it will be done using the _brew_ ([Homebrew](https://docs.brew.sh/Installation)), which I have installed using
```
ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)" < /dev/null 2> /dev/null
```
Run
```
brew install socat
socat TCP-LISTEN:6000,reuseaddr,fork UNIX-CLIENT:\"$DISPLAY\"
```
to install _socat_, and then give access to the host display.

On another Mac terminal, start XQuartz with
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

**WARNING.**
  - If on WiFi, _en0_ might need to be used instead of _en1_.
  - If network is changed, this command needs to be rerun to get the correct IP.

**Lessons learnt**
Using _docker cp_ command to copy the scenario input files and running scripts from host to container before being able to run the simulation inside the container. It turned out that doing so from MacOS would copy the files under different UID:GID on the container, which made it impossible to run _chmod_ and set the running scripts as executable. Therefore, I have adopted a different methods, as seen in _runVisualTESPContainer-TE30-Mac.sh_ docker run command, that is mounting the folder that contains the files on a folder on the container, and then copy them to the simulation folder. See below.
```
#!/bin/bash
clear
# 
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":V2"
TESP_CONT="tespV2"
HOST_FOLDER="$PWD"

#
docker images

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

echo "===== List of containers on the machine."
docker ps -a
docker container start ${TESP_CONT}
echo "===== Container ${TESP_CONT} has been started."

# =================== TE30 Challenge Running scripts ====================================================
echo "===== Setting up running scripts folder."
docker container exec ${TESP_CONT} /bin/bash -c 'RUN_SCR_DIR=RunningScripts && cd ${TESP} && mkdir ${RUN_SCR_DIR} && \
  cp /tmp/scenarioData/RunningScripts-20180516/tespTE30.py ${TESP}/${RUN_SCR_DIR} && \
  cp /tmp/scenarioData/RunningScripts-20180516/tespTE30_20180521.yaml ${TESP}/${RUN_SCR_DIR} && \
  cp /tmp/scenarioData/RunningScripts-20180516/fncs.py.DockerVersion ${TESP}/${RUN_SCR_DIR}/fncs.py && \
  cp /tmp/scenarioData/RunningScripts-20180516/runTE30_ChallengePYPOWER_20180516.sh ${TESP}/${RUN_SCR_DIR} && \
  cp /tmp/scenarioData/RunningScripts-20180516/runGUITE30Challenge.sh ${TESP}/${RUN_SCR_DIR} && \
  chmod u+x ${TESP}/${RUN_SCR_DIR}/runTE30_ChallengePYPOWER_20180516.sh && \
  chmod u+x ${TESP}/${RUN_SCR_DIR}/runGUITE30Challenge.sh'

# =================== FNCS settings =========================================================
echo "===== Setting up FNCS paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${FNCS_INSTALL}/bin/playerFiles; then rmdir ${FNCS_INSTALL}/bin/playerFiles; mkdir ${FNCS_INSTALL}/bin/playerFiles; else mkdir ${FNCS_INSTALL}/bin/playerFiles; fi && \
  if test -e ${FNCS_INSTALL}/bin/outputFiles; then rmdir ${FNCS_INSTALL}/bin/outputFiles; mkdir ${FNCS_INSTALL}/bin/outputFiles; else mkdir ${FNCS_INSTALL}/bin/outputFiles; fi'

# ================== GridLAB-D settings ============================================================
echo "===== Setting up GridLAB-D paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${GLD_INSTALL}/bin/modelFiles; then rmdir ${GLD_INSTALL}/bin/modelFiles; mkdir ${GLD_INSTALL}/bin/modelFiles; else mkdir ${GLD_INSTALL}/bin/modelFiles; fi && \
  if test -e ${GLD_INSTALL}/bin/inputFilesTE30; then rmdir ${GLD_INSTALL}/bin/inputFilesTE30; mkdir ${GLD_INSTALL}/bin/inputFilesTE30; else mkdir ${GLD_INSTALL}/bin/inputFilesTE30; fi && \
  if test -e ${GLD_INSTALL}/bin/outputFiles; then rmdir ${GLD_INSTALL}/bin/outputFiles; mkdir ${GLD_INSTALL}/bin/outputFiles; else mkdir ${GLD_INSTALL}/bin/outputFiles; fi && \
  cp /tmp/scenarioData/GridLABD/modelFiles-20180516/* ${GLD_INSTALL}/bin/modelFiles && \
  cp -R /tmp/scenarioData/GridLABD/inputFilesTE30/ ${GLD_INSTALL}/bin/'

# =================== Energy Plus settings =========================================================
echo "===== Settting up Energy Plus paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUS_INSTALL}/outputFiles; then rmdir ${EPLUS_INSTALL}/outputFiles; mkdir ${EPLUS_INSTALL}/outputFiles; else mkdir ${EPLUS_INSTALL}/outputFiles; fi && \
  cp /tmp/scenarioData/EnergyPlus/eplus.yaml ${EPLUS_INSTALL} && \
  cp /tmp/scenarioData/EnergyPlus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw ${EPLUS_INSTALL} && \
  cp /tmp/scenarioData/EnergyPlus/SchoolDualController.idf ${EPLUS_INSTALL}'

# =================== Energy Plus JSON settings =========================================================
echo "===== Setting up Energy Plus JSON paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${EPLUSJSON_INSTALL}/outputFiles; then rmdir ${EPLUSJSON_INSTALL}/outputFiles; mkdir ${EPLUSJSON_INSTALL}/outputFiles; else mkdir ${EPLUSJSON_INSTALL}/outputFiles; fi && \
  cp /tmp/scenarioData/EnergyPlusJSON-20180516/eplus_json.yaml ${EPLUSJSON_INSTALL}'

# =================== PyPower settings =========================================================
echo "===== Settting up PyPower paths and folders."
docker container exec ${TESP_CONT} /bin/bash -c 'if test -e ${PYPOWER_INSTALL}/outputFiles; then rmdir ${PYPOWER_INSTALL}/outputFiles; mkdir ${PYPOWER_INSTALL}/outputFiles; else mkdir ${PYPOWER_INSTALL}/outputFiles; fi && \
  cp /tmp/scenarioData/PyPower-20180516/NonGLDLoad.txt ${PYPOWER_INSTALL} && \
  cp /tmp/scenarioData/PyPower-20180516/ppcasefile.py ${PYPOWER_INSTALL} && \
  cp /tmp/scenarioData/PyPower-20180516/pypowerConfig_TE30dispload.yaml ${PYPOWER_INSTALL} && \
  cp /tmp/scenarioData/PyPower-20180516/TE30_ChallengePYPOWER_m_dict.json ${PYPOWER_INSTALL}'

# =================== Agents settings =========================================================
echo "===== Settting up Agents paths and folders."
docker container exec ${TESP_CONT} /bin/sh -c 'if test -e ${AGENTS_INSTALL}/inputFiles; then rmdir ${AGENTS_INSTALL}/inputFiles; mkdir ${AGENTS_INSTALL}/inputFiles; else mkdir ${AGENTS_INSTALL}/inputFiles; fi && \
  if test -e ${AGENTS_INSTALL}/outputFiles; then rmdir ${AGENTS_INSTALL}/outputFiles; mkdir ${AGENTS_INSTALL}/outputFiles; else mkdir ${AGENTS_INSTALL}/outputFiles; fi && \
  cp -R /tmp/scenarioData/Agents-20180516/inputFiles ${AGENTS_INSTALL}'


# =================== Run TE30 =========================================================
# echo "===== Run script to simulate."
# docker container exec -i ${TESP_CONT} /bin/bash -c 'export TERM=xterm && echo "===== TERM = ${TERM}" && export FNCS_LOG_STDOUT=no && echo "===== FNCS_LOG_STDOUT = ${FNCS_LOG_STDOUT}" && cd ${TESP}/${RUN_SCR_DIR} && python tespTE30.py&'
# docker container exec ${TESP_CONT} /bin/sh -c "export TERM=xterm && cd /tesp/ && ./runTE30ChallengeDocker.sh > te30DockerRun.log &"
# docker container exec ${TESP_CONT} /bin/sh -c "tail -f ${GLD_INSTALL}/bin/outputFiles/gld1_1Subst.out"

# echo "===== Done with running use case. Copying the post processing scripts to the container."
# docker cp ${HOME}/work/CoSimulation/TESP-pypower/outputFiles/process_pypower.py ${TESP_CONT}:${PYPOWER_INSTALL}outputFiles/
# docker cp ${HOME}/work/CoSimulation/TESP-GridLABD1048install/bin/outputFiles/process_gld.py ${TESP_CONT}:${GLD_INSTALL}/bin/outputFiles/
# docker cp ${HOME}/work/CoSimulation/ENERGYPLUS_JSONinstall/outputFiles/process_eplus.py ${TESP_CONT}:${EPLUSJSON_INSTALL}outputFiles/
# docker cp ${HOME}/work/CoSimulation/Agents/outputFiles/TE30_Challenge_PYPOWER_agent_dict.json ${TESP_CONT}:/tesp/AgentsInstall
# docker cp ${HOME}/work/CoSimulation/Agents/outputFiles/process_agents.py ${TESP_CONT}:/tesp/AgentsInstall/
# echo "===== Transferred post-processing files. Let's run."

# USE_CASE="TE30_Challenge_PYPOWER" 

echo "=========================================================================================="

# echo "===== STOP ALL CONTAINERS."
# docker stop $(docker ps -a -q)
# echo "===== REMOVE ALL CONTAINERS."
# docker rm $(docker ps -a -q)
# echo "===== List of containers."
# docker ps -a
#echo "===== Running bash in the container."
docker container exec -it ${TESP_CONT} /bin/bash -c 'stty cols 200 rows 60 && bash'
```

(The Linux script has also been modified to account for these changes.)

Once the container is started and the bash command is open, run the simulation
```
cd RunningScripts
./runGUITE30Challenge.sh
```