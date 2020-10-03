#   Copyright (C) 2020 Battelle Memorial Institute
import csv;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

# CSV: seconds, 8*LMP, 8*CLR, 8*BID, 8*SET

d = np.loadtxt('ercot_8_dso.csv', skiprows=1, delimiter=',')
h = d[:,0] / 3600.0

fig, ax = plt.subplots(2, 4, sharex = 'col')
bus = 1
for row in range(2):
  for col in range(4):
    iLMP = bus
    ax[row,col].plot(h, d[:,iLMP+8], color='red', label='CLR')
    ax[row,col].plot(h, d[:,iLMP+16], color='blue', label='BID')
    ax[row,col].plot(h, d[:,iLMP+24], color='green', label='SET')
    bus += 1
    ax[row,col].grid()
    ax[row,col].legend()
    ax[row,col].set_title ('Bus {:d}'.format(bus))
    ax[row,col].set_ylabel ('MW')
    if row == 1:
      ax[row,col].set_xlabel ('Hours')

plt.show()


