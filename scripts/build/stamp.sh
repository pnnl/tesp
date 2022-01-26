#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

build="${TESPDIR}/scripts/build"
cd "${REPODIR}" || exit

for dir in *
do
  if [ -d "$dir" ]; then
    repo=$dir/.git
    if [ -d "$repo" ]; then
      cd "$dir" || exit
      git rev-parse HEAD > "$build/$dir.id"
      git diff > "$build/$dir.patch"
      cd "${REPODIR}" || exit
    fi
  fi
done

#helics submodule in ns3
name="helics-ns3"
dir="${REPODIR}/ns-3-dev/contrib/helics"
if [ -d "$dir" ]; then
  cd "$dir" || exit
  git rev-parse HEAD > "$build/$name.id"
  git diff > "$build/$name.patch"
  cd "${REPODIR}" || exit
fi
