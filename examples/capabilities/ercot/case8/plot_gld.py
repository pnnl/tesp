#	Copyright (C) 2017-2022 Battelle Memorial Institute
# file: process_gld.py; custom for the IEEE 8500-node circuit

import json
import sys
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

# first, read and print a dictionary of all the monitored GridLAB-D objects
lp = open (sys.argv[1] + '_glm_dict.json').read()
dict = json.loads(lp)
sub_keys = list(dict['feeders'].keys())
sub_keys.sort()
hse_keys = list(dict['houses'].keys())
hse_keys.sort()
mtr_keys = list(dict['billingmeters'].keys())
mtr_keys.sort()
xfMVA = dict['transformer_MVA']
bulkBus = dict['bulkpower_bus']
print ("\n\nFile", sys.argv[1], "has substation", sub_keys[0], "at bulk system bus", bulkBus, "with", xfMVA, "MVA transformer")

# parse the substation metrics file first; there should just be one entity per time sample
# each metrics file should have matching time points
lp_s = open ('substation_' + sys.argv[1] + '_metrics.json').read()
lst_s = json.loads(lp_s)
print ('\nMetrics data starting', lst_s['StartTime'])

# make a sorted list of the sample times in hours
lst_s.pop('StartTime')
meta_s = lst_s.pop('Metadata')
times = list(map(int,list(lst_s.keys())))
times.sort()
print ('There are', len (times), 'sample times at', times[1] - times[0], 'second intervals')
hrs = np.array(times, dtype=np.float)
denom = 3600.0
hrs /= denom

# parse the substation metadata for 2 things of specific interest
print ('\nSubstation Metadata for', len(lst_s['3600']), 'objects')
for key, val in meta_s.items():
#	print (key, val['index'], val['units'])
	if key == 'real_power_avg':
		SUB_POWER_IDX = val['index']
		SUB_POWER_UNITS = val['units']
	elif key == 'real_power_median':
		SUB_MEDIAN_IDX = val['index']
		SUB_MEDIAN_UNITS = val['units']
	elif key == 'real_power_losses_avg':
		SUB_LOSSES_IDX = val['index']
		SUB_LOSSES_UNITS = val['units']

# create a NumPy array of all metrics for the substation
data_s = np.empty(shape=(len(sub_keys), len(times), len(lst_s['3600'][sub_keys[0]])), dtype=np.float)
print ('\nConstructed', data_s.shape, 'NumPy array for Substations')
j = 0
for key in sub_keys:
	i = 0
	for t in times:
		ary = lst_s[str(t)][sub_keys[j]]
		data_s[j, i,:] = ary
		i = i + 1
	j = j + 1

# display some averages
print ('Max avg power =', data_s[0,:,SUB_POWER_IDX].max(), SUB_POWER_UNITS)
print ('Average power =', data_s[0,:,SUB_POWER_IDX].mean(), SUB_POWER_UNITS)
print ('Average losses =', data_s[0,:,SUB_LOSSES_IDX].mean(), SUB_LOSSES_UNITS)

# read the other JSON files; their times (hrs) should be the same
lp_h = open ('house_' + sys.argv[1] + '_metrics.json').read()
lst_h = json.loads(lp_h)
lp_m = open ('billing_meter_' + sys.argv[1] + '_metrics.json').read()
lst_m = json.loads(lp_m)

# houses
lst_h.pop('StartTime')
meta_h = lst_h.pop('Metadata')
print('\nHouse Metadata for', len(lst_h['3600']), 'objects')
for key, val in meta_h.items():
#	print (key, val['index'], val['units'])
	if key == 'air_temperature_max':
		HSE_AIR_MAX_IDX = val['index']
		HSE_AIR_MAX_UNITS = val['units']
	elif key == 'air_temperature_min':
		HSE_AIR_MIN_IDX = val['index']
		HSE_AIR_MIN_UNITS = val['units']
	elif key == 'air_temperature_avg':
		HSE_AIR_AVG_IDX = val['index']
		HSE_AIR_AVG_UNITS = val['units']
	elif key == 'air_temperature_median':
		HSE_AIR_MED_IDX = val['index']
		HSE_AIR_MED_UNITS = val['units']
	elif key == 'total_load_avg':
		HSE_TOTAL_AVG_IDX = val['index']
		HSE_TOTAL_AVG_UNITS = val['units']
	elif key == 'hvac_load_avg':
		HSE_HVAC_AVG_IDX = val['index']
		HSE_HVAC_AVG_UNITS = val['units']
	elif key == 'waterheater_load_avg':
		HSE_WH_AVG_IDX = val['index']
		HSE_WH_AVG_UNITS = val['units']
data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h['3600'][hse_keys[0]])), dtype=np.float)
print ('\nConstructed', data_h.shape, 'NumPy array for Houses')
j = 0
for key in hse_keys:
	i = 0
	for t in times:
		ary = lst_h[str(t)][hse_keys[j]]
		data_h[j, i,:] = ary
		i = i + 1
	j = j + 1

print ('average all house temperatures during simulation:', data_h[:,:,HSE_AIR_AVG_IDX].mean())

