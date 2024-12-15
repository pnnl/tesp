#!/bin/bash

# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: stamp.sh

if [[ -z ${TESPDIR} ]]; then
  echo "Edit 'tesp.env' in the TESP home directory"
  echo "Run 'source tesp.env' in that same directory"
  exit
fi

cd "$DOCKER_DIR" || exit
tesp_ver=$(cat ../tesp_version)
grid_ver=$(cat ../grid_version)

echo
echo "Stamping TESP ${tesp_ver} and grid applications ${grid_ver}."
echo "If you want to change the version, edit 'scripts/tesp_version' or 'scripts/grid_version' file."
echo "You should also update any documentation CHANGELOG.TXT or README.rst before stamping."
echo "The command below can show the branch and merge history to help you update documentation."
echo
echo "    git log --pretty=format:"%h %s" --graph"
echo

while true; do
    read -rp "Are you ready to stamp TESP ${tesp_ver} and grid applications ${grid_ver}? " yn
    case $yn in
        [Yy]* ) stamp="yes"; break;;
        [Nn]* ) stamp="no"; break;;
        * ) echo "Please answer [y]es or [n]o.";;
    esac
done

if [[ $stamp == "no" ]]; then
  echo "Exiting grid applications software stamping"
  exit
fi

cd "${REPO_DIR}" || exit
echo "Stamping commit ids for:"
for dir in *
do
  if [ -d "$dir" ]; then
    repo=$dir/.git
    if [ -d "$repo" ]; then
      cd "$dir" || exit
      git rev-parse HEAD > "${BUILD_DIR}/$dir.id"
      git diff > "${BUILD_DIR}/$dir.patch"
      echo "...$dir"
      cd "${REPO_DIR}" || exit
    fi
  fi
done

#helics submodule in ns3
name="helics-ns3"
dir="${REPO_DIR}/ns-3-dev/contrib/helics"
if [ -d "$dir" ]; then
  cd "$dir" || exit
  git rev-parse HEAD > "${BUILD_DIR}/$name.id"
  git diff > "${BUILD_DIR}/$name.patch"
  echo "...$name"
  cd "${REPO_DIR}" || exit
fi

echo "Creating grid_binaries_$grid_ver.zip for installed binaries for grid applications software"
cd "${INSTDIR}" || exit
# zip -r -9 "${BUILD_DIR}/grid_binaries_$grid_ver.zip" . &> "${BUILD_DIR}/grid_binaries.log" &

pip list > "${BUILD_DIR}/tesp_pypi.id"

echo "Stamping grid applications software $grid_ver and TESP $tesp_ver for install"
cd "${TESPDIR}" || exit
echo "$tesp_ver" > "src/tesp_support/version"

# un-comment for final version
# git tag "v$tesp_ver"

echo "Creating TESP distribution package for pypi"
cd "${TESPDIR}/src/tesp_support" || exit
python3 -m build . > "${BUILD_DIR}/package.log"
echo "Checking TESP distribution package for pypi"
twine check dist/*
echo
echo "To upload the new TESP $tesp_ver pypi,"
echo "change directory to ${TESPDIR}/src/tesp_support"
echo "and run the command 'twine upload dist/*'"
echo
