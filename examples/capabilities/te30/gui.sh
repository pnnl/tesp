#!/bin/bash
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: gui.sh

(export FNCS_CONFIG_FILE=TESP_Monitor.yaml && exec python3 -c "import tesp_support.api as tesp;tesp.show_tesp_monitor()" &)

