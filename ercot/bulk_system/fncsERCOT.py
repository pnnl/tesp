import numpy as np;
import scipy.interpolate as ip;
import pypower.api as pp;
import tesp_support.api as tesp;
import sys;
import matplotlib.pyplot as plt

load_shape = [0.6704,
              0.6303,
              0.6041,
              0.5902,
              0.5912,
              0.6094,
              0.6400,
              0.6725,
              0.7207,
              0.7584,
              0.7905,
              0.8171,
              0.8428,
              0.8725,
              0.9098,
              0.9480,
              0.9831,
              1.0000,
              0.9868,
              0.9508,
              0.9306,
              0.8999,
              0.8362,
              0.7695,
              0.6704]  # wrap to the next day

def rescale_case(ppc, scale):
    ppc['bus'][:,2] *= scale  # Pd
    ppc['bus'][:,3] *= scale  # Qd
    ppc['bus'][:,5] *= (scale * scale)  # Qs
    ppc['gen'][:,1] *= scale  # Pg
    return

x = np.array (range (25))
y = np.array (load_shape)
l = len(x)
t = np.linspace(0,1,l-2,endpoint=True)
t = np.append([0,0,0],t)
t = np.append(t,[1,1,1])
tck_load=[t,[x,y],3]
u3=np.linspace(0,1,num=86400/300 + 1,endpoint=True)
newpts = ip.splev (u3, tck_load)

ppc = tesp.load_json_case ('ercot_8.json')
ppopt_regular = pp.ppoption(VERBOSE=1, 
                            OUT_SYS_SUM=1, 
                            OUT_BUS=1, 
                            OUT_GEN=0, 
                            OUT_BRANCH=1, 
                            PF_DC=0, 
                            PF_ALG=1)

ppopt_market = pp.ppoption(VERBOSE=1, 
                            OUT_SYS_SUM=1, 
                            OUT_BUS=1, 
                            OUT_GEN=1, 
                            OUT_BRANCH=1, 
                            OUT_LINE_LIM=1, 
                            PF_DC=1, 
                            PF_ALG=1)

#rpf = pp.runpf (ppc, ppopt_regular)
#ropf = pp.runopf (ppc, ppopt_market)

StartTime = ppc['StartTime']
tmax = int(ppc['Tmax'])
period = int(ppc['Period'])
dt = int(ppc['dt'])

# bus, topic, gld_scale, curve_scale, curve_skew
fncs_bus = ppc['FNCS']
loads = {'h':[],'1':[],'2':[],'3':[],'4':[],'5':[],'6':[],'7':[],'8':[]}

ts = 0

while ts <= tmax:
  loads['h'].append (float(ts) / 3600.0)
  for row in fncs_bus:
    sec = (ts + int (row[4])) % 86400
    h = float (sec) / 3600.0
    val = ip.splev ([h / 24.0], tck_load)
    loads[str(row[0])].append(val[1])
  ts += dt

#print (max(y), max(newpts[1]))
#fig, ax = plt.subplots()
#ax.plot (x, y, 'b')
#ax.plot (newpts[0], newpts[1], 'r')
#plt.show()
fig, ax = plt.subplots()
ax.plot (loads['h'], loads['1'], 'b')
ax.plot (loads['h'], loads['2'], 'g')
ax.plot (loads['h'], loads['3'], 'r')
ax.plot (loads['h'], loads['4'], 'c')
ax.plot (loads['h'], loads['5'], 'm')
ax.plot (loads['h'], loads['6'], 'y')
ax.plot (loads['h'], loads['7'], 'k')
ax.plot (loads['h'], loads['8'], 'b')
plt.show()

