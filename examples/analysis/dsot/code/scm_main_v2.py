import copy
import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import cvxpy as cp
import random
import multiprocessing
from multiprocessing import Pool


def plot_scm_results(ev_demand_recorder, xfmr_demand, soc_record, lambda_c, xfmr_loading, n_batt, n_intervals,
                     num_ports):
    plt.subplot(1, 3, 1)
    plt.plot(xfmr_loading, 'g--o')
    _legend = ['xfmr-base']
    color_ev_p = []
    for k in range(n_batt):
        _legend.append('batt_' + str(k))
        color = [random.random(), random.random(), random.random()]
        color_ev_p.append(color)
        plt.plot(ev_demand_recorder[k], color=color)
    plt.plot(xfmr_demand, 'r--.')
    _legend.append('xfmr-EV')
    plt.xlabel('Time in Hours')
    plt.ylabel('Transformer Flow and EV Demand')
    plt.legend(_legend)

    plt.subplot(1, 3, 2)
    for k in range(n_batt):
        plt.plot(soc_record[k], color=color_ev_p[k])
    plt.xlabel('Time in Hours')
    plt.ylabel('Battery SoC')
    plt.legend(_legend[1:-1])

    plt.subplot(1, 3, 3)
    n_ports_used = []
    for t in range(n_intervals):
        s = 0
        for idx in range(n_batt):
            s += lambda_c[(idx, t)].value
        n_ports_used.append(s)
    plt.plot(n_ports_used, 'g--o')
    plt.plot([num_ports] * n_intervals, 'r--')
    plt.xlabel('Time in Hours')
    plt.ylabel('Number of Ports Used')
    plt.show()


