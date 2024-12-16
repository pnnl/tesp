.. 
    _ Copyright (c) 2021-2023 Battelle Memorial Institute
    _ file: Installing_Building_TESP.rst
    
.. toctree::
    :maxdepth: 2

.. _local_build_installation:

Installing and Building TESP
****************************
TESP, as a software platform, provides much of its functionality through third-party software that it integrates to provide the means of performing transactive analysis. All of this software is open-source and in every case can be built on any of the three major OSs (Mac, Windows, and Linux). That said, TESP itself is only officially supported on Ubuntu Linux simply as a means of reducing the support burden and allowing us, the TESP developers, to add and improve TESP itself without spending the significant time required to ensure functionality across all three OSs. If you're comfortable with building your own software, a quick inspection of the build scripts we use to install TESP on Ubuntu Linux will be likely all you need to figure out how to get it built and installed on your OS of choice.

The current supported method uses a set of custom build scripts to download source code from public repositories and build from source. This particular method was chosen for a key reason: it allows you, the user, to pull down the latest version of TESP (which may include bug fixes in a special branch) and have those changes quickly be realized in your installation. Similarly, the live linking of the third-party tools' repositories with git allows similar bugfix changes and upgrades to those tools to be readily applied to your installation. This installation method provides not only working executables of all the software but also all of the source code for said tools. In fact, for those that are more daring or have more complex analysis requirements, this installation method allows edits to the source code of any of the software tools and by re-compiling and installing that source (which the installation scripts automate) a custom version of any of the tools can be utilized and maintained in this installation. (We'll cover this in more detail in a dedicated section on customizing TESP in :doc:`Developing_Customizing_TESP`.)

Create a Github account (somewhat optional)
===========================================
Many of the repositories holding the source code for the simulation tools used in TESP are hosted on Github. If you want to be able to push code back up to these repositories, you'll need a Github account. The Github user name and email are typically provided as part of running the TESP install script but are technically optional and can be omitted. TESP will still install but the ability to commit back into the repository will not exist.

Installation Guide
==================
This guide will assume that TESP is being installed on a clean Ubuntu Linux installation or Windows 10 using WSL2.

For many, this will be a virtual machine (VM) and the good news is that there is a no-cost means of creating this VM using Oracle's `VirtualBox <https://www.virtualbox.org>`_. Other commercial virtualization software such as VMWare and Parallels will also do the trick.

For Windows 10 users we can use WSL2. In many ways a it is like a virtual machine that allows shell commands just as if it were Linux.

There are other `Alternate Installation Installs <altinstalls_>`__ can be achieved

Creating a Ubuntu Linux VM with VirtualBox
------------------------------------------
There is lots of documentation out there on installing Ubuntu on a VirtualBox VM and we won't rehash those instructions here. Below are a few links you can try:

- `Install Ubuntu on Oracle VirtualBox <https://brb.nci.nih.gov/seqtools/installUbuntu.html?>`_
- `How to Install Ubuntu on VirtualBox? Here’s the Full Guide <https://www.minitool.com/partition-disk/how-to-install-ubuntu-on-virtualbox.html>`_
- `How to install Ubuntu on VirtualBox <https://www.freecodecamp.org/news/how-to-install-ubuntu-with-oracle-virtualbox/>`_

You can get the OS disk image (.iso) `from Ubuntu <https://ubuntu.com/download/desktop>`_ and mount it in the virtual machine for installation. Alternatively, `OSboxes <https://www.osboxes.org/virtualbox-images/>`_ provides a hard drive image with the OS already installed that you can install in your virtual machine.

A few notes:
    - Installing TESP will require building (compiling) software from source which is generally resource intensive. Giving the VM lots of compute resources (CPUs, memory) will be very helpful when installing (and running) TESP.
    - However you install Ubuntu, there is a good chance that some of the software included in the installation is out of date since the image was made. Ubuntu should prompt you to update the software but if it doesn't manually run the "Update Software" application, otherwise TESP install will do for you.
    - Make sure you install the VirtualBox Guest Additions to improve the integration with the host OS and the overall user experience.
    - Administrative access for the account where TESP will be installed is required.

Creating a WLS2 on Windows 10
------------------------------
The setup procedure for creating a WLS2 on Windows 10 very easy with these `instructions <https://learn.microsoft.com/en-us/windows/wsl/install>`_ . However, some further adjustments maybe necessary with permissions and proxy.

Running TESP install script
---------------------------
Once you have a working installation (Ubuntu or WLS2 on Windows), the TESP install process is straight-forward. From a command prompt, issue the following commands:

