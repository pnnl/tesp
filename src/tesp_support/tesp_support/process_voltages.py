# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: process_voltages.py
"""Functions to plot all billing meter voltages from GridLAB-D

Public Functions:
    :process_voltages: Reads the data and metadata, then makes the plot.  

"""
import json;
import sys;
import numpy as np;
try:
  import matplotlib as mpl;
  import matplotlib.pyplot as plt;
except:
  pass

def process_voltages(nameroot, dictname = ''):
  """ Plots the min and max line-neutral voltages for every billing meter

  This function reads *substation_nameroot_metrics.json* and 
  *billing_meter_nameroot_metrics.json* for the voltage data, and 
  *nameroot_glm_dict.json* for the meter names.  
  These must all exist in the current working directory.
  One graph is generated with 2 subplots:
  
  1. The Min line-to-neutral voltage at each billing meter  
  2. The Max line-to-neutral voltage at each billing meter  

  Args:
    nameroot (str): name of the TESP case, not necessarily the same as the GLM case, without the extension
    dictname (str): metafile name (with json extension) for a different GLM dictionary, if it's not *nameroot_glm_dict.json*. Defaults to empty.
  """
  # first, read and print a dictionary of all the monitored GridLAB-D objects
  if len (dictname) > 0:
      lp = open (dictname).read()
  else:
      lp = open (nameroot + "_glm_dict.json").read()
  dict = json.loads(lp)
  mtr_keys = list(dict['billingmeters'].keys())
  mtr_keys.sort()
# print("\nBilling Meter Dictionary:")
# for key in mtr_keys:
#   row = dict['billingmeters'][key]
# # print (key, "on phase", row['phases'], "of", row['feeder_id'], "with", row['children'])

  # make a sorted list of the sample times in hours
  lp_m = open ("billing_meter_" + nameroot + "_metrics.json").read()
  lst_m = json.loads(lp_m)
  lst_m.pop('StartTime')
  meta_m = lst_m.pop('Metadata')
  times = list(map(int,list(lst_m.keys())))
  times.sort()
  print ("There are", len (times), "sample times at", times[1] - times[0], "second intervals")
  hrs = np.array(times, dtype=np.float)
  denom = 3600.0
  hrs /= denom

  #print("\nBilling Meter Metadata for", len(lst_m['3600']), "objects")
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

  time_key = str(times[0])
  data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m[time_key][mtr_keys[0]])), dtype=np.float)
  print ("\nConstructed", data_m.shape, "NumPy array for Meters")
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

  # display a plot
  fig, ax = plt.subplots(2, 1, sharex = 'col')
  i = 0
  for key in mtr_keys:
    ax[0].plot(hrs, data_m[i,:,MTR_VOLT_MIN_IDX], color="blue")
    ax[1].plot(hrs, data_m[i,:,MTR_VOLT_MAX_IDX], color="red")
    i = i + 1
  ax[0].set_ylabel("Min Voltage [%]")
  ax[1].set_ylabel("Max Voltage [%]")
  ax[1].set_xlabel("Hours")
  ax[0].set_title ("Voltage at all Meters")

  plt.show()


