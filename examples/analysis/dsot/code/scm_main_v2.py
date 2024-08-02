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
import time


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
                xfmr_dict2,sens_flag, threshold_cutoff, smooth, soc_per_hour, soc_dict, energy_dict, p_batt_c_dict,
                deplete_per_unavailable_hour, all_allocated_ev_dayofweek_availability, energy_port_dict,
                n_ports_used_dict):

    # Define Optimization Variables
    soc = cp.Variable((n_batt, n_intervals), integer=False, name='soc')
    p_batt_c = cp.Variable((n_batt, n_intervals), integer=False, name='p_batt_c')
    lambda_c = cp.Variable((n_batt, n_intervals), boolean=True, name='lambda_c')
    xfmr_flow = cp.Variable(n_intervals, integer=False, name='xfmr_flow')
    xfmr_flow_mod = cp.Variable(n_intervals, integer=False, name='xfmr_flow_mod')
    b = cp.Variable((n_batt, n_intervals), boolean=True, name='b')
    M = 1000.0

    # n_intervals = 24  # Avijit: to stop simulation at a specific interval.

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
                # deplete energy when vehicle is driving (first piece of if condition) and if vehicle is available
                # that day at the charging station (second piece of if condition). basically capturing both "time"
                # and "day" of charging.
                if (ev_charger_availability[idx][t] == 0) and (all_allocated_ev_dayofweek_availability[idx][t] == 1):
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
    mydict = {"MSK_DPAR_OPTIMIZER_MAX_TIME": 60}
    problem.solve(verbose=False, solver=cp.MOSEK, mosek_params=mydict) # solver=cp.ECOS, feastol=1e-2
    # problem.solve(solver='SCIPY', verbose=True, scipy_options={'maxiter': 10000, 'tol':1e-2})
    # except:
    #     pass
    print(f"Optimization status at transformer name = {xfmr_index}:", problem.status)

    # Collect Optimization Results
    ev_demand_recorder = {}
    soc_record = {}
    energy_record = {}
    pbat_record = {}
    lambda_c_record = {}
    for k in range(n_batt):
        if k not in ev_demand_recorder:
            ev_demand_recorder[k] = []
            soc_record[k] = []
            energy_record[k] = []
            pbat_record[k] = []
            lambda_c_record[k] = []
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
            lambda_c_record[idx].append(toadd3)
            s += toadd3

    n_ports_used = []
    for t in range(n_intervals):
        s = 0
        for idx in range(n_batt):
            if lambda_c[(idx, t)].value is None:
                toadd = 0
            else:
                toadd = lambda_c[(idx, t)].value
            s += toadd
        n_ports_used.append(s)

    # NOTES:
    # 1. pbat_record: gives the EV demand on grid for all EVs connected to the grid via ports
    # 2. energy_record: gives the total energy of all EVs at any point irrespective of if an EV is connected to a port.
    # 3. energy_record_port: gives the total energy of EVs that are only connected to the grid via port (at any given
    # point of time).
    # 4. n_ports_used: gives the total ports in use under a transformer at any given point of time. This can be used
    # to mention about total number of active sessions
    energy_record_list = []
    for key, value in energy_record.items():
        energy_record_list.append(value)

    energy_record_port = [[x * y for x, y in zip(i, v)] for i, v in
                                zip(ev_charger_availability, energy_record_list)]  # knowingly not using lambda_c
    # because it means vehicle behave exactly as told by SCM versus ev charger availability assumes EVs are still
    # connected to the ports based on the EV availability inputs to SCM (to avoid strong dependency on ev behavior
    # due to SCM).
    energy_record_port_at_times = [sum(i) for i in zip(*energy_record_port)]  # aggrgated energy of all evs connected
    # to a port at any given point of time

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
    energy_port_dict[xfmr_index] = energy_record_port_at_times
    n_ports_used_dict[xfmr_index] = n_ports_used