.. code-block:: shell-session
   :caption: TESP installation commands for Ubuntu/WLS2 on Window10

   wget --no-check-certificate https://raw.githubusercontent.com/pnnl/tesp/main/scripts/tesp.sh
   chmod 755 tesp.sh
   ./tesp.sh <Github user name> <Github email address>

In the last line, the optional name and email must be entered in that order, both must be included. For me, it looks like this:

.. code-block:: shell-session
   :caption: TESP sample installation script execution

   ./tesp.sh trevorhardy trevor.hardy@pnnl.gov

**Important note:** we've seen some trouble with TESP building and/or running correctly in conda virtual environments, even the base virtual environment. For this reason, we recommend that all conda environments be deactivated before installing TESP (``conda deactivate``).  TESP sets up its own virtual environment ("GRID") using the Python "venv" library that is activated with the ``source tesp.env`` command. Any additional software or Python libraries you may want to install can be done after activating this TESP-specific library.

Running this script will kick off a process where all latest pre-requisite Linux packages are installed, then the Python environment is setup with the required packages installed, and after that the repositories are cloned locally and compiled one-by-one. Depending on the computing resources available and network bandwidth, this process will generally take a few hours. Due to this length of time, ``sudo`` credentials will likely expire at one or more points in the build process and will need to be re-entered.

After getting TESP software installed and the executables built, the TESP installation will have created a "grid" directory on the same directory level as the "tesp.sh" script. All installed files are within the "grid" folder.

Setting Up TESP Environment
---------------------------
Prior to running any of the included examples, we need to be sure to set up the compute environment so that the TESP software can be found by the system. The "tesp.env" file is located at ``grid/tesp/tesp.env`` and it contains all the environment configuration.

.. code-block:: shell-session

    source tesp.env
    
You will need to do this every time you open a new terminal. If the computing environment set-up you're using allows it, you can add this command to your ".bashrc" or equivalent so that it is automatically run for you each time you start a terminal session.

Validate TESP installation 
--------------------------
There are several progressively more comprehensive ways to validate the TESP installation process.

Check OS can find TESP software
...............................
TESP includes a small script that attempts to run a trivial command with each of the software packages it installs (typically checking the version). The script is located at ``grid/tesp/scripts/build/versions.sh``. This script runs automatically at the end of the build and install process and produces and output something like this (version numbers will vary):

.. code-block:: text

    ++++++++++++++  Compiling and Installing TESP software is complete!  ++++++++++++++

    TESP software modules installed are:

    TESP 1.3.6
    FNCS installed
    HELICS 3.5.3-main-g389bc8929 (2024-11-18)
    HELICS Java, 3.5.3-main-g389bc8929 (2024-11-18)

    GridLAB-D 5.21.0-19775 (0affdba1:master:Modified) 64-bit LINUX RELEASE
    EnergyPlus, Version 9.3.0-fd4546e21b (No OpenGL)
    NS-3 installed
    Ipopt 3.13.2 (x86_64-pc-linux-gnu), ASL(20190605)

    ++++++++++++++  TESP has been installed! That's all folks!  ++++++++++++++

If you see any messages indicating ``command not found`` if indicates one of the software packages did not install correctly.


Shorter Autotest: Example Subset
...................................
A (relatively) shorter autotest script has been written that tests many (but not all) of the
installed examples to verify the installation was successful. This test can be run as follows
and assumes the commandline prompt '~$' in the TESP root directory:

.. code-block:: shell-session
    :caption: TESP example subset autotest

    ~$ source tesp.env
    (TESP) ~$ cd grid/tesp/examples
    (TESP) ~/grid/tesp/examples$ ./autotest.sh
    (TESP) ~/grid/tesp/examples$ deactivate
    ~/grid/tesp/examples$


The first command is essential after starting a terminal session prior to running anything in TESP for the first time. After running the first line above, the prompt now shows the prefix "(GRID)" being used for the variable environment. If you don't run the first line, simulations will generally fail for lack of being able to find their dependencies. If things aren't working, double-check to make sure your commandline shows the prefix "(GRID)".

The forth command, 'deactivate', returns the environment path to the state it was before the the first command started and remove the "(GRID)" prefix from the prompt.
All other environment variables are present but the TESP python requirements may/may not be present, depending on your configuration.
   
The commandline that ran this autotest was executed in the background, so that can close the terminal, but don't close the VM. You can open terminal later and check progress by viewing the short.log. Even this subset of examples can take several hours to run (roughly 4.9 hours in the results shown below) and at the end, prints a final results table showing the runtime in seconds for each test:

