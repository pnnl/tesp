#!/bin/bash

build="tesp/scripts/build"

cd "${1}" || exit
a=$(git rev-parse HEAD)
b=$(cat "$build/${3}")

if [ "$a" = "$b" ]; then
  echo "Repository has been installed to commit id on file"
else
  git reset --hard "$b"
  echo "Repository HEAD does not match, resetting to previous commit id on file"
fi

if [ -f "$build/${2}" ]; then
  if [ -s "$build/${2}" ]; then
    cp "$build/${2}" "${1}"/tesp_patch
    cd "${1}" || exit
    git apply tesp_patch
    echo "Apply patches for repository ${1}"
  fi
fi
