Installing on Linux
-------------------

The following procedure was tested on a clean installation of Ubuntu 18.04 LTS.
It comes with a minimal *python3* installation. By default there is no *root* user,
but the installing user will need administrative privileges to run *sudo* commands.
The specific procedures may differ for other flavors of Linux, or if other versions
of Python and/or Java have been installed.

1. Download the current Linux TESP installer from https://github.com/pnnl/tesp/releases
2. From a terminal/command window, install the Python and Java prerequisites:

::

 sudo apt install python3-pip
 sudo apt install python3-tk
 pip3 install tesp_support --upgrade
 sudo apt install default-jre
 sudo apt install default-jdk

3. From a terminal/command window, run the TESP installer, changing *0.3.2* to match 
   the version downloaded in step 1. Install **both** the Data and Executable files.

::

 cd ~/Downloads
 chmod +x tesp-0.3.2-linux-x64-installer.run
 sudo ./tesp-0.3.2-linux-x64-installer.run

4. After the installer finishes, it's necessary to give user-level permissions to
   run simulations or add files to the tesp directory. Assuming default locations
   were accepted in step 3, enter the following commands from a terminal/command
   window, using your own *username* and *group*:

::

 cd ~/tesp
 sudo chown -R username:group *

To get started after basic installation:

1. Try the video tutorial at https://github.com/pnnl/tesp/releases
2. Try :ref:`RunExamples` 

You may also use the `Docker Version`_. This option is useful for distributed processing, and for 
isolating TESP from your other software, including other versions of GridLAB-D. However, 
it may require a little more data file management.

.. _`Docker Version`: https://github.com/pnnl/tesp/blob/develop/install/Docker/ReadMe.md



