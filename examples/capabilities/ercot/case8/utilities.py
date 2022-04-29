# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: uutilities.py

import os
import re
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
    python = {'args': ['python', 'fncsTSO.py'],
              'env': [['FNCS_CONFIG_FILE', 'tso8.yaml'],
                      ['FNCS_FATAL', 'YES'],
                      ['FNCS_LOG_STDOUT', 'YES']],
              'log': 'bulk.log'}
    commands = [fncsBroker] + gridlabds + [python]
    federates = {'time_stop': timeStop, 'yaml_delta': timeDelta, 'commands': commands}
    print(json.dumps(federates), file=op)


# HELICS message utilities
def write_message_file(_n, _t, _p, _s, _fn):
    msg = {"name": _n, "period": _t, "publications": _p, "subscriptions": _s}
    op = open(_fn, 'w', encoding='utf-8')
    json.dump(msg, op, ensure_ascii=False, indent=2)
    op.close()


def pubs_append(_pb, _g, _k, _t, _o, _p):
    _pb.append({"global": _g, "key": _k, "type": _t, "info": {"object": _o, "property": _p}})


def pubs_append_n(_pb, _g, _k, _t):
    _pb.append({"global": _g, "key": _k, "type": _t})


def subs_append(_sb, _k, _t, _o, _p):
    _sb.append({"key": _k, "type": _t, "info": {"object": _o, "property": _p}})


def subs_append_n(_sb, _n, _k, _t):
    _sb.append({"name": _n, "key": _k, "type": _t})


# write helics json message files
def write_substation_msg(fileroot, gldSimName, aucSimName, controllers, dt):
    subs = []
    pubs = []

    pubs_append_n(pubs, False, "responsive_c1", "double")
    pubs_append_n(pubs, False, "responsive_c2", "double")
    pubs_append_n(pubs, False, "responsive_deg", "integer")
    pubs_append_n(pubs, False, "responsive_max_mw", "double")
    pubs_append_n(pubs, False, "unresponsive_mw", "double")
    pubs_append_n(pubs, False, "clear_price", "double")

    subs_append_n(subs, "LMP", "pypower/LMP_" + fileroot, "double")
    subs_append_n(subs, "refload", gldSimName + '/distribution_load', "complex")
    for key, val in controllers.items():
        houseName = str(val['houseName'])
        meterName = str(val['meterName'])
        subs_append_n(subs, key + '#V1:',  gldSimName + '/' + meterName + '#measured_voltage_1', "double")
        subs_append_n(subs, key + '#Tair:', gldSimName + '/' + houseName + '#air_temperature', "double")
        subs_append_n(subs, key + '#Load:', gldSimName + '/' + houseName + '#hvac_load', "double")
        subs_append_n(subs, key + '#On:', gldSimName + '/' + houseName + '#power_state', "string")

        pubs_append_n(pubs, False, key + "/cooling_setpoint", "double")
        pubs_append_n(pubs, False, key + "/heating_setpoint", "double")
        pubs_append_n(pubs, False, key + "/thermostat_deadband", "double")
        pubs_append_n(pubs, False, key + "/bill_mode", "string")
        pubs_append_n(pubs, False, key + "/price", "double")
        pubs_append_n(pubs, False, key + "/monthly_fee", "double")

    write_message_file(aucSimName, dt, pubs, subs, fileroot + '_substation.json')