def ev_schedule(ev_charger_availability, ev_cap_charger, ev_e_rated, energy_depleted, 
                soc_min, soc_max, eff, soc_init, n_batt, n_intervals, xfmr_loading, num_ports,
                controlled_demand_xfmrs, controlled_demand_evs, xfmr_index, xfmr_dict, xfmr_rating,
                xfmr_dict2,sens_flag, threshold_cutoff, smooth, soc_per_hour, soc_dict, energy_dict, p_batt_c_dict, deplete_per_unavailable_hour):

    # Define Optimization Variables
    soc = cp.Variable((n_batt, n_intervals), integer=False, name='soc')
    p_batt_c = cp.Variable((n_batt, n_intervals), integer=False, name='p_batt_c')
    lambda_c = cp.Variable((n_batt, n_intervals), boolean=True, name='lambda_c')
    xfmr_flow = cp.Variable(n_intervals, integer=False, name='xfmr_flow')
    xfmr_flow_mod = cp.Variable(n_intervals, integer=False, name='xfmr_flow_mod')
    b = cp.Variable((n_batt, n_intervals), boolean=True, name='b')
    M = 1000.0

    # n_intervals = 5  # Avijit: to stop simulation at a specific interval.

    # Objective is to maximize SoC of EV battery subject to transformer loading
    # Obj 1: Max Power drawn by EVs to increase their SoC for every time stamp
    objective = sum(-10 * soc[idx][t] for idx in range(n_batt) for t in range(n_intervals))
    # Obj 2: Avoid multiple charging instances
    # objective += sum(10 * lambda_c[idx][t] for idx in range(n_batt) for t in range(n_intervals))
    # if smooth:
    #     objective += sum(-10 * lambda_c[idx][t] for idx in range(n_batt) for t in range(n_intervals))
    if sens_flag == "relax":
        # Obj 3: Put transformer kva rating exceedance as penalty since it is not always avoidable
        objective += 100 * sum(xfmr_flow_mod[t] for t in range(n_intervals))

    constraints = []
    for idx in range(n_batt):
        for t in range(n_intervals):
            # Min and Max SoC
            constraints.append(soc[idx][t] >= soc_min[idx])
            constraints.append(soc[idx][t] <= soc_max[idx])

            # charging power depends on availability (lambda_c) and battery size (ev_cap)
            constraints.append(p_batt_c[idx][t] >= 0)
            constraints.append(p_batt_c[idx][t] <= lambda_c[idx][t] * ev_cap_charger[idx])
            if t > 0:
                if ev_charger_availability[idx][t] == 0:
                    # TODO: idea is all vehicle are depreciated to 70% of their storage capacity at the end.
                    # no matter their discharge rate, we make soc for unavailability to be 0.3
                    # constraints.append(soc[idx][t] == 0.3)
                    # constraints.append(
                    #     soc[idx][t] == soc[idx][t - 1] - (energy_depleted[idx] / (ev_e_rated[idx]))* (ev_charger_availability[idx][t+1]))

                    constraints.append(
                        soc[idx][t] == soc[idx][t - 1] - deplete_per_unavailable_hour[idx][t] / (ev_e_rated[idx]))
                    # if ev_charger_availability[idx][t+1] > 0:
                    #     constraints.append(soc[idx][t] == soc[idx][t-1]-(energy_depleted[idx]/ (ev_e_rated[idx]*eff[idx])))
                    # else:
                    #     constraints.append(soc[idx][t] == soc[idx][t-1])
                    constraints.append(p_batt_c[idx][t] == 0)
                else:

                    if smooth:
                        # soc per hour constraint for smooth
                        constraints.append(soc[idx][t] <= soc[idx][t - 1] + soc_per_hour[idx][t])

                    # SoC depends on efficiency and charge rate
                    constraints.append(soc[idx][t] == soc[idx][t - 1] + ((p_batt_c[idx][t-1]*eff[idx])/ev_e_rated[idx]))

            else:
                constraints.append(soc[idx][t] == soc_init[idx])
            # Only charging decision is true for available times
            constraints.append(lambda_c[idx][t] <= ev_charger_availability[idx][t])

    for t in range(n_intervals):
        # Port constraints. Number of EVs that can be charged depends on available ports
        constraints.append(num_ports >= sum(lambda_c[idx][t] for idx in range(n_batt)))

        # Transformer loading constraints. Forecasted plus EV load
        constraints.append(xfmr_flow[t] == xfmr_loading[t] + sum(p_batt_c[idx][t] for idx in range(n_batt)))

        # Try to maintain xfmr loading within limit
        if sens_flag == "tight":
            constraints.append(xfmr_flow[t] <= threshold_cutoff*xfmr_rating)
        elif sens_flag == "relax":
            constraints.append(xfmr_flow_mod[t] >= xfmr_flow[t] - threshold_cutoff*xfmr_rating)
            constraints.append(xfmr_flow_mod[t] >= -(xfmr_flow[t] - threshold_cutoff*xfmr_rating))

    problem = cp.Problem(cp.Minimize(objective), constraints)
    print(f"Attempting to solve transformer name = {xfmr_index}")
    # try:
    problem.solve(verbose=False, solver=cp.MOSEK) # solver=cp.ECOS, feastol=1e-2
    # problem.solve(solver='SCIPY', verbose=True, scipy_options={'maxiter': 10000, 'tol':1e-2})
    # except:
    #     pass
    print(f"Optimization status at transformer name = {xfmr_index}:", problem.status)

    # Collect Optimization Results
    ev_demand_recorder = {}
    soc_record = {}
    energy_record = {}
    pbat_record = {}
    for k in range(n_batt):
        if k not in ev_demand_recorder:
            ev_demand_recorder[k] = []
            soc_record[k] = []
            energy_record[k] = []
            pbat_record[k] = []
    _xfmr_demand = []
    _ev_demand = []
    _energy_at_times = []
    for t in range(n_intervals):
        s = 0
        energy_sum = 0
        for idx in range(n_batt):
            # print(p_batt_c[(idx, t)].value)
            if p_batt_c[(idx, t)].value is None:
                toadd = 0
                toadd2 = 0
            else:
                toadd = p_batt_c[(idx, t)].value
                toadd2 = soc[(idx, t)].value
            ev_demand_recorder[idx].append(toadd)
            s += toadd

            energy_sum += ev_e_rated[idx]*toadd2

        _ev_demand.append(s)
        _energy_at_times.append(energy_sum)
        _xfmr_demand.append(xfmr_flow[t].value)
    s = 0
    for idx in range(n_batt):
        for t in range(n_intervals):
            if p_batt_c[(idx, t)].value is None:
                toadd = 0
                toadd2 = 0
                toadd3 = 0
            else:
                toadd = p_batt_c[(idx, t)].value
                toadd2 = soc[(idx, t)].value
                toadd3 = lambda_c[(idx, t)].value
            soc_record[idx].append(toadd2)
            energy_record[idx].append(ev_e_rated[idx]*toadd2)
            pbat_record[idx].append(toadd)
            s += toadd3

    # changing time to 8 AM start time
    xfmr_demand = _xfmr_demand  # _xfmr_demand[7:] + _xfmr_demand[:7]
    ev_demand = _ev_demand  # _ev_demand[7:] + _ev_demand[:7]
    energy_at_times = _energy_at_times
    # plot_scm_results(ev_demand_recorder, xfmr_demand, soc_record, lambda_c, xfmr_loading, n_batt, n_intervals,
    #                  num_ports)
    # controlled_demand_xfmrs[xfmr_index] = xfmr_demand
    # controlled_demand_evs[xfmr_index] = ev_demand
    xfmr_dict[xfmr_index] = xfmr_demand
    xfmr_dict2[xfmr_index] = ev_demand
    soc_dict[xfmr_index] = soc_record  # may be needed for future but energy directly gives better information same as
    # SOC
    energy_dict[xfmr_index] = energy_at_times  # needed for results
    p_batt_c_dict[xfmr_index] = pbat_record  # not needed, this is same as _ev_demand when sum for every time stamp
    # across all available EVs. Here I am just saving them separately.