.. code-block:: text

    Test Case(s)                  Time(sec) Taken
    =============================================
    GridLAB-D Player/Recorder            0.891868
    Loadshed - HELICS ns-3               4.129848
    Loadshed - HELICS Python             1.014755
    Loadshed - HELICS Java               4.055216
    Loadshed - HELICS/EPlus             11.930494
    Establishing baseline results       70.629668
    Load shedding w/o comm network      70.957783
    Load shedding over comm network    368.501483
    PYPOWER - HELICS                     5.283039
    Houston,TX Baselines build types  1183.537504
    Generated EMS/IDF files - HELICS     1.555593
    EnergyPlus EMS - HELICS              6.210505
    Weather Agent - HELICS               8.205831
    Houses                             180.550353
    TE30 - HELICS Market               297.990520
    TE30 - HELICS No Market            301.580143
    4 Feeders - HELICS                 824.673296
    Eplus w/Comm - HELICS              432.880265
    No Comm Base - HELICS             3289.462584
    Eplus Restaurant - HELICS         2958.467020
    SGIP1c - HELICS                   3087.110814

Total runtime will depend on the compute resources available and each example runs serially.

Longer Autotest: Remaining examples
............................................

.. code-block:: shell-session
    :caption: TESP remaining examples autotest

    ~$ source tespEnv
    (TESP) ~$ cd ~/grid/tesp/examples
    (TESP) ~/grid/tesp/examples$ ./autotest_long.sh

The commandline that ran this autotest was executed in the background, so that can close the terminal, but don't close the VM. You can open terminal later and check progress by viewing the long.log. This subset of examples can take several days to run (roughly 49.8 hours in the results shown below) and at the end, prints a final results table showing the runtime in seconds for each test:

.. code-block:: text

    Test Case(s)                Time(sec) Taken
    ===========================================
    SGIP1a - HELICS                14132.360023
    SGIP1b - HELICS                14143.111387
    SGIP1c - HELICS                15305.805641
    SGIP1d - HELICS                17289.504798
    SGIP1e - HELICS                19784.953376
    SGIP1ex - HELICS               19623.103407
    PNNL Team IEEE8500                 0.023067
    PNNL Team 30 - HELICS             98.790637
    PNNL Team ti30 - HELICS          103.635829
    PNNL Team 8500 - HELICS        13872.056659
    PNNL Team 8500 TOU - HELICS    13375.151752
    PNNL Team 8500 Volt - HELICS   13513.567733
    PNNL Team 8500 Base            12338.000525
    PNNL Team 8500 VoltVar         13278.476238
    PNNL Team 8500 VoltWatt        12584.246679

.. _altinstalls:

Alternate Installation Methods
==============================

Windows- or macOS-Based Installation with Docker
------------------------------------------------

For those not running on a Linux-based system, TESP is also distributed via a Docker image that can be run on Windows (with WSL 2), macOS, and Linux. The TESP Docker containers are created to mount the locally cloned TESP respository folder such that anything placed in this folder is visible inside the Docker containers. This allows users to place custom code, model, and datasets in this folder and use them with applications in the Docker containers.

The biggest downside to using the Docker containers is that customization of any of the compiled tools (_e.g._ GridLAB-D) is not possible without rebuilding the appropriate Docker image. 

Install Docker
..............

For Windows and macOS, Docker is generally installed via `Docker Desktop <https://www.docker.com/products/docker-desktop/>`__, a GUI app that installs the Docker engine and allows containers to be run locally. For Linux, the “docker” app is almost certainly available via the package manager appropriate for your installation.

Pull TESP Docker Image from Docker Hub
......................................

The TESP Docker image is available on Docker Hub in the `"pnnl/tesp channel" <https://hub.docker.com/repository/docker/pnnl/tesp/general>`_.

Clone TESP Repo
...............

Though the goal of the Docker image is to provide a consistent execution environment, to get Docker set up properly for TESP it is necessary to have a local clone of the respository.

.. code-block:: shell-session

   $ git clone https://github.com/pnnl/tesp.git

Entering the Docker to Use TESP
...............................

With the Docker image pulled and the repository cloned in, it is possible to start the Docker container interactively, effectively giving you a Linux command-line prompt with a working TESP installation. Before you begin, make sure to login to the docker with `docker login`. To launch the container, two launch scripts are provided in the TESP repository depending on your OS.

* Linux and macOS: :code:`$ tesp/scripts/helpers/runtesp.sh`
* Windows: :code:`$ tesp/scripts/helpers/runtesp.bat`

Running these scripts from the command line will return a Linux prompt and any of the TESP examples and autotests described in :ref:`local_build_installation` will run successfully.

Running TESP with a Local Model or Code
.......................................

The TESP container has been constructed in such a way that the entire contents of the local TESP repository are visible inside the TESP container in the “/home/worker/tesp” folder. This means any files placed in the TESP repo folder on the host OS (outside the Docker containers) will be visible and executable from within the container. For example, if you create a GridLAB-D model called “model.glm” and place it in the TESP repository folder (“tesp”), you can enter the TESP container and run it with GridLAB-D:

