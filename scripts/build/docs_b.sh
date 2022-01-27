#!/bin/bash

if [[ -z ${INSTDIR} ]]; then
  . "${HOME}/tespEnv"
fi

pip3 install recommonmark sphinx-jsonschema sphinx_rtd_theme sphinxcontrib-bibtex
# sphinxcontrib-bibtex 2.0.0 has introduced an incompatibility
# pip3 install sphinxcontrib-bibtex==1.0.0
cd "${TESPDIR}/doc" || exit
make clean
make html