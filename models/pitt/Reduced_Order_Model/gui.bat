set FNCS_CONFIG_FILE=TESP_Monitor.yaml
start /b cmd /c python -c "import tesp_support.tesp_monitor as tesp;tesp.show_tesp_monitor()"

