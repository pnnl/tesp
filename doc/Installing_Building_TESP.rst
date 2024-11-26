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
Once you have a working Ubuntu/WLS2 on Windows installation, the TESP install process is straight-forward. From a command prompt, issue the following commands:

.. code-block:: shell-session
   :caption: TESP installation commands for Ubuntu/WLS2 on Window10

   wget --no-check-certificate https://raw.githubusercontent.com/pnnl/tesp/main/scripts/tesp.sh
   chmod 755 tesp.sh
   ./tesp.sh <Github user name> <Github email address>

In the last line, the optional name and email must be entered in that order, both must be included. For me, it looks like this:

.. code-block:: shell-session
   :caption: TESP sample installation script execution

   ./tesp.sh trevorhardy trevor.hardy@pnnl.gov

Running this script will kick off a process where all latest linux packages are installed, then the Python environment is setup with the required packages installed after that the repositories are cloned locally and compiled one-by-one. Depending on the computing resources available and network bandwidth, this process will generally take a few hours. Due to this length of time, `sudo` credentials will likely expire at one or more points in the build process and will need to be re-entered.

After getting TESP software installed and the executables built, the TESP installation will have created a `tesp` directory the same directory level as the `tesp.sh` script. All installed files are descended from the `tesp` directory.

Setting Up TESP Environment
---------------------------
Prior to running any of the included examples, we need to be sure to set up the compute environment so that the TESP software can be found by the system. The `tespEnv` file is added at the same level as the root `tesp` folder and it contains all the environment configuration.

.. code-block:: shell-session

    source tespEnv
    
You will need to do this every time you open a new terminal. If the computing environment set-up you're using allows it, you can add this command to your ".bashrc" or equivalent so that it is automatically run for you each time you start a terminal session.

Validate TESP installation 
--------------------------
Once the installation process has finished there should be a folder name `tesp` where all the TESP software, data, and models have been installed. There are several progressively more comprehensive ways to validate the TESP installation process.

Check OS can find TESP software
...............................
TESP includes a small script that attempts to run a trivial command with each of the software packages it installs (typically checking the version). The script is located at `~/grid/tesp/scripts/build/versions.sh`. This script runs automatically at the end of the build and install process and produces and output something like this (version numbers will vary):

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

If you see any messages indicating `command not found` if indicates one of the software packages did not install correctly.

Check directory structure
.........................
An easy manual high-level check to see if TESP installed correctly is to look at the directory structure that was installed and make sure everything ended up in the right place. A tree view from top-level `tesp` folder you should see something like this:

.. code-block:: text
 
    grid
    ├── tesp
    ├── venv
    │   ├── bin
    │   │   ├── ...
    │   │   ├── python
    │   │   ├── python3
    │   │   └── python3.8
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
    └── repo
        ├── Ames-V5.0
        ├── EnergyPlus
        ├── fncs
        ├── gridlab-d
        ├── HELICS-src
        ├── Ipopt
        ├── KLU_DLL
        ├── ns-3-dev
        ├── ThirdParty-ASL
        └── ThirdParty-Mumps

Shorter Autotest: Example Subset
...................................
A (relatively) shorter autotest script has been written that tests many (but not all) of the
installed examples to verify the installation was successful. This test can be run as follows
and assumes the commandline prompt '~$' in the TESP root directory:

.. code-block:: shell-session
    :caption: TESP example subset autotest

    ~$ source tespEnv
    (TESP) ~$ cd ~grid/tesp/examples
    (TESP) ~/grid/tesp/examples$ exec python3 autotest.py &> short.log &
    (TESP) ~/grid/tesp/examples$ deactivate
    ~/grid/tesp/examples$


The first command is essential after starting a terminal session prior to running anything in
TESP for the first time. After running the first line above, the prompt now shows the prefix `(TESP)` being used for the variable environment.
If you don't run the first line, simulations will generally fail for lack of being able to find their dependencies.
If things aren't working, double-check to make sure your commandline shows the prefix `(TESP)`.

The forth command, 'deactivate', returns the environment path to the state it was before the the first command started and remove the `(TESP)` prefix from the prompt.
All other environment variables are present but the TESP python requirements may/may not be present, depending on your configuration.
   
The commandline that ran this autotest was executed in the background, so that can close the terminal, but don't close the VM. You can open terminal later and check progress by viewing the short.log.
Even this subset of examples can take several hours to run (roughly 4.9 hours in the results shown below) and at the end, prints a final results table showing the runtime in seconds for each test:

.. code-block:: text

    Test Case(s)                       Time Taken
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

Total runtime will depend on the compute resources available and each example run serially.

Longer Autotest: Remaining examples
............................................

.. code-block:: shell-session
    :caption: TESP remaining examples autotest

    ~$ source tespEnv
    (TESP) ~$ cd ~/grid/tesp/examples
    (TESP) ~/grid/tesp/examples$ exec python3 autotest_long.py &> long.log &

