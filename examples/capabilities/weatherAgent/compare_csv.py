# Copyright (C) 2021 Battelle Memorial Institute
# file: compare_csv.py

import csv;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def add_plot (x, y, ax, i, j, key, col, lbl):
  ax[i,j].set_title (key + ':' + lbl)
  ax[i,j].plot(x, y[key+'_tmy3'][:,col], color='red', label='TMY3')
  ax[i,j].plot(x, y[key+'_agent'][:,col], color='blue', label='Agent')
  ax[i,j].grid()
  ax[i,j].legend()

data = {}

ccols = ['timestamp', 
         'temperature',
         'humidity',
         'solar_direct',
         'solar_diffuse',
         'pressure',
         'wind_speed',
         'solar_azimuth',
         'solar_elevation',
         'solar_zenith']
gcols = ['timestamp', 
         'Insolation',
         'wind_speed',
         'Tmodule',
         'Tambient',
         'NOCT']
hcols = ['timestamp', 
         'solar_gain',
         'incident_solar',
         'diffuse_solar',
         'outdoor_temp',
         'outdoor_rh']

for froot in ['climate', 'house', 'generator']:
  fkey = froot + '_tmy3'
  fname = fkey + '.csv'
  data[fkey] = np.genfromtxt(fname, skip_header=8, delimiter=',')

  fkey = froot + '_agent'
  fname = fkey + '.csv'
  data[fkey] = np.genfromtxt(fname, skip_header=8, delimiter=',')

length = data['climate_tmy3'].shape[0]
hmin = 0.0
hmax = (length-1) / 12.0

hrs = np.linspace(0, hmax, length)

fig, ax = plt.subplots(3, 6, sharex = 'col', figsize=(15,9)) #, constrained_layout=True)
for j in range(6):
  add_plot (hrs, data, ax, 0, j, 'climate', j+1, ccols[j+1])
for j in range(5):
  add_plot (hrs, data, ax, 1, j, 'house', j+1, hcols[j+1])
for j in range(4):
  add_plot (hrs, data, ax, 2, j, 'generator', j+1, gcols[j+1])
add_plot (hrs, data, ax, 1, 5, 'climate', 7, ccols[7])
add_plot (hrs, data, ax, 2, 4, 'climate', 8, ccols[8])
add_plot (hrs, data, ax, 2, 5, 'climate', 9, ccols[9])
for j in range(6):
  ax[2,j].set_xlabel ('Hours')
plt.show()


