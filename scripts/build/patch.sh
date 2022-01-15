#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

if [[ -f "${2}" ]]; then
  cp "${2}" "${1}"/tesp_patch
  cd "${1}"
  git apply tesp_patch
  echo "Apply patches for repository ${1}"
fi