def scm_ev(df_ev, df_port, xfmr_loading_df, xfmr_rating_info, batch_size, n_intervals, f1, f2, sens_flag,
           threshold_cutoff, smooth, f3, f4, f5, f6):

    # Initialize variables for optimization
    # port_to_vehicle = df_port.to_dict()

    port_to_vehicle = dict(zip(df_port.Location, df_port.NumberofPorts))

    # timestamp starts from 8 AM
    _timestamp = xfmr_loading_df['# timestamp'].tolist()
    timestamp = _timestamp  # _timestamp[7:] + _timestamp[:7]
    days_here =xfmr_loading_df['day'].tolist()
    hours_here = xfmr_loading_df['hour'].tolist()

    # 0-6 --> Monday to Sunday
    dayofweek_info = pd.to_datetime(xfmr_loading_df['# timestamp']).dt.dayofweek.tolist()

    # # initialize variables to store data
    # controlled_demand_xfmrs = {'# timestamp': timestamp, 'day': dayofweek_info, 'hour': hours_here}
    # controlled_demand_evs = {'# timestamp': timestamp, 'day': dayofweek_info,
    #                          'hour': hours_here}
    #
    # all_energy_dict = {'# timestamp': timestamp, 'day': dayofweek_info, 'hour': hours_here}
    # all_demand_dict = {}
    # time_dict_here = {'# timestamp': timestamp, 'day': dayofweek_info, 'hour': hours_here}
    #
    # all_energy_ports = {'# timestamp': timestamp, 'day': dayofweek_info, 'hour': hours_here}
    # all_ports_used = {'# timestamp': timestamp, 'day': dayofweek_info, 'hour': hours_here}

    # initialize variables to store data
    controlled_demand_xfmrs = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}
    controlled_demand_evs = {'# timestamp': timestamp, 'day': days_here,
                             'hour': hours_here}

    all_energy_dict = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}
    all_demand_dict = {}
    time_dict_here = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}

    all_energy_ports = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}
    all_ports_used = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}

    # parallel processor parameters
    jobs = []
    manager = multiprocessing.Manager()
    xfmr_dict = manager.dict()
    xfmr_dict2 = manager.dict()
    soc_dict = manager.dict()
    energy_dict = manager.dict()
    p_batt_c_dict = manager.dict()
    energy_port_dict = manager.dict()
    n_ports_used_dict = manager.dict()
    total_vehicles_at_time_dict = {'# timestamp': timestamp, 'day': days_here, 'hour': hours_here}


    xfmr_loading_df = xfmr_loading_df.drop(columns=['# timestamp', 'day', 'hour'])

    # Do in a batch instead of all xfmrs at once
    xfrmr_name_list_here = xfmr_loading_df.columns.tolist()
    total_xfmrs = len(xfrmr_name_list_here)
    for batch in range(0, total_xfmrs, batch_size):
        # for k in xfmr_loading_df.columns.tolist():
        for ktoo in range(batch, min(batch + batch_size, total_xfmrs)):
            # ktoo = 1  # Avijit: uncomment this to always test a specific transformer that you are debugging.
            k = xfrmr_name_list_here[ktoo]
            # if k == '129':
            #     dkj = 1
            evs_allocation_df = df_ev.loc[df_ev['Location'] == float(k)]

            # short list the evs based on the day of availability
            # create a binary vector (same length as daysofweek/timestamp) with 0 = not available and 1 = available
            all_allocated_ev_dayofweek_availability = []
            for row_index, act_row in evs_allocation_df.iterrows():  # for each EV+
                current_ev_dayofweek_availability = []
                check_category = act_row["Charge category"]
                if act_row["alldaypluggedin"] == 1: # if ev that is parked all day then it is fully charged and
                            # does not cause any ev demand as per the meeting discussion.
                    for d in dayofweek_info:
                        current_ev_dayofweek_availability.append(0)
                else:
                    # d < 4 (mon - thursday) and vehicle category = 0 (means vehicle wants to charge on fri, sat, sun)
                    for d in dayofweek_info:  # for all days in the simulation time
                        if check_category == 0 and d < 4:
                            current_ev_dayofweek_availability.append(0)
                        # d > 4 (fri, sat, sun) and category = 66 (vehicle wants to charge on mon-fri)
                        elif check_category == 66 and d > 4:
                            current_ev_dayofweek_availability.append(0)
                        # vehicle wants to charge a specific day of a week
                        elif check_category >= 1 and check_category <= 7:
                            if check_category - 1 != d:  # checks if the vehicle's specific day matches with the day of
                                # uncontrolled simulation
                                current_ev_dayofweek_availability.append(0)
                            else:
                                current_ev_dayofweek_availability.append(1)
                        else:
                            current_ev_dayofweek_availability.append(1)

                all_allocated_ev_dayofweek_availability.append(current_ev_dayofweek_availability)

            if len(evs_allocation_df) > 0:
                xfmr_loading = ((xfmr_loading_df[str(k)] / 1000)*0.9).tolist()  # xfrmr loading in va converted to kw since EV demand is in kw (for overload comparison purpose in optimization)
                # Max vehicle that can charge in a given transformer is based on number of ports
                num_ports = port_to_vehicle[float(k)]

                # gather EVs parameters
                n_batt = len(evs_allocation_df)
                ev_cap_charger = evs_allocation_df['Size of the charger (kw)'].tolist()
                ev_e_rated = evs_allocation_df['Rating of EV battery (kwh)'].tolist()
                soc_min = [x/100 for x in evs_allocation_df['min SOC'].tolist()]
                soc_max = [x/100 for x in evs_allocation_df['max SOC'].tolist()]
                eff = evs_allocation_df['Efficiency of charging'].tolist()
                soc_init = [x/100 for x in evs_allocation_df['max SOC'].tolist()]
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

                ev_charger_availability2 = [[x * y for x, y in zip(i, v)] for i, v in
                                            zip(ev_charger_availability, all_allocated_ev_dayofweek_availability)]

                total_vehicles_at_times = []
                for t in range(n_intervals):
                    s = 0
                    for idx in range(n_batt):
                        if ev_charger_availability2[idx][t] is None:
                            toadd = 0
                        else:
                            toadd = ev_charger_availability2[idx][t]
                        s += toadd
                    total_vehicles_at_times.append(s)
                total_vehicles_at_time_dict[k] = total_vehicles_at_times

                # start multiprocessing
                p = multiprocessing.Process(target=ev_schedule,
                                            args=(ev_charger_availability2, ev_cap_charger, ev_e_rated,
                                            energy_depleted,
                                                  soc_min, soc_max, eff, soc_init, n_batt, n_intervals,
                                                  xfmr_loading, num_ports, controlled_demand_xfmrs,
                                                  controlled_demand_evs, k, xfmr_dict,
                                                  xfmr_rating_info[str(k)], xfmr_dict2, sens_flag, threshold_cutoff,
                                                  smooth, soc_per_hour, soc_dict, energy_dict, p_batt_c_dict,
                                                  deplete_per_unavailable_hour,
                                                  all_allocated_ev_dayofweek_availability, energy_port_dict,
                                n_ports_used_dict))

                # # temp fix for residential xfrmrs whose ratings are smaller than peak load (look for xfrmrs = 264 i.e., "feeder1_R2_12_47_1_xfmr_8_set1": 2643, in the input data)
                # if max(xfmr_loading) > xfmr_rating_info[str(k)]:  # todo: look at this, fix it in glm side when you can: update:fixed
                #     xfmr_rating_info[str(k)] = max(xfmr_loading)*1.1


                # ev_schedule(ev_charger_availability2, ev_cap_charger, ev_e_rated, energy_depleted,
                #                                   soc_min, soc_max, eff, soc_init, n_batt, n_intervals,
                #                                   xfmr_loading, num_ports, controlled_demand_xfmrs,
                #                                   controlled_demand_evs, k, xfmr_dict,
                #                                   xfmr_rating_info[str(k)], xfmr_dict2, sens_flag, threshold_cutoff,
                #             smooth, soc_per_hour, soc_dict, energy_dict, p_batt_c_dict, deplete_per_unavailable_hour,
                #             all_allocated_ev_dayofweek_availability, energy_port_dict,
                # n_ports_used_dict)

                p.start()
                jobs.append(p)


        for proc in jobs:
            proc.join()

        print(f"Finished batch = {batch}/{total_xfmrs/batch_size} ......")

        for xfmr in xfmr_dict:
            controlled_demand_xfmrs[xfmr] = xfmr_dict[xfmr]

        for xfmr in xfmr_dict2:
            controlled_demand_evs[xfmr] = xfmr_dict2[xfmr]

        for xfmr in energy_dict:
            all_energy_dict[xfmr] = energy_dict[xfmr]

        for xfmr in p_batt_c_dict:
            all_demand_dict[xfmr] = p_batt_c_dict[xfmr]

        for xfmr in energy_port_dict:
            all_energy_ports[xfmr] = energy_port_dict[xfmr]

        for xfmr in n_ports_used_dict:
            all_ports_used[xfmr] = n_ports_used_dict[xfmr]



    # with open(f3, 'w') as f:
    #     json.dump(all_energy_dict, f)

    # with open(f4, 'w') as f:
    #     json.dump(all_demand_dict, f)

    # with open("timestamp_info.json", 'w') as f:
    #     json.dump(time_dict_here, f)

    # n_intervals = 24
    controlled_demand_xfmrs["# timestamp"] = controlled_demand_xfmrs["# timestamp"][:n_intervals]
    controlled_demand_xfmrs["day"] = controlled_demand_xfmrs["day"][:n_intervals]
    controlled_demand_xfmrs["hour"] = controlled_demand_xfmrs["hour"][:n_intervals]
    df = pd.DataFrame(controlled_demand_xfmrs)
    df = df.drop(columns=['# timestamp'])
    df.to_csv(f1, index=False)

    controlled_demand_evs["# timestamp"] = controlled_demand_evs["# timestamp"][:n_intervals]
    controlled_demand_evs["day"] = controlled_demand_evs["day"][:n_intervals]
    controlled_demand_evs["hour"] = controlled_demand_evs["hour"][:n_intervals]
    df = pd.DataFrame(controlled_demand_evs)
    df = df.drop(columns=['# timestamp'])
    df.to_csv(f2, index=False)

    all_energy_dict["# timestamp"] = all_energy_dict["# timestamp"][:n_intervals]
    all_energy_dict["day"] = all_energy_dict["day"][:n_intervals]
    all_energy_dict["hour"] = all_energy_dict["hour"][:n_intervals]
    df = pd.DataFrame(all_energy_dict)
    df = df.drop(columns=['# timestamp'])
    df.to_csv(f3, index=False)

    all_energy_ports["# timestamp"] = all_energy_ports["# timestamp"][:n_intervals]
    all_energy_ports["day"] = all_energy_ports["day"][:n_intervals]
    all_energy_ports["hour"] = all_energy_ports["hour"][:n_intervals]
    df = pd.DataFrame(all_energy_ports)
    df = df.drop(columns=['# timestamp'])
    df.to_csv(f4, index=False)

    all_ports_used["# timestamp"] = all_ports_used["# timestamp"][:n_intervals]
    all_ports_used["day"] = all_ports_used["day"][:n_intervals]
    all_ports_used["hour"] = all_ports_used["hour"][:n_intervals]
    df = pd.DataFrame(all_ports_used)
    df = df.drop(columns=['# timestamp'])
    df.to_csv(f5, index=False)

    total_vehicles_at_time_dict["# timestamp"] = total_vehicles_at_time_dict["# timestamp"][:n_intervals]
    total_vehicles_at_time_dict["day"] = total_vehicles_at_time_dict["day"][:n_intervals]
    total_vehicles_at_time_dict["hour"] = total_vehicles_at_time_dict["hour"][:n_intervals]
    df = pd.DataFrame(total_vehicles_at_time_dict)
    df = df.drop(columns=['# timestamp'])
    df.to_csv(f6, index=False)

    return df



