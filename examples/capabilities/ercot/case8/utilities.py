# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: uutilities.py

import os
import json
import tesp_support.helpers as helpers

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
            print('Removing existing Ercot_monitor.yaml file failed: ' + str(ex) +
                  '\nIt could cause problem in running the ERCOT monitor. Please check the file before run the monitor.')

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
        house_name = val['houseName']
        houseNumber = house_name.split('_')[-1]
        aucSimName = 'auction' + fileroot
        sub_key = aucSimName + '/' + key + '/'
        if houseNumber == '1':
            print('  ' + fileroot + '_vpos:', file=yp)
            print('    topic: pypower/three_phase_voltage_' + fileroot, file=yp)
            print('    default: 0', file=yp)
            print('  ' + fileroot + '_Hse1_Price:', file=yp)
            print('    topic: ' + sub_key + 'price', file=yp)
            print('    default: 0', file=yp)
            print('  ' + fileroot + '_Hse1_AirTemp:', file=yp)
            print('    topic: ' + gldSimName + '/' + house_name + '/air_temperature', file=yp)
            print('    default: 80', file=yp)
            break
    yp.close()


def write_json_for_ercot_monitor(timeStop, timeDelta, numberOfFederates):
    op = open(jsonFile, 'w')
    fncsBroker = {'args': ['fncs_broker', str(numberOfFederates)],
                  'env': [['FNCS_BROKER', 'tcp://*:5570'],
                          ['FNCS_LOG_STDOUT', 'YES'],
                          ['FNCS_FATAL', 'YES']],
                  'log': 'broker.log'}
    gridlabds = []
    for i in range(numberOfFederates - 2):
        gridlabd = {'args': ['gridlabd', '-D', 'USE_FNCS', '-D', 'METRICS_FILE = Bus' + str(i + 1) + '_metrics.json',
                             'Bus' + str(i + 1) + '.glm'],
                    'env': [['FNCS_FATAL', 'YES'],
                            ['FNCS_LOG_STDOUT', 'YES']],
                    'log': 'Bus' + str(i + 1) + '.log'}
        gridlabds.append(gridlabd)
    python = {'args': ['python', 'tso_psst_f.py'],
              'env': [['FNCS_CONFIG_FILE', 'tso8.yaml'],
                      ['FNCS_FATAL', 'YES'],
                      ['FNCS_LOG_STDOUT', 'YES']],
              'log': 'bulk.log'}
    commands = [fncsBroker] + gridlabds + [python]
    federates = {'time_stop': timeStop, 'yaml_delta': timeDelta, 'commands': commands}
    print(json.dumps(federates), file=op)


# write helics json message files
def write_substation_msg(fileroot, gldSimName, aucSimName, controllers, dt):
    dso = helpers.HelicsMsg(aucSimName, dt)

    bs = fileroot[3:]
    gldSimName = "gridlabdBus" + bs
    dso.pubs_n(False, "unresponsive_mw", "double")
    dso.pubs_n(False, "responsive_max_mw", "double")
    dso.pubs_n(False, "responsive_c1", "double")
    dso.pubs_n(False, "responsive_c2", "double")
    dso.pubs_n(False, "responsive_deg", "integer")
    dso.pubs_n(False, "clear_price", "double")

    dso.subs_n("pypower" + "/LMP_" + bs, "double")
    dso.subs_n(gldSimName + "/distribution_load", "complex")
    pubSubMeters = set()
    for key, val in controllers.items():
        house_name = str(val['houseName'])
        meter_name = str(val['meterName'])
        dso.subs_n(gldSimName + "/" + house_name + "#air_temperature", "double")
        dso.subs_n(gldSimName + "/" + house_name + "#hvac_load", "double")
        dso.subs_n(gldSimName + "/" + house_name + "#power_state", "string")
        dso.pubs_n(False, key + "/cooling_setpoint", "double")
        dso.pubs_n(False, key + "/heating_setpoint", "double")
        dso.pubs_n(False, key + "/thermostat_deadband", "double")
        if meter_name not in pubSubMeters:
            pubSubMeters.add(meter_name)
            dso.subs_n(gldSimName + "/" + meter_name + "#measured_voltage_1", "double")
            dso.pubs_n(False, key + "/" + meter_name + "/bill_mode", "string")
            dso.pubs_n(False, key + "/" + meter_name + "/price", "double")
            dso.pubs_n(False, key + "/" + meter_name + "/monthly_fee", "double")

    dso.write_file(fileroot + '_substation.json')


