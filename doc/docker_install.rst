Docker-Based Installation
=========================

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

Clone TESP rRpo
---------------

Though the goal of the Docker image is to provide a consistent execution
environment, in the case of TESP having the TESP repository cloned
locally plays a roll in getting the container started properly. Thus,
cloning in the TESP respository is necessary.

``git clone https://github.com/pnnl/tesp.git``

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

Any location in the TESP repository folder is fine but it is recommended
for significant project you create a dedicated folder (*e.g.*
“tesp/examples/my_project”) to keep all your custom files separate from
the TESP code.
