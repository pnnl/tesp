#!/bin/bash

id="tesp/scripts/build/${2}.id"
patch="tesp/scripts/build/${2}.patch"

a=$(cat "$id")
cd "${1}" || exit
b=$(git rev-parse HEAD)
if [ "$a" = "$b" ]; then
  echo "Repository has been installed to a commit id on file"
else
  echo "Repository HEAD does not match, resetting to a commit id on file"
  git reset --hard "$a"
fi

cd - > /dev/null || exit
if [ -f "$patch" ]; then
  if [ -s "$patch" ]; then
    cp "$patch" "${1}/tesp.patch"
    cd "${1}" || exit
    git apply tesp.patch
    echo "Apply patches for repository ${1}"
  fi
fi