# Billing Meters 
lst_m.pop('StartTime')
meta_m = lst_m.pop('Metadata')
print('\nBilling Meter Metadata for', len(lst_m['3600']), 'objects')
for key, val in meta_m.items():
#	print (key, val['index'], val['units'])
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
print ('\nConstructed', data_m.shape, 'NumPy array for Meters')
j = 0
for key in mtr_keys:
	i = 0
	for t in times:
		ary = lst_m[str(t)][mtr_keys[j]]
		data_m[j, i,:] = ary
		i = i + 1
	j = j + 1

# normalize each meter voltage
j = 0
for key in mtr_keys:
	vln = dict['billingmeters'][key]['vln']
	vll = dict['billingmeters'][key]['vll']
	data_m[j,:,MTR_VOLT_MIN_IDX] /= vln
	data_m[j,:,MTR_VOLT_MAX_IDX] /= vln
	data_m[j,:,MTR_VOLT_AVG_IDX] /= vln
	data_m[j,:,MTR_VOLT12_MIN_IDX] /= vll
	data_m[j,:,MTR_VOLT12_MAX_IDX] /= vll
	j = j + 1

print ('Total meter bill =', '{:.2f}'.format(data_m[:,-1,MTR_BILL_IDX].sum()))
print ('Min house voltage = ', '{:.2f} pu'.format(data_m[:,:,MTR_VOLT_MIN_IDX].min()))
print ('Min house voltage = ', '{:.2f} pu'.format(data_m[:,:,MTR_VOLT_MAX_IDX].max()))
print ('Min feeder power =', '{:.2f}'.format(1.0e-6 * data_s[0,:,SUB_POWER_IDX].min()), 'MW')
print ('Max feeder power =', '{:.2f}'.format(1.0e-6 * data_s[0,:,SUB_POWER_IDX].max()), 'MW')

# display a plot
fig, ax = plt.subplots(2, 2, sharex = 'col')

total1 = (data_h[:,:,HSE_TOTAL_AVG_IDX]).squeeze()
total2 = total1.sum(axis=0)
hvac1 = (data_h[:,:,HSE_HVAC_AVG_IDX]).squeeze()
hvac2 = hvac1.sum(axis=0)
wh1 = (data_h[:,:,HSE_WH_AVG_IDX]).squeeze()
wh2 = wh1.sum(axis=0)
subkw = 0.001 * data_s[0,:,SUB_POWER_IDX]
submdn = 0.001 * data_s[0,:,SUB_MEDIAN_IDX]
losskw = 0.001 * data_s[0,:,SUB_LOSSES_IDX]
ax[0,0].plot(hrs, subkw, color='blue', label='Substation Mean')
ax[0,0].plot(hrs, submdn, color='cyan', label='Substation Median')
ax[0,0].plot(hrs, losskw, color='red', label='Losses')
ax[0,0].plot(hrs, total2, color='green', label='Houses')
ax[0,0].plot(hrs, hvac2, color='magenta', label='HVAC')
ax[0,0].plot(hrs, wh2, color='orange', label='WH')
ax[0,0].set_ylabel('kW')
ax[0,0].set_title ('Real Power')
ax[0,0].legend(loc='best')
print('final values of Substation, Losses, Houses, HVAC, WH', subkw[-1],losskw[-1],total2[-1],hvac2[-1],wh2[-1])

avg1 = (data_h[:,:,HSE_AIR_AVG_IDX]).squeeze()
avg2 = avg1.mean(axis=0)
min1 = (data_h[:,:,HSE_AIR_MIN_IDX]).squeeze()
min2 = min1.min(axis=0)
max1 = (data_h[:,:,HSE_AIR_MAX_IDX]).squeeze()
max2 = max1.max(axis=0)
ax[0,1].plot(hrs, max2, color='blue', label='Max')
ax[0,1].plot(hrs, min2, color='red', label='Min')
ax[0,1].plot(hrs, avg2, color='green', label='Avg')
ax[0,1].set_ylabel('degF')
ax[0,1].set_title ('Temperature over All Houses')
ax[0,1].legend(loc='best')

vavg = (data_m[:,:,MTR_VOLT_AVG_IDX]).squeeze().mean(axis=0)
vmin = (data_m[:,:,MTR_VOLT_MIN_IDX]).squeeze().min(axis=0)
vmax = (data_m[:,:,MTR_VOLT_MAX_IDX]).squeeze().max(axis=0)
ax[1,0].plot(hrs, vmax, color='blue', label='Max')
ax[1,0].plot(hrs, vmin, color='red', label='Min')
ax[1,0].plot(hrs, vavg, color='green', label='Avg')
ax[1,0].set_xlabel('Hours')
ax[1,0].set_ylabel('pu')
ax[1,0].set_title ('Voltage over all Meters')
ax[1,0].legend(loc='best')

bill1 = (data_m[:,:,MTR_BILL_IDX]).squeeze()
bill2 = bill1.sum(axis=0)
ax[1,1].plot(hrs, bill2, color='blue')
ax[1,1].set_xlabel('Hours')
ax[1,1].set_ylabel(MTR_BILL_UNITS)
ax[1,1].set_title ('Bill over all Meters')

plt.show()


