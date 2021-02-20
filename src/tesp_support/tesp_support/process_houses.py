# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: process_houses.py; focus on HVAC
"""Functions to plot house data from GridLAB-D

Public Functions:
    :process_houses: Reads the data and metadata, then makes the plot.  

"""
import json;
import sys;
import numpy as np;
try:
  import matplotlib as mpl;
  import matplotlib.pyplot as plt;
except:
  pass

def plot_houses (dict, save_file, save_only):
  hrs = dict['hrs']
  data_h = dict['data_h']
  idx_h = dict['idx_h']
  keys_h = dict['keys_h']

  # display a plot
  fig, ax = plt.subplots(2, 1, sharex = 'col')
  i = 0
  for key in keys_h:
    ax[0].plot(hrs, data_h[i,:,idx_h['HSE_AIR_AVG_IDX']], color='blue')
    ax[1].plot(hrs, data_h[i,:,idx_h['HSE_HVAC_AVG_IDX']], color='red')
    i = i + 1
  ax[0].set_ylabel('Degrees')
  ax[1].set_ylabel('kW')
  ax[1].set_xlabel('Hours')
  ax[0].set_title ('HVAC at all Houses')

  if save_file is not None:
    plt.savefig(save_file)
  if not save_only:
    plt.show()

def read_house_metrics (nameroot, dictname = ''):
  # first, read and print a dictionary of all the monitored GridLAB-D objects
  if len (dictname) > 0:
      lp = open (dictname).read()
  else:
      lp = open (nameroot + "_glm_dict.json").read()
  dict = json.loads(lp)
  hse_keys = list(dict['houses'].keys())
  hse_keys.sort()
# print("\nHouse Dictionary:")
# for key in hse_keys:
#   row = dict['houses'][key]
# # print (key, "on", row['billingmeter_id'], "has", row['sqft'], "sqft", row['cooling'], "cooling", row['heating'], "heating", row['wh_gallons'], "gal WH")
#   # row['feeder_id'] is also available

  # Houses 
  lp_h = open ("house_" + nameroot + "_metrics.json").read()
  lst_h = json.loads(lp_h)
  lst_h.pop('StartTime')
  meta_h = lst_h.pop('Metadata')
  times = list(map(int,list(lst_h.keys())))
  times.sort()
  print ("There are", len (times), "sample times at", times[1] - times[0], "second intervals")
  hrs = np.array(times, dtype=np.float)
  denom = 3600.0
  hrs /= denom

#  print("\nHouse Metadata for", len(lst_h[time_key]), "objects")
  data_h = None
  idx_h = {}
  for key, val in meta_h.items():
  # print (key, val['index'], val['units'])
    if key == 'air_temperature_avg':
      idx_h['HSE_AIR_AVG_IDX'] = val['index']
    elif key == 'air_temperature_min':
      idx_h['HSE_AIR_MIN_IDX'] = val['index']
    elif key == 'air_temperature_max':
      idx_h['HSE_AIR_MAX_IDX'] = val['index']
    elif key == 'hvac_load_avg':
      idx_h['HSE_HVAC_AVG_IDX'] = val['index']
    elif key == 'hvac_load_min':
      idx_h['HSE_HVAC_MIN_IDX'] = val['index']
    elif key == 'hvac_load_max':
      idx_h['HSE_HVAC_MAX_IDX'] = val['index']
    elif key == 'waterheater_load_avg':
      idx_h['HSE_WH_AVG_IDX'] = val['index']
    elif key == 'waterheater_load_min':
      idx_h['HSE_WH_MIN_IDX'] = val['index']
    elif key == 'waterheater_load_max':
      idx_h['HSE_WH_MAX_IDX'] = val['index']
    elif key == 'total_load_avg':
      idx_h['HSE_TOTAL_AVG_IDX'] = val['index']
    elif key == 'total_load_min':
      idx_h['HSE_TOTAL_MIN_IDX'] = val['index']
    elif key == 'total_load_max':
      idx_h['HSE_TOTAL_MAX_IDX'] = val['index']
    elif key == 'air_temperature_setpoint_cooling':
      idx_h['HSE_SET_COOL_IDX'] = val['index']
    elif key == 'air_temperature_setpoint_heating':
      idx_h['HSE_SET_HEAT_IDX'] = val['index']

  time_key = str(times[0])
  data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h[time_key][hse_keys[0]])), dtype=np.float)
  print ("\nConstructed", data_h.shape, "NumPy array for Houses")
  j = 0
  for key in hse_keys:
    i = 0
    for t in times:
      ary = lst_h[str(t)][hse_keys[j]]
      data_h[j, i,:] = ary
      i = i + 1
    j = j + 1

  dict = {}
  dict['hrs'] = hrs
  dict['data_h'] = data_h
  dict['keys_h'] = hse_keys
  dict['idx_h'] = idx_h

  return dict

def process_houses(nameroot, dictname = '', save_file=None, save_only=True):
  """ Plots the temperature and HVAC power for every house

  This function reads *substation_nameroot_metrics.json* and
  *house_nameroot_metrics.json* for the data;
  it reads *nameroot_glm_dict.json* for the metadata.
  These must all exist in the current working directory.  
  Makes one graph with 2 subplots:
  
  1. Average air temperature at every house
  2. Average HVAC power at every house  

  Args:
    nameroot (str): name of the TESP case, not necessarily the same as the GLM case, without the extension
    dictname (str): metafile name (with json extension) for a different GLM dictionary, if it's not *nameroot_glm_dict.json*. Defaults to empty.
    save_file (str): name of a file to save plot, should include the *png* or *pdf* extension to determine type.
    save_only (Boolean): set True with *save_file* to skip the display of the plot. Otherwise, script waits for user keypress.
  """
  dict = read_house_metrics (nameroot, dictname)
  plot_houses (dict, save_file, save_only)

