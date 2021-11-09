#!/bin/sh

# script for execution of deployed applications
#
# Sets up the MATLAB runtime environment for the current $ARCH and executes 
# the specified command.
#
exe_name=$0
exe_dir=`dirname "$0"`
echo "------------------------------------------"
if [ "x$1" = "x" ]; then
  echo Usage:
  echo    $0 args
else
#  echo Setting up environment variables
  MCRROOT="/Applications/MATLAB/MATLAB_Runtime/v85"
#  echo ---
  DYLD_LIBRARY_PATH=.:${MCRROOT}/runtime/maci64 ;
  DYLD_LIBRARY_PATH=${DYLD_LIBRARY_PATH}:${MCRROOT}/bin/maci64 ;
  DYLD_LIBRARY_PATH=${DYLD_LIBRARY_PATH}:${MCRROOT}/sys/os/maci64;
  export DYLD_LIBRARY_PATH;
#  echo DYLD_LIBRARY_PATH is ${DYLD_LIBRARY_PATH};
#  shift 1
  args=
  while [ $# -gt 0 ]; do
      token=$1
      args="${args} \"${token}\"" 
      shift
  done
  echo $args
  eval "\"${exe_dir}/fncsMATPOWER.app/Contents/MacOS/fncsMATPOWER\"" $args
fi
exit
