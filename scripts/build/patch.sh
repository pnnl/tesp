#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  echo "Edit tespEnv in the $HOME directory"
  echo "Run 'source tespEnv' in that same directory"
  exit
fi

id="${BUILD_DIR}/${2}.id"
patch="${BUILD_DIR}/${2}.patch"

a=$(cat "$id")
cd "${1}" || exit
b=$(git rev-parse HEAD)
if [ "$a" = "$b" ]; then
  echo "Repository has been installed to a commit id $a file"
else
  echo "Repository HEAD id $b does not match, resetting to a commit id $a"
  git reset --hard "$a"
fi

cd - > /dev/null || exit
if [ -f "$patch" ]; then
  if [ -s "$patch" ]; then
    cp "$patch" "${1}/tesp.patch"
    cd "${1}" || exit
    git apply tesp.patch
    echo "Apply patches for repository ${1}"
    echo "Patch file at ${1}/tesp.patch"
  fi
fi
