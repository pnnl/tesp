.. toctree::
    :maxdepth: 2

Installing and Building TESP
****************************

TESP, as a software platform, provides much of its functionality through third-party software that it integrates to provide the means of performing transactive analysis. All of this software is open-source and in every case can be built on any of the three major OSs (Mac, Windows, and Linux). That said, TESP itself is only officially supported on Ubuntu Linux simply as a means of reducing the support burden and allowing us, the TESP developers, to add and improve TESP itself without spending the significant time required to ensure functionality across all three OSs. If you're comfortable with building your own software, a quick inspection of the scripts we use to install TESP on Ubuntu Linux will be likely all you need to figure out how to get it built and installed on your OS of choice.

In the past TESP has provided a wide variety of installation methods and the currently supported method uses a set of custom build scripts to download source code from public repositories and build from source. This particular method was chosen for a key reason: it allows you, the user, to pull down the latest version of TESP (which may include bug fixes in a special branch) and have those changes quickly be realized in your installation. Similarly, the live linking of the third-party tools' repositories with git allows similar bugfix changes and upgrades to those tools to be readily applied to your installation. This installation method provides not only working executables of all the software but also all of the source code for said tools. In fact, for those that are more daring or have more complex analysis requirements, this installation method allows edits to the source code of any of the software tools and by re-compiling and installing that source (which the installation scripts automate) a custom version of any of the tools can be utilized and maintained in this installation. (We'll cover this in more detail in a dedicated section on customizing TESP in :ref:`Developing and Customizing TESP`.)

Installation Guide
==================

This guide will assume that TESP is being installed on a clean Ubuntu Linux installation. For many, this will be a virtual machine (VM) and the good news is that there is a no-cost means of creating this VM using Oracle's `VirtualBox <https://www.virtualbox.org>`_. Other commercial virtualization software such as VMWare and Parallels will also do the trick.

Creating a Ubuntu Linux VM with VirtualBox
------------------------------------------
There is lots of documentation out there on installing Ubuntu on a VirtualBox VM and we won't re-harsh those instructions here. Below are a few links you can try:

- `Install Ubuntun on Oracle VirtualBox <https://brb.nci.nih.gov/seqtools/installUbuntu.html?`_
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

   wget https://raw.githubusercontent.com/pnnl/tesp/main/scripts/tesp.sh
   chmod 755 tesp.sh
   ./tesp.sh <Github user name> <Github email address>
   
For me, the last line looks like this:

.. code-block:: shell-session
   :caption: TESP sample installation script execution

   ./tesp.sh trevorhardy trevor.hardy@pnnl.gov

Running this script will kick off a process where all repositories for the necessary tools are cloned locally and then compiled one-by-one. Depending on the computing resources available and network bandwidth, this process will generally take a few hours. Due to this length of time, `sudo` credentials will likely expire at one or more points in the build process and will need to be re-entered.

The TESP installation will be created at the same level as the `tesp.sh` script.


Validate TESP installation 
--------------------------
Once the installation process has finished there should be a folder names `tesp` where all the TESP software, data, and models have been installed. There are several progressively more comprehensive ways to validate the TESP installation process.


Check directory structure
.........................
An easy high-level check to see if TESP installed correctly is to look at the directory structure that was installed and make sure everything ended up in the right place. This can easily be done by running `tree` from inside the top-level `tesp` folder. Your output should look something like this:


.. code-block:: none
   :caption: TESP installation abbreviated `tree` output 



Check OS can find TESP software
...............................


Run minimal autotests (forthcoming)
...................................


Run all examples (forthcoming)
..............................


Trouble-shooting Installation
-----------------------------
 
