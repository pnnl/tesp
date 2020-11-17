# usage 'python3 gplots.py metrics_root'
import sys
import os
import tesp_support.process_gld as gp
import numpy as np
import json
try:
  import matplotlib as mpl;
  import matplotlib.pyplot as plt;
except:
  pass

rootname = sys.argv[1]

dict = gp.read_gld_metrics (rootname)
hrs = dict['hrs']
data_s = dict['data_s']
data_m = dict['data_m']
data_i = dict['data_i']
keys_s = dict['keys_s']
keys_m = dict['keys_m']
keys_i = dict['keys_i']
idx_s = dict['idx_s']
idx_m = dict['idx_m']
idx_i = dict['idx_i']
solar_kw = dict['solar_kw']
battery_kw = dict['battery_kw']

bldg_mtrs = {}
fp = open('BuildingDefinitions.json', 'r').read()
bldg_defs = json.loads(fp)
for key, row in bldg_defs.items():
  mtr = row['Meter']
  bldg_mtrs[mtr.upper()] = {'idx':keys_m.index(mtr), 'name':row['Name']}
print ('Building meters are', bldg_mtrs)

prop_cycle = plt.rcParams['axes.prop_cycle']
colors = prop_cycle.by_key()['color']

fig, ax = plt.subplots(2, 3, sharex = 'col', figsize=(16,8))
fig.suptitle ('GridLAB-D Metrics:' + rootname)

ax[0,0].set_title ('Substation Real Power')
ax[0,0].plot(hrs, 0.001 * data_s[0,:,idx_s['SUB_POWER_IDX']], color='blue', label='Total')
ax[0,0].plot(hrs, 0.001 * data_s[0,:,idx_s['SUB_LOSSES_IDX']], color='red', label='Losses')
ax[0,0].set_ylabel('kW')
ax[0,0].legend(loc='best')

ax[1,0].set_title ('Total Inverter Power')
ax[1,0].plot(hrs, solar_kw, color='blue', label='Solar')
ax[1,0].plot(hrs, battery_kw, color='red', label='Battery')
ax[1,0].set_ylabel('kW')
ax[1,0].legend(loc='best')

ax[0,1].set_title ('Real Power at Building Meters')
i = 0
for key, row in bldg_mtrs.items():
  idx = row['idx']
  lbl = row['name']
  ax[0,1].plot(hrs, 0.001 * data_m[idx,:,idx_m['MTR_REAL_POWER_AVG_IDX']], color=colors[i], label=lbl)
  i = i + 1
ax[0,1].set_ylabel('kW')
ax[0,1].legend(loc='best')

ax[1,1].set_title ('Voltage Range at Building Meters')
i = 0
for key, row in bldg_mtrs.items():
  idx = row['idx']
  lbl = row['name']
  ax[1,1].plot(hrs, data_m[idx,:,idx_m['MTR_VOLT_MIN_IDX']], color=colors[i], label=lbl)
  ax[1,1].plot(hrs, data_m[idx,:,idx_m['MTR_VOLT_MAX_IDX']], color=colors[i])
  i = i + 1
ax[1,1].set_ylabel('Voltage [%]')
ax[1,1].legend(loc='best')

ax[0,2].set_title ('Building Meter Bills')
i = 0
for key, row in bldg_mtrs.items():
  idx = row['idx']
  lbl = row['name']
  ax[0,2].plot(hrs, data_m[idx,:,idx_m['MTR_BILL_IDX']], color=colors[i], label=lbl)
  i = i + 1
ax[0,2].set_ylabel(idx_m['MTR_BILL_UNITS'])
ax[0,2].legend(loc='best')

ax[1,2].set_title ('Total Meter Bill')
ax[1,2].plot(hrs, data_m[:,:,idx_m['MTR_BILL_IDX']].sum(axis=0), color='blue')
ax[1,2].set_ylabel(idx_m['MTR_BILL_UNITS'])

for i in range(3):
  ax[1,i].set_xlabel('Hours')

plt.show()

