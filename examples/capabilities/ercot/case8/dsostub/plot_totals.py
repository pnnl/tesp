#   Copyright (C) 2017-2022 Battelle Memorial Institute
import json
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt


def process_pypower(nameroot):
  # first, read and print a dictionary of relevant PYPOWER objects
  lp = open (nameroot + '_m_dict.json').read()
  dict = json.loads(lp)
  baseMVA = dict['baseMVA']
  gen_keys = list(dict['generators'].keys())
  gen_keys.sort(key=int)
  bus_keys = list(dict['dsoBuses'].keys())
  bus_keys.sort(key=int)
  print ('\n\nFile', nameroot, 'has baseMVA', baseMVA)
  print('\nGenerator Dictionary:')
  print('Unit Bus Type   Fuel     Pmin   Pmax StartCst  StopCst     C2     C1     C0')
  for key in gen_keys:
    row = dict['generators'][key]
    print ('{:2d}   {:2d}  {:6s} {:8s} {:8.2f} {:8.2f} {:8.4f} {:8.4f} {:8.4f} {:8.4f} {:8.4f}'.format (int(key), 
        int(row['bus']), row['bustype'], row['genfuel'], float(row['Pmin']), float(row['Pmax']), 
        float(row['StartupCost']), float(row['ShutdownCost']), float(row['c2']), 
        float(row['c1']), float(row['c0'])))
  print('\nFNCS Bus Dictionary:')
  print('Bus  Pnom   Qnom  Scale  Substation')
  for key in bus_keys:
    row = dict['dsoBuses'][key]
    print ('{:2d} {:8.2f} {:8.2f} {:8.2f}  {:s}'.format (int(key), float(row['Pnom']), 
      float(row['Qnom']), float(row['ampFactor']), row['GLDsubstations'][0]))  #TODO curveScale, curveSkew

  # read the bus metrics file
  lp_b = open ('bus_' + nameroot + '_metrics.json').read()
  lst_b = json.loads(lp_b)
  print ('\nBus Metrics data starting', lst_b['StartTime'])

  # make a sorted list of the times, and NumPy array of times in hours
  lst_b.pop('StartTime')
  meta_b = lst_b.pop('Metadata')
  times = list(map(int,list(lst_b.keys())))
  times.sort()
  print ('There are', len (times), 'sample times at', times[1] - times[0], 'second intervals')
  hrs = np.array(times, dtype=np.float)
  denom = 3600.0
  hrs /= denom

  # parse the metadata for things of specific interest
  for key, val in meta_b.items():
    if key == 'LMP_P':
      LMP_P_IDX = val['index']
      LMP_P_UNITS = val['units']
    elif key == 'LMP_Q':
      LMP_Q_IDX = val['index']
      LMP_Q_UNITS = val['units']
    elif key == 'PD':
      PD_IDX = val['index']
      PD_UNITS = val['units']
    elif key == 'QD':
      QD_IDX = val['index']
      QD_UNITS = val['units']
    elif key == 'Vang':
      VANG_IDX = val['index']
      VANG_UNITS = val['units']
    elif key == 'Vmag':
      VMAG_IDX = val['index']
      VMAG_UNITS = val['units']
    elif key == 'Vmax':
      VMAX_IDX = val['index']
      VMAX_UNITS = val['units']
    elif key == 'Vmin':
      VMIN_IDX = val['index']
      VMIN_UNITS = val['units']
    elif key == 'unresp':
      UNRESP_IDX = val['index']
      UNRESP_UNITS = val['units']
    elif key == 'resp_max':
      RESP_MAX_IDX = val['index']
      RESP_MAX_UNITS = val['units']
    elif key == 'c1':
      C1_IDX = val['index']
      C1_UNITS = val['units']
    elif key == 'c2':
      C2_IDX = val['index']
      C2_UNITS = val['units']

  # create a NumPy array of all bus metrics, display summary information
  data_b = np.empty(shape=(len(bus_keys), len(times), len(lst_b[str(times[0])][bus_keys[0]])), dtype=np.float)
  print ('\nConstructed', data_b.shape, 'NumPy array for Buses')
  print ('#  LMPavg   LMPmax  LMP1avg  LMP1std   Vmin   Vmax   Unresp  RespMax     C1     C2')
  last1 = int (3600 * 24 / (times[1] - times[0]))
  j = 0
  for key in bus_keys:
    i = 0
    for t in times:
      ary = lst_b[str(t)][bus_keys[j]]
      data_b[j, i,:] = ary
      i = i + 1
    print ('{:2d}'.format(int(key)),
         '{:8.4f}'.format (data_b[j,:,LMP_P_IDX].mean()),
         '{:8.4f}'.format (data_b[j,:,LMP_P_IDX].max()),
         '{:8.4f}'.format (data_b[j,0:last1,LMP_P_IDX].mean()), 
         '{:8.4f}'.format (data_b[j,0:last1,LMP_P_IDX].std()),
         '{:8.4f}'.format (data_b[j,:,VMIN_IDX].min()),
         '{:8.4f}'.format (data_b[j,:,VMAX_IDX].max()),
         '{:8.2f}'.format (data_b[j,0:last1,UNRESP_IDX].mean()), 
         '{:8.2f}'.format (data_b[j,0:last1,RESP_MAX_IDX].mean()), 
         '{:8.4f}'.format (data_b[j,0:last1,C1_IDX].mean()), 
         '{:8.4f}'.format (data_b[j,0:last1,C2_IDX].mean())) 
    j = j + 1

  # read the generator metrics file
  lp_g = open ('gen_' + nameroot + '_metrics.json').read()
  lst_g = json.loads(lp_g)
  print ('\nGenerator Metrics data starting', lst_g['StartTime'])
  # make a sorted list of the times, and NumPy array of times in hours
  lst_g.pop('StartTime')
  meta_g = lst_g.pop('Metadata')
  for key, val in meta_g.items():
    if key == 'Pgen':
      PGEN_IDX = val['index']
      PGEN_UNITS = val['units']
    elif key == 'Qgen':
      QGEN_IDX = val['index']
      QGEN_UNITS = val['units']
    elif key == 'LMP_P':
      GENLMP_IDX = val['index']
      GENLMP_UNITS = val['units']

  # create a NumPy array of all generator metrics
  data_g = np.empty(shape=(len(gen_keys), len(times), len(lst_g[str(times[0])][gen_keys[0]])), dtype=np.float)
  print ('\nConstructed', data_g.shape, 'NumPy array for Generators')
  print ('Unit Bus Type   Fuel    Pmax    CF   COV')
  j = 0
  for key in gen_keys:
    i = 0
    for t in times:
      ary = lst_g[str(t)][gen_keys[j]]
      data_g[j, i,:] = ary
      i = i + 1
    p_avg = data_g[j,:,PGEN_IDX].mean()
    p_std = data_g[j,:,PGEN_IDX].std()
    row = dict['generators'][key]
    p_max = float (row['Pmax'])
    CF = p_avg/p_max
    if p_avg > 0.0:
      COV = p_std/p_avg
    else:
      COV = 0.0

    print ('{:4d} {:3d} {:6s} {:8s}'.format (int(key), int(row['bus']), row['bustype'], row['genfuel']),
         '{:7.1f}'.format (p_max), '{:7.4f}'.format (CF), '{:7.4f}'.format (COV))
    j = j + 1

  # read the dso stub metrics, which uses the same bus keys but different hrs
  lp_d = open ('dso_' + nameroot + '_metrics.json').read()
  lst_d = json.loads(lp_d)
  print ('\nDSO bus data starting', lst_d['StartTime'])
  lst_d.pop('StartTime')
  meta_d = lst_d.pop('Metadata')
  dtimes = list(map(int,list(lst_d.keys())))
  dtimes.sort()
  print ('There are', len (dtimes), 'sample times at', dtimes[1] - dtimes[0], 'second intervals')
  dhrs = np.array(dtimes, dtype=np.float)
  denom = 3600.0
  dhrs /= denom