def scm_ev(df_ev, df_port, xfmr_loading_df, xfmr_rating_info, batch_size, n_intervals, f1, f2, sens_flag, threshold_cutoff, smooth, f3):

    # Initialize variables for optimization
    # port_to_vehicle = df_port.to_dict()

    port_to_vehicle = dict(zip(df_port.Location, df_port.NumberofPorts))

    # timestamp starts from 8 AM
    _timestamp = xfmr_loading_df['# timestamp'].tolist()
    timestamp = _timestamp  # _timestamp[7:] + _timestamp[:7]
    days_here =xfmr_loading_df['day'].tolist()
    hours_here = xfmr_loading_df['hour'].tolist()
    # initialize variables to store data
    controlled_demand_xfmrs = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}
    controlled_demand_evs = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}

    all_energy_dict = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}
    all_demand_dict = {}
    time_dict_here = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}

    # parallel processor parameters
    jobs = []
    manager = multiprocessing.Manager()
    xfmr_dict = manager.dict()
    xfmr_dict2 = manager.dict()
    soc_dict = manager.dict()
    energy_dict = manager.dict()
    p_batt_c_dict = manager.dict()

    xfmr_loading_df = xfmr_loading_df.drop(columns=['# timestamp', 'day', 'hour'])

    # Do in a batch instead of all xfmrs at once
    xfrmr_name_list_here = xfmr_loading_df.columns.tolist()
    total_xfmrs = len(xfrmr_name_list_here)
    for batch in range(0, total_xfmrs, batch_size):
        # for k in xfmr_loading_df.columns.tolist():
        for ktoo in range(batch, min(batch + batch_size, total_xfmrs)):
            # ktoo = 153  # Avijit: uncomment this to always test a specific transformer that you are debugging.
            k = xfrmr_name_list_here[ktoo]
            if k == '2643':
                dkj = 1
            evs_allocation_df = df_ev.loc[df_ev['Location'] == float(k)]
            if len(evs_allocation_df) > 0:
                xfmr_loading = (xfmr_loading_df[str(k)] / 1000).tolist()
                # Max vehicle that can charge in a given transformer is based on number of ports
                num_ports = port_to_vehicle[float(k)]

                # gather EVs parameters
                n_batt = len(evs_allocation_df)
                ev_cap_charger = evs_allocation_df['Size of the charger (kw)'].tolist()
                ev_e_rated = evs_allocation_df['Rating of EV battery (kwh)'].tolist()
                soc_min = [x/100 for x in evs_allocation_df['min SOC'].tolist()]
                soc_max = evs_allocation_df['max SOC'].tolist()
                eff = evs_allocation_df['Efficiency of charging'].tolist()
                soc_init = evs_allocation_df['max SOC'].tolist()
                energy_depleted = evs_allocation_df['Daily energy depleted (kwh)'].tolist()


                ev_charger_availability = []
                soc_per_hour = []
                deplete_per_unavailable_hour = []
                for ev_idx in range(n_batt):
                    ev_availability = [1] * 24  #n_intervals
                    start_drive = evs_allocation_df['Reach office (24h)'].tolist()[ev_idx]
                    if (start_drive >= 8) and (start_drive <= 23):
                        start_drive = start_drive - 8
                    else:
                        start_drive = 16 + start_drive
                    end_drive = evs_allocation_df['Reach home (24h)'].tolist()[ev_idx]
                    if (end_drive >= 8) and (end_drive <= 23):
                        end_drive = end_drive - 8
                    else:
                        end_drive = 16 + end_drive
                    if start_drive < end_drive:    
                        ev_availability[start_drive:end_drive] = [0] * (end_drive - start_drive)
                    else:
                        ev_availability[end_drive:start_drive] = [0] * (start_drive - end_drive)
                    # extend info to several days
                    days_count = n_intervals/24
                    if days_count.is_integer():
                        unavailability_hours = 24 - sum(ev_availability)

                        no_scm_charging_duration = next((i for i, j in enumerate(ev_availability) if not j), None)
                        # total_energy_depleted_at_unavailable_time = unavailability_hours
                        scm_working_hours = 23 - ((no_scm_charging_duration - 1) + unavailability_hours)
                        per_hour = 0.07  # (energy_depleted[ev_idx]/ev_e_rated[ev_idx])/scm_working_hours

                        # diff = soc_max[ev_idx] - soc_min[ev_idx]
                        # per_hour = diff/sum(ev_availability)

                        energy_depleted_per_unavailable_hour = [x/unavailability_hours for x in energy_depleted]
                        ev_charger_availability.append(ev_availability*int(days_count))
                        soc_per_hour.append([x * per_hour for x in ev_charger_availability[ev_idx]])
                        deplete_per_unavailable_hour.append([(1-x) * energy_depleted_per_unavailable_hour[ev_idx] for x in ev_charger_availability[ev_idx]])
                    else:
                        print("There is extra timestamp row in load forecast, expected the load forecast to have"
                              " n_intervals as mutiples of 24 always.. exiting...")
                        exit()

                # # start multiprocessing
                # p = multiprocessing.Process(target=ev_schedule,
                #                             args=(ev_charger_availability, ev_cap_charger, ev_e_rated, energy_depleted,
                #                                   soc_min, soc_max, eff, soc_init, n_batt, n_intervals,
                #                                   xfmr_loading, num_ports, controlled_demand_xfmrs,
                #                                   controlled_demand_evs, k, xfmr_dict,
                #                                   xfmr_rating_info[str(k)], xfmr_dict2, sens_flag, threshold_cutoff, smooth, soc_per_hour, soc_dict, energy_dict, p_batt_c_dict, deplete_per_unavailable_hour))

                # temp fix for residential xfrmrs whose ratings are smaller than peak load (look for xfrmrs = 264 i.e., "feeder1_R2_12_47_1_xfmr_8_set1": 2643, in the input data)
                if max(xfmr_loading) > xfmr_rating_info[str(k)]:  # todo: look at this, fix it in glm side when you can
                    xfmr_rating_info[str(k)] = max(xfmr_loading)*1.1


                ev_schedule(ev_charger_availability, ev_cap_charger, ev_e_rated, energy_depleted,
                                                  soc_min, soc_max, eff, soc_init, n_batt, n_intervals,
                                                  xfmr_loading, num_ports, controlled_demand_xfmrs,
                                                  controlled_demand_evs, k, xfmr_dict,
                                                  xfmr_rating_info[str(k)], xfmr_dict2, sens_flag, threshold_cutoff, smooth, soc_per_hour, soc_dict, energy_dict, p_batt_c_dict, deplete_per_unavailable_hour)

                # jobs.append(p)
                # p.start()


        # for proc in jobs:
        #     proc.join()

        print(f"Finished batch = {batch}/{total_xfmrs/batch_size} ......")

        for xfmr in xfmr_dict:
            controlled_demand_xfmrs[xfmr] = xfmr_dict[xfmr]

        for xfmr in xfmr_dict2:
            controlled_demand_evs[xfmr] = xfmr_dict2[xfmr]

        for xfmr in energy_dict:
            all_energy_dict[xfmr] = energy_dict[xfmr]

        for xfmr in p_batt_c_dict:
            all_demand_dict[xfmr] = p_batt_c_dict[xfmr]



    # with open(f3, 'w') as f:
    #     json.dump(all_energy_dict, f)

    # with open(f4, 'w') as f:
    #     json.dump(all_demand_dict, f)

    # with open("timestamp_info.json", 'w') as f:
    #     json.dump(time_dict_here, f)

    df = pd.DataFrame(controlled_demand_xfmrs)
    df = df.drop(columns=['# timestamp'])
    df.to_csv(f1, index=False)

    df = pd.DataFrame(controlled_demand_evs)
    df = df.drop(columns=['# timestamp'])
    df.to_csv(f2, index=False)

    df = pd.DataFrame(all_energy_dict)
    df = df.drop(columns=['# timestamp'])
    df.to_csv(f3, index=False)

    return df



