#!/bin/bash

clear

#Compile exports
export WAREDIR=$HOME/grid/software
export REPODIR=$HOME/grid/repository
export INSTDIR=$HOME/grid/installed
export GLPATH=$INSTDIR/lib/gridlabd:$INSTDIR/share/gridlabd
export FNCS_INCLUDE_DIR=$INSTDIR/include
export FNCS_LIBRARY=$INSTDIR/lib
export CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial
export TESPDIR=$REPODIR/tesp

#Running exports

#export PYTHONPATH=$PYTHONPATH:/usr/.local/lib/python3.6
#export PYTHONPATH=$PYTHONPATH:/opt/ibm/ILOG/CPLEX_Studio129/cplex/python/3.6/x86-64_linux
##export PYTHONPATH=$PYTHONPATH:/home/osboxes/grid/repository/ERCOTTestSystem/AMES-V5.0/SCUCresources
#export PYTHONPATH=$PYTHONPATH:/home/osboxes/grid/repository/ERCOTTestSystem/AMES-V5.0/psst
##export PYTHONPATH=$PYTHONPATH:/home/osboxes/grid/repository/isu/AMES-V5.0/SCUCresources
##export PYTHONPATH=$PYTHONPATH:/home/osboxes/grid/repository/isu/AMES-V5.0/psst

#export PSST_SOLVER=/opt/ibm/ILOG/CPLEX_Studio129/cplex/bin/x86-64_linux/cplexamp
#export PSST_SOLVER=/opt/ibm/ILOG/CPLEX_Studio129/cplex/bin/x86-64_linux/cplex

#export SOLVER_HOME=/opt/ibm/ILOG/CPLEX_Studio129/cplex/bin/x86-64_linux
#export SOLVER_HOME=$WAREDIR/gurobi-8.1.0/bin
#export SOLVER_HOME=$WAREDIR/scipoptsuite-6.0.1/build/bin

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

export PATH=$PATH:$INSTDIR/bin
export PATH=$PATH:$INSTDIR/engeryplus
export PATH=$PATH:$INSTDIR/engeryplus/PostProcess
#export PATH=$PATH:$HOME/.local/bin:
export PATH=$PATH:$JAVA_HOME
#export PATH=$PATH:$SOLVER_HOME
#export PATH=$PATH:$SOLVER_HOME/bin

#export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$INSTDIR/lib
#export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/osboxes/grid/repository/fncs/java/build

# Install all pip libraries
pip3 install wheel colorama glm seaborn matplotlib networkx==2.3 numpy pandas pulp pyutilib==5.8.0 pyomo==5.6.8 PYPOWER scikit-learn scipy tables h5py xlrd


echo #++++++++++++++ FNCS
cd "${REPODIR}/fncs" || exit
autoreconf -isf
./configure 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2' --prefix="${INSTDIR}"
# leave off --prefix if using the /usr/local
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install

echo #++++++++++++++ FNCS Java lib
cd java || exit
rm -r build
mkdir build
cd build || exit

#fix include and lib path in cmakelist.txt lines 11, 12
#-FIND_PATH(FNCS_INCLUDE_DIR fncs.hpp)
#-FIND_LIBRARY(FNCS_LIBRARY fncs)
# 11 - PATHS $ENV{FNCS_INCLUDE_DIR}
# 12 - PATHS $ENV{FNCS_LIBRARY}
#+FIND_PATH(FNCS_INCLUDE_DIR fncs.hpp PATHS $ENV{FNCS_INCLUDE_DIR})
#+FIND_LIBRARY(FNCS_LIBRARY fncs PATHS $ENV{FNCS_LIBRARY})
#sed -i "s:\(FNCS_INCLUDE_DIR fncs.hpp\):\(FNCS_INCLUDE_DIR fncs.hpp PATHS $ENV\{FNCS_INCLUDE_DIR\}\):g"
#sed -i "s:\(FNCS_LIBRARY fncs\):\(FNCS_LIBRARY fncs PATHS $ENV\{FNCS_LIBRARY\}\):g"

#replace custom command in cmakelist.txt lines ~26-33
# generate JNIfncs.h stub
#ADD_CUSTOM_COMMAND(
#    OUTPUT fncs_JNIfncs.h
#    COMMAND ${Java_JAVAC_EXECUTABLE} -h ../fncs -verbose
#        -classpath fncs
#         ../fncs/JNIfncs.java
#    MAIN_DEPENDENCY fncs.jar
#)

cmake ..
make -j "$(grep -c "^processor" /proc/cpuinfo)"
mkdir "${TESPDIR}/examples/capabilities/loadshed/java"
cp fncs.jar "${TESPDIR}/examples/capabilities/loadshed/java/"
cp libJNIfncs.so "${TESPDIR}/examples/capabilities/loadshed/java/"


echo #++++++++++++++ HELICS
cd "${REPODIR}/HELICS-src" || exit
sudo rm -r build
mkdir build
cd build || exit
cmake -DBUILD_JAVA_INTERFACE=ON -DBUILD_SHARED_LIBS=ON \
      -DJAVA_AWT_INCLUDE_PATH=NotNeeded -DHELICS_DISABLE_BOOST=ON \
      -DCMAKE_INSTALL_PREFIX="${INSTDIR}" -DCMAKE_BUILD_TYPE=Release ..
# leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
git submodule update --init
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install


echo #++++++++++++++ KLU solver
cd "${REPODIR}/KLU_DLL" || exit
sudo rm -r build
mkdir build
cd build || exit
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="${INSTDIR}" ..
# replace $INSTDIR with /usr/local if using the default
sudo cmake --build . --target install


echo #++++++++++++++ GridLAB-D
cd "${REPODIR}/gridlab-d" || exit
autoreconf -isf
# for ARM/'constance' processer needs libtinfo.a,   edit 'ax_with_curses.m4'  lines 206,219,325,338  add -ltinfo
./configure --prefix="${INSTDIR}" --with-fncs="${INSTDIR}" --with-hdf5=yes --enable-silent-rules \
            'CFLAGS=-w -O2' 'CXXFLAGS=-w -O2 -std=c++14' 'LDFLAGS=-w'
# in configure --with-fncs and --with-helics can not be left blank, so use either $INSTDIR or /usr/local for both
# leave off --prefix if using the default /usr/local
# for debugging use 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -std=c++14 -g -O0' and 'LDFLAGS=-w -g -O0'
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install
#gridlabd --validate


#++++++++++++++  EnergyPlus
cd "${INSTDIR}" || exit
mkdir energyplus
cd "${REPODIR}/EnergyPlus" || exit
sudo rm -r build
mkdir build
cd build || exit
cmake -DCMAKE_INSTALL_PREFIX:PATH="${INSTDIR}/energyplus" -DCMAKE_PREFIX_PATH="${INSTDIR}" -DBUILD_FORTRAN=ON -DBUILD_PACKAGE=ON -DENABLE_INSTALL_REMOTE=OFF ..
# todo warning[-Wmissing-include-dirs]
# leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install


#++++++++++++++  EnergyPlus Json
cd "${TESPDIR}/src/energyplus" || exit
# the following steps are also in go.sh
autoheader
aclocal
automake --add-missing
autoconf
./configure --prefix="${INSTDIR}"  --with-fncs="${INSTDIR}" 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2'
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install

#++++++++++++++ NS-3
cd "${REPODIR}/pybindgen"
sudo python3 setup.py install

cd "${REPODIR}/ns-3-dev"
# first build: use the following command for HELICS interface to ns3:
# git clone -b feature/13b https://github.com/GMLC-TDC/helics-ns3 contrib/helics
# subsequent builds: use the following 3 commands to update HELICS interface code:
# cd contrib/helics
# git pull
# cd ../..
# then configure, build and test ns3 with the HELICS interface
# --with-helics may not be left blank, so use either $TESP_INSTALL or /usr/local
./waf distclean
./waf configure --prefix="${INSTDIR}" --with-helics="${INSTDIR}" --build-profile=optimized --disable-werror --enable-logs --enable-examples --enable-tests
./waf build
sudo ./waf install
./test.py


#++++++++++++++ Ipopt
IPOPT_VERSION=3.13.2
cd "${WAREDIR}" || exit
wget https://www.coin-or.org/download/source/Ipopt/Ipopt-${IPOPT_VERSION}.tgz
tar -xzf Ipopt-${IPOPT_VERSION}.tgz
mv Ipopt-releases-${IPOPT_VERSION} Ipopt
mkdir Ipopt/build
rm "Ipopt-${IPOPT_VERSION}.tgz"

# coin-or's third party ASL
ASL_VERSION=2.0
cd "${WAREDIR}" || exit
wget https://github.com/coin-or-tools/ThirdParty-ASL/archive/stable/${ASL_VERSION}.zip
unzip ${ASL_VERSION}.zip
mv ThirdParty-ASL-stable-${ASL_VERSION} ThirdParty-ASL
cd ThirdParty-ASL || exit
./get.ASL
./configure --prefix="${INSTDIR}"
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install
rm "../${ASL_VERSION}.zip"

# coin-or's third party Mumps
MUMPS_VERSION=2.1
cd "${WAREDIR}" || exit
wget https://github.com/coin-or-tools/ThirdParty-Mumps/archive/stable/${MUMPS_VERSION}.zip
unzip ${MUMPS_VERSION}.zip
mv ThirdParty-Mumps-stable-${MUMPS_VERSION} ThirdParty-Mumps
cd ThirdParty-Mumps || exit
./get.Mumps
./configure --prefix="${INSTDIR}"
make -j "$(grep -c "^processor" /proc/cpuinfo)"
sudo make install
rm "../${MUMPS_VERSION}.zip"

# Make Ipopt
cd "${WAREDIR}/Ipopt" || exit
./configure --prefix="${INSTDIR}"
make -j "$(grep -c "^processor" /proc/cpuinfo)"
make test
sudo make install

# creates the necessary links and cache to the most recent shared libraries found
# in the directories specified on the command line, in the file /etc/ld.so.conf,
# and in the trusted directories (/lib and /usr/lib).
sudo ldconfig