# Project: Transactive Energy Simulation Platform (TESP) #
## Using a TESP Docker container to develop and run scenario use-cases ##
***************************************
_Author: **Laurentiu Dan Marinovici**_

Copyright (C) 2018-2022, Battelle Memorial Institute
***************************************
Updated 04/17/2019

Currently, there are 2 Docker images containing the TESP, according to the co-simulation environment used, that is:
- **laurmarinovici/tesp:fncs**, which uses [Framework for Network Co-Simulation (FNCS)](https://github.com/FNCS "FNCS") as the co-simulation environment, and contains
  - [FNCS](https://github.com/FNCS/fncs.git "https://github.com/FNCS/fncs.git"), _develop_ branch
  - [GridLAB-D](https://github.com/gridlab-d/gridlab-d.git "https://github.com/gridlab-d/gridlab-d.git"), _feature/1146_ branch
  - [Energy Plus](https://github.com/FNCS/EnergyPlus.git "https://github.com/FNCS/EnergyPlus.git"), _fncs-v8.3.0_ branch
  - [Energy Plus JSON](https://github.com/pnnl/tesp/tree/develop/src/energyplus "https://github.com/pnnl/tesp/tree/develop/src/energyplus")
  - PyPower as part of the _tesp-support_ package in Python
- **laurmarinovici/tesp:helics**, which uses [Hierarchical Engine for Large-scale Infrastructure Co-Simulation (HELICS)](https://github.com/GMLC-TDC/HELICS-src "HELICS") as the co-simulation environment, and contains
  - [HELICS](https://github.com/GMLC-TDC/HELICS-src.git "https://github.com/GMLC-TDC/HELICS-src.git"), _develop_ branch
  - [GridLAB-D](https://github.com/gridlab-d/gridlab-d.git "https://github.com/gridlab-d/gridlab-d.git"), _feature/1146_ branch
  - [ns-3](https://gitlab.com/nsnam/ns-3-dev.git "https://gitlab.com/nsnam/ns-3-dev.git"), _develop_ branch, to which the following modules are added
    - [helics-ns3](https://github.com/GMLC-TDC/helics-ns3.git "https://github.com/GMLC-TDC/helics-ns3.git")
    - [fnss-ns3](https://github.com/fnss/fnss-ns3.git "https://github.com/fnss/fnss-ns3.git")
  - PyPower as part of the _tesp-support_ package in Python

Both images originate from an enhanced Ubuntu 18.04 base, which has all the needed dependencies installed, such as:
  - _xerces_ libraries
  - _zmq_ libraries
  - _boost_ libraries
  - _jsoncpp_ libraries
  - Python libraires, such as _numpy_, _scipy_, _networkx_, _tesp-support_, etc.

In order to be able to pull these images, Docker software needs to be installed. There are desktop versions for [Windows](https://hub.docker.com/editions/community/docker-ce-desktop-windows "https://hub.docker.com/editions/community/docker-ce-desktop-windows") and [MacOS](https://hub.docker.com/editions/community/docker-ce-desktop-mac "https://hub.docker.com/editions/community/docker-ce-desktop-mac") to download from and install, or one could follow the procedure below for installation under Linux.

__Install Docker Community Edition under Linux__

File [Script to install Docker CE on Ubuntu](https://github.com/GRIDAPPSD/gridappsd-docker/blob/master/docker_install_ubuntu.sh "Run this script."), which presents what the docker installation site shows at [Docker installation](https://docs.docker.com/install/linux/docker-ce/ubuntu/ "Online Docker documentation"), can be used as helper to download and install Docker CE on Ubuntu.
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
The script also installs Docker Composer, used to define and run a multi-container Docker application. See [Compose overview](https://docs.docker.com/compose/overview/).

__Warning.__ To be able to run the Docker CLI without needing root, you need a reboot.

### Pre-requisites ###

In order to enable the graphical user interface (GUI) of TESP within its Docker container, X server is needed on the Ubuntu/Mac host computer. Detailed information can be found at [Using GUI's with Docker](http://wiki.ros.org/docker/Tutorials/GUI "http://wiki.ros.org/docker/Tutorials/GUI"), and [Running a GUI application in a Docker container](https://linuxmeerkat.wordpress.com/2014/10/17/running-a-gui-application-in-a-docker-container/ "https://linuxmeerkat.wordpress.com/2014/10/17/running-a-gui-application-in-a-docker-container/"). Therefore, first X server needs to be installed on the host computer.

__On Ubuntu__, at the terminal, run
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

__On Mac__, the X server MacOS counterpart is [XQuartz](https://www.xquartz.org/ "Click to get the dmg"). Once XQuartz is installed, run it at the terminal with
```
open -a XQuartz
```
and in X11 Preferences under Security tab, make sure "Allow connections from network clients" is checked.

Also, _socat_ ([Netcat on steroids :)](http://www.dest-unreach.org/socat/)) needs to be installed. And it will be done using the _brew_ ([Homebrew](https://docs.brew.sh/Installation)), which, if not installed previously, could be installed using
```
ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)" /dev/null
```
Run
```
brew install socat
socat TCP-LISTEN:6000,reuseaddr,fork UNIX-CLIENT:\"$DISPLAY\"&
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

Once the Docker software and pre-requisites are installed, to get access to any of the images, once can go to the terminal window and type
```
docker pull <docker_hub_image_name:tag_name>
```
and that should initiate the download. When downloading has completed, running 
```
  docker images
```
at the terminal should return all the available images that could be used to start the Docker containers.

The script _runFNCS-TESP-Container-Mac.sh_ in the _TESP-Docker-Inputs_ sets and starts the TESP container that includes FNCS as the co-simulation platform on a Mac platform. Here are some notes regarding several of the lines in the bash script.
- Define the Docker image name from which the Docker container is going to be created
```
#!/bin/bash
clear
# 
TESP_REP="laurmarinovici/tesp"
TESP_TAG=":fncs"
TESP_CONT="tespFNCS"
```
- Set the user name and host folders that are going to be mapped inside the container. These are mainly the folders on the host computer where the user could develop agents or other applications that could be tested on the container. They will have to be personalized based on the host platform and location. Also, the _runningScripts_ folder currently contains the scripts to run some of the TESP examples.
```
HOST_FOLDER="$PWD"
HOST_SCRIPTS="$PWD/runningScripts"
TESP_USER="tesp-user"
HOST_EXAMPLE="/Users/mari009/PNNL_Projects/GitHubRepositories/TESP_github/examples"
HOST_SUPPORT="/Users/mari009/PNNL_Projects/GitHubRepositories/TESP_github/support"
HOST_ERCOT="/Users/mari009/PNNL_Projects/GitHubRepositories/TESP_github/ercot"
HOST_AGENTS="/Users/mari009/PNNL_Projects/GitHubRepositories/TESP_github/src/tesp_support/tesp_support"
TESP_SUPPORT="/home/${TESP_USER}/TESP-support/support"
TESP_EXAMPLE="/home/${TESP_USER}/TESP-support/examples"
TESP_ERCOT="/home/${TESP_USER}/TESP-support/ercot"
TESP_AGENTS="/home/${TESP_USER}/TESP-support/TESP-agents"
TESP_SCRIPTS="/home/${TESP_USER}/runningScripts"
```
- If container is already running, turn it off and re-start.
``` 
if (docker inspect -f {{.State.Running}} ${TESP_CONT} &> /dev/null); then
  echo "===== Container ${TESP_CONT} is already running, so I will close and remove it first. ====="
  docker stop ${TESP_CONT}
  docker rm ${TESP_CONT}
fi
```
- Run the container mapping local host folder to container folders, and also setting the XQuartz environment
```
docker run --name ${TESP_CONT} \
                      -dit --rm \
                      -e DISPLAY=$IP:0 \
                      --mount type=bind,source=${HOST_EXAMPLE},destination=${TESP_EXAMPLE} \
                      --mount type=bind,source=${HOST_ERCOT},destination=${TESP_ERCOT} \
                      --mount type=bind,source=${HOST_SUPPORT},destination=${TESP_SUPPORT} \
                      --mount type=bind,source=${HOST_SCRIPTS},destination=${TESP_SCRIPTS} \
                      --mount type=bind,source=${HOST_AGENTS},destination=${TESP_AGENTS} \
                      --mount type=bind,source=/tmp/.X11-unix,destination=/tmp/.X11-unix \
                      --net=host --ipc=host --user=${TESP_USER} \
                      ${TESP_REP}${TESP_TAG}
```
For the Ubuntu platform, the following line should be added
```
--env="QT_X11_NO_MITSHM=1"
```
- Start a terminal window in the container and then make sure the _tesp-support_ module is updated to the latest version.
```
docker container exec -it ${TESP_CONT} /bin/bash -c 'stty cols 200 rows 60 && bash && echo "Updating tesp-support Python package." && pip install --upgrade tesp-support'
```

The scripts in _runningScripts_ folder are written specifically for the structure of the _laurmarinovici/tesp:fncs_ container and are meant to run one certain example at the time, that is _te30_, _comm_, or _ercot_.
