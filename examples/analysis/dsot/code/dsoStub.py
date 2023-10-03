import json
import logging as log
import os

import tesp_support.original.fncs as fncs
import tesp_support.api.tso_helpers as tso
from tesp_support.api.parse_helpers import parse_mva


def dso_make_yaml(casename):
    log.info('Reading configuration...')
    ppc = tso.load_json_case(casename + '.json')
    port = str(ppc['port'])
    nd = ppc['DSO'].shape[0]

    # write player yaml(s) for load and generator players
    players = ppc["players"]
    for idx in range(len(players)):
        player = ppc[players[idx]]
        yamlfile = player[0] + '_player.yaml'
        yp = open(yamlfile, 'w')
        print('name: ' + player[0] + 'player', file=yp)
        print('time_delta: 15s', file=yp)
        print('broker: tcp://localhost:' + port, file=yp)
        print('aggregate_sub: true', file=yp)
        print('aggregate_pub: true', file=yp)
        yp.close()

    yp = open('dso.yaml', 'w')
    print('name: dsostub', file=yp)
    print('time_delta: 15s', file=yp)
    print('broker: tcp://localhost:' + port, file=yp)
    print('aggregate_sub: true', file=yp)
    print('aggregate_pub: true', file=yp)
    print('values:', file=yp)
    for i in range(nd):
        bs = str(i + 1)
        print('  SUBSTATION_' + bs + ':', file=yp)
        print('    topic: refplayer/ref_load_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  SUBHISTORY_' + bs + ':', file=yp)
        print('    topic: refplayer/ref_load_history_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  IND_LOAD_' + bs + ':', file=yp)
        print('    topic: indplayer/ind_load_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  IND_LD_HIST_' + bs + ':', file=yp)
        print('    topic: indplayer/ind_load_history_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  LMP_DA_Bus_' + bs + ':', file=yp)
        print('    topic: pypower/lmp_da_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  LMP_RT_Bus_' + bs + ':', file=yp)
        print('    topic: pypower/lmp_rt_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  V_Bus_' + bs + ':', file=yp)
        print('    topic: pypower/three_phase_voltage_' + bs, file=yp)
        print('    default: 1.0', file=yp)
    yp.close()

    yp = open('tso.yaml', 'w')
    print('name: pypower', file=yp)
    print('time_delta: 15s', file=yp)
    print('broker: tcp://localhost:' + port, file=yp)
    print('values:', file=yp)
    for i in range(nd):
        bs = str(i + 1)
        print('  DA_BID_' + bs + ':', file=yp)
        print('    topic: dsostub/da_bid_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  RT_BID_' + bs + ':', file=yp)
        print('    topic: dsostub/rt_bid_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  REF_LOAD_' + bs + ':', file=yp)
        print('    topic: refplayer/ref_load_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  REF_LD_HIST_' + bs + ':', file=yp)
        print('    topic: refplayer/ref_load_history' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  GLD_LOAD_' + bs + ':', file=yp)
        print('    topic: gldplayer/gld_load_' + bs, file=yp)
        print('    default: 0', file=yp)
        print('  GLD_LD_HIST_' + bs + ':', file=yp)
        print('    topic: gldplayer/gld_load_history_' + bs, file=yp)
        print('    default: 0', file=yp)
    if ppc['genPower']:
        genFuel = ppc['genfuel']
        for i in range(len(genFuel)):
            if genFuel[i][0] in ppc['renewables']:
                idx = str(genFuel[i][2])
                for plyr in ["genMn", "genForecastHr"]:
                    player = ppc[plyr]
                    if player[6] and not player[8]:
                        print('  ' + player[0].upper() + '_POWER_' + idx + ':', file=yp)
                        print('    topic: ' + player[0] + 'player/' + player[0] + '_power_' + idx, file=yp)
                        print('    default: 0', file=yp)
                    if player[7] and not player[8]:
                        print('  ' + player[0].upper() + '_PWR_HIST_' + idx + ':', file=yp)
                        print('    topic: ' + player[0] + 'player/' + player[0] + '_power_history_' + idx, file=yp)
                        print('    default: 0', file=yp)

    yp.close()


def dso_loop(casename):
    ts = 0
    rt_period = 300
    da_period = 43200  # 86400
    tnext_rt = -30  # start the real time bid
    tnext_da = (10 * 3600) - 15  # start the day ahead bid
    power_factor = 0.57  # roughly 30 deg

    logger = log.getLogger()
    # logger.setLevel(log.DEBUG)
    logger.setLevel(log.INFO)
    # logger.setLevel(log.WARNING)

    log.info('Reading configuration...')
    ppc = tso.load_json_case(casename + '.json')

    tmax = int(ppc['Tmax'])
    dt = int(ppc['dt'])
    bWantMarket = ppc['priceSensLoad']
    dso_bus = ppc['DSO']
    nd = dso_bus.shape[0]

    with open(os.path.join("..", ppc['dataPath'], ppc['dsoPopulationFile']), 'r', encoding='utf-8') as json_file:
        dso_config = json.load(json_file)
        json_file.close()

    dsoList = []
    for dso_key, dso_val in dso_config.items():
        if 'DSO' not in dso_key:
            continue
        bus = dso_val['bus_number']
        used = dso_val['used']
        if used:
            dsoList.append(bus)
    log.info("DSO List: " + str(dsoList))

    gld_bus = {}  # key on bus number
    for i in range(nd):
        busnum = i + 1
        gld_bus[busnum] = {
            'dalmp': {}, 'rtlmp': 0, 'v': 0,
            'p': 0, 'q': 0, 'p_hist': {},
            'p_i': 0, 'q_i': 0, 'p_i_hist': {}
        }

    log.info("FNCS Initalize")
    fncs.initialize()

    log.info("starting tso loop...")
    while ts <= tmax:
        events = fncs.get_events()
        # log.info('at ' + str(ts))
        for topic in events:
            val = fncs.get_value(topic)
            # get voltages and LMPs from the TSO
            if 'LMP_DT_Bus_' in topic:
                busnum = int(topic[11:])
                # gld_bus[busnum]['dalmp'] = float(val)
            elif 'LMP_RT_Bus_' in topic:
                busnum = int(topic[11:])
                # gld_bus[busnum]['rtlmp'] = float(val)
            elif 'V_Bus_' in topic:
                busnum = int(topic[6:])
                # gld_bus[busnum]['v'] = float(val)
            elif 'SUBSTATION_' in topic:  # gridlabd - residential/commercial
                busnum = int(topic[11:])
                p, q = parse_mva(val)
                # log.info('at ' + str(ts) + " " + topic + " " + val)
                gld_bus[busnum]['p'] = p  # MW active
                gld_bus[busnum]['q'] = q  # MW reactive
            elif 'SUBHISTORY_' in topic:  # gridlabd - residential/commercial
                busnum = int(topic[11:])
                # log.info('at ' + str(ts) + " " + topic + val)
                gld_bus[busnum]['p_hist'] = json.loads(val)  # MW active
            elif 'IND_LOAD_' in topic:
                busnum = int(topic[9:])
                p, q = parse_mva(val)
                # log.info('at ' + str(ts) + " " + topic + " " + val)
                gld_bus[busnum]['p_i'] = p  # MW
                gld_bus[busnum]['q_i'] = q  # MW
            elif 'IND_LD_HIST_' in topic:
                busnum = int(topic[12:])
                # log.info('at ' + str(ts) + " " + topic + val)
                gld_bus[busnum]['p_i_hist'] = json.loads(val)  # MW active

        # bid into the day-ahead market for each bus
        # as with real-time market, half the hourly load will be unresponsive and half responsive
        # the bid curve is also fixed
        # however, we will add some noise to the day-ahead bid
        if ts >= tnext_da:
            for row in dso_bus:
                busnum = int(row[0])
                if busnum in dsoList:
                    da_bid = {
                        'unresp_mw': [],
                        'resp_max_mw': [],
                        'resp_c2': [],
                        'resp_c1': [],
                        'resp_c0': [],
                        'resp_deg': []
                    }
                    for i in range(24):
                        p = gld_bus[busnum]['p_hist'][24 + i]  # + gld_bus[busnum]['p_i_hist'][24+i]
                        da_bid['unresp_mw'].append(p)
                        da_bid['resp_max_mw'].append(0.0)
                        da_bid['resp_c2'].append(0.0)
                        da_bid['resp_c1'].append(0.0)
                        da_bid['resp_c0'].append(0.0)
                        da_bid['resp_deg'].append(0)

                    # this is what the tso8stub.yaml expects to receive from a dso auction
                    log.info('Day-Ahead bid for DSO stub at' + str(ts) + ' = ' + str(da_bid))
                    fncs.publish('da_bid_' + str(busnum), json.dumps(da_bid))
            tnext_da += da_period

        # update the bid, and publish simulated load as unresponsive + cleared_responsive
        if ts >= tnext_rt:
            for row in dso_bus:
                busnum = int(row[0])
                if busnum in dsoList:
                    p = gld_bus[busnum]['p']  # + gld_bus[busnum]['p_i']
                    rt_bid = {
                        'unresp_mw': p,
                        'resp_max_mw': 0.0,
                        'resp_c2': 0.0,
                        'resp_c1': 0.0,
                        'resp_c0': 0.0,
                        'resp_deg': 0
                    }
                    if bWantMarket:
                        rt_bid['unresp_mw'] = p * 0.95
                        rt_bid['resp_max_mw'] = p * 0.05
                        rt_bid['resp_c2'] = 0.05
                        rt_bid['resp_c1'] = 60.0
                        rt_bid['resp_c0'] = 0.0
                        rt_bid['resp_deg'] = 0

                    # this is what the tso8stub.yaml expects to receive from a dso auction
                    log.info('Real Time bid for DSO stub at ' + str(ts) + ' = ' + str(rt_bid))
                    fncs.publish('rt_bid_' + str(busnum), json.dumps(rt_bid))

            tnext_rt += rt_period

        # request the next time step, if necessary
        if ts >= tmax:
            log.info('breaking out at ' + str(ts))
            break
        ts = fncs.time_request(min(ts + dt, tmax))

    # ======================================================
    log.info('finalizing FNCS')
    fncs.finalize()


if __name__ == "__main__":
    # dso_make_yaml('./generate_case_config')
    dso_loop('./generate_case_config')
