# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: process_gld.py
"""Functions to plot data from GridLAB-D

Public Functions:
    :process_gld: Reads the data and metadata, then makes the plots.

"""
import logging
import json
import os

import numpy as np
import matplotlib.pyplot as plt

# Setting up logging
logger = logging.getLogger(__name__)


def read_gld_metrics(path, name_root, diction_name=''):
    glm_dict_path = os.path.join(path, f'{name_root}_glm_dict.json')
    sub_dict_path = os.path.join(path, f'substation_{name_root}_metrics.json')
    house_dict_path = os.path.join(path, f'house_{name_root}_metrics.json')
    bm_dict_path = os.path.join(path, f'billing_meter_{name_root}_metrics.json')
    inv_dict_path = os.path.join(path, f'inverter_{name_root}_metrics.json')
    cap_dict_path = os.path.join(path, f'capacitor_{name_root}_metrics.json')
    reg_dict_path = os.path.join(path, f'regulator_{name_root}_metrics.json')

    # the feederGenerator now inserts metrics_collector objects on capacitors and regulators
    bCollectedRegCapMetrics = True

    # first, read and print a dictionary of all the monitored GridLAB-D objects
    if len(diction_name) > 0:
        try:
            lp = open(diction_name).read()
        except:
            logger.error(f'Unable to open metrics diction file {diction_name}')
    else:
        try:
            lp = open(glm_dict_path).read()
        except:
            logger.error(f'Unable to open metrics diction file {glm_dict_path}')
    diction = json.loads(lp)
    fdr_keys = list(diction['feeders'].keys())
    fdr_keys.sort()
    inv_keys = list(diction['inverters'].keys())
    inv_keys.sort()
    hse_keys = list(diction['houses'].keys())
    hse_keys.sort()
    mtr_keys = list(diction['billingmeters'].keys())
    mtr_keys.sort()
    cap_keys = list(diction['capacitors'].keys())
    cap_keys.sort()
    reg_keys = list(diction['regulators'].keys())
    reg_keys.sort()
    # reg_keys = list(diction['evchargerdet'].keys())
    # reg_keys.sort()
    # reg_keys = list(diction['line'].keys())
    # reg_keys.sort()
    # reg_keys = list(diction['transformer'].keys())
    # reg_keys.sort()
    xfMVA = diction['transformer_MVA']
    bulkBus = diction['bulkpower_bus']

    # parse the substation metrics file first; there should just be one entity per time sample
    # each metrics file should have matching time points
    lp_s = open(sub_dict_path).read()
    lst_s = json.loads(lp_s)
    print('\nMetrics data starting', lst_s['StartTime'])

    # make a sorted list of the sample times in hours
    lst_s.pop('StartTime')
    meta_s = lst_s.pop('Metadata')
    times = list(map(int, list(lst_s.keys())))
    times.sort()
    print('There are', len(times), 'sample times at', times[1] - times[0], 'second intervals')
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    time_key = str(times[0])

    # find the actual substation name (not a feeder name) as GridLAB-D wrote it to the metrics file
    sub_key = list(lst_s[time_key].keys())[0]
    print('\n\nFile', sub_dict_path, 'has substation', sub_key, 'at bulk system bus',
          bulkBus, 'with', xfMVA, 'MVA transformer')
    print('\nFeeder Dictionary:')
    for key in fdr_keys:
        row = diction['feeders'][key]
        print(key, 'has', row['house_count'], 'houses and', row['inverter_count'], 'inverters')

    # parse the substation metadata for 2 things of specific interest
    # print ('\nSubstation Metadata for', len(lst_s[time_key]), 'objects')
    idx_s = {}
    for key, val in meta_s.items():
        # print (key, val['index'], val['units'])
        if key == 'real_power_avg':
            idx_s['SUB_POWER_IDX'] = val['index']
            idx_s['SUB_POWER_UNITS'] = val['units']
        elif key == 'real_power_losses_avg':
            idx_s['SUB_LOSSES_IDX'] = val['index']
            idx_s['SUB_LOSSES_UNITS'] = val['units']

    # create a NumPy array of all metrics for the substation
    data_s = np.empty(shape=(1, len(times), len(lst_s[time_key][sub_key])), dtype=np.float)
    print('\nConstructed', data_s.shape, 'NumPy array for Substations')
    j = 0
    for key in [sub_key]:
        i = 0
        for t in times:
            ary = lst_s[str(t)][key]
            data_s[j, i, :] = ary
            i = i + 1
        j = j + 1

    # display some averages
    print('Maximum power =',
          '{:.3f}'.format(data_s[0, :, idx_s['SUB_POWER_IDX']].max()), idx_s['SUB_POWER_UNITS'])
    print('Average power =',
          '{:.3f}'.format(data_s[0, :, idx_s['SUB_POWER_IDX']].mean()), idx_s['SUB_POWER_UNITS'])
    print('Average losses =',
          '{:.3f}'.format(data_s[0, :, idx_s['SUB_LOSSES_IDX']].mean()), idx_s['SUB_LOSSES_UNITS'])

    # read the other JSON files; their times (hrs) should be the same
    lp_h = open(house_dict_path).read()
    lst_h = json.loads(lp_h)
    lp_m = open(bm_dict_path).read()
    lst_m = json.loads(lp_m)
    lp_i = open(inv_dict_path).read()
    lst_i = json.loads(lp_i)
    lp_c = open(cap_dict_path).read()
    lst_c = json.loads(lp_c)
    lp_r = open(reg_dict_path).read()
    lst_r = json.loads(lp_r)

    # houses
    idx_h = {}
    data_h = None
    lst_h.pop('StartTime')
    meta_h = lst_h.pop('Metadata')
    # print('\nHouse Metadata for', len(lst_h[time_key]), 'objects')
    for key, val in meta_h.items():
        # print (key, val['index'], val['units'])
        if key == 'air_temperature_avg':
            idx_h['HSE_AIR_AVG_IDX'] = val['index']
            idx_h['HSE_AIR_AVG_UNITS'] = val['units']
        elif key == 'air_temperature_max':
            idx_h['HSE_AIR_MAX_IDX'] = val['index']
            idx_h['HSE_AIR_MAX_UNITS'] = val['units']
        elif key == 'air_temperature_min':
            idx_h['HSE_AIR_MIN_IDX'] = val['index']
            idx_h['HSE_AIR_MIN_UNITS'] = val['units']
        elif key == 'air_temperature_avg':
            idx_h['HSE_AIR_AVG_IDX'] = val['index']
            idx_h['HSE_AIR_AVG_UNITS'] = val['units']
        elif key == 'air_temperature_setpoint_cooling':
            idx_h['HSE_AIR_SETC_IDX'] = val['index']
            idx_h['HSE_AIR_SETC_UNITS'] = val['units']
        elif key == 'air_temperature_setpoint_heating':
            idx_h['HSE_AIR_SETH_IDX'] = val['index']
            idx_h['HSE_AIR_SETH_UNITS'] = val['units']
        elif key == 'total_load_avg':
            idx_h['HSE_TOTAL_AVG_IDX'] = val['index']
            idx_h['HSE_TOTAL_AVG_UNITS'] = val['units']
        elif key == 'hvac_load_avg':
            idx_h['HSE_HVAC_AVG_IDX'] = val['index']
            idx_h['HSE_HVAC_AVG_UNITS'] = val['units']
        elif key == 'waterheater_load_avg':
            idx_h['HSE_WH_AVG_IDX'] = val['index']
            idx_h['HSE_WH_AVG_UNITS'] = val['units']
    if len(hse_keys) > 0:
        # there may be some houses in the dictionary that we don't write metrics for,
        # e.g., write_node_houses with default node_metrics_interval=None
        hse_keys = [x for x in hse_keys if x in lst_h[time_key]]
        print(len(hse_keys), 'houses left')
        data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h[time_key][hse_keys[0]])), dtype=np.float)
        print('\nConstructed', data_h.shape, 'NumPy array for Houses')
        j = 0
        for _ in hse_keys:
            i = 0
            for t in times:
                ary = lst_h[str(t)][hse_keys[j]]
                data_h[j, i, :] = ary
                i = i + 1
            j = j + 1

        print('average all house temperatures Noon-8 pm first day:',
              '{:.3f}'.format(data_h[:, 144:240, idx_h['HSE_AIR_AVG_IDX']].mean()))

    # Billing Meters
    idx_m = {}
    data_m = None
    lst_m.pop('StartTime')
    meta_m = lst_m.pop('Metadata')
    nBillingMeters = 0
    if not lst_m[time_key] is None:
        nBillingMeters = len(lst_m[time_key])
    #  print('\nBilling Meter Metadata for', nBillingMeters, 'objects')
    for key, val in meta_m.items():
        #    print(key, val['index'], val['units'])
        if key == 'voltage_max':
            idx_m['MTR_VOLT_MAX_IDX'] = val['index']
            idx_m['MTR_VOLT_MAX_UNITS'] = val['units']
        elif key == 'voltage_min':
            idx_m['MTR_VOLT_MIN_IDX'] = val['index']
            idx_m['MTR_VOLT_MIN_UNITS'] = val['units']
        elif key == 'voltage_avg':
            idx_m['MTR_VOLT_AVG_IDX'] = val['index']
            idx_m['MTR_VOLT_AVG_UNITS'] = val['units']
        elif key == 'voltage12_max':
            idx_m['MTR_VOLT12_MAX_IDX'] = val['index']
            idx_m['MTR_VOLT12_MAX_UNITS'] = val['units']
        elif key == 'voltage12_min':
            idx_m['MTR_VOLT12_MIN_IDX'] = val['index']
            idx_m['MTR_VOLT12_MIN_UNITS'] = val['units']
        elif key == 'voltage_unbalance_max':
            idx_m['MTR_VOLTUNB_MAX_IDX'] = val['index']
            idx_m['MTR_VOLTUNB_MAX_UNITS'] = val['units']
        elif key == 'bill':
            idx_m['MTR_BILL_IDX'] = val['index']
            idx_m['MTR_BILL_UNITS'] = val['units']
        elif key == 'above_RangeA_Count':
            idx_m['MTR_AHI_COUNT_IDX'] = val['index']
        elif key == 'above_RangeB_Count':
            idx_m['MTR_BHI_COUNT_IDX'] = val['index']
        elif key == 'below_RangeA_Count':
            idx_m['MTR_ALO_COUNT_IDX'] = val['index']
        elif key == 'below_RangeB_Count':
            idx_m['MTR_BLO_COUNT_IDX'] = val['index']
        elif key == 'below_10_percent_NormVol_Count':
            idx_m['MTR_OUT_COUNT_IDX'] = val['index']
        elif key == 'above_RangeA_Duration':
            idx_m['MTR_AHI_DURATION_IDX'] = val['index']
        elif key == 'above_RangeB_Duration':
            idx_m['MTR_BHI_DURATION_IDX'] = val['index']
        elif key == 'below_RangeA_Duration':
            idx_m['MTR_ALO_DURATION_IDX'] = val['index']
        elif key == 'below_RangeB_Duration':
            idx_m['MTR_BLO_DURATION_IDX'] = val['index']
        elif key == 'below_10_percent_NormVol_Duration':
            idx_m['MTR_OUT_DURATION_IDX'] = val['index']
        elif key == 'reactive_energy':
            idx_m['MTR_REACTIVE_ENERGY_IDX'] = val['index']
        elif key == 'reactive_power_avg':
            idx_m['MTR_REACTIVE_POWER_AVG_IDX'] = val['index']
        elif key == 'reactive_power_max':
            idx_m['MTR_REACTIVE_POWER_MAX_IDX'] = val['index']
        elif key == 'reactive_power_min':
            idx_m['MTR_REACTIVE_POWER_MIN_IDX'] = val['index']
        elif key == 'real_energy':
            idx_m['MTR_REAL_ENERGY_IDX'] = val['index']
        elif key == 'real_power_avg':
            idx_m['MTR_REAL_POWER_AVG_IDX'] = val['index']
        elif key == 'real_power_max':
            idx_m['MTR_REAL_POWER_MAX_IDX'] = val['index']
        elif key == 'real_power_min':
            idx_m['MTR_REAL_POWER_MIN_IDX'] = val['index']

    if nBillingMeters > 0:
        # there may be some meters in the dictionary that we don't write metrics for,
        # e.g., write_node_houses with default node_metrics_interval=None
        mtr_keys = [x for x in mtr_keys if x in lst_m[time_key]]
        print(len(mtr_keys), 'meters left, expecting', nBillingMeters)
        data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m[time_key][mtr_keys[0]])), dtype=np.float)
        print('\nConstructed', data_m.shape, 'NumPy array for Meters')
        j = 0
        for _ in mtr_keys:
            i = 0
            for t in times:
                ary = lst_m[str(t)][mtr_keys[j]]
                data_m[j, i, :] = ary
                i = i + 1
            j = j + 1

    # normalize the meter voltages to 100 percent
    j = 0
    for key in mtr_keys:
        vln = diction['billingmeters'][key]['vln'] / 100.0
        vll = diction['billingmeters'][key]['vll'] / 100.0
        data_m[j, :, idx_m['MTR_VOLT_MIN_IDX']] /= vln
        data_m[j, :, idx_m['MTR_VOLT_MAX_IDX']] /= vln
        data_m[j, :, idx_m['MTR_VOLT_AVG_IDX']] /= vln
        data_m[j, :, idx_m['MTR_VOLT12_MIN_IDX']] /= vll
        data_m[j, :, idx_m['MTR_VOLT12_MAX_IDX']] /= vll
        j = j + 1

    idx_i = {}
    data_i = None
    lst_i.pop('StartTime')
    meta_i = lst_i.pop('Metadata')
    # assemble the total solar and battery inverter power
    solar_kw = np.zeros(len(times), dtype=np.float)
    battery_kw = np.zeros(len(times), dtype=np.float)
    #  print('\nInverter Metadata for', len(inv_keys), 'objects')
    for key, val in meta_i.items():
        #    print (key, val['index'], val['units'])
        if key == 'real_power_avg':
            idx_i['INV_P_AVG_IDX'] = val['index']
            idx_i['INV_P_AVG_UNITS'] = val['units']
        elif key == 'reactive_power_avg':
            idx_i['INV_Q_AVG_IDX'] = val['index']
            idx_i['INV_Q_AVG_UNITS'] = val['units']
    if len(inv_keys) > 0:
        data_i = np.empty(shape=(len(inv_keys), len(times), len(lst_i[time_key][inv_keys[0]])), dtype=np.float)
        print('\nConstructed', data_i.shape, 'NumPy array for Inverters')
        j = 0
        for _ in inv_keys:
            i = 0
            for t in times:
                ary = lst_i[str(t)][inv_keys[j]]
                data_i[j, i, :] = ary
                i = i + 1
            j = j + 1
        j = 0
        for key in inv_keys:
            res = diction['inverters'][key]['resource']
            if res == 'solar':
                solar_kw += 0.001 * data_i[j, :, idx_i['INV_P_AVG_IDX']]
            elif res == 'battery':
                battery_kw += 0.001 * data_i[j, :, idx_i['INV_P_AVG_IDX']]
            j = j + 1

    idx_c = {}
    data_c = None
    lst_c.pop('StartTime')
    meta_c = lst_c.pop('Metadata')
    #  print('\nCapacitor Metadata for', len(cap_keys), 'objects')
    for key, val in meta_c.items():
        if key == 'operation_count':
            idx_c['CAP_COUNT_IDX'] = val['index']
            idx_c['CAP_COUNT_UNITS'] = val['units']
    if len(cap_keys) > 0 and bCollectedRegCapMetrics:
        data_c = np.empty(shape=(len(cap_keys), len(times), len(lst_c[time_key][cap_keys[0]])), dtype=np.float)
        print('\nConstructed', data_c.shape, 'NumPy array for Capacitors')
        j = 0
        for _ in cap_keys:
            i = 0
            for t in times:
                ary = lst_c[str(t)][cap_keys[j]]
                data_c[j, i, :] = ary
                i = i + 1
            j = j + 1
        print('Total cap switchings =', data_c[:, -1, idx_c['CAP_COUNT_IDX']].sum())

    idx_r = {}
    data_r = None
    lst_r.pop('StartTime')
    meta_r = lst_r.pop('Metadata')
    #  print('\nRegulator Metadata for', len(reg_keys), 'objects')
    for key, val in meta_r.items():
        if key == 'operation_count':
            idx_r['REG_COUNT_IDX'] = val['index']
            idx_r['REG_COUNT_UNITS'] = val['units']
    if len(reg_keys) > 0 and bCollectedRegCapMetrics:
        data_r = np.empty(shape=(len(reg_keys), len(times), len(lst_r[time_key][reg_keys[0]])), dtype=np.float)
        print('\nConstructed', data_r.shape, 'NumPy array for Regulators')
        j = 0
        for _ in reg_keys:
            i = 0
            for t in times:
                ary = lst_r[str(t)][reg_keys[j]]
                data_r[j, i, :] = ary
                i = i + 1
            j = j + 1
        print('Total tap changes =', data_r[:, -1, idx_r['REG_COUNT_IDX']].sum())

    if data_m is not None:
        print('Total meter bill =',
              '{:.3f}'.format(data_m[:, -1, idx_m['MTR_BILL_IDX']].sum()))

    return {
        'hrs': hrs,
        'data_s': data_s,
        'data_m': data_m,
        'data_i': data_i,
        'data_h': data_h,
        'data_c': data_c,
        'data_r': data_r,
        'keys_s': fdr_keys,
        'keys_m': mtr_keys,
        'keys_i': inv_keys,
        'keys_h': hse_keys,
        'keys_c': cap_keys,
        'keys_r': reg_keys,
        'idx_s': idx_s,
        'idx_m': idx_m,
        'idx_i': idx_i,
        'idx_h': idx_h,
        'idx_c': idx_c,
        'idx_r': idx_r,
        'solar_kw': solar_kw,
        'battery_kw': battery_kw,
        'subname': sub_key
    }


