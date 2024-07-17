# -*- coding: utf-8 -*-
"""
Created on Mon Mar 27 14:29:51 2023

@author: dasa880, gudd172
"""
import os

import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import glob
import random, decimal

def main(path, list_dates, num_hours, outputfilename):
    idx_xcel_cod = 7  # Difference between excel time and code time, for example, if in excel, time is 8, in the code that time would be 8-7 = 1

    list_datetimes = [datetime.strptime(x, '%m-%d-%Y') for x in list_dates]

    num_days = [x.weekday() for x in list_datetimes]
    # Defining number of days, weekends are 4,5,6 in python
    # style including Friday. 0-6 --> monday - sunday

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
    charge_category = EV_info["Charge category"].to_numpy()  # importing maximum SOC of EVs
        
    max_soc = EV_info["max SOC"].to_numpy()/100  # importing maximum SOC of EVs
    min_socs = EV_info["min SOC"].to_numpy()/100  # importing minimum SOC of EVs
    efficiency = EV_info["Efficiency of charging"].to_numpy()  # importing efficiency of EV batteries
    charger_size = EV_info["Size of the charger (kw)"].to_numpy()  # importing charger ratings
    capacity = EV_info["Rating of EV battery (kwh)"].to_numpy()  # EV's energy capacity
    daily_energy_depleted = EV_info["Daily energy depleted (kwh)"].to_numpy()  # improting daily depletion of EVs
    allday_available_evs = EV_info["alldaypluggedin"].to_numpy()  # EVs that are available all day

    leave_office_time = EV_info["Reach office (24h)"].to_numpy()  # didn't use it in the code, this is for adding time uncertainties
    reach_home_time = EV_info["Reach home (24h)"].to_numpy()  # didn't use it in the code, this is for adding time uncertainties
    
    travel_time = []
    for i in range(len(leave_office_time)):
        if leave_office_time[i] == 0:
            leave_office_time[i] = 24
            
        if leave_office_time[i]-8 < 0:
            cc = leave_office_time[i]-8+24
            leave_office_time[i] = cc
        else:
            leave_office_time[i]-=8
            
        if reach_home_time[i] == 0:
            reach_home_time[i] = 24
            
        if reach_home_time[i]-8 < 0:
            cc = reach_home_time[i]-8+24
            reach_home_time[i] = cc
        else:
            reach_home_time[i]-=8   
            
        # if  reach_home_time[i] >  leave_office_time[i]:
        #     travel_time.append(reach_home_time[i] - leave_office_time[i])
        # else:
        #     travel_time.append(reach_home_time[i] + 24 - leave_office_time[i])

    ev_charger_availability = []
    for ev_idx in range(len(location_all)):
        ev_availability = [1] * 24  # n_intervals
        start_drive = leave_office_time[ev_idx]
        if (start_drive >= 8) and (start_drive <= 23):
            start_drive = start_drive - 8
        else:
            start_drive = 16 + start_drive
        end_drive = reach_home_time[ev_idx]
        if (end_drive >= 8) and (end_drive <= 23):
            end_drive = end_drive - 8
        else:
            end_drive = 16 + end_drive
        if start_drive < end_drive:
            ev_availability[start_drive:end_drive] = [0] * (end_drive - start_drive)
        else:
            ev_availability[end_drive:start_drive] = [0] * (start_drive - end_drive)
        ev_charger_availability.append(ev_availability)

        travel_time.append(24 - sum(ev_availability))

    min_leave_time = min(leave_office_time)  # didn't use it in the code, this is for adding time uncertainties
    min_reach_time = min(reach_home_time)  # didn't use it in the code, this is for adding time uncertainties

    # if depletionassumption:
    #     per_hour_energy_depletion = [i / j for i, j in zip(0.7*capacity,
    #                                                        travel_time)]  # calculating daily depletion of EVs per hours
    # else:
    #     # print("do not make depletionassumption flag False. because then SCM depletion assumption constraint also needs "
    #     #       "a proper fix which is currently not automated.")
    #     # exit()
    per_hour_energy_depletion = [i / j for i, j in zip(daily_energy_depleted,
                                                            travel_time)]  # calculating daily depletion of EVs per hours

    all_load_days = []
    per_day_profile = []
    loads_at_locations = {}
    map_idx_to_location_actual = {}
    for idx, value in enumerate(location):
        map_idx_to_location_actual[idx] = value

    for day in num_days:
        loads_at_locations[day] = {}
        for i in location:
            loads_at_locations[day][i] = [0]*num_hours

    for hsis, d in enumerate(num_days):

        total_load = np.zeros(num_hours)  # initializing daily load with zeros
        initial_socs = max_soc.copy()  # initializing initial socs

        for t in range(num_hours):  # time loop
            total_power = 0

            if t >= min_reach_time:  # charging time

                # for i in range(len(location)):  # loop for locations
                for idx_row, each_unique_loc in enumerate(location):

                    # idx_location = [idx for idx, val in enumerate(EV_info["Location"].to_numpy()) if
                    #                 val == i + 1 and t >= reach_home_time[
                    #                     idx] - idx_xcel_cod]  # finding EVs in corresponding location
                    idx_location = [idx for idx, val in enumerate(list(location_all)) if
                                    val == each_unique_loc and (ev_charger_availability[idx][t]==1)]  # finding EVs in corresponding location
                    ev_battery_soc_check = initial_socs[idx_location] - max_soc[idx_location]  # finding EVs need charge
                    idx_vehicle_need_charge = [idx for idx, val in enumerate(ev_battery_soc_check) if
                                               val < 0]  # finding indexes of EVs need charge

                    infeasible_index = []
                    for ij in range(len(idx_vehicle_need_charge)):
                        check_category = charge_category[idx_location[idx_vehicle_need_charge[ij]]]
                        ev_all_day_or_not = allday_available_evs[idx_location[idx_vehicle_need_charge[ij]]]
                        if ev_all_day_or_not == 1:  # if ev that is parked all day then it is fully charged and
                            # does not cause any ev demand as per the meeting discussion.
                            infeasible_index.append(idx_vehicle_need_charge[ij])
                        else:
                            # d < 4 (mon - thursday) and vehicle category = 0 (means vehicle wants to charge on fri, sat, sun)
                            if check_category == 0 and d < 4:
                                infeasible_index.append(idx_vehicle_need_charge[ij])
                                # d > 4 (fri, sat, sun) and category = 66 (vehicle wants to charge on mon-fri)
                            elif check_category == 66 and d > 4:
                                infeasible_index.append(idx_vehicle_need_charge[ij])
                                # vehicle wants to charge a specific day of a week
                            elif check_category >= 1 and check_category <= 7:
                                # checks if the vehicle's specific day matches with the day of uncontrolled simulation
                                if check_category-1 != d:
                                    infeasible_index.append(idx_vehicle_need_charge[ij])
                    
                    if len(infeasible_index) > 0:
                        idx_vehicle_need_charge = [ elem for elem in idx_vehicle_need_charge if elem not in infeasible_index]
                    
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

            if t >= 0:
                
                for evs in range(len(per_hour_energy_depletion)):  # considering hourly depletion
                    if leave_office_time[evs] < reach_home_time[evs]:    
                        if t >= leave_office_time[evs] and t < reach_home_time[evs]:
                            # numerator = 0.7*capacity[evs]
                            initial_socs[evs] -= per_hour_energy_depletion[evs] / capacity[evs]
                            # initial_socs[evs] -= numerator / capacity[evs]
                            if initial_socs[evs] < min_socs[evs]:
                                initial_socs[evs] = min_socs[evs]
                    else:
                        if t >= reach_home_time[evs] and t < leave_office_time[evs]:
                            initial_socs[evs] -= per_hour_energy_depletion[evs] / capacity[evs]
                            # initial_socs[evs] -= numerator / capacity[evs]
                            if initial_socs[evs] < min_socs[evs]:
                                initial_socs[evs] = min_socs[evs]
                            

            total_load[t] = total_power  # adding total power and saving hourly
            all_load_days.append(total_power)  # saving the total EV load data
            print(f"File = {path}, Simulating day = {hsis} and hour = {t}.")
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
    path = r"vehicle_master_Large_Year_2041.xlsx"
    # my_main_loc = os.getcwd()
    # os.chdir(f"final_vehicle_inventory/")
    # all_files = glob.glob('./*.xlsx')
    # size_list = [x.split("_")[2] for x in all_files]
    # year_list = [x.split("_")[4].split(".")[0] for x in all_files]
    # os.chdir(my_main_loc)
    # for idx, value in enumerate(size_list):
    #     path = f"final_vehicle_inventory/vehicle_master_{value}_Year_{year_list[idx]}.xlsx"

    num_hours = 24  # Defining number of hours in each day
    outputfilename = "Finaloutput.csv"

    list_of_days_to_simulate = ['7-10-2021']

    all_load_days, per_day_profile, loads_at_locations, main_output_df = main(path, list_of_days_to_simulate, num_hours, outputfilename)


    k = 1


        
        
    

