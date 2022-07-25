#   Copyright (C) 2020-2022 Battelle Memorial Institute
import csv
import sys
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

# OPF: seconds, OPFconverged, TotalLoad, Production, SwingGen, ClearedResp, LMP1, LMP2, LMP3, LMP4, LMP5, LMP6, LMP7, LMP8, gas1, coal1, nuc1, gas2, coal2, nuc2, gas3, coal3, gas4, gas5, coal4, gas6, coal5, wind1, wind2, wind3, wind4, wind5, TotalWindGen
# PF: seconds, PFConverged, TotalLoad, TotalGen, TotalLoss, SwingGen, v1, v2, v3, v4, v5, v6, v7, v8, gas1, coal1, nuc1, gas2, coal2, nuc2, gas3, coal3, gas4, gas5, coal4, gas6, coal5, wind1, wind2, wind3, wind4, wind5, TotalWindGen

colset = [0,14,15,16,17,18,19,20,21,22,23,24,25,26]
dpf = np.loadtxt('ercot_8_pf.csv', skiprows=1, delimiter=',', usecols=colset)
hpf = dpf[:,0] / 3600.0
dopf = np.loadtxt('ercot_8_opf.csv', skiprows=1, delimiter=',', usecols=colset)
hopf = dopf[:,0] / 3600.0

plots = [{'idx':14, 'row':0, 'col':0, 'lbl':'Gas, Bus 1'},
         {'idx':15, 'row':0, 'col':1, 'lbl':'Coal, Bus 1'},
         {'idx':16, 'row':0, 'col':2, 'lbl':'Nuclear, Bus 1'},
         {'idx':17, 'row':0, 'col':3, 'lbl':'Gas, Bus 2'},
         {'idx':18, 'row':0, 'col':4, 'lbl':'Coal, Bus 2'},
         {'idx':19, 'row':1, 'col':0, 'lbl':'Nuclear, Bus 2'},
         {'idx':20, 'row':1, 'col':1, 'lbl':'Gas, Bus 3'},
         {'idx':21, 'row':1, 'col':2, 'lbl':'Coal, Bus 3'},
         {'idx':22, 'row':1, 'col':3, 'lbl':'Gas, Bus 4'},
         {'idx':23, 'row':1, 'col':4, 'lbl':'Gas, Bus 5'},
         {'idx':24, 'row':2, 'col':0, 'lbl':'Coal, Bus 5'},
         {'idx':25, 'row':2, 'col':1, 'lbl':'Gas, Bus 7'},
         {'idx':26, 'row':2, 'col':2, 'lbl':'Coal, Bus 7'}]

fig, ax = plt.subplots (3, 5, sharex = 'col')
fig.suptitle ('Comparing Generator Outputs from Optimal and Regular Power Flow')
for plot in plots:
  row = plot['row']
  col = plot['col']
  idx = plot['idx'] - 13
  ax[row,col].plot (hpf, dpf[:,idx], color='red', label='PF')
  ax[row,col].plot (hopf, dopf[:,idx], color='blue', label='OPF')
  ax[row,col].set_title (plot['lbl'])
  ax[row,col].legend(loc='best')
#  ax[row,col].set_ylabel ('MW')
#  ax[row,col].set_xlabel ('Hours')
  ax[row,col].grid()

plt.show()


