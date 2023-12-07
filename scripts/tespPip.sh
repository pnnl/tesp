#!/bin/bash

git checkout HEAD requirements.txt
pip install -r "$HOME/tesp/requirements.txt" >> "$HOME/tesp.log"

if [[ -z $VIRTUAL_ENV ]]; then
  VIRTUAL=""
else
  VIRTUAL=$VIRTUAL_ENV/bin/activate
fi

cat >> "$HOME/tespEnv" << EOF
$VIRTUAL

# TESP exports
export TESPDIR=$HOME/tesp
export INSTDIR=\$TESPDIR/tenv
export REPODIR=\$TESPDIR/repository
export TESPBUILD=\$TESPDIR/scripts/build
export TESPHELPR=\$TESPDIR/scripts/helpers

# COMPILE exports
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PYHELICS_INSTALL=\$INSTDIR
export GLPATH=\$INSTDIR/lib/gridlabd:\$INSTDIR/share/gridlabd
export CPLUS_INCLUDE_PATH=/usr/include/hdf5/serial:\$INSTDIR/include
export FNCS_INCLUDE_DIR=\$INSTDIR/include
export FNCS_LIBRARY=\$INSTDIR/lib
export LD_LIBRARY_PATH=\$INSTDIR/lib
export LD_RUN_PATH=\$INSTDIR/lib
# export BENCH_PROFILE=1

# PATH
export PATH=\$INSTDIR/bin:\$PATH
export PATH=\$JAVA_HOME:\$PATH
export PATH=\$PATH:\$INSTDIR/energyplus
export PATH=\$PATH:\$INSTDIR/energyplus/PreProcess
export PATH=\$PATH:\$INSTDIR/energyplus/PostProcess
export PATH=\$PATH:\$TESPHELPR

# PSST environment variables
export PSST_SOLVER=cbc
# 'PSST_SOLVER path' -- one of "cbc", "ipopt", "/ibm/cplex/bin/x86-64_linux/cplexamp"
export PSST_WARNING=ignore
# 'PSST_WARNING action' -- one of "error", "ignore", "always", "default", "module", or "once"

# PROXY export if needed
# export HTTPS_PROXY=http://proxy01.pnl.gov:3128
EOF
