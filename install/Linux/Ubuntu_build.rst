Building on Ubuntu
------------------

This procedure builds all components from scratch. If you've already
built GridLAB-D on your machine, please take note of the specific
GitHub branch requirements for TESP:

- feature/1146 for GridLAB-D
- develop for FNCS
- fncs-v8.3.0 for EnergyPlus

You may also need to upgrade the gcc and g++ compilers. This build 
procedure has been tested on a clean virtual machine with Ubuntu 16.04 
LTS and gcc/g++ 5.4.0.

When you finish the build, try :ref:`RunExamples`.


Preparation - Python Packages, Java, build tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 sudo apt-get install git
 sudo apt-get install build-essential
 sudo apt-get install autoconf
 sudo apt-get install libtool
 sudo apt-get install cmake
 sudo apt-get install libjsoncpp-dev
 # Java 8 is required; the following works on Ubuntu 16.04
 sudo apt-get install default-jdk
 # a non-vi text editor, if desired
 sudo apt-get install emacs24

 mkdir ~/src
 cd ~/src
 # may need sudo on the following steps to install for all users
 wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
 chmod +x Miniconda3-latest-Linux-x86_64.sh
 # during following install, accept the choice of adding Miniconda to your PATH
 ./Miniconda3-latest-Linux-x86_64.sh
 conda update conda
 conda install pandas
 # tesp_support, including verification of PYPOWER dependency
 pip install tesp_support
 opf

Checkout PNNL repositories from github
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src
 git config --global user.name "your user name"
 git config --global user.email "your email"
 git clone -b develop https://github.com/FNCS/fncs.git
 git clone -b feature/1146 https://github.com/gridlab-d/gridlab-d.git
 git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git
 git clone -b master https://github.com/pnnl/tesp.git

Choosing and Configuring the Install Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Consistent with instructions for other PNNL software that uses FNCS, we will
use the environment variable $FNCS_INSTALL to specify where all executables and
libraries will be installed.  If you have the permissions and only need one 
version of TESP, FNCS and GridLAB-D, you may install everything into /usr/local,
which is the default value of $FNCS_INSTALL. In this case, leave out all 
configuration parameters that reference $FNCS_INSTALL in the instructions below.

If you don't have administrative permission for /usr/local, or you want to maintain
multiple versions, then you must specify and use $FNCS_INSTALL. For example, 
a directory called *FNCS_install* under your home directory. The following example
is for Ubuntu; other flavors of Linux may differ.

::

 sudo emacs /etc/environment
 # or sudo gedit /etc/environment
 #
 # add these two lines in the *environment* file, and save it:
 #
 FNCS_INSTALL="$HOME/FNCS_install"
 GLPATH="$FNCS_INSTALL/lib/gridlabd:$FNCS_INSTALL/share/gridlabd"
 #
 # Use this command before proceeding with the subsequent build steps
 #
 source /etc/environment

FNCS with Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src
 wget --no-check-certificate http://download.zeromq.org/zeromq-4.1.3.tar.gz
 tar -xzf zeromq-4.1.3.tar.gz
 cd zeromq-4.1.3
 ./configure --without-libsodium --prefix=$FNCS_INSTALL
 make
 sudo make install

 cd ..
 wget --no-check-certificate http://download.zeromq.org/czmq-3.0.2.tar.gz
 tar -xzf czmq-3.0.2.tar.gz
 cd czmq-3.0.2
 ./configure 'CPPFLAGS=-Wno-format-truncation' --prefix=$FNCS_INSTALL --with-libzmq=$FNCS_INSTALL
 make
 sudo make install

 cd ../fncs
 autoreconf -if
 ./configure 'CXXFLAGS=-w' 'CFLAGS=-w' --prefix=$FNCS_INSTALL --with-zmq=$FNCS_INSTALL
 make
 sudo make install

 cd java
 mkdir build
 cd build
 cmake ..
 make
 cp fncs.jar ~/src/tesp/examples/loadshed/java
 cp libJNIfncs.so ~/src/tesp/examples/loadshed/java

GridLAB-D with Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src/gridlab-d
 autoreconf -isf

 cd third_party
 tar -xvzf xerces-c-3.1.1.tar.gz
 cd xerces-c-3.1.1
 ./configure 'CXXFLAGS=-w' 'CFLAGS=-w'
 make
 sudo make install
 cd ../..

 # for debugging ./configure --with-fncs=$FNCS_INSTALL 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -g -O0'
 ./configure --with-fncs=$FNCS_INSTALL 'CXXFLAGS=-w' 'CFLAGS=-w'

 sudo make
 sudo make install
 gridlabd --validate 

EnergyPlus with Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src/EnergyPlus
 mkdir build
 cd build
 cmake ..
 make

 # Before installing, we need components of the public version, including but not limited to the critical Energy+.idd file
 # The compatible public version is at https://github.com/NREL/EnergyPlus/releases/tag/v8.3.0
 # That public version should be installed to /usr/local/EnergyPlus-8-3-0 before going further

 sudo make install

 # Similar to the experience with Mac and Windows, this installation step wrongly puts
 #  the build products in /usr/local instead of /usr/local/bin and /usr/local/lib
 #  the following commands will copy FNCS-compatible EnergyPlus over the public version
 cd /usr/local
 cp energyplus-8.3.0 EnergyPlus-8-3-0
 cp libenergyplusapi.so.8.3.0 EnergyPlus-8-3-0

 # if ReadVarsESO is not found at the end of a simulation, try this
 /usr/local/EnergyPlus-8-3-0$ sudo ln -s PostProcess/ReadVarsESO ReadVarsESO

Build eplus_json
~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/src/energyplus
 # the following steps are also in go.sh
 autoheader
 aclocal
 automake --add-missing
 autoconf
 ./configure --prefix=$FNCS_INSTALL --with-zmq=$FNCS_INSTALL
 make
 sudo make install

Prepare for Testing
~~~~~~~~~~~~~~~~~~~

This command ensures Ubuntu will find all the new libraries, 
before you try :ref:`RunExamples`.

::

 sudo ldconfig

If you have both Python 2 and Python 3 installed, the TESP example
scripts and post-processing programs need to find Python 3 first.

::

 emacs ~/.profile
 #
 # edit the line with PATH as follows, to put Python 3 before other
 # directories in the path, and then save the file
 #
 PATH="$HOME/miniconda3/bin:$HOME/bin: and more directories"

TODO: MATPOWER, MATLAB Runtime (MCR) and wrapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src/tesp/src/matpower/ubuntu
 ./get_mcr.sh
 mkdir temp
 mv *.zip temp
 cd temp
 unzip MCR_R2013a_glnxa64_installer.zip
 ./install  # choose /usr/local/MATLAB/MCR/v81 for installation target directory
 cd ..
 make

 # so far, start_MATPOWER executable is built
 # see MATLAB_MCR.conf for instructions to add MCR libraries to the Ubuntu search path
 # unfortunately, this creates problems for other applications, and had to be un-done.
 # need to investigate further: 
 # see http://sgpsproject.sourceforge.net/JavierVGomez/index.php/Solving_issues_with_GLIBCXX_and_libstdc%2B%2B 