.. code-block:: shell-session

   $ gridlabd /home/worker/tesp/model.glm


TESP API Installation
---------------------
The TESP API is Python-based and provides functionality that doesn't require running simulations. For example, TESP has a GridLAB-D model modification API that can be used by installing the TESP API and without installing GridLAB-D or any other simulation tool.

Installing Tools 
................
Make sure the following tools are installed.

* Python 3 - `Windows needs to install manually <https://www.python.org/downloads/windows/>`_, Linux and macOS generally include it.
*  (optional) An IDE (integrated development environment), `VS Code <https://code.visualstudio.com/download>`_ and `PyCharm CE <https://www.jetbrains.com/pycharm/download/?section=windows>`_ are popular but there are others.
* Package manager - `Anaconda <https://www.anaconda.com/download>`_ or `pip <https://pip.pypa.io/en/stable/installation/>`_ (macOS and Linux generally come with pip already installed).
* git - `Windows installer is here <https://git-scm.com/downloads/win>`_; macOS and Linux already have git installed.
* pip - `Windows installer is here <https://pip.pypa.io/en/stable/installation/>`_; macOS and Linux already have pip installed.


Create a Virtual Environment
............................
A virtual environment is a useful way of isolating software projects from each other such that changing libraries or environment variables in one doesn't affect the operation of the other. It's recommended that users of the TESP API set up a dedicated virtual environment; we'll call it "tesp_env" in this example.

.. code-block:: shell-session
   :caption: Creation and activation of conda virtual environment

   $ conda create -n tesp_env python=3.10
   $ conda activate

.. code-block:: shell-session
   :caption: Creation and activation of venv virtural environment on macOS and Linux

   $ python -m venv /path/to/new/tesp_env
   $ source /path/to/new/tesp_env/bin/activate

.. code-block:: doscon
   :caption: Creation and activation of venv virtural environment on Windows

   C:\> python -m venv /path/to/new/tesp_env
   C:\> path/to/new/tesp_env/Scripts/activate.bat

Installing the TESP API
.......................
Once inside the virtual environment, installing the TESP API is a two-step process: cloning the repository with "git" and installing it with "pip".

.. code-block:: shell-session
   :caption: Cloning and installing TESP API on macOS and Linux

   $ git clone https://github.com/pnnl/tesp.git
   $ cd tesp/src/tesp_support
   $ source /path/to/new/tesp_env/bin/activate
   $ pip install -e .

.. code-block:: doscon
   :caption: Cloning and installing TESP API on Windows

   C:\> git clone https://github.com/pnnl/tesp.git
   C:\> cd tesp/src/tesp_support
   C:\> path/to/new/tesp_env/Scripts/activate.bat
   C:\> pip install -e .


Trouble-shooting Installation
-----------------------------

Docker Integration
..................

If executing the `runtesp.bat` results in the error `docker: Error response from daemon: pull access denied for runtesp, repository does not exist or may require 'docker login'.`

First confirm that you are logged in to docker:

`docker login`

If that still fails, try renormalizing the tesp repository.

.. code-block:: shell-session
    :caption: Renormalize tesp repository

    $ git config --global core.eol lf
    $ git add --update --renormalize
    $ git ls-files -z | xargs -0 rm
    $ git checkout .
 
Docker file access with Linux as the host
.........................................

TESP uses linux group permissions to share files between linux host and docker container.
The 'runner:x:9002' group has been added to the docker image for this purpose.
These instructions are to be run on your host machine.
For the text below, substitute your login name for 'userName', share group name for 'groupName'.

To find out what 'groupName' that might have been used for the id 9002, issue the following command:

.. code-block:: shell-session
    
    $ cat /etc/group | grep 9002

If the group 'groupName:x:9002:...' is found, we need find out what groups your login has, issue the follow command:

.. code-block:: shell-session
    
    $ groups

If the 'groupName' is not a member of the group list, add the 'groupName' to the group list from '$ groups' command above to the user by modifying the 'userName':

.. code-block:: shell-session
    
    $ sudo usermod -aG userName,sudo,groupName userName

If that succeeds, you are now a member of the group and can skip the next paragraph.

If there are no groups with the id 9002, we must add a new group to the system.
Then add the 'groupName' to the group list from '$ groups' command above to the user by modifying 'userName':

.. code-block:: shell-session

    $ sudo addgroup groupName --gid 9002
    $ sudo usermod -aG userName,sudo,groupName userName

Change the directory to your TESP clone directory and set the permissions to use the 'groupName' group for the files.

.. code-block:: shell-session
    
    $ cd ~/grid/tesp
    $ chgrp -R groupName .

