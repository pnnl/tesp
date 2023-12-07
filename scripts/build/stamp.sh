#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

ver="1.3.5"

echo
echo "Stamping TESP $ver, if you want to change the version, edit this file."
echo "You should also update any documentation CHANGELOG.TXT or README.rst before stamping."
echo "The command below can show the branch and merge history to help you update documentation."
echo
echo "    git log --pretty=format:"%h %s" --graph"
echo

while true; do
    read -p "Are you ready to stamp TESP $ver? " yn
    case $yn in
        [Yy]* ) stamp="yes" break;;
        [Nn]* ) stamp="no"; break;;
        * ) echo "Please answer [y]es or [n]o.";;
    esac
done

if [[ $stamp == "no" ]]; then
  echo "Exiting TESP stamping"
  exit
fi

cd "${REPODIR}" || exit
echo "Stamping commit ids for:"
for dir in *
do
  if [ -d "$dir" ]; then
    repo=$dir/.git
    if [ -d "$repo" ]; then
      cd "$dir" || exit
      git rev-parse HEAD > "${TESPBUILD}/$dir.id"
      git diff > "${TESPBUILD}/$dir.patch"
      echo "...$dir"
      cd "${REPODIR}" || exit
    fi
  fi
done

#helics submodule in ns3
name="helics-ns3"
dir="${REPODIR}/ns-3-dev/contrib/helics"
if [ -d "$dir" ]; then
  cd "$dir" || exit
  git rev-parse HEAD > "${TESPBUILD}/$name.id"
  git diff > "${TESPBUILD}/$name.patch"
  echo "...$name"
  cd "${REPODIR}" || exit
fi

echo "Creating tesp_binaries.zip for installed binaries on TESP install"
cd "${INSTDIR}" || exit
zip -r -9 "${TESPBUILD}/tesp_binaries.zip" . &> "${TESPBUILD}/tesp_binaries.log" &
pip3 list > "${TESPBUILD}/tesp_pypi.id"

echo "Stamping TESP $ver for install"
cd "${TESPDIR}" || exit
echo "$ver" > "scripts/version"
echo "$ver" > "src/tesp_support/version"

# un-comment for final version
# git tag "v$ver"

echo "Creating TESP distribution package for pypi"
cd "${TESPDIR}/src/tesp_support" || exit
python3 -m build . > "${TESPBUILD}/package.log"
echo "Checking TESP distribution package for pypi"
twine check dist/*
echo
echo "To upload the new TESP $ver pypi,"
echo "change directory to ${TESPDIR}/src/tesp_support"
echo "and run the command 'twine upload dist/*'"
echo
