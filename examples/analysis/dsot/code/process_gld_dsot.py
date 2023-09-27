# Copyright (C) 2017-2023 Battelle Memorial Institute
# file: process_gld_dsot.py
"""Functions to plot data from GridLAB-D

Public Functions:
    :process_gld: Reads the data and metadata, then makes the plots.

"""
import csv
import json
import os

import numpy as np

try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
except:
    pass


def get_nominal_voltage(voltage):
    nom_volt_lst = np.array([120.0, 277.0, 480.0, 7200])
    idx = (np.abs(voltage - nom_volt_lst)).argmin()
    return nom_volt_lst[idx]


def process_gld(name_root, diction_name=''):
    """ Plots a summary/sample of power, air temperature and voltage

    This function reads *substation_[name_root]_metrics.json*,
    *billing_meter_[name_root]_metrics.json* and
    *house_[name_root]_metrics.json* for the data;
    it reads *[name_root]_glm_dict.json* for the metadata.
    These must all exist in the current working directory.
    Makes one graph with 4 subplots:

    1. Substation real power and losses
    2. Average air temperature over all houses
    3. Min/Max line-to-neutral voltage and Min/Max line-to-line voltage at the first billing meter
    4. Min, Max and Average air temperature at the first house

    Args:
      name_root (str): name of the TESP case, not necessarily the same as the GLM case, without the extension
      diction_name (str): metafile name (with json extension) for a different GLM dictionary, if it's not *[name_root]_glm_dict.json*. Defaults to empty.
    """
    dso_num = name_root[-1]
    # Somehow metrics files are not being named properly. Rename them properly
    for file in os.listdir():
        if name_root + '_metrics_' in file and '.json' not in file:
            new_name = file + '.json'
            os.rename(file, new_name)

    # let's get the starttime and endtime
    lp_ag = open("../DSO_" + dso_num + "/" + name_root + "_agent_dict.json").read()
    agent_dict = json.loads(lp_ag)
    start_time = agent_dict['StartTime']
    end_time = agent_dict['EndTime']
    # region first, read and print a dictionary of all the monitored GridLAB-D objects
    if len(diction_name) > 0:
        lp = open(diction_name).read()
    else:
        lp = open("../DSO_" + dso_num + "/" + name_root + "_glm_dict.json").read()
    diction = json.loads(lp)
    sub_keys = list(diction['feeders'].keys())
    sub_keys.sort()
    inv_keys = list(diction['inverters'].keys())
    inv_keys.sort()
    hse_keys = list(diction['houses'].keys())
    hse_keys.sort()
    mtr_keys = list(diction['billingmeters'].keys())
    mtr_keys.sort()
    xfMVA = diction['transformer_MVA']
    bulkBus = diction['bulkpower_bus']
    print("\n\nFile", name_root, "has substation", sub_keys[0], "at bulk system bus", bulkBus, "with", xfMVA,
          "MVA transformer")
    print("\nFeeder Dictionary:")
    for key in sub_keys:
        row = diction['feeders'][key]
        print(key, "has", row['house_count'], "houses and", row['inverter_count'], "inverters")
    print("\nBilling Meter Dictionary:")
    for key in mtr_keys:
        row = diction['billingmeters'][key]
        print(key, "on phase", row['phases'], "of", row['feeder_id'], "with", row['children'])
    print("\nHouse Dictionary:")
    for key in hse_keys:
        row = diction['houses'][key]
        print(key, "on", row['billingmeter_id'], "has", row['sqft'], "sqft", row['cooling'], "cooling", row['heating'],
              "heating", row['wh_gallons'], "gal WH")
        # row['feeder_id'] is also available
    print("\nInverter Dictionary:")
    for key in inv_keys:
        row = diction['inverters'][key]
        print(key, "on", row['billingmeter_id'], "has", row['rated_W'], "W", row['resource'], "resource")
        # row['feeder_id'] is also available
    # endregion

    # Parse the substation metrics file first; there should just be one entity per time sample
    # each metrics file should have matching time points
    # region Collecting Substation Data
    lp_s = open(name_root + "_metrics_substation.json").read()
    lst_s = json.loads(lp_s)
    print("\nMetrics data starting", lst_s['StartTime'])

    # make a sorted list of the sample times in hours
    lst_s.pop('StartTime')
    meta_s = lst_s.pop('Metadata')
    times = list(map(int, list(lst_s.keys())))
    times.sort()
    print("There are", len(times), "sample times at", times[1] - times[0], "second intervals")
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    time_key = str(times[0])

    # parse the substation metadata for 2 things of specific interest
    print("\nSubstation Metadata for", len(lst_s[time_key]), "objects")
    for key, val in meta_s.items():
        print(key, val['index'], val['units'])
        if key == 'real_power_avg':
            SUB_POWER_IDX = val['index']
            SUB_POWER_UNITS = val['units']
        elif key == 'real_power_losses_avg':
            SUB_LOSSES_IDX = val['index']
            SUB_LOSSES_UNITS = val['units']

    # create a NumPy array of all metrics for the substation
    data_s = np.empty(shape=(len(sub_keys), len(times), len(lst_s[time_key][sub_keys[0]])), dtype=np.float)
    print("\nConstructed", data_s.shape, "NumPy array for Substations")
    j = 0
    for key in sub_keys:
        i = 0
        for t in times:
            ary = lst_s[str(t)][sub_keys[j]]
            data_s[j, i, :] = ary
            i = i + 1
        j = j + 1

    # display some averages
    print("Maximum power =", data_s[0, :, SUB_POWER_IDX].max(), SUB_POWER_UNITS)
    print("Average power =", data_s[0, :, SUB_POWER_IDX].mean(), SUB_POWER_UNITS)
    print("Average losses =", data_s[0, :, SUB_LOSSES_IDX].mean(), SUB_LOSSES_UNITS)
    # endregion

    # read the other JSON files; their times (hrs) should be the same
    # region:Collecting House Data
    lp_h = open(name_root + "_metrics_house.json").read()
    lst_h = json.loads(lp_h)
    lst_h.pop('StartTime')
    meta_h = lst_h.pop('Metadata')
    print("\nHouse Metadata for", len(lst_h[time_key]), "objects")
    for key, val in meta_h.items():
        print(key, val['index'], val['units'])
        if key == 'air_temperature_max':
            HSE_AIR_MAX_IDX = val['index']
            HSE_AIR_MAX_UNITS = val['units']
        elif key == 'air_temperature_min':
            HSE_AIR_MIN_IDX = val['index']
            HSE_AIR_MIN_UNITS = val['units']
        elif key == 'air_temperature_avg':
            HSE_AIR_AVG_IDX = val['index']
            HSE_AIR_AVG_UNITS = val['units']
        elif key == 'hvac_load_avg':
            HVAC_LOAD_AVG_IDX = val['index']
            HVAC_LOAD_AVG_UNITS = val['units']
        elif key == 'total_load_avg':
            TOTAL_LOAD_AVG_IDX = val['index']
            TOTAL_LOAD_AVG_UNITS = val['units']
        elif key == 'waterheater_load_avg':
            WH_AVG_IDX = val['index']
        elif key == 'air_temperature_deviation_cooling':
            DEV_COOL_IDX = val['index']
        elif key == 'air_temperature_deviation_heating':
            DEV_HEAT_IDX = val['index']

    data_h = np.empty(shape=(len(hse_keys), len(times), len(lst_h[time_key][hse_keys[0]])), dtype=np.float)
    print("\nConstructed", data_h.shape, "NumPy array for Houses")
    j = 0
    for key in hse_keys:
        i = 0
        for t in times:
            ary = lst_h[str(t)][hse_keys[j]]
            data_h[j, i, :] = ary
            i = i + 1
        j = j + 1

    # print('average all house temperatures Noon-8 pm first day:', data_h[:, 144:240, HSE_AIR_AVG_IDX].mean())
    # endregion
    # House collection ended

    # region Collecting Billing Meter Data
    lp_m = open(name_root + "_metrics_billing_meter.json").read()
    lst_m = json.loads(lp_m)
    lst_m.pop('StartTime')
    meta_m = lst_m.pop('Metadata')
    nBillingMeters = 0
    if not lst_m[time_key] is None:
        nBillingMeters = len(lst_m[time_key])
    print('\nBilling Meter Metadata for', nBillingMeters, 'objects')
    for key, val in meta_m.items():
        print(key, val['index'], val['units'])
        if key == 'voltage_max':
            MTR_VOLT_MAX_IDX = val['index']
            MTR_VOLT_MAX_UNITS = val['units']
        elif key == 'voltage_min':
            MTR_VOLT_MIN_IDX = val['index']
            MTR_VOLT_MIN_UNITS = val['units']
        elif key == 'voltage12_max':
            MTR_VOLT12_MAX_IDX = val['index']
            MTR_VOLT12_MAX_UNITS = val['units']
        elif key == 'voltage12_min':
            MTR_VOLT12_MIN_IDX = val['index']
            MTR_VOLT12_MIN_UNITS = val['units']
        elif key == 'voltage_unbalance_max':
            MTR_VOLTUNB_MAX_IDX = val['index']
            MTR_VOLTUNB_MAX_UNITS = val['units']
        elif key == 'real_power_avg':
            MTR_REAL_POWER_AVG = val['index']

    if nBillingMeters > 0:
        data_m = np.empty(shape=(len(mtr_keys), len(times), len(lst_m[time_key][mtr_keys[0]])), dtype=np.float)
        print('\nConstructed', data_m.shape, 'NumPy array for Meters')
        j = 0
        for key in mtr_keys:
            i = 0
            for t in times:
                ary = lst_m[str(t)][mtr_keys[j]]
                data_m[j, i, :] = ary
                i = i + 1
            j = j + 1
    # endregion

    # region Collecting Inverter Data
    lp_i = open(name_root + "_metrics_inverter.json").read()
    lst_i = json.loads(lp_i)
    lst_i.pop('StartTime')
    meta_i = lst_i.pop('Metadata')
    # print("\nInverter Metadata for", len(lst_i[time_key]), "objects")
    for key, val in meta_i.items():
        print(key, val['index'], val['units'])
        if key == 'real_power_avg':
            INV_P_AVG_IDX = val['index']
            INV_P_AVG_UNITS = val['units']
        elif key == 'reactive_power_avg':
            INV_Q_AVG_IDX = val['index']
            INV_Q_AVG_UNITS = val['units']
    if lst_i[time_key]:
        inv_keys = list(lst_i[time_key].keys())  # TODO: inv_keys extracted earlier at line 49 is not correct
        inv_keys.sort()
        data_i = np.empty(shape=(len(inv_keys), len(times), len(lst_i[time_key][inv_keys[0]])), dtype=np.float)
        print("\nConstructed", data_i.shape, "NumPy array for Inverters")
        j = 0
        for key in inv_keys:
            i = 0
            for t in times:
                ary = lst_i[str(t)][inv_keys[j]]
                data_i[j, i, :] = ary
                i = i + 1
            j = j + 1
    # endregion

    # #Collecting outside air temperature from weather agent
    out_temp = []
    with open('../weather_Substation_' + dso_num + '/weather.dat', mode='r') as csv_file:
        for i in range(1):
            next(csv_file)
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            if row[0] == start_time:
                out_temp.append(row[1])
                break
        for row in csv_reader:
            out_temp.append(row[1])
        out_temp = np.array(out_temp)
        out_temp = out_temp.astype(np.float)
        # print(out_temp)

    # out_temp=[]
    # with open("recorder_outside_temperature.csv", mode='r') as csv_file:
    #     for i in range(9):
    #         next(csv_file)
    #     csv_reader = csv.reader(csv_file)
    #     #csv_data = [csv_file for csv_file in csv_reader]
    #     for row in csv_reader:
    #         #print({row[1]})
    #         out_temp.append(row[1])
    #         #print('out**')
    #     out_temp = np.array(out_temp)
    #     out_temp = out_temp.astype(np.float)
    #     print(out_temp)
    #
    # in_temp=[]
    # with open('recorder_air_temperature.csv', mode='r') as csv_file:
    #     for i in range(9):
    #         next(csv_file)
    #     csv_reader = csv.reader(csv_file)
    #     #csv_data = [csv_file for csv_file in csv_reader]
    #     for row in csv_reader:
    #         #print({row[1]})
    #         in_temp.append(row[10])
    #         #print('out**')
    #     in_temp = np.array(in_temp)
    #     in_temp = in_temp.astype(np.float)
    #     #print(in_temp)
    #
    # set_pt=[]
    # with open('recorder_cooling_setpoint.csv', mode='r') as csv_file:
    #     for i in range(9):
    #         next(csv_file)
    #     csv_reader = csv.reader(csv_file)
    #     #csv_data = [csv_file for csv_file in csv_reader]
    #     for row in csv_reader:
    #         #print({row[1]})
    #         set_pt.append(row[10])
    #         #print('out**')
    #     set_pt = np.array(set_pt)
    #     set_pt = set_pt.astype(np.float)
    #     #print(in_temp)

    # fl_area=[]
    # with open('floor_area.csv', mode='r') as csv_file:
    #     for i in range(9):
    #         next(csv_file)
    #     csv_reader = csv.reader(csv_file)
    #     for row in csv_reader:
    #         row.pop(0)
    #         break
    #     fl_area = np.array(row)
    #     fl_area = fl_area.astype(np.float)
    #
    # hvac_oversize = []
    # with open('hvac_oversize.csv', mode='r') as csv_file:
    #     for i in range(9):
    #         next(csv_file)
    #     csv_reader = csv.reader(csv_file)
    #     for row in csv_reader:
    #         row.pop(0)
    #         break
    #     hvac_oversize = np.array(row)
    #     hvac_oversize = hvac_oversize.astype(np.float)

    discarded_hours = 24 * 2  # discarded hours
    discard_secs = discarded_hours * 60 * 60  # first discard_secs should be discarded while plotting
    for l in times:
        if l >= discard_secs:
            hrs_start = times.index(l)
            break
    # hrs_start = discard_secs/60/(hrs[1]-hrs[0])
    hrs_start = int(hrs_start)
    hrs = hrs - discard_secs / 3600
    hrs = hrs[hrs_start:]

    # Plotting temperatures via csv files with gld time resolution
    # plt.plot(np.linspace(0, 48, len(out_temp)), out_temp, label='outside')
    # plt.plot(np.linspace(0, 48, len(in_temp)), in_temp, label='inside')
    # plt.plot(np.linspace(0, 48, len(set_pt)), set_pt, label='set point')
    # plt.xlabel("hours")
    # plt.ylabel("F (degree)")
    # plt.title("Temperatures Profile due to HVAC")
    # plt.legend(loc='best')
    # plt.show()

    # display an aggregated plot
    fig1, ax1 = plt.subplots(2, 2, sharex='col')

    hvac_load = np.sum(data_h, axis=0)[:, HVAC_LOAD_AVG_IDX]
    wh_load = np.sum(data_h, axis=0)[:, WH_AVG_IDX]
    total_load = np.sum(data_h, axis=0)[:, TOTAL_LOAD_AVG_IDX]
    mtr_load = np.sum(data_m, axis=0)[:, MTR_REAL_POWER_AVG] / 1000
    sub_load = data_s[0, :, SUB_POWER_IDX] / 1000
    sub_losses = data_s[0, :, SUB_LOSSES_IDX] / 1000
    net_load = hvac_load + wh_load
    if lst_i[time_key]:
        inv_load = np.sum(data_i, axis=0)[:, INV_P_AVG_IDX] / 1000
        inv_load_var = np.sum(data_i, axis=0)[:, INV_Q_AVG_IDX] / 1000
        net_load = hvac_load + wh_load + inv_load

    # estimating % of devices in ON state at each time
    hvac_on_per = np.count_nonzero(data_h[:, :, HVAC_LOAD_AVG_IDX], 0) / len(data_h[:, 0, HVAC_LOAD_AVG_IDX]) * 100
    wh_on_per = np.count_nonzero(data_h[:, :, WH_AVG_IDX], 0) / len(data_h[:, 0, WH_AVG_IDX]) * 100

    ax1[0, 0].plot(hrs, hvac_load[hrs_start:], label="hvac")
    ax1[0, 0].plot(hrs, wh_load[hrs_start:], label="waterheater")
    ax1[0, 0].plot(hrs, total_load[hrs_start:] - hvac_load[hrs_start:] - wh_load[hrs_start:], label="ZIP")
    ax1[0, 0].plot(hrs, total_load[hrs_start:], label="total")
    # ax1[0,0].plot(hrs, mtr_load[hrs_start:], "k--", label="net meter",)
    if lst_i[time_key]:
        ax1[0, 0].plot(hrs, -inv_load[hrs_start:], label="inverter_real")
        ax1[0, 0].plot(hrs, -inv_load_var[hrs_start:], label="inverter_var")
        ax1[0, 0].plot(hrs, total_load[hrs_start:] - inv_load[hrs_start:], label="total+inv")
        ax1[0, 1].plot(hrs, -inv_load[hrs_start:], label="Total DERs")
    ax1[0, 0].set_ylabel("kW")
    ax1[0, 0].set_title("Load Composition")
    ax1[0, 0].legend(loc='best')

    ax1[0, 1].plot(hrs, total_load[hrs_start:], label="Total Load")
    ax1[0, 1].plot(hrs, sub_losses[hrs_start:], color="red", label="Total Losses")
    ax1[0, 1].plot(hrs, sub_load[hrs_start:], color="blue", label="Net Load")
    ax1[0, 1].set_ylabel("kW")
    ax1[0, 1].set_title("Substation Real Power at " + sub_keys[0])
    ax1[0, 1].legend(loc='best')

    # avg1 = (data_h[:, :, HSE_AIR_AVG_IDX]).squeeze()
    # avg2 = avg1.mean(axis=0)
    # ax1[1, 0].plot(hrs, avg2[hrs_start:], color="red", label="Average_All_Houses")
    # #ax1[1, 0].plot(hrs, out_temp[discard_mins*60:len(out_temp):300], 'k--', label="outside")
    # ax1[1, 0].set_ylabel('degF')
    # ax1[1, 1].set_xlabel("Hours")
    # ax1[1, 0].set_title('Average Temperature over All Houses')
    # ax1[1, 0].legend(loc='best')

    for i in range(len(hse_keys)):
        ax1[1, 0].plot(hrs, data_h[i, hrs_start:, DEV_COOL_IDX], color="black")
        # ax1[1, 0].plot(hrs, data_h[i, hrs_start:, DEV_COOL_IDX], color="black", label="cooling setpoint")
    # ax1[1, 0].plot(np.linspace(0, 24, len(out_temp)), out_temp, label='outside air temp')
    ax1[1, 0].plot(hrs, out_temp[hrs_start + 1:hrs_start + 1 + len(hrs)], label='outside air temp')
    ax1[1, 0].set_title("Cooling setpoints for all HVAC units")
    ax1[1, 0].set_ylabel("Farenhite")
    ax1[1, 0].set_xlabel("hours")
    ax1[1, 0].legend(loc='best')

    # ax1[1, 0].plot(hrs, hvac_on_per[hrs_start:], label="HVAC")
    # ax1[1, 0].plot(hrs, wh_on_per[hrs_start:], label="WH")
    # ax1[1, 0].set_xlabel("Hours")
    # ax1[1, 0].set_ylabel("% of Devices ON")
    # ax1[1, 0].set_title("Percentage of HVAC and WH Devices ON")
    # ax1[1, 0].legend(loc='best')

    i = 0
    for key in mtr_keys:
        nominal_v = get_nominal_voltage(data_m[i, hrs_start, MTR_VOLT_MIN_IDX])
        ax1[1, 1].plot(hrs, data_m[i, hrs_start:, MTR_VOLT_MIN_IDX] / nominal_v, color="blue", label="Min")
        ax1[1, 1].plot(hrs, data_m[i, hrs_start:, MTR_VOLT_MAX_IDX] / nominal_v, color="red", label="Max")
        i = i + 1
    ax1[1, 1].plot(hrs, np.ones(len(hrs)) * 0.95, 'k--')
    ax1[1, 1].plot(hrs, np.ones(len(hrs)) * 1.05, 'k--')
    ax1[1, 1].set_xlabel("Hours")
    ax1[1, 1].set_ylabel("Voltage (pu)")
    ax1[1, 1].set_title("Meter Voltages at all Houses")
    # ax1[1, 1].legend(loc='best')
    # plt.show()

    # fig, ax = plt.subplots(2, 2, sharex='col')
    # vabase = diction['inverters'][inv_keys[0]]['rated_W']
    # print ("Inverter base power =", vabase)
    # ax[0,1].plot(data_i[0,:,INV_P_AVG_IDX] / vabase, color="blue", label="Real")
    # ax[0,1].plot(data_i[0,:,INV_Q_AVG_IDX] / vabase, color="red", label="Reactive")
    # ax[0,1].set_ylabel("perunit")
    # ax[0,1].set_title ("Inverter Power at " + inv_keys[0])
    # ax[0,1].legend(loc='best')

    # ax[0,1].plot(hrs, data_m[0,:,MTR_VOLTUNB_MAX_IDX], color="red", label="Max")
    # ax[0,1].set_ylabel("perunit")
    # ax[0,1].set_title ("Voltage Unbalance at " + mtr_keys[0])

    # Plotting at one house
    fig, ax = plt.subplots(2, 2, sharex='col')
    house_key = hse_keys.index('R5_12_47_3_tn_5_hse_1')
    meter_key = mtr_keys.index('R5_12_47_3_tn_5_mtr_1')
    if lst_i[time_key]:
        inv_key = inv_keys.index('R5_12_47_3_tn_5_ibat_2')
        ax[0, 1].plot(hrs, data_i[inv_key, hrs_start:, INV_P_AVG_IDX] / 1000, label="inv P")
        ax[0, 1].plot(hrs, data_i[inv_key, hrs_start:, INV_Q_AVG_IDX] / 1000, label="inv Q")
        # ax[0, 1].plot(hrs, data_h[house_key, hrs_start:, TOTAL_LOAD_AVG_IDX], label="total")
        ax[0, 1].set_ylabel('kW')
        ax[0, 1].set_title("Inverter power at " + inv_keys[inv_key])
        ax[0, 1].legend(loc='best')

    ax[0, 0].plot(hrs, data_h[house_key, hrs_start:, HVAC_LOAD_AVG_IDX], label="hvac")
    # ax[0,0].plot(hrs, data_h[house_key, hrs_start:, WH_AVG_IDX], label="wh")
    ax[0, 0].plot(hrs, data_h[house_key, hrs_start:, TOTAL_LOAD_AVG_IDX], label="total")
    # ax[0,0].plot(hrs, -data_i[house_key, hrs_start:, INV_P_AVG_IDX] / 1000, label="inverter")
    # ax[0,0].plot(hrs, data_m[meter_key, hrs_start:, MTR_REAL_POWER_AVG] / 1000, label="net meter")
    # ax[0,0].plot(hrs, data_h[house_key, hrs_start:, TOTAL_LOAD_AVG_IDX]-data_i[house_key, hrs_start:, INV_P_AVG_IDX]/1000, label="total - inv")
    ax[0, 0].set_ylabel("kW")
    ax[0, 0].set_title("Load Profiles at " + hse_keys[house_key])
    ax[0, 0].legend(loc='best')

    if nBillingMeters > 0:
        ax[1, 0].plot(hrs, np.ones(len(hrs)) * 0.95, 'k--')
        ax[1, 0].plot(hrs, np.ones(len(hrs)) * 1.05, 'k--')
        nominal_v = get_nominal_voltage(data_m[meter_key, hrs_start, MTR_VOLT_MIN_IDX])
        ax[1, 0].plot(hrs, data_m[meter_key, hrs_start:, MTR_VOLT_MAX_IDX] / nominal_v, color="blue", label="Max LN")
        ax[1, 0].plot(hrs, data_m[meter_key, hrs_start:, MTR_VOLT_MIN_IDX] / nominal_v, color="red", label="Min LN")
        # ax[1, 0].plot(hrs, data_m[0, :, MTR_VOLT12_MAX_IDX], color="green", label="Max LL")
        # ax[1, 0].plot(hrs, data_m[0, :, MTR_VOLT12_MIN_IDX], color="magenta", label="Min LL")
        ax[1, 0].set_xlabel("Hours")
        ax[1, 0].set_ylabel("Voltage (pu)")
        ax[1, 0].set_title("Meter Voltages at " + mtr_keys[meter_key])
        ax[1, 0].legend(loc='best')
    else:
        ax[1, 0].set_title('No Billing Meters to Plot')

    ax[1, 1].plot(hrs, data_h[house_key, hrs_start:, HSE_AIR_AVG_IDX], color="blue", label="Mean")
    ax[1, 1].plot(hrs, data_h[house_key, hrs_start:, HSE_AIR_MIN_IDX], color="red", label="Min")
    ax[1, 1].plot(hrs, data_h[house_key, hrs_start:, HSE_AIR_MAX_IDX], color="green", label="Max")
    ax[1, 1].plot(hrs, data_h[house_key, hrs_start:, DEV_COOL_IDX], color="black", label="cooling setpoint")
    # for i in range(len(hse_keys)):
    #     ax[1, 1].plot(hrs, data_h[i, :, DEV_COOL_IDX], color="black", label="cooling setpoint")
    ax[1, 1].plot(hrs, data_h[house_key, hrs_start:, DEV_HEAT_IDX], color="black", label="heating setpoint")
    # ax[1, 1].plot(hrs,out_temp[discard_mins*60:len(out_temp):300], 'b--', label="outside")
    ax[1, 1].set_xlabel("Hours")
    ax[1, 1].set_ylabel(HSE_AIR_AVG_UNITS)
    ax[1, 1].set_title("House Air at " + hse_keys[house_key])
    ax[1, 1].legend(loc='best')

    # plotting inverter battery performance
    if lst_i[time_key]:
        fig, ax_in = plt.subplots(2, 1, sharex='col')
        inv_key = inv_keys.index('R5_12_47_3_tn_5_ibat_2')
        ax_in[0].plot(hrs, data_i[inv_key, hrs_start:, INV_P_AVG_IDX] / 1000, label="inv P")
        ax_in[0].plot(hrs, data_i[inv_key, hrs_start:, INV_Q_AVG_IDX] / 1000, label="inv Q")
        ax_in[0].set_ylabel('kW')
        ax_in[0].set_xlabel('Time (hour')
        ax_in[0].set_title("Inverter power at " + inv_keys[inv_key])
        ax_in[0].legend(loc='best')
        ax_in[0].grid(True)
        ax_in[1].plot(hrs, inv_load[hrs_start:], label="inverter_real")
        ax_in[1].plot(hrs, inv_load_var[hrs_start:], label="inverter_var")
        ax_in[1].set_ylabel('kW')
        ax_in[1].set_title("Aggregated Inverter Power")
        ax_in[1].legend(loc='best')
        ax_in[1].set_xlabel('Time (hour')
        ax_in[1].grid(True)

    # fig2, ax2 = plt.subplots()
    # for i in range(len(hse_keys)):
    #     ax2.plot(hrs, data_h[i, hrs_start:, DEV_COOL_IDX], color="black")
    #     # ax2.plot(hrs, data_h[i, hrs_start:, DEV_COOL_IDX], color="black", label="cooling setpoint")
    # ax2.plot(np.linspace(0, 24, len(out_temp)), out_temp, label='outside air temp')
    # ax2.set_title("Cooling setpoints for all HVAC units")
    # ax2.set_ylabel("Farenhite")
    # ax2.set_xlabel("hours")
    # ax2.legend(loc='best')

    # fig3, ax3 = plt.subplots()
    # ax3.scatter(fl_area, hvac_oversize, color="black", label="")
    # ax3.set_xlabel("Floor area")
    # ax3.set_ylabel("Oversizing factor of hvac")
    # ax3.set_title("HVAC oversizing with respect to floor area")

    plt.show()
    #    fig1.savefig('Figures\ aggregated.svg')
    #    fig.savefig('Figures\ individual.svg')
    fig1.savefig('Figures\ aggregated.png')
    fig.savefig('Figures\ individual.png')