def main(inventory_filename, grid_forecast_filename, size_of_batch, xfmr_rating_data_filename, f1, f2, sens_flag,
         threshold_cutoff, smooth, f3, f4, f5, f6):
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
    # if len(check_this) != 0:
    #     print("found a scenario where there is an ev xfrmr name that is not found in xfrmr names from grid. this should"
    #           " not be possible, check for bug, exiting...")
    #     exit()
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
    controlled_demand_evs = scm_ev(df_ev_input, df_port_info, base_xfmr_loading_df, xfmr_rating_data, size_of_batch,
                                   n_hrs, f1, f2, sens_flag, threshold_cutoff, smooth, f3, f4, f5, f6)

    # function to verify if any xfrmrs failed its SCM optimization
    df1 = base_xfmr_loading_df.drop(columns=['# timestamp', 'day', 'hour'])
    pre_scm_xfrmr_set = set(df1.columns)
    df2 = controlled_demand_evs.drop(columns=['day', 'hour'])
    post_scm_xfrmr_set = set(df2.columns)
    failed_xfrmrs = pre_scm_xfrmr_set.difference(post_scm_xfrmr_set)

    return [int(float(x)) for x in failed_xfrmrs]

if __name__ == '__main__':

    inventory_filename = "vehicle_master_Large_Year_2042_jul31.xlsx"  # 'vehicle_master_Large_Year_2040_randmaxsoc.xlsx'
    # inventory_filename = "vehicle_master_Large_Year_2040_randmaxsoc.xlsx"
    grid_forecast_filename = 'AZ_Tucson_Large_grid_forecast_jul31.csv'
    # decide on size of batch
    size_of_batch = 50
    xfmr_rating_data_filename = "AZ_Tucson_Large_grid_dummy_to_size_mapping_jul31.json"

    f1 = 'controlled_xfmr_demand_smooth_jul31.csv'

    f2 = 'controlled_ev_demand_smooth_jul31.csv'

    f3 = 'all_ev_energy_info_jul31.csv'

    f4 = 'ev_energy_ports_connected_jul31.csv'

    f5 = 'number_ports_sessions_in_use_jul31.csv'

    f6 = "total_vehicles_available_at_times_jul31.csv"

    sens_flag = "tight"  # "tight", "relax"

    threshold_cutoff = 1

    smooth = True
    start_time = time.time()
    failed_xfrmrs = main(inventory_filename, grid_forecast_filename, size_of_batch, xfmr_rating_data_filename, f1,
                         f2, sens_flag, threshold_cutoff, smooth, f3, f4, f5, f6)
    end_time = time.time()
    print(f"Total time taken to perform this run = {(end_time - start_time)/60} minutes.")