def main(inventory_filename, grid_forecast_filename, size_of_batch, xfmr_rating_data_filename, f1, f2, sens_flag, threshold_cutoff, smooth, f3):
    # read EV data and Port data
    df_ev_input = pd.read_excel(inventory_filename, sheet_name='main_info')
    df_port_info = pd.read_excel(inventory_filename, sheet_name='locationAndPorts')

    # Base Loading of Transformers
    base_xfmr_loading_df = pd.read_csv(grid_forecast_filename)

    # reduce xfrmrs to optimize
    ev_xfrmr_locations = set(df_ev_input["Location"])  # NOTE: BUG:df_ev_input["Location"].unique() and
    # df_port_info["Location"] are not same!! see --> np.setdiff1d(df_port_info['Location'], df_ev_input['Location'])
    # AND np.setdiff1d(df_ev_input['Location'], df_port_info['Location'])
    all_xfrmr_locations_on_grid = []
    for col in base_xfmr_loading_df.columns:
        if (col != '# timestamp') and (col != 'day') and (col != 'hour'):
            all_xfrmr_locations_on_grid.append(int(float(col)))
    all_xfrmr_locations_on_grid_set = set(all_xfrmr_locations_on_grid)
    check_this = ev_xfrmr_locations.difference(all_xfrmr_locations_on_grid_set)
    if len(check_this) != 0:
        print("found a scenario where there is an ev xfrmr name that is not found in xfrmr names from grid. this should"
              " not be possible, check for bug, exiting...")
        exit()
    columns_to_drop = all_xfrmr_locations_on_grid_set.difference(ev_xfrmr_locations)
    base_xfmr_loading_df = base_xfmr_loading_df.drop(columns=[str(x) for x in list(columns_to_drop)])

    # # TODO: xfmr_rating as 150 for testing. Using dict, Kishan said this will be the format.
    # xfmr_rating_data = {}
    # for k in base_xfmr_loading_df.columns:
    #     xfmr_rating_data[k] = 150

    with open(xfmr_rating_data_filename, 'r') as fp:
        xfmr_rating_data = json.load(fp)


    # # Reduce sim impact: one day sim
    # base_xfmr_loading_df = base_xfmr_loading_df.iloc[0:24]

    # TODO: Time interval for optimization. Currently using the csv file that has 25 interval.
    # I subtracted 1 from the length, because I usually don't trust first output of GridLAB-D
    n_hrs = len(base_xfmr_loading_df)

    # function for SCM
    controlled_demand_evs = scm_ev(df_ev_input, df_port_info, base_xfmr_loading_df, xfmr_rating_data, size_of_batch, n_hrs, f1, f2, sens_flag, threshold_cutoff, smooth, f3)

    # function to verify if any xfrmrs failed its SCM optimization
    df1 = base_xfmr_loading_df.drop(columns=['# timestamp', 'day', 'hour'])
    pre_scm_xfrmr_set = set(df1.columns)
    df2 = controlled_demand_evs.drop(columns=['day', 'hour'])
    post_scm_xfrmr_set = set(df2.columns)
    failed_xfrmrs = pre_scm_xfrmr_set.difference(post_scm_xfrmr_set)

    return [int(float(x)) for x in failed_xfrmrs]

if __name__ == '__main__':

    inventory_filename = "vehicle_master_Large_Year_2042_randmaxsoc_latest.xlsx"  # 'vehicle_master_Large_Year_2040_randmaxsoc.xlsx'
    # inventory_filename = "vehicle_master_Large_Year_2040_randmaxsoc.xlsx"
    grid_forecast_filename = 'AZ_Tucson_Large_grid_forecast_latest.csv'
    # decide on size of batch
    size_of_batch = 50
    xfmr_rating_data_filename = "AZ_Tucson_Large_grid_dummy_to_size_mapping.json"

    f1 = 'controlled_xfmr_demand_smooth_diff_evtimes.csv'

    f2 = 'controlled_ev_demand_smooth_diff_evtimes.csv'

    f3 = 'ev_energy_info_diff_evtimes.csv'

    sens_flag = "tight"  # "tight", "relax"

    threshold_cutoff = 1

    smooth = True

    failed_xfrmrs = main(inventory_filename, grid_forecast_filename, size_of_batch, xfmr_rating_data_filename, f1, f2, sens_flag, threshold_cutoff, smooth, f3)