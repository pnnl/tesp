#!/bin/bash


if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi


ver="v1.2.0"

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
echo "$ver" > "${TESPBUILD}/version"
