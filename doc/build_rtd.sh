#!/bin/bash
# API documentation
sphinx-apidoc -f -T -M -d 2 -o . ../src/tesp_support/tesp_support
mv tesp_support.rst references/tesp_support.inc
mv tesp_support*.rst references
# Traditional documentation
python -m sphinx -T -E -b html -d _build/doctrees -D language=en . _build/html