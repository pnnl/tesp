# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: process_gld.py
'''Functions to plot data from GridLAB-D

Public Functions:
    :process_gld: Reads the data and metadata, then makes the plots.  

'''
import json;
import sys;
import numpy as np;
try:
  import matplotlib as mpl;
  import matplotlib.pyplot as plt;
except:
  pass

def process_gld(nameroot, dictname = ''):
  ''' Plots a summary/sample of power, air temperature and voltage

  This function reads *substation_nameroot_metrics.json*,  
  *billing_meter_nameroot_metrics.json* and
  *house_nameroot_metrics.json* for the data;
  it reads *nameroot_glm_dict.json* for the metadata.  
  These must all exist in the current working directory.  
  Makes one graph with 4 subplots:
  
  1. Substation real power and losses
  2. Average air temperature over all houses
  3. Min/Max line-to-neutral voltage and Min/Max line-to-line voltage at the first billing meter
  4. Min, Max and Average air temperature at the first house 

  Args:
    nameroot (str): name of the TESP case, not necessarily the same as the GLM case, without the extension
    dictname (str): metafile name (with json extension) for a different GLM dictionary, if it's not *nameroot_glm_dict.json*. Defaults to empty.
  '''

  # the feederGenerator now inserts metrics_collector objects on capacitors and regulators
  bCollectedRegCapMetrics = True 

  # first, read and print a dictionary of all the monitored GridLAB-D objects
  if len (dictname) > 0:
      lp = open (dictname).read()
  else:
      lp = open (nameroot + '_glm_dict.json').read()
  dict = json.loads(lp)
  fdr_keys = list(dict['feeders'].keys())
  fdr_keys.sort()
  inv_keys = list(dict['inverters'].keys())
  inv_keys.sort()
  hse_keys = list(dict['houses'].keys())
  hse_keys.sort()
  mtr_keys = list(dict['billingmeters'].keys())
  mtr_keys.sort()
  cap_keys = list(dict['capacitors'].keys())
  cap_keys.sort()
  reg_keys = list(dict['regulators'].keys())
  reg_keys.sort()
  #print ('Capacitor Keys', cap_keys)
  #print ('Regulator Keys', reg_keys)
  xfMVA = dict['transformer_MVA']
  bulkBus = dict['bulkpower_bus']
#  print('\nBilling Meter Dictionary:')
#  for key in mtr_keys:
#    row = dict['billingmeters'][key]
#    print (key, 'on phase', row['phases'], 'of', row['feeder_id'], 'with', row['children'])
#  print('\nHouse Dictionary:')
#  for key in hse_keys:
#    row = dict['houses'][key]
#    print (key, 'on', row['billingmeter_id'], 'has', row['sqft'], 'sqft', row['cooling'], 'cooling', row['heating'], 'heating', row['wh_gallons'], 'gal WH')
#  print('\nInverter Dictionary:')
#  for key in inv_keys:
#    row = dict['inverters'][key]
#    print (key, 'on', row['billingmeter_id'], 'has', row['rated_W'], 'W', row['resource'], 'resource')

  # parse the substation metrics file first; there should just be one entity per time sample
  # each metrics file should have matching time points
  lp_s = open ('substation_' + nameroot + '_metrics.json').read()
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

  time_key = str(times[0])

  # find the actual substation name (not a feeder name) as GridLAB-D wrote it to the metrics file
  sub_key = list(lst_s[time_key].keys())[0]
  print ('\n\nFile', nameroot, 'has substation', sub_key, 'at bulk system bus', bulkBus, 'with', xfMVA, 'MVA transformer')
  print('\nFeeder Dictionary:')
  for key in fdr_keys:
    row = dict['feeders'][key]
    print (key, 'has', row['house_count'], 'houses and', row['inverter_count'], 'inverters')

  # parse the substation metadata for 2 things of specific interest
#  print ('\nSubstation Metadata for', len(lst_s[time_key]), 'objects')
  for key, val in meta_s.items():
