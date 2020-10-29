#   Copyright (C) 2020 Battelle Memorial Institute
import sys;
import numpy as np;
import matplotlib as mpl;
import matplotlib.pyplot as plt;

def next_val (fp, var, bInteger = True):
  match = '# name: ' + var
  looking = True
  val = None
  while looking:
    ln = fp.readline()
    if len(ln) < 1:
      print ('EOF looking for', var)
      return val
    if ln.strip() == match:
      looking = False
      fp.readline()
      if bInteger:
        val = int(fp.readline().strip())
      else:
        val = float(fp.readline().strip())
#  print (var, '=', val)
  return val

def next_matrix (fp, var):
  match = '# name: ' + var
  looking = True
  mat = None
  while looking:
    ln = fp.readline()
    if len(ln) < 1:
      print ('EOF looking for', var)
      return mat
    if ln.strip() == match:
      looking = False
      fp.readline()
      toks = fp.readline().strip().split()
      rows = int(toks[2])
      toks = fp.readline().strip().split()
      cols = int(toks[2])
#      print ('{:s} [{:d}x{:d}]'.format (var, rows, cols))
      mat = np.empty ((rows, cols))
      for i in range(rows):
        mat[i] = np.fromstring (fp.readline().strip(), sep=' ')
  return mat

fp = open ('msout.txt', 'r')

f = next_val (fp, 'f', False)
nb = next_val (fp, 'nb')
ng = next_val (fp, 'ng')
nl = next_val (fp, 'nl')
ns = next_val (fp, 'ns')
nt = next_val (fp, 'nt')
nj_max = next_val (fp, 'nj_max')
psi = next_matrix (fp, 'psi')
Pg = next_matrix (fp, 'Pg')
Pd = next_matrix (fp, 'Pd')
Rup = next_matrix (fp, 'Rup')
Rdn = next_matrix (fp, 'Rdn')
Pf = next_matrix (fp, 'Pf')
u = next_matrix (fp, 'u')
lamP = next_matrix (fp, 'lamP')
muF = next_matrix (fp, 'muF')
fp.close()

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
        'yellow', 'pink', 'tan', 'peru', 'darkgray']
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
for i in range(13):
  ax[0,0].plot(h, 0.25 * u[i,:] + i + 1.0, label='Gen{:d}'.format (i+1), color = cset[i])
ax[0,0].set_ylim (0, 14)
ax[0,0].set_yticks ([0,2,4,6,8,10,12,14])
ax[0,0].set_ylabel ('Unit #')

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

