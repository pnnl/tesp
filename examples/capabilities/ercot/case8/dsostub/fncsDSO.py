#   Copyright (C) 2017-2022 Battelle Memorial Institute
import json
import random
import sys
import numpy as np
import scipy.interpolate as ip

import tesp_support.api.fncs as fncs
import tesp_support.api.tso_helpers as tso

# day-ahead market runs at noon every day
da_period = 86400
da_offset = 12 * 3600 - 300  # submit the day-ahead bid 5 minutes before closing
tnext_da = da_offset

casename = 'ercot_8'
bWantMarket = True
bRandomize = False
bid_c2 = 0.0  # -2.0
bid_c1 = 20.0
bid_c1_daylight_factor = 1.8
daylight_start = 9.0
daylight_end = 19.0
bid_deg = 1  # 2

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

x = np.array(range(25))
y = np.array(load_shape)
l = len(x)
t = np.linspace(0, 1, l - 2, endpoint=True)
t = np.append([0, 0, 0], t)
t = np.append(t, [1, 1, 1])
tck_load = [t, [x, y], 3]

ppc = tso.load_json_case(casename + '.json')
StartTime = ppc['StartTime']
tmax = int(ppc['Tmax'])
period = int(ppc['Period'])
dt = int(ppc['dt'])
dt = 60

# DSO: bus, topic, gld_scale, Pnom, Qnom, curve_scale, curve_skew
dso_bus = ppc['DSO']
gld_bus = {}  # key on bus number
last_bid_c1 = {}
for i in range(8):
    busnum = i + 1
    gld_bus[busnum] = {'pcrv': 0, 'qcrv': 0, 'lmp': 0, 'clr': 0, 'v': 0, 'p': 0, 'q': 0,
                       'unresp': 0, 'resp_max': 0, 'resp': 0, 'c2': bid_c2, 'c1': bid_c1, 'deg': bid_deg}
    last_bid_c1[busnum] = bid_c1


def hour_block_bid(h, h1, h2, p1, p2, q1, q2):  # p is price (c1), q is quantity (P)
    # conservative values
    p = max(p1, p2)
    q = max(q1, q2)
    # average values
    #  s = (h - h1) / (h2 - h1)
    #  p = p1 + s * (p2 - p1)
    #  q = q1 + s * (q2 - q1)
    #  print ('hour_block_bid {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f} {:.4f}'
    #  .format (h, h1, h2, s, p1, p2, p, q1, q2, q))
    return p, q


# bid the average price and quantity from the beginning and end of each hour
def make_da_bid(row, bWantMarket):
    da_bid = {'unresp_mw': [], 'resp_max_mw': [], 'resp_c2': [], 'resp_c1': [], 'resp_deg': []}
    busnum = int(row[0])
    gld_scale = float(row[2])  # divide published P, Q values by gld_scale, because tso_psst_f.py multiplies by gld_scale
    Pnom = float(row[3])
    curve_scale = float(row[5])
    curve_skew = int(row[6])
    if bWantMarket:
        c2 = 0.0  # gld_bus[busnum]['c2']
        c1 = gld_bus[busnum]['c1']
        deg = 1  # gld_bus[busnum]['deg']
    else:
        c2 = 0
        c1 = 0
        deg = 0
    for i in range(24):
        sec = (3600 * i + curve_skew) % 86400
        #    h = float (sec) / 3600.0
        #    val = ip.splev ([h / 24.0], tck_load)
        #    Phour = Pnom * curve_scale * float(val[1])
        h1 = float(sec) / 3600.0
        h2 = h1 + 1.0
        val1 = ip.splev([h1 / 24.0], tck_load)
        val2 = ip.splev([h2 / 24.0], tck_load)
        Phour1 = Pnom * curve_scale * float(val1[1])
        Phour2 = Pnom * curve_scale * float(val2[1])
        c1hour1 = c1
        c1hour2 = c1hour1
        if bRandomize and bWantMarket:
            c1hour1 += random.random()
            c1hour2 += random.random()
        if h1 >= daylight_start and h1 <= daylight_end:
            c1hour1 *= bid_c1_daylight_factor
        if h2 >= daylight_start and h2 <= daylight_end:
            c1hour2 *= bid_c1_daylight_factor
        Cblock, Pblock = hour_block_bid(int(h2), h1, h2, c1hour1, c1hour2, Phour1, Phour2)
        if bWantMarket:
            #      resp_max = Phour * 0.5
            #      unresp = Phour * 0.5
            #      cbid = c1
            #      if bRandomize:
            #        cbid += random.random()
            resp_max = Pblock * 0.5
            unresp = Pblock * 0.5
            c1bid = Cblock
        else:
            resp_max = 0.0
            #      unresp = Phour
            unresp = 2.0 * Pblock
            c1bid = 0.0
        da_bid['unresp_mw'].append(round(unresp / gld_scale, 3))
        da_bid['resp_max_mw'].append(round(resp_max / gld_scale, 3))
        da_bid['resp_c2'].append(c2)
        #    if h >= daylight_start and h <= daylight_end:
        #      cbid *= bid_c1_daylight_factor
        #    da_bid['resp_c1'].append(round (cbid, 3))
        da_bid['resp_c1'].append(round(c1bid, 3))
        da_bid['resp_deg'].append(deg)
    return da_bid