The commandline that ran this autotest was executed in the background, so that can close the terminal, but don't close the VM. You can open terminal later and check progress by viewing the long.log.
This subset of examples can take several days to run (roughly 49.8 hours in the results shown below) and at the end, prints a final results table showing the runtime in seconds for each test:

.. code-block:: text

    Test Case(s)                     Time Taken
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

Alternate Installation Installs
===============================



Windows-Based Installation with Docker
--------------------------------------

For those not running on a Linux-based system, TESP is also distributed
via a Docker image that can be run on Windows, macOS, and Linux.

Install Docker
..............

For Windows and macOS, Docker is generally installed via `Docker
Desktop <https://www.docker.com/products/docker-desktop/>`__, a GUI app
that installs the Docker engine and allows containers to be run locally.
For Linux, the “docker” app is almost certainly available via the
package manager appropriate for your installation.

Pull TESP Docker Image from Docker Hub
......................................

The TESP Docker image is available on Docker Hub in the “PNNL” channel.

Clone TESP Repo
...............

Though the goal of the Docker image is to provide a consistent execution
environment, in the case of TESP having the TESP repository cloned
locally plays a roll in getting the container started properly. Thus,
cloning in the TESP respository is necessary.

`git clone https://github.com/pnnl/tesp.git`

Entering the Docker to Use TESP
...............................

With the Docker image pulled and the repository cloned in, it is
possible to start the Docker container interactively, effectively giving
you a Linux command-line prompt with a working TESP installation. To
launch the container like this, two launch scripts are provided in the
TESP repository.

Linux and macOS: “tesp/helper/runtesp.sh” Windows:
“tesp/helper/runtesp.bat”

Running these scripts from the command line will return a Linux prompt
and any of the TESP examples and autotests described in
:ref:`local_build_installation` will run successfully.

Running TESP with a Local Model or Code
.......................................

The TESP container has been constructed in such a way that the entire
contents of the TESP repository that have been cloned in locally are
visible inside the TESP container in the “/home/worker/tesp” folder.
This means any files placed in the TESP repo folder on the host OS will
be visible and executable from within the container. For example, if you
create a GridLAB-D model called “model.glm” and place it in the TESP
repository folder (“tesp”), you can enter the TESP container and run it
with GridLAB-D:

``gridlabd /home/worker/tesp/model.glm``


Windows-Based Installation with Linux server
--------------------------------------------

What you will need (as a windows user)
......................................

-  A python IDE (integrated development environment)

   -  VS Code or PyCharm

-  A python package manager

   -  Python, Anaconda, conda, pip, or similar

-  mobaxterm: https://mobaxterm.mobatek.net/

   -  Download and install

Setup an environment and install TESP through the server
........................................................

-  mobaxterm

   -  Download and install

   -  Connect using ssh session of mobaxterm into a linux computing resources

      -  Note that you need to request access individually
      -  Session -> new session -> user@resource.company.com
      -  Enter password

-  vscode (code)

   -  Install from the command line in mobaxterm:
      ::

         sudo apt install snapd
         sudo snap install --classic code

   -  Here is how to start the environment and pycharm and capture pycharm log for any errors from the terminal:
      ::

         source ~/grid/tesp/tesp.env
         code &> ~/code.log&

   -  To kill sessions from the terminal: ``killall code``

-  pycharm (pycharm-community)

   -  Install from the command line in mobaxterm:
      ::

         sudo apt install snapd
         sudo snap install pycharm-community --classic

   -  Here is how to start the environment and pycharm and capture pycharm log for any errors from the terminal:
      ::

         source ~/grid/tesp/tesp.env
         pycharm-community &> ~/charm.log&

   -  To kill sessions from the terminal: ``killall pycharm-community``

Windows-Based Installation with TESP clone only
-----------------------------------------------
For those Windows user want to run only windows.
No grid applications are available other GridLABD.  GridLABD can be install from here.

What you will need (as a windows user)
......................................

-  A python IDE (integrated development environment)

   -  VS Code or PyCharm

-  A python package manager

   -  Python, Anaconda, conda, pip, or similar

Setup an environment and install TESP through Windows
.....................................................

-  Create a tesp environment, e.g.``win-tesp``. Using Conda, from the terminal:
   ::

      conda create --name win-tesp python=3.10

-  Install pip. Using Conda, from the terminal:
   ::

      conda install pip

-  Clone the tesp repository: https://github.com/pnnl/tesp. VS Code `Git
   Instructions <https://code.visualstudio.com/docs/sourcecontrol/intro-to-git#:~:text=To%20clone%20a%20repository%2C%20run,to%20clone%20to%20your%20machine>`__

-  Install TESP. From the terminal:
   ::

      cd [tesp_directory]
      pip install -r requirements.txt

-  Add the tesp directory as environment variable ``TESPDIR``

   -  Navigate to Settings -> Environment Variables -> New

      -  Variable name: ``TESPDIR``
      -  Variable value: ``C:\Users\Name\path_to_tesp_directory``

   -  Once set, restart computer to take effect.


Trouble-shooting Installation (forthcoming)
-------------------------------------------
 
