import numpy as np;
import scipy.interpolate as ip;
import pypower.api as pp;
import tesp_support.fncs as fncs
import sys;
import json;
import math;

casename = 'ercot_8'

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

x = np.array (range (25))
y = np.array (load_shape)
l = len(x)
t = np.linspace(0,1,l-2,endpoint=True)
t = np.append([0,0,0],t)
t = np.append(t,[1,1,1])
tck_load=[t,[x,y],3]
u3=np.linspace(0,1,num=86400/300 + 1,endpoint=True)
newpts = ip.splev (u3, tck_load)

ppc = tesp.load_json_case (casename + '.json')
StartTime = ppc['StartTime']
tmax = int(ppc['Tmax'])
period = int(ppc['Period'])
dt = int(ppc['dt'])
# FNCS: bus, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew
fncs_bus = ppc['FNCS']
gld_bus = {} # key on bus number
for i in range (8):
  busnum = i+1
  gld_bus[busnum] = {'pcrv':0,'qcrv':0,'lmp':0,'v':0,'p':0,'q':0,'unresp':0,'resp_max':0,'c2':0,'c1':0,'deg':0} 

# initialize for time stepping
ts = 0
fncs.initialize()
# MAIN LOOP starts here
while ts <= tmax:
  # start by getting the latest inputs from TSO, namely the LMP and voltage
  events = fncs.get_events()
  for topic in events:
    val = fncs.get_value(topic)
    if 'LMP' in topic:
      busnum = int (topic[3:])
      gld_bus[busnum]['lmp'] = float(val)
    elif 'V' in topic:
      busnum = int (topic[1:])
      gld_bus[busnum]['v'] = float(val)

  # always baseline the loads from the curves
  for row in fncs_bus:
    busnum = int (row[0])
    pubtopic = row[1]
    gld_scale = float (row[2])
    Pnom = float (row[3])
    Qnom = float (row[4])
    curve_scale = float (row[5])
    curve_skew = int (row[6])
    sec = (ts + curve_skew) % 86400
    h = float (sec) / 3600.0
    val = ip.splev ([h / 24.0], tck_load)
    gld_bus[busnum]['pcrv'] = Pnom * curve_scale * float(val[1])
    gld_bus[busnum]['qcrv'] = Qnom * curve_scale * float(val[1])

    # the actual load is the same as the curve load
    p = gld_bus[busnum]['pcrv']
    q = gld_bus[busnum]['qcrv']
    gld_bus[busnum]['p'] = p
    gld_bus[busnum]['q'] = q
    distload = '{:.3f}'.format(p) + '+' + '{:.3f}'.format(q) + 'j MVA'
    fncs.publish ('gridlabdBus' + str(busnum) '/distribution_load', distload)

    # bid half the load as unresponsive, and the remainder with a fixed price
    resp_max = gld_bus[busnum]['resp_max'] * gld_scale * 0.5
    unresp = gld_bus[busnum]['unresp'] * gld_scale * 0.5
    c2 = gld_bus[busnum]['c2'] / gld_scale
    c1 = gld_bus[busnum]['c1']
    deg = gld_bus[busnum]['deg']
    fncs.publish (pubtopic + '/unresponsive_mw', unresp)
    fncs.publish (pubtopic + '/responsive_max_mw', resp_max)
    fncs.publish (pubtopic + '/responsive_c2', c2)
    fncs.publish (pubtopic + '/responsive_c1', c1)
    fncs.publish (pubtopic + '/responsive_deg', deg)

  # request the next time step, if necessary
  if ts >= tmax:
    print ('breaking out at',ts,flush=True)
    break
  ts = fncs.time_request(min(ts + dt, tmax))

# ======================================================
print ('finalizing FNCS', flush=True)
fncs.finalize()

