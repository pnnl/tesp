import os
import json
yamlFile = 'Ercot_monitor.yaml'
jsonFile = 'tesp_monitor_ercot.json'

# write header part of the Ercot_monitor.yaml file
def write_FNCS_config_yaml_file_header():
    # yamlFile = 'Ercot_monitor.yaml'
    brokerName = 'tesp_monitor_ercot'
    dt = 15
    broker = 'tcp://localhost:5570'
    if os.path.isfile(yamlFile):
        try:
            os.remove(yamlFile)
        except Exception as ex:
            print('Removing existing Ercot_monitor.yaml file failed: ' + str(ex) + '\nIt could cause problem in running the ERCOT monitor. Please check the file before run the monitor.')

    yp = open(yamlFile, 'w')
    print('name:', brokerName, file=yp)
    print('time_delta: ' + str(dt) + 's', file=yp)
    print('broker:', broker, file=yp)
    print('values:', file=yp)
    yp.close()

def write_FNCS_config_yaml_file_values(fileroot, controllers):
    # yamlFile = 'Ercot_monitor.yaml'
    gldSimName = 'gridlabd' + fileroot
    yp = open(yamlFile, 'a')
    print('  LMP_' + fileroot, ':', file=yp)
    print('    topic: pypower/LMP_' + fileroot, file=yp)
    print('    default: 0.1', file=yp)
    print('    type: double', file=yp)
    print('    list: false', file=yp)
    print('  distribution_load_' + fileroot + ':', file=yp)
    print('    topic: ' + gldSimName + '/distribution_load', file=yp)
    print('    default: 0', file=yp)
    print('    type: complex', file=yp)
    print('    list: false', file=yp)
    for key, val in controllers.items():
        houseName = val['houseName']
        houseNumber = houseName.split('_')[-1]
        aucSimName = 'auction' + fileroot
        aucSimKey = aucSimName + '/' + key
        if houseNumber == '1':
            print('  ' + fileroot + '_vpos:', file=yp)
            print('    topic: pypower/three_phase_voltage_' + fileroot, file=yp)
            print('    default: 0', file=yp)
            print('  ' + fileroot + '_Hse1_Price:', file=yp)
            print('    topic: ' + aucSimKey + '/price', file=yp)
            print('    default: 0', file=yp)
            print('  ' + fileroot + '_Hse1_AirTemp:', file=yp)
            print('    topic: ' + gldSimName + '/' + houseName + '/air_temperature', file=yp)
            print('    default: 80', file=yp)
            break
    yp.close()

def write_json_for_ercot_monitor(timeStop, timeDelta, numberOfFederates):
    op = open (jsonFile, 'w')
    fncsBroker = {'args' : ['fncs_broker', str(numberOfFederates)],
                  'env' : [['FNCS_BROKER', 'tcp://*:5570'],
                           ['FNCS_LOG_STDOUT', 'YES'],
                           ['FNCS_FATAL', 'YES']],
                  'log' : 'broker.log'}
    gridlabds = []
    for i in range(numberOfFederates - 2):
        gridlabd = {'args' : ['gridlabd', '-D', 'USE_FNCS', '-D', 'METRICS_FILE = Bus' + str(i + 1) + '_metrics.json', 'Bus' + str(i + 1) + '.glm'],
                    'env' : [['FNCS_FATAL', 'YES'],
                           ['FNCS_LOG_STDOUT', 'YES']],
                    'log' : 'Bus' + str(i + 1) + '.log'}
        gridlabds.append(gridlabd)
    python = {'args' : ['python', 'fncsTSO.py'],
              'env' : [['FNCS_CONFIG_FILE', 'tso8.yaml'],
                       ['FNCS_FATAL', 'YES'],
                       ['FNCS_LOG_STDOUT', 'YES']],
              'log' : 'bulk.log'}
    commands = [fncsBroker] + gridlabds + [python]
    federates = {'time_stop' : timeStop, 'yaml_delta' : timeDelta, 'commands' : commands}
    print(json.dumps(federates), file=op)
if __name__ == "__main__":
    write_FNCS_config_yaml_file_header()
    write_FNCS_config_yaml_file_values('abc', dict())