def write_gridlabd_msg(fileroot, weatherName, aucSimName, controllers, dt):
    # write the GridLAB-D publications and subscriptions for HELICS
    gld = helpers.HelicsMsg("gridlabd" + fileroot, dt)

    bs = fileroot[3:]
    gld.pubs(False, "distribution_load", "complex", "network_node", "distribution_load")
    gld.subs("pypower/three_phase_voltage_" + fileroot, "complex", "network_node", "positive_sequence_voltage")
    if len(weatherName) > 0:
        for wTopic in ['temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed']:
            gld.subs(weatherName + '/#' + wTopic, "double", weatherName, wTopic)

    # if len(Eplus_Bus) > 0:  # hard-wired names for a single building
    #     gld.subs("eplus_agent/power_A", "complex", Eplus_Load, "constant_power_A")
    #     gld.subs("eplus_agent/power_B", "complex", Eplus_Load, "constant_power_B")
    #     gld.subs("eplus_agent/power_C", "complex", Eplus_Load, "constant_power_C")
    #     gld.subs("eplus_agent/bill_mode", "string", Eplus_Meter, "bill_mode")
    #     gld.subs("eplus_agent/price", "double", Eplus_Meter, "price")
    #     gld.subs("eplus_agent/monthly_fee", "double", Eplus_Meter, "monthly_fee")

    pubSubMeters = set()
    for key, val in controllers.items():
        meter_name = val['meterName']
        house_name = val['houseName']
        house_class = val['houseClass']
        sub_key = aucSimName + "/" + key + "/"
        for prop in ['power_state']:
            gld.pubs(False, house_name + "#" + prop, "string", house_name, prop)
        for prop in ['air_temperature', 'hvac_load']:
            gld.pubs(False, house_name + "#" + prop, "double", house_name, prop)
        for prop in ['cooling_setpoint', 'heating_setpoint', 'thermostat_deadband']:
            gld.subs(sub_key + prop, "double", house_name, prop)
        if meter_name not in pubSubMeters:
            pubSubMeters.add(meter_name)
            prop = 'measured_voltage_1'
            if ('BIGBOX' in house_class) or ('OFFICE' in house_class) or ('STRIPMALL' in house_class):
                prop = 'measured_voltage_A'  # TODO: the HELICS substation always expects measured_voltage_1
            gld.pubs(False, meter_name + "#measured_voltage_1", "complex", meter_name, prop)
            for prop in ['bill_mode']:
                gld.subs(sub_key + meter_name + "/" + prop, "string", meter_name, prop)
            for prop in ['price', 'monthly_fee']:
                gld.subs(sub_key + meter_name + "/" + prop, "double", meter_name, prop)

    gld.write_file(fileroot + '_gridlabd.json')


def write_ercot_tso_msg(numBuses):
    tso = helpers.HelicsMsg("pypower", 300)

    for i in range(numBuses):
        bs = str(i + 1)
        tso.pubs_n(False, "three_phase_voltage_Bus" + bs, "double")
        tso.pubs_n(False, "LMP_" + bs, "double")
        tso.pubs_n(False, "LMP_RT_Bus_" + bs, "string")
        tso.pubs_n(False, "LMP_DA_Bus_" + bs, "string")
        tso.pubs_n(False, "cleared_q_rt_" + bs, "string")
        tso.pubs_n(False, "cleared_q_da_" + bs, "string")

    for i in range(numBuses):
        bs = str(i + 1)
        tso.subs_n("gridlabdBus" + bs + "/distribution_load", "complex")
        tso.subs_n("substationBus" + bs + "/unresponsive_mw", "double")
        tso.subs_n("substationBus" + bs + "/responsive_max_mw", "double")
        tso.subs_n("substationBus" + bs + "/responsive_c2", "double")
        tso.subs_n("substationBus" + bs + "/responsive_c1", "double")
        tso.subs_n("substationBus" + bs + "/responsive_deg", "integer")
        tso.subs_n("substationBus" + bs + "/clear_price", "double")

    tso.write_file('tso_h.json')


if __name__ == "__main__":
    write_FNCS_config_yaml_file_header()
    write_FNCS_config_yaml_file_values('abc', dict())