def write_gridlabd_msg(fileroot, weatherName, aucSimName, controllers, dt):
    # write the GridLAB-D publications and subscriptions for HELICS
    subs = []
    pubs = []
    pubs_append(pubs, False, "distribution_load", "complex", "network_node", "distribution_load")
    subs_append(subs, "pypower/three_phase_voltage_" + fileroot, "complex", "network_node", "positive_sequence_voltage")
    if len(weatherName) > 0:
        for wTopic in ['temperature', 'humidity', 'solar_direct', 'solar_diffuse', 'pressure', 'wind_speed']:
            subs_append(subs, weatherName + '/' + wTopic, "double", weatherName, wTopic)
    # if len(Eplus_Bus) > 0:  # hard-wired names for a single building
    #     subs_append("eplus_agent/power_A", "complex", Eplus_Load, "constant_power_A"}})
    #     subs_append("eplus_agent/power_B", "complex", Eplus_Load, "constant_power_B"}})
    #     subs_append("eplus_agent/power_C", "complex", Eplus_Load, "constant_power_C"}})
    #     subs_append("eplus_agent/bill_mode", "string", Eplus_Meter, "bill_mode"}})
    #     subs_append("eplus_agent/price", "double", Eplus_Meter, "price"}})
    #     subs_append("eplus_agent/monthly_fee", "double", Eplus_Meter, "monthly_fee"}})

    pubSubMeters = set()
    for key, val in controllers.items():
        houseName = val['houseName']
        houseClass = val['houseClass']
        meterName = val['meterName']
        aucSimKey = aucSimName + '/' + key + "/"
        for prop in ['power_state']:
            pubs_append(pubs, False, houseName + "#" + prop, "string", houseName, prop)
        for prop in ['air_temperature', 'hvac_load']:
            pubs_append(pubs, False, houseName + "#" + prop, "double", houseName, prop)
        for prop in ['cooling_setpoint', 'heating_setpoint', 'thermostat_deadband']:
            subs_append(subs, aucSimKey + prop, "double", houseName, prop)
        if meterName not in pubSubMeters:
            pubSubMeters.add(meterName)
            prop = 'measured_voltage_1'
            if ('BIGBOX' in houseClass) or ('OFFICE' in houseClass) or ('STRIPMALL' in houseClass):
                prop = 'measured_voltage_A'  # TODO: the HELICS substation always expects measured_voltage_1
            pubs_append(pubs, False, meterName + "#measured_voltage_1", "complex", meterName, prop)
            for prop in ['bill_mode']:
                subs_append(subs, aucSimKey + prop, "string", meterName, prop)
            for prop in ['price', 'monthly_fee']:
                subs_append(subs, aucSimKey + prop, "double", meterName, prop)

    write_message_file("gridlabd" + fileroot, dt, pubs, subs, fileroot + '_HELICS_gld_msg.json')


def write_ercot_tso_msg(nd):
    subs = []
    pubs = []

    for i in range(nd):
        bs = str(i + 1)
        pubs_append_n(pubs, False, "three_phase_voltage_Bus" + bs, "double")
        pubs_append_n(pubs, False, "LMP_Bus" + bs, "double")
        pubs_append_n(pubs, False, "LMP_RT_Bus_" + bs, "string")
        pubs_append_n(pubs, False, "LMP_DA_Bus_" + bs, "string")
        pubs_append_n(pubs, False, "cleared_q_rt_" + bs, "string")
        pubs_append_n(pubs, False, "cleared_q_da_" + bs, "string")

    for i in range(nd):
        bs = str(i + 1)
        subs_append_n(subs, "SUBSTATION" + bs, "gridlabdBus" + bs + "/distribution_load", "complex")
        subs_append_n(subs, "UNRESPONSIVE_MW_" + bs, "substationBus" + bs + "/unresponsive_mw", "double")
        subs_append_n(subs, "RESPONSIVE_MAX_MW_" + bs, "substationBus" + bs + "/responsive_max_mw", "double")
        subs_append_n(subs, "RESPONSIVE_C2_" + bs, "substationBus" + bs + "/responsive_c2", "double")
        subs_append_n(subs, "RESPONSIVE_C1_" + bs, "substationBus" + bs + "/responsive_c1", "double")
        subs_append_n(subs, "RESPONSIVE_DEG_" + bs, "substationBus" + bs + "/responsive_deg", "integer")
        subs_append_n(subs, "CLEAR_PRICE_" + bs, "substationBus" + bs + "/clear_price", "double")

    write_message_file("pypower", 300, pubs, subs, 'tso_h.json')


if __name__ == "__main__":
    write_FNCS_config_yaml_file_header()
    write_FNCS_config_yaml_file_values('abc', dict())
