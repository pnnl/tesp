#!/bin/bash

#lsof -i tcp:5570 | awk 'NR!=1 {print $2}' | xargs -t kill -9

pkill -9 fncs_broker
pkill -9 python
pkill -9 gridlab
