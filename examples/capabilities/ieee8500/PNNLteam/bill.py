# Copyright (C) 2018-2020 Battelle Memorial Institute
# file: bill.py; custom for the IEEE 8500-node circuit
import json;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;
import os.path;

rootname = sys.argv[1]
dictname = rootname + '_glm_dict.json'
if not os.path.exists(dictname):
  dictname = 'inv8500_glm_dict.json'

# first, read and print a dictionary of all the monitored GridLAB-D objects
lp = open (dictname).read()
dict = json.loads(lp)
inv_keys = list(dict['inverters'].keys())
inv_keys.sort()
mtr_keys = list(dict['billingmeters'].keys())
mtr_keys.sort()
xfMVA = dict['transformer_MVA']
bulkBus = dict['bulkpower_bus']

# each metrics file should have matching time points
lp_m = open ("billing_meter_" + rootname + "_metrics.json").read()
lst_m = json.loads(lp_m)
print ("\nMetrics data starting", lst_m['StartTime'])

# make a sorted list of the sample times in hours
lst_m.pop('StartTime')
meta_m = lst_m.pop('Metadata')
times = list(map(int,list(lst_m.keys())))
times.sort()
print ("There are", len (times), "sample times at", times[1] - times[0], "second intervals")
hrs = np.array(times, dtype=np.float)
denom = 3600.0
hrs /= denom
time_key = str(times[0])

# parse the metadata for things of specific interest
#print("\nBilling Meter Metadata for", len(lst_m[time_key]), "objects")
for key, val in meta_m.items():
  if key == 'real_power_avg':
    POWER_IDX = val['index']
  elif key == 'real_energy':
    ENERGY_IDX = val['index']
  elif key == 'bill':
    BILL_IDX = val['index']

# create a NumPy array of all metrics
data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m[time_key][mtr_keys[0]])), dtype=np.float)
j = 0
for key in mtr_keys:
  i = 0
  for t in times:
    ary = lst_m[str(t)][mtr_keys[j]]
    data_m[j, i,:] = ary
    i = i + 1
  j = j + 1

final_bill = np.empty(shape=(len(times)), dtype=np.float)
final_bill[0] = 0.0
for i in range (1, len(hrs)):
	if hrs[i] > 15.0 and hrs[i] <= 19.0:
		price = 0.15
	else:
		price = 0.11
	kwh = 0.001 * data_m[:,i,ENERGY_IDX].sum()
	# print ('adding', kwh, 'at', price)
	final_bill[i] = final_bill[i-1] + price * kwh

print ("Initial meter bill =", '{:.2f}'.format(data_m[:,-1,BILL_IDX].sum()))
print ("Final meter bill =", '{:.2f}'.format(final_bill[-1]))
# display a plot
fig, ax = plt.subplots(1, 3)
tmin = 0.0
tmax = 24.0
xticks = [0,4,8,12,16,20,24]

ax[0].set_title ('Total Billings')                
ax[0].set_ylabel('USD')                         
ax[0].plot(hrs, (data_m[:,:,BILL_IDX]).squeeze().sum(axis=0), color='blue', label='Initial')
ax[0].plot(hrs, final_bill, color='red', label='Final')
ax[0].set_xlim(tmin,tmax)
ax[0].set_xticks(xticks)
ax[0].set_xlabel('Hours')                                 
ax[0].legend(loc='best')

ax[1].set_title ('Interval Energy')                
ax[1].set_ylabel('kWh')                         
ax[1].plot(hrs, 0.001 * (data_m[:,:,ENERGY_IDX]).squeeze().sum(axis=0))
ax[1].set_xlim(tmin,tmax)
ax[1].set_xticks(xticks)
ax[1].set_xlabel('Hours')                                 

ax[2].set_title ('Total Real Power')                
ax[2].set_ylabel('kW')                         
ax[2].plot(hrs, 0.001 * (data_m[:,:,POWER_IDX]).squeeze().sum(axis=0))
ax[2].set_xlim(tmin,tmax)
ax[2].set_xticks(xticks)
ax[2].set_xlabel('Hours')                                 

plt.tight_layout(pad=0.2, w_pad=0.2, h_pad=0.2)
plt.show()