if len(sys.argv) > 1:
    print('write DAM bid to', sys.argv[1])
    da_bids = {}
    for row in dso_bus:
        da_bids[row[1]] = make_da_bid(row, bWantMarket)
    fp = open(sys.argv[1], 'w')
    json.dump(da_bids, fp, indent=2)
    fp.close()
    quit()

# initialize for time stepping and metrics
op = open(casename + '_dso.csv', 'w')
print('ts,LMP1,LMP2,LMP3,LMP4,LMP5,LMP6,LMP7,LMP8,CLR1,CLR2,CLR3,CLR4,CLR5,CLR6,CLR7,CLR8,' +
      'BID1,BID2,BID3,BID4,BID5,BID6,BID7,BID8,SET1,SET2,SET3,SET4,SET5,SET6,SET7,SET8', file=op)

ts = 0
fncs.initialize()
dso_mp = open('dso_' + casename + '_metrics.json', 'w')
dso_meta = {'Pdso': {'units': 'MW', 'index': 0}, 'Qdso': {'units': 'MVAR', 'index': 1},
            'LMP': {'units': 'USD/kwh', 'index': 2}, 'Pcleared': {'units': 'MW', 'index': 3}}
dso_metrics = {'Metadata': dso_meta, 'StartTime': ppc['StartTime']}

