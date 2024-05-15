# -*- coding: utf-8 -*-
"""
Created on Mon Mar 27 14:29:51 2023

@author: dasa880, gudd172
"""
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob
import random, decimal

def main(path, num_days, num_hours, outputfilename, depletionassumption):
    idx_xcel_cod = 7  # Difference between excel time and code time, for example, if in excel, time is 8, in the code that time would be 8-7 = 1

    total_load = np.zeros(num_hours)  # initializing load with zeros

    data = pd.read_excel(path, sheet_name=['main_info', 'locationAndPorts'])  # Data from the excel file
    location_column = data['main_info']["Location"]
    # location = np.arange(min(location_column), max(location_column)+1, 1)
    location_all = location_column.to_numpy()
    location = np.unique(location_all)

    EV_info = data['main_info']  # .to_numpy()  # EV information

    Location_port_info = data['locationAndPorts']  # .to_numpy()  # Location information

    ports = Location_port_info["NumberofPorts"].to_numpy()  # Port information

    location_to_port = Location_port_info["Location"].to_numpy()

    # if randomsoc:
    #     EV_info['max SOC'] = [float(decimal.Decimal(random.randrange(60, 90))/100) for k in EV_info.index]
    #     max_soc = EV_info["max SOC"].to_numpy()
    # else:
    max_soc = EV_info["max SOC"].to_numpy()  # importing maximum SOC of EVs
    min_socs = EV_info["min SOC"].to_numpy()  # importing minimum SOC of EVs
    efficiency = EV_info["Efficiency of charging"].to_numpy()  # importing efficiency of EV batteries
    charger_size = EV_info["Size of the charger (kw)"].to_numpy()  # importing charger ratings
    capacity = EV_info["Rating of EV battery (kwh)"].to_numpy()  # EV's energy capacity
    daily_energy_depleted = EV_info["Daily energy depleted (kwh)"].to_numpy()  # improting daily depletion of EVs

    leave_office_time = EV_info["Reach office (24h)"].to_numpy()  # didn't use it in the code, this is for adding time uncertainties
    min_leave_time = min(leave_office_time)  # didn't use it in the code, this is for adding time uncertainties

    reach_home_time = EV_info["Reach home (24h)"].to_numpy()  # didn't use it in the code, this is for adding time uncertainties
    min_reach_time = min(reach_home_time)  # didn't use it in the code, this is for adding time uncertainties

    if depletionassumption:
        per_hour_energy_depletion = [i / j for i, j in zip(0.7*capacity,
                                                           reach_home_time - leave_office_time)]  # calculating daily depletion of EVs per hours
    else:
        print("do not make depletionassumption flag False. because then SCM depletion assumption constraint also needs "
              "a proper fix which is currently not automated.")
        exit()
        # per_hour_energy_depletion = [i / j for i, j in zip(daily_energy_depleted,
        #                                                    reach_home_time - leave_office_time)]  # calculating daily depletion of EVs per hours

    all_load_days = []
    per_day_profile = []
    loads_at_locations = {}
    map_idx_to_location_actual = {}
    for idx, value in enumerate(location):
        map_idx_to_location_actual[idx] = value

    for day in range(num_days):
        loads_at_locations[day] = {}
        for i in location:
            loads_at_locations[day][i] = [0]*num_hours

    for d in range(num_days):

        total_load = np.zeros(num_hours)  # initializing daily load with zeros
        initial_socs = max_soc.copy()  # initializing initial socs

        for t in range(num_hours):  # time loop
            total_power = 0

            if t >= min_reach_time - idx_xcel_cod:  # charging time

                # for i in range(len(location)):  # loop for locations
                for idx_row, each_unique_loc in enumerate(location):

                    # idx_location = [idx for idx, val in enumerate(EV_info["Location"].to_numpy()) if
                    #                 val == i + 1 and t >= reach_home_time[
                    #                     idx] - idx_xcel_cod]  # finding EVs in corresponding location
                    idx_location = [idx for idx, val in enumerate(list(location_all)) if
                                    val == each_unique_loc and t >= reach_home_time[
                                        idx] - idx_xcel_cod]  # finding EVs in corresponding location
                    ev_battery_soc_check = initial_socs[idx_location] - max_soc[idx_location]  # finding EVs need charge
                    idx_vehicle_need_charge = [idx for idx, val in enumerate(ev_battery_soc_check) if
                                               val < 0]  # finding indexes of EVs need charge
                    row_of_port = np.argwhere(location_to_port == each_unique_loc)[0][0]
                    # num_EVs_charging = min(ports[i],
                    #                        len(idx_vehicle_need_charge))  # determining number of EVs to be charged at the charging station
                    num_EVs_charging = min(ports[row_of_port],
                                           len(idx_vehicle_need_charge))  # determining number of EVs to be charged at the charging station

                    dummy_var  = 0
                    if num_EVs_charging > 0:  # condition to see if there is any charging need
                        for j in range(num_EVs_charging):  # loop for charging EVs begin
                            if initial_socs[idx_location[idx_vehicle_need_charge[j]]] < max_soc[idx_location[
                                idx_vehicle_need_charge[j]]]:  # checking if current SOC is higher than max SOC
                                power_location = charger_size[idx_location[
                                    idx_vehicle_need_charge[j]]]  # finding rating of corresponding charging location
                                total_power += power_location  # adding power to the total load
                                dummy_var += power_location
                                new_soc = initial_socs[idx_location[idx_vehicle_need_charge[j]]] + (
                                            power_location * efficiency[idx_location[idx_vehicle_need_charge[j]]] /
                                            capacity[idx_location[idx_vehicle_need_charge[j]]])  # updating battery SOC
                                initial_socs[
                                    idx_location[idx_vehicle_need_charge[j]]] = new_soc  # updating old SOC with new SOC
                    loads_at_locations[d][each_unique_loc][t] = dummy_var

            if t >= 0 and t < max(reach_home_time) - idx_xcel_cod:

                # dummy_var1 = 0
                # for i in range(len(location)):
                #     loads_at_locations[map_idx_to_location_actual[i]].append(dummy_var1)

                for evs in range(len(per_hour_energy_depletion)):  # considering hourly depletion
                    if t >= leave_office_time[evs] - idx_xcel_cod and t < reach_home_time[evs] - idx_xcel_cod:
                        # numerator = 0.7*capacity[evs]
                        initial_socs[evs] -= per_hour_energy_depletion[evs] / capacity[evs]
                        # initial_socs[evs] -= numerator / capacity[evs]
                        if initial_socs[evs] < min_socs[evs]:
                            initial_socs[evs] = min_socs[evs]

            total_load[t] = total_power  # adding total power and saving hourly
            all_load_days.append(total_power)  # saving the total EV load data
        per_day_profile.append(total_load)

    # save results
    print(f"Peak EV demand for {outputfilename} = {max(all_load_days)/1000} MWs")
    main_output_df = pd.DataFrame()
    for day_key, day_value in loads_at_locations.items():
        output_df = pd.DataFrame.from_dict(day_value, orient='index').transpose()
        output_df["day"] = day_key
        output_df["hour"] = pd.Series([8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7])
        main_output_df = pd.concat([main_output_df, output_df])
        # output_df[""]
        # output_df["day"] = key
    main_output_df.to_csv(outputfilename, index=False)

    # plt.plot(all_load_days)
    # plt.xlabel('Time')
    # plt.ylabel('EV Load (kW)')
    # plt.show()

    return all_load_days, per_day_profile, loads_at_locations, main_output_df

if __name__ == '__main__':
    # path = r"inputs_scm_feb20_Avijit_up.xlsx"
    path = r"vehicle_master_Large_Year_2033.xlsx"
    # my_main_loc = os.getcwd()
    # os.chdir(f"final_vehicle_inventory/")
    # all_files = glob.glob('./*.xlsx')
    # size_list = [x.split("_")[2] for x in all_files]
    # year_list = [x.split("_")[4].split(".")[0] for x in all_files]
    # os.chdir(my_main_loc)
    # for idx, value in enumerate(size_list):
    #     path = f"final_vehicle_inventory/vehicle_master_{value}_Year_{year_list[idx]}.xlsx"

    num_days = 7  # Defining number of days
    num_hours = 24  # Defining number of hours in each day
    outputfilename = "Finaloutput.csv"
    depletionassumption = True
    randomsoc = True
    all_load_days, per_day_profile, loads_at_locations, main_output_df = main(path, num_days, num_hours, outputfilename, depletionassumption, randomsoc)


    k = 1


        
        
    

