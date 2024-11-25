Windows-Based Installation with Docker
======================================

For those not running on a Linux-based system, TESP is also distributed
via a Docker image that can be run on Windows, macOS, and Linux.

Install Docker
--------------

For Windows and macOS, Docker is generally installed via `Docker
Desktop <https://www.docker.com/products/docker-desktop/>`__, a GUI app
that installs the Docker engine and allows containers to be run locally.
For Linux, the “docker” app is almost certainly available via the
package manager appropriate for your installation.

Pull TESP Docker Image from Docker Hub
--------------------------------------

The TESP Docker image is available on Docker Hub in the “PNNL” channel.

Clone TESP Repo
---------------

Though the goal of the Docker image is to provide a consistent execution
environment, in the case of TESP having the TESP repository cloned
locally plays a roll in getting the container started properly. Thus,
cloning in the TESP respository is necessary.

`git clone https://github.com/pnnl/tesp.git`

Entering the Docker to Use TESP
-------------------------------

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
---------------------------------------

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
============================================

What you will need (as a windows user)
--------------------------------------

-  A python IDE (integrated development environment)

   -  VS Code or PyCharm

-  A python package manager

   -  Python, Anaconda, conda, pip, or similar

-  mobaxterm: https://mobaxterm.mobatek.net/

   -  Download and install

Setup an environment and install TESP through the server
--------------------------------------------------------

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

Windows-Based Installation no with Linux server
===============================================
For those Windows user want to run only windows.
No grid applications are available other GridLABD.  GridLABD can be install from here.

What you will need (as a windows user)
--------------------------------------

-  A python IDE (integrated development environment)

   -  VS Code or PyCharm

-  A python package manager

   -  Python, Anaconda, conda, pip, or similar

Setup an environment and install TESP through Windows
-----------------------------------------------------

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

Full Installation
=================
-  The TESP Read The Docs page walks through this process:
   https://tesp.readthedocs.io/en/latest/Installing_Building_TESP.html

When you’ve successfully completed these steps, you should be able to
activate the environment from your tesp directory. Remember to activate
your environment before attempting to run anything within TESP.

Activate environment: ``source tesp.env``

