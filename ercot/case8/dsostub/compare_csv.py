import csv;
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

# OPF: seconds, OPFconverged, TotalLoad, Production, SwingGen, ClearedResp, LMP1, LMP2, LMP3, LMP4, LMP5, LMP6, LMP7, LMP8, gas1, coal1, nuc1, gas2, coal2, nuc2, gas3, coal3, gas4, gas5, coal4, gas6, coal5, wind1, wind2, wind3, wind4, wind5, TotalWindGen
# PF: seconds, PFConverged, TotalLoad, TotalGen, TotalLoss, SwingGen, v1, v2, v3, v4, v5, v6, v7, v8

dpf = np.loadtxt('ercot_8_pf.csv', skiprows=1, delimiter=',', usecols=[0,2,3,5])
hpf = dpf[:,0] / 3600.0

dopf = np.loadtxt('ercot_8_opf.csv', skiprows=1, delimiter=',', usecols=[0,2,3,4,5])
hopf = dopf[:,0] / 3600.0

fig, ax = plt.subplots(1, 1, sharex = 'col')

ax.plot(hpf, dpf[:,1], color='black', label='PF Load')
ax.plot(hopf, dopf[:,1], color='gray', label='OPF Load')
ax.plot(hopf, dopf[:,4], color='green', label='Resp Load')

ax.plot(hpf, dpf[:,2], color='red', label='PF Gen')
ax.plot(hopf, dopf[:,2], color='orange', label='OPF Gen')

ax.plot(hpf, dpf[:,3], color='blue', label='PF Swing')
ax.plot(hopf, dopf[:,3], color='cyan', label='OPF Swing')

diff = dpf[:,3][::20] - dopf[:,3]
ax.plot(hopf, diff, color='magenta', label='Gen Diff')

ax.set_title ('OPF and PF Load/Generation Comparison')
ax.set_ylabel ('MW')
ax.set_xlabel ('Hours')
ax.grid()
ax.legend()

plt.show()


