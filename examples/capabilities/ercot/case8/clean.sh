#!/bin/bash

# Run Prepare
rm -f *_dict.json
rm -f weather*.json
#if FNCS
rm -f *auction.yaml
# tso8.yaml - static
rm -f *substation.yaml
rm -f *_FNCS_Config.txt
#if HELICS
#no monitor file yet
rm -f tso_h.json
rm -f *substation.json
rm -f *_msg.json

# Run Generated
rm -f *metrics.json
rm -f *_ercot.json
rm -f *.log
rm -f *_opf.csv
rm -f *_pf.csv
rm -f ercot_8.csv
rm -f *.h5
rm -f *.dat
rm -f *.xml
rm -f *.zpl
rm -rf PyomoTempFiles