def plot_gld(diction, save_file=None, save_only=False):
    # the feederGenerator now inserts metrics_collector objects on capacitors and regulators
    bCollectedRegCapMetrics = True

    hrs = diction['hrs']
    data_s = diction['data_s']
    data_m = diction['data_m']
    # data_i = diction['data_i']  # not used
    data_h = diction['data_h']
    data_c = diction['data_c']
    data_r = diction['data_r']
    # keys_s = diction['keys_s']  # not used
    keys_m = diction['keys_m']
    # keys_i = diction['keys_i']  # not used
    keys_h = diction['keys_h']
    keys_c = diction['keys_c']
    keys_r = diction['keys_r']
    idx_s = diction['idx_s']
    idx_m = diction['idx_m']
    # idx_i = diction['idx_i']  # not used
    idx_h = diction['idx_h']
    idx_c = diction['idx_c']
    idx_r = diction['idx_r']
    solar_kw = diction['solar_kw']
    battery_kw = diction['battery_kw']

    # display a plot
    fig, ax = plt.subplots(2, 5, sharex='col')

    total2 = None
    hvac2 = None
    wh2 = None
    if len(keys_h) > 0:
        total1 = (data_h[:, :, idx_h['HSE_TOTAL_AVG_IDX']]).squeeze()
        total2 = total1.sum(axis=0)
        hvac1 = (data_h[:, :, idx_h['HSE_HVAC_AVG_IDX']]).squeeze()
        hvac2 = hvac1.sum(axis=0)
        wh1 = (data_h[:, :, idx_h['HSE_WH_AVG_IDX']]).squeeze()
        wh2 = wh1.sum(axis=0)
    ax[0, 0].plot(hrs, 0.001 * data_s[0, :, idx_s['SUB_POWER_IDX']], color='blue', label='Total')
    ax[0, 0].plot(hrs, 0.001 * data_s[0, :, idx_s['SUB_LOSSES_IDX']], color='red', label='Losses')
    if len(keys_h) > 0:
        ax[0, 0].plot(hrs, total2, color='green', label='Houses')
        ax[0, 0].plot(hrs, hvac2, color='magenta', label='HVAC')
        ax[0, 0].plot(hrs, wh2, color='orange', label='WH')
    ax[0, 0].set_ylabel('kW')
    ax[0, 0].set_title('Real Power at\n ' + diction['subname'])
    ax[0, 0].legend(loc='best')

    # vabase = diction['inverters'][inv_keys[0]]['rated_W']
    # print ('Inverter base power =', vabase)
    # ax[0,1].plot(hrs, data_i[0,:,INV_P_AVG_IDX] / vabase, color='blue', label='Real')
    # ax[0,1].plot(hrs, data_i[0,:,INV_Q_AVG_IDX] / vabase, color='red', label='Reactive')
    # ax[0,1].set_ylabel('perunit')
    # ax[0,1].set_title ('Inverter Power at ' + inv_keys[0])
    # ax[0,1].legend(loc='best')

    # ax[0,1].plot(hrs, data_m[0,:,MTR_VOLTUNB_MAX_IDX], color='red', label='Max')
    # ax[0,1].set_ylabel('perunit')
    # ax[0,1].set_title ('Voltage Unbalance at ' + mtr_keys[0])

    if len(keys_h) > 0:
        avg1 = (data_h[:, :, idx_h['HSE_AIR_AVG_IDX']]).squeeze()
        avg2 = avg1.mean(axis=0)
        min1 = (data_h[:, :, idx_h['HSE_AIR_MIN_IDX']]).squeeze()
        min2 = min1.min(axis=0)
        max1 = (data_h[:, :, idx_h['HSE_AIR_MAX_IDX']]).squeeze()
        max2 = max1.max(axis=0)
        ax[0, 1].plot(hrs, max2, color='blue', label='Max')
        ax[0, 1].plot(hrs, min2, color='red', label='Min')
        ax[0, 1].plot(hrs, avg2, color='green', label='Avg')
        ax[0, 1].set_ylabel('degF')
        ax[0, 1].set_title('Temperature over\n {:d} Houses'.format(len(keys_h)))
        ax[0, 1].legend(loc='best')
    else:
        ax[0, 1].set_title('No Houses')

    if len(keys_m) > 0:
        if len(keys_m) > 1:
            vavg = (data_m[:, :, idx_m['MTR_VOLT_AVG_IDX']]).squeeze().mean(axis=0)
            vmin = (data_m[:, :, idx_m['MTR_VOLT_MIN_IDX']]).squeeze().min(axis=0)
            vmax = (data_m[:, :, idx_m['MTR_VOLT_MAX_IDX']]).squeeze().max(axis=0)
            ax[1, 0].plot(hrs, vmax, color='blue', label='Max')
            ax[1, 0].plot(hrs, vmin, color='red', label='Min')
            ax[1, 0].plot(hrs, vavg, color='green', label='Avg')
            ax[1, 0].set_title('Voltage over\n {:d} Meters'.format(len(keys_m)))
            ax[1, 0].legend(loc='best')
        else:
            ax[1, 0].plot(hrs, data_m[0, :, idx_m['MTR_VOLT_AVG_IDX']], color='blue')
            ax[1, 0].set_title('Voltage at ' + keys_m[0])
        ax[1, 0].set_xlabel('Hours')
        ax[1, 0].set_ylabel('%')
    else:
        ax[1, 0].set_title('No Billing Meter\n Voltages')

    if len(keys_h) > 0:
        ax[1, 1].plot(hrs, data_h[0, :, idx_h['HSE_AIR_AVG_IDX']], color='blue', label='Mean')
        ax[1, 1].plot(hrs, data_h[0, :, idx_h['HSE_AIR_MIN_IDX']], color='red', label='Min')
        ax[1, 1].plot(hrs, data_h[0, :, idx_h['HSE_AIR_MAX_IDX']], color='green', label='Max')
        ax[1, 1].plot(hrs, data_h[0, :, idx_h['HSE_AIR_SETC_IDX']], color='magenta', label='SetC')
        ax[1, 1].plot(hrs, data_h[0, :, idx_h['HSE_AIR_SETH_IDX']], color='orange', label='SetH')
        ax[1, 1].set_xlabel('Hours')
        ax[1, 1].set_ylabel(idx_h['HSE_AIR_AVG_UNITS'])
        ax[1, 1].set_title('House Air at\n ' + keys_h[0])
        ax[1, 1].legend(loc='best')
    else:
        ax[1, 1].set_title('No Houses')

    ax[0, 2].plot(hrs, solar_kw, color='blue', label='Solar')
    ax[0, 2].plot(hrs, battery_kw, color='red', label='Battery')
    ax[0, 2].set_xlabel('Hours')
    ax[0, 2].set_ylabel('kW')
    ax[0, 2].set_title('Total Inverter Power')
    ax[0, 2].legend(loc='best')

    if len(keys_m) > 0:
        ax[1, 2].plot(hrs, data_m[:, :, idx_m['MTR_BILL_IDX']].sum(axis=0), color='blue')
        ax[1, 2].set_xlabel('Hours')
        ax[1, 2].set_ylabel(idx_m['MTR_BILL_UNITS'])
        ax[1, 2].set_title('Total Meter Bill')
    else:
        ax[1, 2].set_title('No Billing Meters')

    if len(keys_c) > 0 and bCollectedRegCapMetrics:
        ax[0, 3].plot(hrs, data_c[:, :, idx_c['CAP_COUNT_IDX']].sum(axis=0), color='blue', label='Total')
        ax[0, 3].set_ylabel('')
        ax[0, 3].set_title('Capacitor Switchings')
        ax[0, 3].legend(loc='best')
    else:
        ax[0, 3].set_title('No Capacitors')

    if len(keys_r) > 0 and bCollectedRegCapMetrics:
        ax[1, 3].plot(hrs, data_r[:, :, idx_r['REG_COUNT_IDX']].sum(axis=0), color='blue', label='Total')
        #   ax[1,3].plot(hrs, data_r[0,:,idx_r['REG_COUNT_IDX']], color='blue', label=reg_keys[0])
        #   ax[1,3].plot(hrs, data_r[1,:,idx_r['REG_COUNT_IDX']], color='red', label=reg_keys[1])
        #   ax[1,3].plot(hrs, data_r[2,:,idx_r['REG_COUNT_IDX']], color='green', label=reg_keys[2])
        #   ax[1,3].plot(hrs, data_r[3,:,idx_r['REG_COUNT_IDX']], color='magenta', label=reg_keys[3])
        ax[1, 3].set_xlabel('Hours')
        ax[1, 3].set_ylabel('')
        ax[1, 3].set_title('Regulator Tap Changes')
        ax[1, 3].legend(loc='best')
    else:
        ax[1, 3].set_title('No Regulators')

    if len(keys_m) > 1:
        ax[0, 4].plot(hrs, (data_m[:, :, idx_m['MTR_AHI_COUNT_IDX']]).squeeze().sum(axis=0), color='blue', label='Range A Hi')
        ax[0, 4].plot(hrs, (data_m[:, :, idx_m['MTR_BHI_COUNT_IDX']]).squeeze().sum(axis=0), color='cyan', label='Range B Hi')
        ax[0, 4].plot(hrs, (data_m[:, :, idx_m['MTR_ALO_COUNT_IDX']]).squeeze().sum(axis=0), color='green', label='Range A Lo')
        ax[0, 4].plot(hrs, (data_m[:, :, idx_m['MTR_BLO_COUNT_IDX']]).squeeze().sum(axis=0), color='magenta', label='Range B Lo')
        ax[0, 4].plot(hrs, (data_m[:, :, idx_m['MTR_OUT_COUNT_IDX']]).squeeze().sum(axis=0), color='red', label='No Voltage')
        ax[0, 4].set_ylabel('')
        ax[0, 4].set_title('Voltage Violation\n Counts')
        ax[0, 4].legend(loc='best')

        ax[1, 4].plot(hrs, (data_m[:, :, idx_m['MTR_AHI_DURATION_IDX']]).squeeze().sum(axis=0), color='blue', label='Range A Hi')
        ax[1, 4].plot(hrs, (data_m[:, :, idx_m['MTR_BHI_DURATION_IDX']]).squeeze().sum(axis=0), color='cyan', label='Range B Hi')
        ax[1, 4].plot(hrs, (data_m[:, :, idx_m['MTR_ALO_DURATION_IDX']]).squeeze().sum(axis=0), color='green', label='Range A Lo')
        ax[1, 4].plot(hrs, (data_m[:, :, idx_m['MTR_BLO_DURATION_IDX']]).squeeze().sum(axis=0), color='magenta', label='Range B Lo')
        ax[1, 4].plot(hrs, (data_m[:, :, idx_m['MTR_OUT_DURATION_IDX']]).squeeze().sum(axis=0), color='red', label='No Voltage')
        ax[1, 3].set_xlabel('Hours')
        ax[1, 4].set_ylabel('Seconds')
        ax[1, 4].set_title('Voltage Violation\n Durations')
        ax[1, 4].legend(loc='best')
    elif len(keys_m) > 0:
        ax[0, 4].plot(hrs, data_m[0, :, idx_m['MTR_AHI_COUNT_IDX']], color='blue', label='Range A Hi')
        ax[0, 4].plot(hrs, data_m[0, :, idx_m['MTR_BHI_COUNT_IDX']], color='cyan', label='Range B Hi')
        ax[0, 4].plot(hrs, data_m[0, :, idx_m['MTR_ALO_COUNT_IDX']], color='green', label='Range A Lo')
        ax[0, 4].plot(hrs, data_m[0, :, idx_m['MTR_BLO_COUNT_IDX']], color='magenta', label='Range B Lo')
        ax[0, 4].plot(hrs, data_m[0, :, idx_m['MTR_OUT_COUNT_IDX']], color='red', label='No Voltage')
        ax[0, 4].set_ylabel('')
        ax[0, 4].set_title('Voltage Violation\n Counts at ' + keys_m[0])
        ax[0, 4].legend(loc='best')

        ax[1, 4].plot(hrs, data_m[0, :, idx_m['MTR_AHI_DURATION_IDX']], color='blue', label='Range A Hi')
        ax[1, 4].plot(hrs, data_m[0, :, idx_m['MTR_BHI_DURATION_IDX']], color='cyan', label='Range B Hi')
        ax[1, 4].plot(hrs, data_m[0, :, idx_m['MTR_ALO_DURATION_IDX']], color='green', label='Range A Lo')
        ax[1, 4].plot(hrs, data_m[0, :, idx_m['MTR_BLO_DURATION_IDX']], color='magenta', label='Range B Lo')
        ax[1, 4].plot(hrs, data_m[0, :, idx_m['MTR_OUT_DURATION_IDX']], color='red', label='No Voltage')
        ax[1, 4].set_xlabel('Hours')
        ax[1, 4].set_ylabel('Seconds')
        ax[1, 4].set_title('Voltage Violation\n Durations ' + keys_m[0])
        ax[1, 4].legend(loc='best')
    else:
        ax[0, 4].set_title('No Voltage Monitoring')
        ax[1, 4].set_title('No Voltage Monitoring')

    if save_file is not None:
        plt.savefig(save_file)
    if not save_only:
        plt.show()


def process_gld(name_root, diction_name='', save_file=None, save_only=False):
    """ Plots a summary/sample of power, air temperature and voltage

    This function reads *substation_[name_root]_metrics.json*,
    *billing_meter_[name_root]_metrics.json* and
    *house_[name_root]_metrics.json* for the data;
    it reads *[name_root]_glm_dict.json* for the metadata.
    These must all exist in the current working directory.
    Makes one graph with 4 subplots:

    1. Substation real power and losses
    2. Average air temperature over all houses
    3. Min/Max line-to-neutral voltage and Min/Max line-to-line voltage at the first billing meter
    4. Min, Max and Average air temperature at the first house

    Args:
      name_root (str): name of the TESP case, not necessarily the same as the GLM case, without the extension
      diction_name (str): metafile name (with json extension) for a different GLM dictionary, if it's not *[name_root]_glm_dict.json*. Defaults to empty.
      save_file (str): name of a file to save plot, should include the *png* or *pdf* extension to determine type.
      save_only (Boolean): set True with *save_file* to skip the display of the plot. Otherwise, script waits for user keypress.
    """
    path = os.getcwd()
    diction = read_gld_metrics(path, name_root, diction_name)
    plot_gld(diction, save_file, save_only)
