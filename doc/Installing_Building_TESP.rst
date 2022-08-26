..
    _ Copyright (C) 2021-2022 Battelle Memorial Institute
    _ file: Installing_Building_TESP.rst


.. toctree::
    :maxdepth: 2

Installing and Building TESP
****************************

TESP, as a software platform, provides much of its functionality through third-party software that it integrates to provide the means of performing transactive analysis. All of this software is open-source and in every case can be built on any of the three major OSs (Mac, Windows, and Linux). That said, TESP itself is only officially supported on Ubuntu Linux simply as a means of reducing the support burden and allowing us, the TESP developers, to add and improve TESP itself without spending the significant time required to ensure functionality across all three OSs. If you're comfortable with building your own software, a quick inspection of the scripts we use to install TESP on Ubuntu Linux will be likely all you need to figure out how to get it built and installed on your OS of choice.

In the past TESP has provided a wide variety of installation methods and the currently supported method uses a set of custom build scripts to download source code from public repositories and build from source. This particular method was chosen for a key reason: it allows you, the user, to pull down the latest version of TESP (which may include bug fixes in a special branch) and have those changes quickly be realized in your installation. Similarly, the live linking of the third-party tools' repositories with git allows similar bugfix changes and upgrades to those tools to be readily applied to your installation. This installation method provides not only working executables of all the software but also all of the source code for said tools. In fact, for those that are more daring or have more complex analysis requirements, this installation method allows edits to the source code of any of the software tools and by re-compiling and installing that source (which the installation scripts automate) a custom version of any of the tools can be utilized and maintained in this installation. (We'll cover this in more detail in a dedicated section on customizing TESP in :doc:`Developing_Customizing_TESP`.)

Installation Guide
==================

This guide will assume that TESP is being installed on a clean Ubuntu Linux installation. For many, this will be a virtual machine (VM) and the good news is that there is a no-cost means of creating this VM using Oracle's `VirtualBox <https://www.virtualbox.org>`_. Other commercial virtualization software such as VMWare and Parallels will also do the trick.

Creating a Ubuntu Linux VM with VirtualBox
------------------------------------------
There is lots of documentation out there on installing Ubuntu on a VirtualBox VM and we won't re-harsh those instructions here. Below are a few links you can try:

- `Install Ubuntu on Oracle VirtualBox <https://brb.nci.nih.gov/seqtools/installUbuntu.html?>`_
- `How to Install Ubuntu on VirtualBox? Here’s the Full Guide <https://www.minitool.com/partition-disk/how-to-install-ubuntu-on-virtualbox.html>`_
- `How to install Ubuntu on VirtualBox <https://www.freecodecamp.org/news/how-to-install-ubuntu-with-oracle-virtualbox/>`_


You can get the OS disk image (.iso) `from Ubuntu <https://ubuntu.com/download/desktop>`_ and mount it in the virtual machine for installation. Alternatively, `OSboxes provides a hard drive image <https://www.osboxes.org/virtualbox-images/>`_ with the OS already installed that you can install in your virtual machine. 

A few notes:
- Installing TESP will require building (compiling) software from source which is generally resource intensive. Giving the VM lots of compute resources (CPUs, memory) will be very helpful when installing (and running) TESP.
- However you install Ubuntu, there is a good chance that some of the software included in the installation is out of date since the image was made. Ubuntu should prompt you to update the software but if it doesn't manually run the "Update Software" application.
- Make sure you install the VirtualBox Guest Additions to improve the integration with the host OS and the overall user experience.
- Administrative access for the account where TESP will be installed is required.

Create a Github account (somewhat optional)
-------------------------------------------
Many of the repositories holding the source code for the simulation tools used in TESP are hosted on Github. If you want to be able to push code back up to these repositories, you'll need a Github account. The Github user name and email are typically provided as part of running the TESP install script but are technically optional and can be omitted. TESP will still install but the ability to commit back into the repository will not exist.

Running TESP install script
---------------------------
Once you have a working Ubuntu installation, the TESP install process is straight-forward. From a command prompt do the following:

.. code-block:: shell-session
   :caption: TESP installation commands

   wget --no-check-certificate https://raw.githubusercontent.com/pnnl/tesp/main/scripts/tesp.sh
   chmod 755 tesp.sh
   ./tesp.sh <Github user name> <Github email address>

For me, the last line looks like this:

.. code-block:: shell-session
   :caption: TESP sample installation script execution

   ./tesp.sh trevorhardy trevor.hardy@pnnl.gov

Running this script will kick off a process where all repositories for the necessary tools are cloned locally and then compiled one-by-one. Depending on the computing resources available and network bandwidth, this process will generally take a few hours. Due to this length of time, `sudo` credentials will likely expire at one or more points in the build process and will need to be re-entered.

The TESP installation will be created at the same level as the `tesp.sh` script.


Setting Up TESP Environment
---------------------------
After getting all the TESP software built, prior to running any of the included examples, be sure to set up the compute environment so that all the new TESP software can be found by the system. The `tespEnv` file is added at the same level as the root `tesp` folder and it contains all the environment configuration you'll need. 

.. code-block:: shell-session

    source tespEnv
    
You'll need to do this every time you open a new terminal. If the computing set-up you're using allows it, you can add this command to your ".bashrc" or equivalent so that it is automatically run for you each time you start a terminal session.


Validate TESP installation 
--------------------------
Once the installation process has finished there should be a folder names `tesp` where all the TESP software, data, and models have been installed. There are several progressively more comprehensive ways to validate the TESP installation process.

