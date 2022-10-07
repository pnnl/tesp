# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: player_f.py

import datetime
import json

import helics
import numpy as np


def load_player_loop(casename, keyName):
    print('Loading settings from json file ' + casename, flush=True)
    with open(casename + '.json', 'r', encoding='utf-8') as lp:
        ppc = json.load(lp)
    StartTime = ppc['StartTime']
    EndTime = ppc['EndTime']
    tmax = int(ppc['Tmax'])
    dt = int(ppc['dt'])
    genFuel = ppc['genfuel']
    fncs_bus = ppc['DSO']
    renew = ppc['renewables']

    key = ppc[keyName]
    prefix = key[0]
    vals_rows = key[1]
    power_factor = key[2]
    dt_load_collector = key[3]
    date_time_str = key[4]
    data_path = key[5]
    output = key[6]
    output_hist = key[7]
    load = key[8]
    constant = False
    if prefix == 'ind':
        constant = True

    print('Player settings: ' + keyName, flush=True)
    print('StartTime: ' + StartTime, flush=True)
    print('EndTime: ' + EndTime, flush=True)
    print('File: ' + data_path, flush=True)
    load_data = np.genfromtxt(data_path, names=True, delimiter=',', max_rows=vals_rows)

    # initialize for time stepping
    ep = datetime.datetime(1970, 1, 1)
    s = datetime.datetime.strptime(StartTime, '%Y-%m-%d %H:%M:%S')
    e = datetime.datetime.strptime(EndTime, '%Y-%m-%d %H:%M:%S')
    d = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
    sIdx = (s - ep).total_seconds()
    eIdx = (e - ep).total_seconds()
    dIdx = (d - ep).total_seconds()
    sRow = int((sIdx - dIdx) // dt_load_collector)
    eRow = int((eIdx - dIdx) // dt_load_collector)
    nRow = int((eIdx - sIdx))

    # couple of checks
    if sRow < 0 or eRow < 0:
        raise Exception("Error: StartTime is before the start date of the data being loaded")
    if not constant:
        if sRow > vals_rows or eRow > vals_rows:
            raise Exception("Error: StartTime is after the end date of the data being loaded")
    if tmax > nRow:
        raise Exception(
            "Error: Tmax {} is more than nRow {}, the time period specified in StartTime and EndTime".format(tmax,
                                                                                                             nRow))
    if tmax < nRow:
        print("Warning: Tmax is less than the time period specified in StartTime and EndTime", flush=True)

    # in seconds
    ts = 0
    hour = 3600
    day = 86400
    history_cnt = 48
    counter = sRow - 1
    hr_counter = hour // dt_load_collector
    new_row = False
    time_series = None
    time_series_history = None
    dtyp = []
    for j in load_data.dtype.names:
        dtyp.append((j, '<f8'))

    print('Initialize HELICS player federate', flush=True)
    hFed = helics.helicsCreateValueFederateFromConfig("./" + prefix + "_player.json")
    fedName = helics.helicsFederateGetName(hFed)
    subCount = helics.helicsFederateGetInputCount(hFed)
    pubCount = helics.helicsFederateGetPublicationCount(hFed)
    print('Federate name: ' + fedName, flush=True)
    print('Subscription count: ' + str(subCount))
    print('Publications count: ' + str(pubCount), flush=True)
    print('Starting HELICS player federate', flush=True)
    helics.helicsFederateEnterExecutingMode(hFed)

    # MAIN LOOP starts here
    while ts <= tmax:
        tb = ts + 15

        # real time is at dt_load_collector a line at a time
        if tb % dt_load_collector == 0 or ts == 0:
            new_row = True
            counter += 1
            if constant:
                time_series = load_data[[1]]
            else:
                time_series = load_data[[counter]]
            # print("Row:" + str(counter) + "  sec: " + str(ts), flush=True)

        # history is 48-hours (3600 / dt_load_collector) at a line for a time
        if tb % day == 0 or ts == 0:
            history_counter = counter
            time_series_history = [None] * history_cnt
            for i in range(0, history_cnt):
                if constant:
                    time_series_history[i] = load_data[[1]]
                else:
                    # First index
                    # time_series_history[i] = load_data[[history_counter]]

                    # if hr_counter equals = 1 then this(average,min,max) is the same as first index above
                    first = []
                    for j in load_data.dtype.names:
                        d = load_data[j][history_counter:(history_counter + hr_counter)]
                        # min_d = min(d)
                        # max_d = min(d)
                        # first.append(((max_d-min_d)/2) + min_d)     # mean
                        # first.append(min_d)                         # min
                        # first.append(max_d)                         # max
                        first.append(sum(d) / hr_counter)  # average
                    time_series_history[i] = np.array([tuple(first)], dtype=dtyp)

                history_counter += hr_counter
                # print("History Row:" + str(history_counter) + "  sec: " + str(ts), flush=True)

        # publish simulated load
        if load and new_row:
            new_row = False
            for row in fncs_bus:
                idx = str(row[0])
                lbl = 'Bus' + idx
                val = time_series[lbl][0]
                if val < 0:
                    val = 0
                    found_neg_val = True
                val = '+' + '{:.3f}'.format(val) + \
                      '+' + '{:.3f}'.format(val * power_factor) + 'j MVA'
                if output:
                    pub = helics.helicsFederateGetPublication(hFed, prefix + '_load_' + idx)
                    helics.helicsPublicationPublishString(pub, val)
                    # print(prefix + '_load_' + idx, val, flush=True)
                if tb % day == 0 or ts == 0:
                    time_series_history_pub = []
                    for j in range(0, history_cnt):
                        val = time_series_history[j][lbl][0]
                        if val < 0:
                            val = 0
                            found_neg_val = True
                        time_series_history_pub.append(val)
                    if output_hist:
                        pub = helics.helicsFederateGetPublication(hFed, prefix + '_ld_hist_' + idx)
                        helics.helicsPublicationPublishString(pub, json.dumps(time_series_history_pub))
                        # print(prefix + '_load_history_' + idx, json.dumps(time_series_history_pub), flush=True)

        # publish simulated generators
        if not load and new_row:
            new_row = False
            for i in range(len(genFuel)):
                found_neg_val = False
                if genFuel[i][0] in renew:
                    idx = str(genFuel[i][2])
                    lbl = genFuel[i][0] + idx
                    val = time_series[lbl][0]
                    if val < 0:
                        val = 0
                        found_neg_val = True
                    val = '{:.3f}'.format(val)
                    if output:
                        pub = helics.helicsFederateGetPublication(hFed, prefix + '_power_' + idx)
                        helics.helicsPublicationPublishString(pub, val)
                        # print(prefix + '_power_' + idx, val, flush=True)
                    if tb % day == 0 or ts == 0:
                        time_series_history_pub = []
                        for j in range(0, history_cnt):
                            val = time_series_history[j][lbl][0]
                            if val < 0:
                                val = 0
                                found_neg_val = True
                            val = '{:.3f}'.format(val)
                            time_series_history_pub.append(val)
                        if output_hist:
                            pub = helics.helicsFederateGetPublication(hFed, prefix + '_pwr_hist_' + idx)
                            helics.helicsPublicationPublishString(pub, json.dumps(time_series_history_pub))
                            # print(prefix + '_power_history_' + idx, json.dumps(time_series_history_pub), flush=True)
                if found_neg_val:
                    print('Time', str(ts), ', found negative values in', genFuel[i][0] + str(genFuel[i][2]))

        # request the next time step, if necessary
        if ts >= tmax:
            print('breaking out at', ts, flush=True)
            break

        ts = int(helics.helicsFederateRequestTime(hFed, min(ts + dt, tmax)))

    print('Finalizing HELICS player federate', flush=True)
    helics.helicsFederateDestroy(hFed)


if __name__ == "__main__":
    # load_player_loop('./generate_case_config', 'genMn')
    # load_player_loop('./generate_case_config', 'genForecastHr')
    load_player_loop('./generate_case_config', 'refLoadMn')
    # load_player_loop('./generate_case_config', 'refLoadHr')
    # load_player_loop('./generate_case_config', 'gldLoad')