#    print (key, val['index'], val['units'])
    if key == 'real_power_avg':
      SUB_POWER_IDX = val['index']
      SUB_POWER_UNITS = val['units']
    elif key == 'real_power_losses_avg':
      SUB_LOSSES_IDX = val['index']
      SUB_LOSSES_UNITS = val['units']

  # create a NumPy array of all metrics for the substation
  data_s = np.empty(shape=(1, len(times), len(lst_s[time_key][sub_key])), dtype=np.float)
  print ('\nConstructed', data_s.shape, 'NumPy array for Substations')
  j = 0
  for key in [sub_key]:
    i = 0
    for t in times:
      ary = lst_s[str(t)][key]
      data_s[j, i,:] = ary
      i = i + 1
    j = j + 1

  # display some averages
  print ('Maximum power =', 
         '{:.3f}'.format (data_s[0,:,SUB_POWER_IDX].max()), SUB_POWER_UNITS)
  print ('Average power =', 
         '{:.3f}'.format (data_s[0,:,SUB_POWER_IDX].mean()), SUB_POWER_UNITS)
  print ('Average losses =', 
         '{:.3f}'.format (data_s[0,:,SUB_LOSSES_IDX].mean()), SUB_LOSSES_UNITS)

  # read the other JSON files; their times (hrs) should be the same
  lp_h = open ('house_' + nameroot + '_metrics.json').read()
  lst_h = json.loads(lp_h)
  lp_m = open ('billing_meter_' + nameroot + '_metrics.json').read()
  lst_m = json.loads(lp_m)
  lp_i = open ('inverter_' + nameroot + '_metrics.json').read()
  lst_i = json.loads(lp_i)

  # houses
  lst_h.pop('StartTime')
  meta_h = lst_h.pop('Metadata')
#  print('\nHouse Metadata for', len(lst_h[time_key]), 'objects')
  for key, val in meta_h.items():
#    print (key, val['index'], val['units'])
    if key == 'air_temperature_max':
      HSE_AIR_MAX_IDX = val['index']
      HSE_AIR_MAX_UNITS = val['units']
    elif key == 'air_temperature_min':
      HSE_AIR_MIN_IDX = val['index']
      HSE_AIR_MIN_UNITS = val['units']
    elif key == 'air_temperature_avg':
      HSE_AIR_AVG_IDX = val['index']
      HSE_AIR_AVG_UNITS = val['units']
    elif key == 'air_temperature_deviation_cooling':
      HSE_AIR_DEVC_IDX = val['index']
      HSE_AIR_DEVC_UNITS = val['units']
    elif key == 'air_temperature_deviation_heating':
      HSE_AIR_DEVH_IDX = val['index']
      HSE_AIR_DEVH_UNITS = val['units']
    elif key == 'total_load_avg':
      HSE_TOTAL_AVG_IDX = val['index']
      HSE_TOTAL_AVG_UNITS = val['units']
    elif key == 'hvac_load_avg':
      HSE_HVAC_AVG_IDX = val['index']
      HSE_HVAC_AVG_UNITS = val['units']
    elif key == 'waterheater_load_avg':
      HSE_WH_AVG_IDX = val['index']
      HSE_WH_AVG_UNITS = val['units']
  if len(hse_keys) > 0:
    data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h[time_key][hse_keys[0]])), dtype=np.float)
    print ('\nConstructed', data_h.shape, 'NumPy array for Houses')
    j = 0
    for key in hse_keys:
      i = 0
      for t in times:
        ary = lst_h[str(t)][hse_keys[j]]
        data_h[j, i,:] = ary
        i = i + 1
      j = j + 1

    print ('average all house temperatures Noon-8 pm first day:',
         '{:.3f}'.format (data_h[:,144:240,HSE_AIR_AVG_IDX].mean()))

  # Billing Meters 
  lst_m.pop('StartTime')
  meta_m = lst_m.pop('Metadata')
  nBillingMeters = 0
  if not lst_m[time_key] is None:
    nBillingMeters = len(lst_m[time_key])
#  print('\nBilling Meter Metadata for', nBillingMeters, 'objects')
  for key, val in meta_m.items():
