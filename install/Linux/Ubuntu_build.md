

Xterm setup for Mac OS X (XQuartz) and Windows (MobaXterm)
==========================================================

# This may be necessary for XQuartz
sudo apt-get install xauth

# This is what works for Mac OS X via XQuartz, (i.e. -X fails)
# the MobaXterm connection is similar.
ssh -Y admsuser@172.20.128.10

Prep Steps - Python and some other tools
========================================

sudo apt-get install git
sudo apt-get install build-essential

cd /opt
# may need sudo on the following steps to install for all users
wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux_x86_64.sh
conda update conda
conda install matplotlib
conda install scipy
conda install pandas

# a non-vi text editor
sudo apt-get install emacs24

Checkout PNNL repositories from github
======================================

mkdir ~/src
cd ~/src
git config --global (specify user.name, user.email, color.ui)

git clone -b develop https://github.com/FNCS/fncs.git

git clone -b develop https://github.com/gridlab-d/gridlab-d.git

git clone -b fncs-v8.3.0 https://github.com/FNCS/EnergyPlus.git

git clone -b master https://github.com/pnnl/tesp.git

FNCS with Prerequisites (installed to /usr/local)
=================================================

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
cd ../czmq-3.0.2
./configure
make
sudo make install

cd ../fncs
autoconf
./configure
make
sudo make install

GridLAB-D with Prerequisites (installed to /usr/local)
======================================================

sudo apt install autoconf
sudo apt install libtool
cd ~/src/gridlab-d
autoreconf -isf
cd third_party
chmod +x install_xercesc
bash install_xercesc or ./install_xercesc # many warnings about changing permissions ... not important?
./configure --with-fncs=/usr/local # for debugging, add 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -g -O0'
make
sudo make install
# setting the GLPATH on Ubuntu; other flavors of Linux may differ
sudo emacs /etc/environment &
# within the editor, add the following line to /etc/environment and save it
GLPATH="/usr/local/lib/gridlabd:/usr/local/share/gridlabd"
gridlabd --validate 

EnergyPlus with Prerequisites (installed to /usr/local)
=======================================================

sudo apt install cmake
sudo apt-get install libjsoncpp-dev
cs ~/src/EnergyPlus
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
cp energyplus-8-3-0 EnergyPlus-8-3-0
cp libenergyplusapi.so.8.3.0 EnergyPlus-8-3-0

Build eplus_json
================

cd ~/src/tesp/src/energyplus
# the following steps are also in go.sh
autoheader
aclocal
automake --add-missing
autoconf
./configure
make
sudo make install

PYPOWER
=======

cd ~/src/tesp/src/pypower
pip install pypower
opf # should produce errors
cp *.py ~/miniconda3/lib/python3.6/site-packages/pypower
opf Should run correctly

TODO: MATPOWER, MATLAB Runtime (MCR) and wrapper
================================================

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

TESP Uses TCP/IP port 5570 for communication
============================================
1.	"lsof -i :5570" will show all processes connected to port 5570; use this or "ls -al *.log", "ls -al *.json", "ls -al *.csv" to show progress of a case solution
2.	"./kill5570.sh" will terminate all processes connected to port 5570; if you have to do this, make sure "lsof -i :5570" shows nothing before attempting another case

TestCase1 - verifies GridLAB-D and Python over FNCS 
===================================================
1.  cd ~/src/tesp/examples/loadshed
2.	python glm_dict.py loadshed
3.	./run.sh
4.	python plot_loadshed.py loadshed

TestCase2 - verifies EnergyPlus over FNCS
=========================================
1.  cd ~/src/tesp/examples/energyplus
2.	./run.sh
3.	python process_eplus.py eplus

TestCase3 - verifies PYPOWER over FNCS
======================================
1.  cd ~/src/tesp/examples/pypower
2.	./runpp.sh
3.	python process_pypower.py ppcase

TestCase4 - 30 houses, 1 school, 4 generators over FNCS
=======================================================
1.  cd ~/src/tesp/examples/te30
2.	python prep_agents.py te_challenge
3.	python glm_dict.py te_challenge
4.	./run30.sh
5.  # the simulation takes about 10 minutes, use "cat TE*.csv" to show progress up to 172800 seconds
6.	python process_eplus.py te_challenge
7.	python process_pypower.py te_challenge
8.	python process_agents.py te_challenge
9.	python process_gld.py te_challenge

SGIP1b - 1594 houses, 1 school, 4 generators over FNCS
======================================================
1.  cd ~/src/tesp/examples/sgip1
2.	python prep_agents.py SGIP1b
3.	python glm_dict.py SGIP1b
4.	./runSGIP1b.sh
5.  # the simulation takes about 120 minutes, use "cat SGIP*.csv" to show progress up to 172800 seconds
6.	python process_eplus.py SGIP1b
7.	python process_pypower.py SGIP1b
8.	python process_agents.py SGIP1b
9.	python process_gld.py SGIP1b