# MAIN LOOP starts here
while ts <= tmax:
    dso_metrics[str(ts)] = {}
    # get voltages and LMPs from the TSO
    events = fncs.get_events()
    for topic in events:
        val = fncs.get_value(topic)
        if 'LMP_RT_Bus_' in topic:
            busnum = int(topic[11:])
        # following is for tso_psst_f.py, the AMES/PSST version
        #      gld_bus[busnum]['lmpRT'][] = float(val)
        elif 'LMP_DA_Bus_' in topic:
            busnum = int(topic[11:])
        # following is for tso_psst_f.py, the AMES/PSST version
        #      gld_bus[busnum]['lmpDA'][] = float(val)
        elif 'LMP' in topic:
            busnum = int(topic[3:])
            gld_bus[busnum]['lmp'] = float(val)
        elif 'V' in topic:
            busnum = int(topic[1:])
            gld_bus[busnum]['v'] = float(val)
        elif 'CLR' in topic:
            busnum = int(topic[3:])
            gld_bus[busnum]['clr'] = float(val)

    # bid into the day-ahead market for each bus
    # as with real-time market, half the hourly load will be unresponsive and half responsive
    # the bid curve is also fixed
    # however, we will add some noise to the day-ahead bid
    if ts >= tnext_da:
        for row in dso_bus:
            da_bid = make_da_bid(row, bWantMarket)

            busnum = int(row[0])
            # this is what the tso8stub.yaml expects to receive from a substation auction
            pubtopic = 'substationBus' + str(busnum)
            print('Day-Ahead bid for {:s} at {:d}, c2={:f}, deg={:d}'
                  .format(pubtopic, ts, da_bid['resp_c2'][0], da_bid['resp_deg'][0]))
            print('  Bid Resp C1', da_bid['resp_c1'])
            print('  Max Resp MW', da_bid['resp_max_mw'])
            print('  Unresp   MW', da_bid['unresp_mw'], flush=True)
            fncs.publish(pubtopic + '/da_bid', json.dumps(da_bid))
        tnext_da += da_period

    # update the RTM bid, and publish simulated load as unresponsive + cleared_responsive
    for row in dso_bus:
        busnum = int(row[0])
        pubtopic = row[1]  # this is what tso_psst_f.py receives it as
        # divide published P, Q values by gld_scale, because tso_psst_f.py multiplies by gld_scale
        gld_scale = float(row[2])
        Pnom = float(row[3])
        Qnom = float(row[4])
        qpratio = 0.0
        if Pnom > 0:
            qpratio = Qnom / Pnom
        curve_scale = float(row[5])
        curve_skew = int(row[6])
        sec = (ts + curve_skew) % 86400
        h = float(sec) / 3600.0
        val = ip.splev([h / 24.0], tck_load)
        gld_bus[busnum]['pcrv'] = Pnom * curve_scale * float(val[1])
        gld_bus[busnum]['qcrv'] = Qnom * curve_scale * float(val[1])

        # bid half the curve load as unresponsive, and the other half with a fixed cost curve, i.e., not time responsive
        if bWantMarket:
            resp_max = gld_bus[busnum]['pcrv'] * 0.5
            unresp = gld_bus[busnum]['pcrv'] * 0.5
            c2 = gld_bus[busnum]['c2']
            c1 = gld_bus[busnum]['c1']
            last_bid_c1[busnum] = c1
            if bRandomize:
                last_bid_c1[busnum] += random.random()
            if h >= daylight_start and h <= daylight_end:
                last_bid_c1[busnum] *= bid_c1_daylight_factor
            deg = gld_bus[busnum]['deg']
        else:
            resp_max = 0.0
            unresp = gld_bus[busnum]['pcrv']
            c2 = 0
            last_bid_c1[busnum] = 0
            deg = 0
        # this is what the tso8stub.yaml expects to receive from a substation auction
        pubtopic = 'substationBus' + str(busnum)
        fncs.publish(pubtopic + '/unresponsive_mw', unresp / gld_scale)
        fncs.publish(pubtopic + '/responsive_max_mw', resp_max / gld_scale)
        fncs.publish(pubtopic + '/responsive_c2', c2)
        fncs.publish(pubtopic + '/responsive_c1', last_bid_c1[busnum])
        fncs.publish(pubtopic + '/responsive_deg', deg)
        #    print ('rtm bid [bus, ts, sec, h, c1]', busnum, ts, sec, h, last_bid_c1[busnum])

        # the actual load is the unresponsive load, plus a cleared portion of the responsive load
        lmp = 1000.0 * gld_bus[busnum]['lmp']
        p_cleared = 0
        #    dso_lmp = lmp
        if bWantMarket:
            p_cleared = gld_bus[busnum]['clr']
            # we can't use c2 with GLPK, so the back-calculation of p_cleared from lmp cannot be used
        #      F = lmp * p_cleared
        #      dso_lmp = last_bid_c1[busnum] + 2.0 * c2 * p_cleared / gld_scale
        p = unresp + p_cleared
        q = p * qpratio
        #    print ('Clearing at {:d}s Bus{:d}: bid={:.2f} lmp={:.2f} resp_max={:.2f} cleared={:.2f}'.format (ts, busnum,
        #            last_bid_c1[busnum], lmp, resp_max, p_cleared))
        gld_bus[busnum]['p'] = p
        gld_bus[busnum]['q'] = q
        gld_bus[busnum]['resp'] = p_cleared
        gld_bus[busnum]['resp_max'] = resp_max
        distload = '{:.3f}'.format(p / gld_scale) + '+' + '{:.3f}'.format(q / gld_scale) + 'j MVA'
        pubtopic = 'gridlabdBus' + str(busnum)  # this is what the tso8stub.yaml expects to receive from GridLAB-D
        fncs.publish(pubtopic + '/distribution_load', distload)

        # update the metrics (resp_max and last_bid_c1 are in the TSO bus metrics)
        dso_metrics[str(ts)][str(busnum)] = [p, q, lmp, p_cleared]

    # update the CSV output
    A = []
    for i in range(1, 9, 1):
        A.append(gld_bus[i]['lmp'])
    for i in range(1, 9, 1):
        A.append(gld_bus[i]['clr'])
    for i in range(1, 9, 1):
        A.append(gld_bus[i]['resp_max'])
    for i in range(1, 9, 1):
        A.append(gld_bus[i]['resp'])
    csvStr = ','.join('{:5f}'.format(item) for item in A)
    print('{:d},{:s}'.format(ts, csvStr), file=op, flush=True)

    # request the next time step, if necessary
    if ts >= tmax:
        print('breaking out at', ts, flush=True)
        break
    ts = fncs.time_request(min(ts + dt, tmax))

# ======================================================
print('writing metrics', flush=True)
print(json.dumps(dso_metrics), file=dso_mp, flush=True)
print('closing files', flush=True)
dso_mp.close()
print('finalizing FNCS', flush=True)
fncs.finalize()
op.close()
