#!/bin/bash

echo
echo "Install git and python, must be installed for other components"
sudo apt-get -y upgrade
sudo apt-get -y install git python3-venv python3-pip python3-tk python3-pil.imagetk

echo
if [[ -z $1 && -z $2 ]]; then
  echo "No user name set for git repositories!"
else
  git config --global user.name "$1"
  git config --global user.email "$2"
  echo "User .name=$1 and .email=$2 have been set for git repositories!"
fi
git config --global credential.helper store

echo
if [[ -z $3 ]]; then
  WORKDIR=$HOME/tesp
else
  WORKDIR=$HOME/$3
fi
echo "Install TESP home directory"
echo "TESP home dirctory is $WORKDIR"

cat > "$HOME/tespEnv" << EOF
. $HOME/.tvenv/bin/activate

# TESP exports
export TESPDIR=$WORKDIR
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

echo
echo "Install a virtual python environment to $HOME/.tvenv"
python3 -m pip install --upgrade pip
python3 -m pip install virtualenv
python3 -m venv "$HOME/.tvenv" --prompt TESP

source "$HOME/tespEnv"

echo "Installing Python Libraries..."
which python > "$HOME/tesp.log" 2>&1
pip install --upgrade pip >> "$HOME/tesp.log" 2>&1

echo "Installing TESP empty repo..."
git clone --no-checkout https://github.com/pnnl/tesp "$TESPDIR"
cd "$TESPDIR" || exit

echo "Installing Python Libraries..."
git checkout HEAD requirements.txt
pip install -r "$TESPDIR/requirements.txt" >> "$HOME/tesp.log" 2>&1

echo "Installing Python TESP API..."
pip install tesp_support >> "$HOME/tesp.log" 2>&1

