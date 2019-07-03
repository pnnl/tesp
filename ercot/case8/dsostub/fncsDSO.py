import numpy as np;
import scipy.interpolate as ip;
import tesp_support.api as tesp;
import tesp_support.fncs as fncs;
import json;

# day-ahead market runs at noon every day
da_period = 86400
da_offset = 12 * 3600 - 300  # submit the day-ahead bid 5 minutes before closing
tnext_da = da_offset

casename = 'ercot_8'
bWantMarket = True
bid_c2 = -2.0
bid_c1 = 60.0
bid_deg = 2

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
dt = 60
# FNCS: bus, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew
fncs_bus = ppc['FNCS']
gld_bus = {} # key on bus number
for i in range (8):
  busnum = i+1
  gld_bus[busnum] = {'pcrv':0,'qcrv':0,'lmp':0,'v':0,'p':0,'q':0,'unresp':0,'resp_max':0,'c2':bid_c2,'c1':bid_c1,'deg':bid_deg} 

# initialize for time stepping and metrics
ts = 0
fncs.initialize()
dso_mp = open ('dso_' + casename + '_metrics.json', 'w')
dso_meta = {'Pdso':{'units':'MW','index':0},'Qdso':{'units':'MVAR','index':1},
  'LMP':{'units':'USD/kwh','index':2},'Pcleared':{'units':'MW','index':3}}
dso_metrics = {'Metadata':dso_meta,'StartTime':ppc['StartTime']}

# MAIN LOOP starts here
while ts <= tmax:
  dso_metrics[str(ts)] = {}
  # get voltages and LMPs from the TSO
  events = fncs.get_events()
  for topic in events:
    val = fncs.get_value(topic)
    if 'LMP' in topic:
      busnum = int (topic[3:])
      gld_bus[busnum]['lmp'] = float(val)
    elif 'V' in topic:
      busnum = int (topic[1:])
      gld_bus[busnum]['v'] = float(val)

  # bid into the day-ahead market for each bus
  # as with real-time market, half the hourly load will be unresponsive and half responsive
  # the bid curve is also fixed
  # however, we will add some noise to the day-ahead bid
  if ts >= tnext_da:
    for row in fncs_bus:
      da_bid = {'unresp_mw':[], 'resp_max_mw':[], 'resp_c2':[], 'resp_c1':[], 'resp_deg':[]}
      busnum = int (row[0])
      pubtopic = row[1] # this is what fncsTSO.py receives it as
      gld_scale = float (row[2]) # divide published P, Q values by gld_scale, because fncsTSO.py multiplies by gld_scale
      Pnom = float (row[3])
      curve_scale = float (row[5])
      curve_skew = int (row[6])
      if bWantMarket:
        c2 = gld_bus[busnum]['c2']
        c1 = gld_bus[busnum]['c1']
        deg = gld_bus[busnum]['deg']
      else:
        c2 = 0
        c1 = 0
        deg = 0
      for i in range(24):
        sec = (3600 * i + curve_skew) % 86400
        h = float (sec) / 3600.0
        val = ip.splev ([h / 24.0], tck_load)
        Phour = Pnom * curve_scale * float(val[1])
        if bWantMarket:
          resp_max = Phour * 0.5
          unresp = Phour * 0.5
        else:
          resp_max = 0.0
          unresp = Phour
        da_bid['unresp_mw'].append(unresp)
        da_bid['resp_max_mw'].append(resp_max)
        da_bid['resp_c2'].append(c2)
        da_bid['resp_c1'].append(c1)
        da_bid['resp_deg'].append(deg)

      pubtopic = 'substationBus' + str(busnum)  # this is what the tso8stub.yaml expects to receive from a substation auction
      print ('Day-Ahead bid for', pubtopic, 'at', ts, '=', da_bid, flush=True)
      fncs.publish (pubtopic + '/da_bid', json.dumps(da_bid))
    tnext_da += da_period

  # update the bid, and publish simulated load as unresponsive + cleared_responsive
  for row in fncs_bus:
    busnum = int (row[0])
    pubtopic = row[1] # this is what fncsTSO.py receives it as
    gld_scale = float (row[2]) # divide published P, Q values by gld_scale, because fncsTSO.py multiplies by gld_scale
    Pnom = float (row[3])
    Qnom = float (row[4])
    qf = 0.0
    if Pnom > 0:
      qf = Qnom / Pnom
    curve_scale = float (row[5])
    curve_skew = int (row[6])
    sec = (ts + curve_skew) % 86400
    h = float (sec) / 3600.0
    val = ip.splev ([h / 24.0], tck_load)
    gld_bus[busnum]['pcrv'] = Pnom * curve_scale * float(val[1])
    gld_bus[busnum]['qcrv'] = Qnom * curve_scale * float(val[1])

    # bid half the curve load as unresponsive, and the other half with a fixed cost curve, i.e., not time responsive
    if bWantMarket:
      resp_max = gld_bus[busnum]['pcrv'] * 0.5
      unresp = gld_bus[busnum]['pcrv'] * 0.5
      c2 = gld_bus[busnum]['c2']
      c1 = gld_bus[busnum]['c1']
      deg = gld_bus[busnum]['deg']
    else:
      resp_max = 0.0
      unresp = gld_bus[busnum]['pcrv']
      c2 = 0
      c1 = 0
      deg = 0
    pubtopic = 'substationBus' + str(busnum)  # this is what the tso8stub.yaml expects to receive from a substation auction
    fncs.publish (pubtopic + '/unresponsive_mw', unresp / gld_scale)
    fncs.publish (pubtopic + '/responsive_max_mw', resp_max / gld_scale)
    fncs.publish (pubtopic + '/responsive_c2', c2 * gld_scale)
    fncs.publish (pubtopic + '/responsive_c1', c1)
    fncs.publish (pubtopic + '/responsive_deg', deg)

    # the actual load is the unresponsive load, plus a cleared portion of the responsive load
    lmp = 1000.0 * gld_bus[busnum]['lmp']
    p_cleared = 0
    if c1 > lmp and bWantMarket:
      p_cleared = 0.5 * gld_scale * (lmp - c1) / c2
      if p_cleared > resp_max:
        p_cleared = resp_max
    p = unresp + p_cleared
    q = p * qf
    gld_bus[busnum]['p'] = p
    gld_bus[busnum]['q'] = q
    distload = '{:.3f}'.format(p / gld_scale) + '+' + '{:.3f}'.format(q / gld_scale) + 'j MVA'
    pubtopic = 'gridlabdBus' + str(busnum)  # this is what the tso8stub.yaml expects to receive from GridLAB-D
    fncs.publish (pubtopic + '/distribution_load', distload)

    # update the metrics
    dso_metrics[str(ts)][str(busnum)] = [p, q, lmp, p_cleared]

  # request the next time step, if necessary
  if ts >= tmax:
    print ('breaking out at',ts,flush=True)
    break
  ts = fncs.time_request(min(ts + dt, tmax))

# ======================================================
print ('writing metrics', flush=True)
print (json.dumps(dso_metrics), file=dso_mp, flush=True)
print ('closing files', flush=True)
dso_mp.close()
print ('finalizing FNCS', flush=True)
fncs.finalize()

