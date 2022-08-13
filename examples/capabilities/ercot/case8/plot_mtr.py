# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: process_gld.py; custom for the IEEE 8500-node circuit

import json
import sys

import matplotlib.pyplot as plt
import numpy as np

# first, read and print a dictionary of all the monitored GridLAB-D objects
lp = open(sys.argv[1] + '_glm_dict.json').read()
dict = json.loads(lp)
sub_keys = list(dict['feeders'].keys())
sub_keys.sort()
hse_keys = list(dict['houses'].keys())
hse_keys.sort()
mtr_keys = list(dict['billingmeters'].keys())
mtr_keys.sort()
xfMVA = dict['transformer_MVA']
bulkBus = dict['bulkpower_bus']
print("\n\nFile", sys.argv[1], "has substation", sub_keys[0], "at bulk system bus", bulkBus, "with", xfMVA,
      "MVA transformer")

lp_m = open('billing_meter_' + sys.argv[1] + '_metrics.json').read()
lst_m = json.loads(lp_m)
print('\nMetrics data starting', lst_m['StartTime'])

lst_m.pop('StartTime')
meta_m = lst_m.pop('Metadata')
times = list(map(int, list(lst_m.keys())))
times.sort()
print('There are', len(times), 'sample times at', times[1] - times[0], 'second intervals')
hrs = np.array(times, dtype=np.float)
denom = 3600.0
hrs /= denom

# Billing Meters 
print('\nBilling Meter Metadata for', len(lst_m['3600']), 'objects')
for key, val in meta_m.items():
    # print (key, val['index'], val['units'])
    if key == 'voltage_max':
        MTR_VOLT_MAX_IDX = val['index']
        MTR_VOLT_MAX_UNITS = val['units']
    elif key == 'voltage_min':
        MTR_VOLT_MIN_IDX = val['index']
        MTR_VOLT_MIN_UNITS = val['units']
    elif key == 'voltage_avg':
        MTR_VOLT_AVG_IDX = val['index']
        MTR_VOLT_AVG_UNITS = val['units']
    elif key == 'voltage12_max':
        MTR_VOLT12_MAX_IDX = val['index']
        MTR_VOLT12_MAX_UNITS = val['units']
    elif key == 'voltage12_min':
        MTR_VOLT12_MIN_IDX = val['index']
        MTR_VOLT12_MIN_UNITS = val['units']
    elif key == 'voltage_unbalance_max':
        MTR_VOLTUNB_MAX_IDX = val['index']
        MTR_VOLTUNB_MAX_UNITS = val['units']
    elif key == 'bill':
        MTR_BILL_IDX = val['index']
        MTR_BILL_UNITS = val['units']
    elif key == 'above_RangeA_Count':
        MTR_AHI_COUNT_IDX = val['index']
    elif key == 'above_RangeB_Count':
        MTR_BHI_COUNT_IDX = val['index']
    elif key == 'below_RangeA_Count':
        MTR_ALO_COUNT_IDX = val['index']
    elif key == 'below_RangeB_Count':
        MTR_BLO_COUNT_IDX = val['index']
    elif key == 'below_10_percent_NormVol_Count':
        MTR_OUT_COUNT_IDX = val['index']
    elif key == 'above_RangeA_Duration':
        MTR_AHI_DURATION_IDX = val['index']
    elif key == 'above_RangeB_Duration':
        MTR_BHI_DURATION_IDX = val['index']
    elif key == 'below_RangeA_Duration':
        MTR_ALO_DURATION_IDX = val['index']
    elif key == 'below_RangeB_Duration':
        MTR_BLO_DURATION_IDX = val['index']
    elif key == 'below_10_percent_NormVol_Duration':
        MTR_OUT_DURATION_IDX = val['index']

data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m['3600'][mtr_keys[0]])), dtype=np.float)
print('\nConstructed', data_m.shape, 'NumPy array for Meters')
j = 0
for key in mtr_keys:
    i = 0
    for t in times:
        ary = lst_m[str(t)][mtr_keys[j]]
        data_m[j, i, :] = ary
        i = i + 1
    j = j + 1

# normalize each meter voltage
j = 0
for key in mtr_keys:
    vln = dict['billingmeters'][key]['vln']
    vll = dict['billingmeters'][key]['vll']
    data_m[j, :, MTR_VOLT_MIN_IDX] /= vln
    data_m[j, :, MTR_VOLT_MAX_IDX] /= vln
    data_m[j, :, MTR_VOLT_AVG_IDX] /= vln
    data_m[j, :, MTR_VOLT12_MIN_IDX] /= vll
    data_m[j, :, MTR_VOLT12_MAX_IDX] /= vll
    j = j + 1

print('Total meter bill =', '{:.2f}'.format(data_m[:, -1, MTR_BILL_IDX].sum()))
print('Min house voltage = ', '{:.2f} pu'.format(data_m[:, :, MTR_VOLT_MIN_IDX].min()))
print('Min house voltage = ', '{:.2f} pu'.format(data_m[:, :, MTR_VOLT_MAX_IDX].max()))

# display a plot
fig, ax = plt.subplots(1, 2, sharex='col')

vavg = (data_m[:, :, MTR_VOLT_AVG_IDX]).squeeze().mean(axis=0)
vmin = (data_m[:, :, MTR_VOLT_MIN_IDX]).squeeze().min(axis=0)
vmax = (data_m[:, :, MTR_VOLT_MAX_IDX]).squeeze().max(axis=0)
ax[0].plot(hrs, vmax, color='blue', label='Max')
ax[0].plot(hrs, vmin, color='red', label='Min')
ax[0].plot(hrs, vavg, color='green', label='Avg')
ax[0].set_xlabel('Hours')
ax[0].set_ylabel('pu')
ax[0].set_title('Voltage over all Meters')
ax[0].legend(loc='best')

bill1 = (data_m[:, :, MTR_BILL_IDX]).squeeze()
bill2 = bill1.sum(axis=0)
ax[1].plot(hrs, bill2, color='blue')
ax[1].set_xlabel('Hours')
ax[1].set_ylabel(MTR_BILL_UNITS)
ax[1].set_title('Bill over all Meters')

plt.show()