#    print (key, val['index'], val['units'])
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

  if nBillingMeters > 0:
    data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m[time_key][mtr_keys[0]])), dtype=np.float)
    print ('\nConstructed', data_m.shape, 'NumPy array for Meters')
    j = 0
    for key in mtr_keys:
      i = 0
      for t in times:
        ary = lst_m[str(t)][mtr_keys[j]]
        data_m[j, i,:] = ary
        i = i + 1
      j = j + 1

  # normalize the meter voltages to 100 percent
  j = 0
  for key in mtr_keys:
    vln = dict['billingmeters'][key]['vln'] / 100.0
    vll = dict['billingmeters'][key]['vll'] / 100.0
    data_m[j,:,MTR_VOLT_MIN_IDX] /= vln
    data_m[j,:,MTR_VOLT_MAX_IDX] /= vln
    data_m[j,:,MTR_VOLT_AVG_IDX] /= vln
    data_m[j,:,MTR_VOLT12_MIN_IDX] /= vll
    data_m[j,:,MTR_VOLT12_MAX_IDX] /= vll
    j = j + 1

  lst_i.pop('StartTime')
  meta_i = lst_i.pop('Metadata')
  # assemble the total solar and battery inverter power
  solar_kw = np.zeros(len(times), dtype=np.float)
  battery_kw = np.zeros(len(times), dtype=np.float)
#  print ('\nInverter Metadata for', len(inv_keys), 'objects')
  for key, val in meta_i.items():
#    print (key, val['index'], val['units'])
    if key == 'real_power_avg':
      INV_P_AVG_IDX = val['index']
      INV_P_AVG_UNITS = val['units']
    elif key == 'reactive_power_avg':
      INV_Q_AVG_IDX = val['index']
      INV_Q_AVG_UNITS = val['units']
  if len(inv_keys) > 0:
    data_i = np.empty(shape=(len(inv_keys), len(times), len(lst_i[time_key][inv_keys[0]])), dtype=np.float)
    print ('\nConstructed', data_i.shape, 'NumPy array for Inverters')
    j = 0
    for key in inv_keys:
      i = 0
      for t in times:
        ary = lst_i[str(t)][inv_keys[j]]
        data_i[j, i,:] = ary
        i = i + 1
      j = j + 1
    j = 0
    for key in inv_keys:
      res = dict['inverters'][key]['resource']
      if res == 'solar':
        solar_kw += 0.001 * data_i[j,:,INV_P_AVG_IDX]
      elif res == 'battery':
        battery_kw += 0.001 * data_i[j,:,INV_P_AVG_IDX]
      j = j + 1

  # capacitors and regulators
  lp_c = open ('capacitor_' + nameroot + '_metrics.json').read()
  lst_c = json.loads(lp_c)
  lp_r = open ('regulator_' + nameroot + '_metrics.json').read()
  lst_r = json.loads(lp_r)

  lst_c.pop('StartTime')
  meta_c = lst_c.pop('Metadata')
#  print('\nCapacitor Metadata for', len(cap_keys), 'objects')
  for key, val in meta_c.items():
    if key == 'operation_count':
      CAP_COUNT_IDX = val['index']
      CAP_COUNT_UNITS = val['units']
  if len(cap_keys) > 0 and bCollectedRegCapMetrics:
    data_c = np.empty(shape=(len(cap_keys), len(times), len(lst_c[time_key][cap_keys[0]])), dtype=np.float)
    print ('\nConstructed', data_c.shape, 'NumPy array for Capacitors')
    j = 0
    for key in cap_keys:
      i = 0
      for t in times:
        ary = lst_c[str(t)][cap_keys[j]]
        data_c[j, i,:] = ary
        i = i + 1
      j = j + 1
    print ('Total cap switchings =', data_c[:,-1,CAP_COUNT_IDX].sum())

  lst_r.pop('StartTime')
  meta_r = lst_r.pop('Metadata')
