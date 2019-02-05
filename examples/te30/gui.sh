#!/bin/bash
(export FNCS_CONFIG_FILE=TESP_Monitor.yaml && export FNCS_LOG_LEVEL="DEBUG2" && exec pythonw -c "import tesp_support.tesp_monitor as tesp;tesp.show_tesp_monitor()" &)

