#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

cd "${REPODIR}/fncs/java" || exit
if [[ $1 == "clean" ]]; then
  rm -rf build
fi 
mkdir -p build
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

JAVAPATH=$INSTDIR/java
sudo mkdir -p "$JAVAPATH"
sudo cp fncs.jar "$JAVAPATH/"
sudo cp libJNIfncs.so "$JAVAPATH/"

