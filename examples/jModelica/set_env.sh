#!/bin/sh

#". set_env.sh"
if test "${JAVA_HOME}" = ""; then
  export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64/
fi
export JMODELICA_HOME=/home/xcosmos/jModelica
export IPOPT_HOME=/home/xcosmos/ipopt
export SUNDIALS_HOME=/home/xcosmos/jModelica/ThirdParty/Sundials
export PYTHONPATH=:/home/xcosmos/jModelica/Python/::$PYTHONPATH
export LD_LIBRARY_PATH=:/home/xcosmos/ipopt/lib/:/home/xcosmos/jModelica/ThirdParty/Sundials/lib:/home/xcosmos/jModelica/ThirdParty/CasADi/lib:$LD_LIBRARY_PATH
export SEPARATE_PROCESS_JVM=/usr/lib/jvm/java-8-openjdk-amd64/