#  print ('\nDSO Bus Metadata [Variable Index Units] for', len(lst_d[str(dtimes[0])]), 'objects')
  for key, val in meta_d.items():
#    print (key, val['index'], val['units'])
    if key == 'Pdso':
      PDSO_IDX = val['index']
      PDSO_UNITS = val['units']
    elif key == 'Qdso':
      QDSO_IDX = val['index']
      QDSO_UNITS = val['units']
    elif key == 'Pcleared':
      PCLEARED_IDX = val['index']
      PCLEARED_UNITS = val['units']
    elif key == 'LMP':
      LMP_IDX = val['index']
      LMP_UNITS = val['units']

  data_d = np.empty(shape=(len(bus_keys), len(dtimes), len(lst_d[str(times[0])][bus_keys[0]])), dtype=np.float)
  print ('\nConstructed', data_d.shape, 'NumPy array for DSO buses')
  j = 0
  for key in bus_keys:
    i = 0
    for t in dtimes:
      ary = lst_d[str(t)][bus_keys[j]]
      data_d[j, i,:] = ary
      i = i + 1
    j = j + 1

  Psteam = np.sum(data_g[0:13,:,PGEN_IDX], axis=0)
  Pwind = np.sum(data_g[13:18,:,PGEN_IDX], axis=0)
  Presp = np.sum(data_d[0:7,:,PCLEARED_IDX], axis=0)
  Punresp = 3.0 * np.sum(data_b[0:7,:,UNRESP_IDX], axis=0)
  Ptotal = Psteam + Pwind
#  Pload = Presp + Punresp

  # display a plot 
  fig, ax = plt.subplots(1, 1, figsize=(15,9), sharex = 'col')
  tmin = 0.0
  tmax = hrs[len(hrs)-1]
  if tmax < 25.0:
    tmax = 24.0 
    xticks = [0,6,12,18,24]
  elif tmax < 49.0:
    tmax = 48.0
    xticks = [0,6,12,18,24,30,36,42,48]
  else:
    tmax = 72.0
    xticks = [0,6,12,18,24,30,36,42,48,54,60,66,72]
  ax.grid (linestyle = '-')
  ax.set_xlim(tmin,tmax)
  ax.set_xticks(xticks)
  ax.set_xlabel('Hours')

  ax.set_title ('Total System Power')
  ax.set_ylabel(PGEN_UNITS)
  ax.plot(hrs, Psteam, label='Steam', color='red')
  ax.plot(hrs, Pwind, label='Wind', color='green')
  ax.plot(dhrs, Presp, label='Responsive Load', color='blue')
  ax.plot(hrs, Punresp, label='Unresponsive Load', color='magenta')
  ax.plot(hrs, Ptotal, label='Total Generation', color='black')
#  ax.plot(hrs, Pload, label='Total Load', color='orange')
  ax.legend(loc='best')

  plt.show()

if __name__ == '__main__':
  process_pypower ('ercot_8')
