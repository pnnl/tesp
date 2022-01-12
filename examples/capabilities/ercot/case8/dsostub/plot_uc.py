#   Copyright (C) 2020-2022 Battelle Memorial Institute
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;
import tesp_support.api as tesp;

f, nb, ng, nl, ns, nt, nj_max, Pg, Pd, Pf, u, lamP = tesp.read_most_solution ('msout.txt')
print ('f={:.2f} nb={:d} ng={:d} nl={:d} ns={:d} nt={:d} nj_max={:d}'.format (f, nb, ng, nl, ns, nt, nj_max))

np.set_printoptions(precision=3)
h = np.linspace (1.0, 24.0, num=nt) - 0.5
#print (lamP)

Psteam = np.sum(Pg[0:13,:], axis=0)
Pwind = np.sum(Pg[13:18,:], axis=0)
Presp = np.abs(np.sum(Pg[18:,:], axis=0))
Pfixed = np.sum(Pd, axis=0)
AvgSteam = np.mean(Psteam)
AvgWind = np.mean(Pwind)
AvgFixed = np.mean(Pfixed)
AvgResp = np.mean(Presp)
AvgErr = AvgSteam + AvgWind - AvgFixed - AvgResp
print ('Average Psteam={:.2f}, Pwind={:.2f}, Pfixed={:.2f}, Presp={:.2f}, Perr={:.2f}'.format (AvgSteam, 
      AvgWind, AvgFixed, AvgResp, AvgErr))
#quit()

cset = ['red', 'blue', 'green', 'magenta', 'cyan', 'orange', 'lime', 'silver',
        'gold', 'pink', 'tan', 'peru', 'darkgray']
fig, ax = plt.subplots(2, 4, sharex = 'col')
tmin = 0.0
tmax = 24.0
xticks = [0,6,12,18,24]
for i in range(2):
    for j in range(4):
        ax[i,j].grid (linestyle = '-')
        ax[i,j].set_xlim(tmin,tmax)
        ax[i,j].set_xticks(xticks)

ax[0,0].set_title ('Unit Commitment Status')
usched = np.zeros (len(h))
ax[0,0].set_ylim (0, 14)
ax[0,0].set_yticks ([0,2,4,6,8,10,12,14])
ax[0,0].set_ylabel ('Unit #')
off_val = -1.0
for i in range(13):
  on_val = i + 1.0
  for j in range(len(h)):
    if u[i,j] < 0.001:
      usched[j] = off_val
    else:
      usched[j] = on_val
  ax[0,0].plot(h, usched, marker='+', linestyle='None', color=cset[i])

ax[0,1].set_title ('Bus LMP')
for i in range(nb):
  ax[0,1].plot(h, lamP[i,:], label='Bus{:d}'.format (i+1), color = cset[i])
ax[0,1].set_ylabel ('$/MWhr')
ax[0,1].legend()

ax[0,2].set_title ('Branch Flows')
for i in range(nl):
  ax[0,2].plot(h, 0.001 * np.abs(Pf[i,:]), label='Ln{:d}'.format (i+1), color = cset[i])
ax[0,2].set_ylabel ('GW')

ax[1,0].set_title ('Unit Dispatch')
for i in range(13):
  ax[1,0].plot(h, 0.001 * Pg[i,:], label='Gen{:d}'.format (i+1), color = cset[i])
ax[1,0].set_ylabel ('GW')

ax[1,1].set_title ('Fixed Load')
for i in range(nb):
  ax[1,1].plot(h, 0.001 * Pd[i,:], label='Bus{:d}'.format (i+1), color = cset[i])
ax[1,1].set_ylabel ('GW')
ax[1,1].legend()

ax[1,2].set_title ('Responsive Load')
for i in range(nb):
  ax[1,2].plot(h, 0.001 * np.abs(Pg[i+18,:]), label='Bus{:d}'.format (i+1), color = cset[i])
ax[1,2].set_ylabel ('GW')
ax[1,2].legend()

ax[0,3].set_title ('System Generation')
ax[0,3].plot(h, 0.001 * Psteam, label='Steam', color='red')
ax[0,3].plot(h, 0.001 * Pwind, label='Wind', color='blue')
ax[0,3].plot(h, 0.001 * (Pfixed + Presp), label='Loads', color='green')
ax[0,3].set_ylabel ('GW')
ax[0,3].legend()

ax[1,3].set_title ('System Load')
ax[1,3].plot(h, 0.001 * Pfixed, label='Fixed', color='red')
ax[1,3].plot(h, 0.001 * Presp, label='Responsive', color='blue')
ax[1,3].set_ylabel ('GW')
ax[1,3].legend()

for j in range(4):
  ax[1,j].set_xlabel ('Hour')
plt.show()

#bus = 1
#for row in range(2):
#  for col in range(4):
#    iLMP = bus
#    ax[row,col].plot(h, d[:,iLMP+8], color='red', label='CLR')
#    ax[row,col].plot(h, d[:,iLMP+16], color='blue', label='BID')
#    ax[row,col].plot(h, d[:,iLMP+24], color='green', label='SET')
#    bus += 1
#    ax[row,col].grid()
#    ax[row,col].legend()
#    ax[row,col].set_title ('Bus {:d}'.format(bus))
#    ax[row,col].set_ylabel ('MW')
#    if row == 1:
#      ax[row,col].set_xlabel ('Hours')
#
#plt.show()
#

