Building on Ubuntu
------------------

This procedure builds all components from scratch. If you've already
built GridLAB-D on your machine, please take note of the specific
GitHub branch requirements for TESP:

- feature/1048 for GridLAB-D
- feature/transactiveEnergyApi for FNCS
- fncs-v8.3.0 for EnergyPlus

When you finish the build, try RunExamples_.


Preparation - Python, Java, build tools, PYPOWER
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 sudo apt-get install git
 sudo apt-get install build-essential
 # Java 8 is required; the following works on Ubuntu 16.04
 sudo apt-get install default-jdk

 cd /opt
 # may need sudo on the following steps to install for all users
 wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
 chmod +x Miniconda3-latest-Linux-x86_64.sh
 ./Miniconda3-latest-Linux-x86_64.sh
 conda update conda
 conda install matplotlib
 conda install scipy
 conda install pandas

 # verify up-to-date PYPOWER
 pip install pypower
 opf

 # a non-vi text editor, if needed
 sudo apt-get install emacs24

Checkout PNNL repositories from github
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 mkdir ~/src
 cd ~/src
 git config --global (specify user.name, user.email, color.ui)
 git clone -b feature/transactiveEnergyApi https://github.com/FNCS/fncs.git
 git clone -b feature/1048 https://github.com/gridlab-d/gridlab-d.git
 git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git
 git clone -b master https://github.com/pnnl/tesp.git

FNCS with Prerequisites (installed to /usr/local)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 cd ~/src
 wget --no-check-certificate http://download.zeromq.org/zeromq-4.1.3.tar.gz
 tar -xzf zeromq-4.1.3.tar.gz
 cd zeromq-4.1.3
 ./configure --without-libsodium
 make
 sudo make install

 cd ..
 wget --no-check-certificate http://download.zeromq.org/czmq-3.0.2.tar.gz
 tar -xzf czmq-3.0.2.tar.gz
 cd czmq-3.0.2
 ./configure 'CPPFLAGS=-Wno-format-truncation'
 make
 sudo make install

 sudo apt-get install autoconf
 sudo apt-get install libtool
 cd ../fncs
 autoreconf -if
 ./configure 'CXXFLAGS=-w' 'CFLAGS=-w'
 make
 sudo make install

 sudo apt-get install cmake
 cd java
 mkdir build
 cd build
 cmake ..
 make
 # then copy jar and jni library to  tesp/src/java

GridLAB-D with Prerequisites (installed to /usr/local)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

 # for debugging ./configure --with-fncs=/usr/local 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -g -O0'
 ./configure --with-fncs=/usr/local 'CXXFLAGS=-w' 'CFLAGS=-w'

 sudo make
 sudo make install
 # setting the GLPATH on Ubuntu; other flavors of Linux may differ
 sudo emacs /etc/environment &
 # within the editor, add the following line to /etc/environment and save it
 GLPATH="/usr/local/lib/gridlabd:/usr/local/share/gridlabd"
 gridlabd --validate 

EnergyPlus with Prerequisites (installed to /usr/local)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

 sudo apt-get install libjsoncpp-dev
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
 ./configure
 make
 sudo make install

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