#  print('\nRegulator Metadata for', len(reg_keys), 'objects')
  for key, val in meta_r.items():
    if key == 'operation_count':
      REG_COUNT_IDX = val['index']
      REG_COUNT_UNITS = val['units']
  if len(reg_keys) > 0 and bCollectedRegCapMetrics:
    data_r = np.empty(shape=(len(reg_keys), len(times), len(lst_r[time_key][reg_keys[0]])), dtype=np.float)
    print ('\nConstructed', data_r.shape, 'NumPy array for Regulators')
    j = 0
    for key in reg_keys:
      i = 0
      for t in times:
        ary = lst_r[str(t)][reg_keys[j]]
        data_r[j, i,:] = ary
        i = i + 1
      j = j + 1
    print ('Total tap changes =', data_r[:,-1,REG_COUNT_IDX].sum())

  print ('Total meter bill =', 
         '{:.3f}'.format (data_m[:,-1,MTR_BILL_IDX].sum()))

  # display a plot
  fig, ax = plt.subplots(2, 5, sharex = 'col')

  if len(hse_keys) > 0:
    total1 = (data_h[:,:,HSE_TOTAL_AVG_IDX]).squeeze()
    total2 = total1.sum(axis=0)
    hvac1 = (data_h[:,:,HSE_HVAC_AVG_IDX]).squeeze()
    hvac2 = hvac1.sum(axis=0)
    wh1 = (data_h[:,:,HSE_WH_AVG_IDX]).squeeze()
    wh2 = wh1.sum(axis=0)
  ax[0,0].plot(hrs, 0.001 * data_s[0,:,SUB_POWER_IDX], color='blue', label='Total')
  ax[0,0].plot(hrs, 0.001 * data_s[0,:,SUB_LOSSES_IDX], color='red', label='Losses')
  if len(hse_keys) > 0:
    ax[0,0].plot(hrs, total2, color='green', label='Houses')
    ax[0,0].plot(hrs, hvac2, color='magenta', label='HVAC')
    ax[0,0].plot(hrs, wh2, color='orange', label='WH')
  ax[0,0].set_ylabel('kW')
  ax[0,0].set_title ('Substation Real Power at ' + sub_key)
  ax[0,0].legend(loc='best')

  #vabase = dict['inverters'][inv_keys[0]]['rated_W']
  #print ('Inverter base power =', vabase)
  #ax[0,1].plot(hrs, data_i[0,:,INV_P_AVG_IDX] / vabase, color='blue', label='Real')
  #ax[0,1].plot(hrs, data_i[0,:,INV_Q_AVG_IDX] / vabase, color='red', label='Reactive')
  #ax[0,1].set_ylabel('perunit')
  #ax[0,1].set_title ('Inverter Power at ' + inv_keys[0])
  #ax[0,1].legend(loc='best')

  #ax[0,1].plot(hrs, data_m[0,:,MTR_VOLTUNB_MAX_IDX], color='red', label='Max')
  #ax[0,1].set_ylabel('perunit')
  #ax[0,1].set_title ('Voltage Unbalance at ' + mtr_keys[0])

  if len(hse_keys) > 0:
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
  else:
    ax[0,1].set_title ('No Houses')

  if nBillingMeters > 0:
    vavg = (data_m[:,:,MTR_VOLT_AVG_IDX]).squeeze().mean(axis=0)
    vmin = (data_m[:,:,MTR_VOLT_MIN_IDX]).squeeze().min(axis=0)
    vmax = (data_m[:,:,MTR_VOLT_MAX_IDX]).squeeze().max(axis=0)
    ax[1,0].plot(hrs, vmax, color='blue', label='Max')
    ax[1,0].plot(hrs, vmin, color='red', label='Min')
    ax[1,0].plot(hrs, vavg, color='green', label='Avg')
    ax[1,0].set_xlabel('Hours')
    ax[1,0].set_ylabel('%')
    ax[1,0].set_title ('Voltage over all Meters')
    ax[1,0].legend(loc='best')
  else:
    ax[1,0].set_title ('No Billing Meter Voltages')

  if len(hse_keys) > 0:
    ax[1,1].plot(hrs, data_h[0,:,HSE_AIR_AVG_IDX], color='blue', label='Mean')
    ax[1,1].plot(hrs, data_h[0,:,HSE_AIR_MIN_IDX], color='red', label='Min')
    ax[1,1].plot(hrs, data_h[0,:,HSE_AIR_MAX_IDX], color='green', label='Max')
    ax[1,1].plot(hrs, data_h[0,:,HSE_AIR_DEVC_IDX], color='magenta', label='DevC')
    ax[1,1].plot(hrs, data_h[0,:,HSE_AIR_DEVH_IDX], color='orange', label='DevH')
    ax[1,1].set_xlabel('Hours')
    ax[1,1].set_ylabel(HSE_AIR_AVG_UNITS)
    ax[1,1].set_title ('House Air at ' + hse_keys[0])
    ax[1,1].legend(loc='best')
  else:
    ax[1,1].set_title ('No Houses')

  ax[0,2].plot(hrs, solar_kw, color='blue', label='Solar')
  ax[0,2].plot(hrs, battery_kw, color='red', label='Battery')
  ax[0,2].set_xlabel('Hours')
  ax[0,2].set_ylabel('kW')
  ax[0,2].set_title ('Total Inverter Power')
  ax[0,2].legend(loc='best')

  ax[1,2].plot(hrs, data_m[:,:,MTR_BILL_IDX].sum(axis=0), color='blue')
  ax[1,2].set_xlabel('Hours')
  ax[1,2].set_ylabel(MTR_BILL_UNITS)
  ax[1,2].set_title ('Total Meter Bill')

  if len(cap_keys) > 0 and bCollectedRegCapMetrics:
    ax[0,3].plot(hrs, data_c[:,:,CAP_COUNT_IDX].sum(axis=0), color='blue', label='Total')
    ax[0,3].set_ylabel('')
    ax[0,3].set_title ('Capacitor Switchings')
    ax[0,3].legend(loc='best')
  else:
    ax[0,3].set_title ('No Capacitors')

  if len(reg_keys) > 0 and bCollectedRegCapMetrics:
    ax[1,3].plot(hrs, data_r[:,:,REG_COUNT_IDX].sum(axis=0), color='blue', label='Total')
