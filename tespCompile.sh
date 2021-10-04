#!/bin/bash

clear
JP=-j4

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

echo #++++++++++++++ FNCS
cd $REPODIR/fncs
autoreconf -isf
./configure 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2' --prefix=$INSTDIR
# leave off --prefix if using the /usr/local
make $JP
sudo make install

echo #++++++++++++++ FNCS Java lib
cd java
rm -r build
mkdir build
cd build

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
make -j4
cp fncs.jar $HOME/grid/repository/tesp/examples/loadshed/java
cp libJNIfncs.so $HOME/grid/repository/tesp/examples/loadshed/java


echo #++++++++++++++ HELICS
cd $REPODIR/HELICS-src
sudo rm -r build
mkdir build
cd build
cmake -DBUILD_JAVA_INTERFACE=ON -DBUILD_SHARED_LIBS=ON \
      -DJAVA_AWT_INCLUDE_PATH=NotNeeded -DHELICS_DISABLE_BOOST=ON \
      -DCMAKE_INSTALL_PREFIX=$INSTDIR -DCMAKE_BUILD_TYPE=Release ..
# leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
git submodule update --init
make $JP
sudo make install


echo #++++++++++++++ KLU solver
cd $REPODIR/KLU_DLL
sudo rm -r build
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$INSTDIR ..
# replace $INSTDIR with /usr/local if using the default
sudo cmake --build . --target install


echo #++++++++++++++ GridLAB-D
cd "$REPODIR/gridlab-d"
autoreconf -isf
# for ARM/'constance' processer needs libtinfo.a,   edit 'ax_with_curses.m4'  lines 206,219,325,338  add -ltinfo
./configure --prefix=$INSTDIR --with-fncs=$INSTDIR --with-hdf5=yes --enable-silent-rules 'CFLAGS=-w -O2' 'CXXFLAGS=-w -O2 -std=c++14' 'LDFLAGS=-w'
# in configure --with-fncs and --with-helics can not be left blank, so use either $INSTDIR or /usr/local for both
# leave off --prefix if using the default /usr/local
# for debugging use 'CXXFLAGS=-w -g -O0' and 'CFLAGS=-w -std=c++14 -g -O0' and 'LDFLAGS=-w -g -O0'

make $JP
sudo make install
#gridlabd --validate


#++++++++++++++  EngeryPlus
cd $INSTDIR
mkdir energyplus
cd $REPODIR/EnergyPlus
sudo rm -r build
mkdir build
cd build
cmake -DCMAKE_INSTALL_PREFIX:PATH=$INSTDIR/energyplus -DCMAKE_PREFIX_PATH=$INSTDIR -DBUILD_FORTRAN=ON -DBUILD_PACKAGE=ON -DENABLE_INSTALL_REMOTE=OFF ..
# todo warning[-Wmissing-include-dirs]
# leave off -DCMAKE_INSTALL_PREFIX if using the default /usr/local
make $JP
sudo make install


#++++++++++++++  EngeryPlus Json
cd $TESPDIR/src/energyplus
# the following steps are also in go.sh
autoheader
aclocal
automake --add-missing
autoconf
./configure --prefix=$INSTDIR  --with-fncs=$INSTDIR 'CXXFLAGS=-w -O2' 'CFLAGS=-w -O2'
make $JP
sudo make install

