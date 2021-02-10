#!/bin/sh

#". set_env.sh"
if test "${JAVA_HOME}" = ""; then
  export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64/
fi
export JMODELICA_HOME=/home/yh/jmodelica
export IPOPT_HOME=/home/yh/ipopt
export SUNDIALS_HOME=/home/yh/jmodelica/ThirdParty/Sundials
export PYTHONPATH=:/home/yh/jmodelica/Python/::$PYTHONPATH
export LD_LIBRARY_PATH=:/home/yh/ipopt/lib/:/home/yh/jmodelica/ThirdParty/Sundials/lib:/home/yh/jmodelica/ThirdParty/CasADi/lib:$LD_LIBRARY_PATH
export SEPARATE_PROCESS_JVM=/usr/lib/jvm/java-8-openjdk-amd64/
