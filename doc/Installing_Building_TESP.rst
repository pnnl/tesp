.. toctree::
    :maxdepth: 2

Installing and Building TESP
****************************

TESP, as a software platform, provides much of its functionality through third-party software that it integrates to provide the means of performing transactive analysis. All of this software is open-source and in every case can be built on any of the three major OSs (Mac, Windows, and Linux). That said, TESP itself is only officially supported on Ubuntu Linux simply as a means of reducing the support burden and allowing us, the TESP developers, to add and improve TESP itself without spending the significant time required to ensure functionality across all three OSs. That said, if you're comfortable with building your own software, a quick inspection of the scripts we use to install TESP on Ubuntu Linux will be likely all you need to figure out how to get it built and installed on your OS of choice.

In the past TESP has provided a wide variety of installation methods and this particular method has been chosen for a key reason: it allows you, the user, to pull down the latest version of TESP (which may include bug fixes in a special branch) and having those changes immediately be realized in your installation. Similarly, the live linking of the third-party tools' repositories with git allows similar bugfix changes an upgrades to be readily applied to your installation. This installation method provides not only working executables of all the software but also all of the source code for said tools. In fact, for those that are more daring or have more complex analysis requirements, this installation method allows edits to the source code of any of the software tools and by re-compiling and installing that source (which the installation scripts automate) a custom version of any of the tools can be utilized and maintained in this installation. (We'll cover this in more detail in a dedicated section on customizing TESP. **TODO Add link to appropriate section.**)

Installation Guide
==================

This guide will assume that TESP is being installed on a clean Ubuntu Linux installation. For many, this will be a virtual machine (VM) and the good news is that there is a no-cost means of creating this VM using Oracle's VirtualBox and a Ubuntu Linux disk image.

Creating a Ubuntu Linux VM with VirtualBox
------------------------------------------

- Download Ubuntu disk image
- Download and install VirtualBox
- Create VM with the following specs
- Virtually insert disk image into VM
- Start (boot) VM
- Run Ubuntu full installation
- Install VirtualBox Guest Additions


git clone TESP
-------------

Run TESP installer scripts
--------------------------

Verify installation with autotest.py script
-------------------------------------------
