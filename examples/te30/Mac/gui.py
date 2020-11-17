import tesp_support.tesp_monitor as tesp
import os
os.environ['FNCS_CONFIG_FILE'] = 'TESP_Monitor.yaml'
# os.environ['FNCS_LOG_LEVEL'] = 'DEBUG2'
tesp.show_tesp_monitor()