#   ax[1,3].plot(hrs, data_r[0,:,REG_COUNT_IDX], color='blue', label=reg_keys[0])
#   ax[1,3].plot(hrs, data_r[1,:,REG_COUNT_IDX], color='red', label=reg_keys[1])
#   ax[1,3].plot(hrs, data_r[2,:,REG_COUNT_IDX], color='green', label=reg_keys[2])
#   ax[1,3].plot(hrs, data_r[3,:,REG_COUNT_IDX], color='magenta', label=reg_keys[3])
    ax[1,3].set_xlabel('Hours')
    ax[1,3].set_ylabel('')
    ax[1,3].set_title ('Regulator Tap Changes')
    ax[1,3].legend(loc='best')
  else:
    ax[1,3].set_title ('No Regulators')

  ax[0,4].plot(hrs, (data_m[:,:,MTR_AHI_COUNT_IDX]).squeeze().sum(axis=0), color='blue', label='Range A Hi')
  ax[0,4].plot(hrs, (data_m[:,:,MTR_BHI_COUNT_IDX]).squeeze().sum(axis=0), color='cyan', label='Range B Hi')
  ax[0,4].plot(hrs, (data_m[:,:,MTR_ALO_COUNT_IDX]).squeeze().sum(axis=0), color='green', label='Range A Lo')
  ax[0,4].plot(hrs, (data_m[:,:,MTR_BLO_COUNT_IDX]).squeeze().sum(axis=0), color='magenta', label='Range B Lo')
  ax[0,4].plot(hrs, (data_m[:,:,MTR_OUT_COUNT_IDX]).squeeze().sum(axis=0), color='red', label='No Voltage')
  ax[0,4].set_ylabel('')
  ax[0,4].set_title ('Voltage Violation Counts')
  ax[0,4].legend(loc='best')

  ax[1,4].plot(hrs, (data_m[:,:,MTR_AHI_DURATION_IDX]).squeeze().sum(axis=0), color='blue', label='Range A Hi')
  ax[1,4].plot(hrs, (data_m[:,:,MTR_BHI_DURATION_IDX]).squeeze().sum(axis=0), color='cyan', label='Range B Hi')
  ax[1,4].plot(hrs, (data_m[:,:,MTR_ALO_DURATION_IDX]).squeeze().sum(axis=0), color='green', label='Range A Lo')
  ax[1,4].plot(hrs, (data_m[:,:,MTR_BLO_DURATION_IDX]).squeeze().sum(axis=0), color='magenta', label='Range B Lo')
  ax[1,4].plot(hrs, (data_m[:,:,MTR_OUT_DURATION_IDX]).squeeze().sum(axis=0), color='red', label='No Voltage')
  ax[1,3].set_xlabel('Hours')
  ax[1,4].set_ylabel('Seconds')
  ax[1,4].set_title ('Voltage Violation Durations')
  ax[1,4].legend(loc='best')

  plt.show()