Check OS can find TESP software
...............................
TESP includes a small script that attempts to run a trivial command with each of the software packages it installs (typically checking the version). (The script is located at tesp/repository/tesp/scripts/build/versions.sh.) This script runs automatically at the end of the build and install process and produces and output something like this (version numbers will vary):

.. code-block:: text

    ++++++++++++++  Compiling and Installing TESP software is complete!  ++++++++++++++

    FNCS, installed

    HELICS, 3.1.0 (2021-11-24)

    HELICS Java, 3.1.1-main-g9a5726ba9 (2022-04-01)

    GridLAB-D 4.3.0-18941 (Navajo [725bec8d:develop:Mod]) 64-bit LINUX RELEASE

    EnergyPlus, Version 9.3.0-fd4546e21b (No OpenGL)

    NS-3, installed

    Ipopt 3.13.2 (x86_64-pc-linux-gnu), ASL(20190605)

    ++++++++++++++  TESP versions has been installed! That's all folks!  ++++++++++++++


If you see any messages indicating `command not found` if indicates one of the software packages did not install correctly.

Check directory structure
.........................
An easy manual high-level check to see if TESP installed correctly is to look at the directory structure that was installed and make sure everything ended up in the right place. This can easily be done by running `tree -L 3` from inside the top-level `tesp` folder. Your output should look something like this:

.. code-block:: text
 
    tesp
    ├── venv
    │   ├── bin
    │   │   ├── ...
    │   │   ├── python
    │   │   └── python3
    │   ├── man
    │   ├── include
    │   ├── lib
    │   │   └── python3.8
    │   └── share
    │       ├── man
    │       └── doc
    ├── tenv
    │   ├── bin
    │   │   ├── eplus_agent*
    │   │   ├── fncs*
    │   │   ├── gridlabd*
    │   │   ├── helics*
    │   │   ├── ipopt*
    │   │   ├── mini_federate
    │   │   ├── ns3-*
    │   │   └── test_comm
    │   ├── energyplus
    │   │   ├── ...
    │   ├── include
    │   │   ├── coin-or
    │   │   ├── fncs.h
    │   │   ├── fncs.hpp
    │   │   ├── gridlabd
    │   │   ├── helics
    │   │   └── ns3-dev
    │   ├── java
    │   │   ├── fncs.jar
    │   │   ├── helics-2.8.0.jar
    │   │   ├── helics.jar -> helics-2.8.0.jar
    │   │   ├── libhelicsJava.so
    │   │   └── libJNIfncs.so
    │   ├── lib
    │   │   ├── cmake
    │   │   ├── gridlabd
    │   │   ├── libcoinasl.*
    │   │   ├── libcoinmumps.*
    │   │   ├── libfncs.*
    │   │   ├── libhelics*
    │   │   ├── libipoptamplinterface.*
    │   │   ├── libipopt.*
    │   │   ├── libns3*
    │   │   ├── libsipopt.*
    │   │   └── pkgconfig
    │   └── share
    │       ├── doc
    │       ├── gridlabd
    │       ├── helics
    │       ├── java
    │       └── man
    └── repository
        ├── Ames-V5.0
        ├── EnergyPlus
        ├── fncs
        ├── gridlab-d
        ├── HELICS-src
        ├── Ipopt
        ├── KLU_DLL
        ├── ns-3-dev
        ├── tesp
        ├── ThirdParty-ASL
        └── ThirdPart-Mumps

Shorter Autotest: Example Subset
...................................
A (relatively) shorter autotest script has been written that tests many (but not all) of the
installed examples to verify the installation was successful. This test can be run as follows
and assumes the commandline prompt '~$' in the TESP root directory:

.. code-block:: shell-session
    :caption: TESP example subset autotest

    ~$ source tespEnv
    (TESP) ~$ cd tesp/repository/tesp/
    (TESP) ~/tesp/repository/tesp$ python3 autotest.py
    (TESP) ~/tesp/repository/tesp$ deactivate
    ~/tesp/repository/tesp$


The first command is essential after starting a terminal session prior to running anything in
TESP for the first time. After running the first line above, the prompt now shows the prefix `(TESP)` being using for the variable environment.
If you don't run the first line, simulations will generally fail for lack of being able to find their dependencies.
If things aren't working, double-check to make sure your commandline shows the prefix `(TESP)`.

The forth command, 'deactivate', returns the environment path to the state it was before the the first command started and remove the `(TESP)` prefix from the prompt.
All other environment variables are present but the TESP python requirements may/may not be present, depending on your configuration.
   
Even this subset of examples can take several hours to run (roughly 3.5 hours in the results shown below) and at the end, prints a final results table showing the runtime in seconds for each test:

.. code-block:: text


    Test Case(s)                     Time Taken
    ===========================================
    GridLAB-D Player/Recorder          0.033965
    Loadshed - HELICS ns-3             6.103482
    Loadshed - HELICS Python           1.116138
    Loadshed - HELICS Java             1.754056
    PYPOWER - HELICS                   7.025858
    EnergyPlus EMS - HELICS           10.403496
    Weather Agent - HELICS            11.020228
    Houses                           284.137236
    TE30 - HELICS Market             293.542043
    TE30 - HELICS No Market          282.648197
    No Comm Base - HELICS           6138.132330
    Eplus Restaurant - HELICS       4206.033149
    SGIP1c - HELICS                 5104.257472
    Eplus w/Comm - HELICS             64.887238
    4 Feeders - HELICS              1241.105777

Total runtime will depend on the compute resources available and each example run serially.



Longer Autotest: All examples (forthcoming)
............................................


Trouble-shooting Installation (forthcoming)
-------------------------------------------
 
