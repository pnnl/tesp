#!/bin/bash
# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: test_helics_java.sh

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tespEnv in the $HOME directory"
  echo "Run 'source tespEnv' in that same directory"
  exit
fi

JAVAPATH=${INSTDIR}/java

cd "${BUILD_DIR}" || exit
if ! [ -f "test_helics.class" ]; then
  javac -classpath ".:$JAVAPATH/helics.jar" test_helics.java
fi
java -classpath ".:$JAVAPATH/helics.jar" -Djava.library.path="$JAVAPATH" test_helics
