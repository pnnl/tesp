import os
import numpy as np
import pandas as pd
import DSOT_post_processing_aggregated_folders
import json
import random

def main(Years, Networks, subfolder_count, main_path, xfrmrrating_evshare, EV_placement_on_grid, date_name,
         custom_suffix_sim_run_uncontrolled, vehicle_inventory_path):
    # Loop through Size followed by years and generate the location mapping. This location mapping remains constant for
    # all climate zones given a specific Size and year!
    os.makedirs(f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}", exist_ok=True)
    collect_no_EV_data_important = []
    random.seed(42)
    for idx, network_size in enumerate(Networks):

        if network_size == "Large":
            customsuffix = "feb12_runs"
        else:
            customsuffix = "feb24_runs"

        # Load the commercial transformers and their sizes from all subfolders for a given size.
        # Create subfolder location paths (assume arizona as references - it maybe an issue if other climate zones have
        # 16 subfolders instead of 17 subfolders, right now, it's fine because all success cases have 17 subfolders)
        xfmr_size_name_mapping = {}
        for i in range(subfolder_count[idx]):
            folder_name = f"AZ_Tucson_{network_size}_{customsuffix}_{i+1}_fl"
            path = main_path + folder_name + '/Substation_1/'
            # config_to_power_rating_map_dict has ratings in kva!
            load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name, xfrmr_name_to_size = (
                DSOT_post_processing_aggregated_folders.transformer_map(path))
            for key, value in xfrmr_name_to_size.items():
                modified_key = key + f"_set{i+1}"
                xfmr_size_name_mapping[modified_key] = value



        # convert json info to dataframe
        xfmr_size_map_df = pd.DataFrame(xfmr_size_name_mapping.items(), columns=['Name', 'Size'])

        # # find the max EV count limit for each transformer. for this to work, we use 2040 vehicle inventory and total
        # # available transformer information.
        # # load the 2040 vehicle inventory for current grid size
        # filename = f"{vehicle_inventory_path}/vehicle_master_{network_size}_Year_2040.csv"
        # df = pd.read_csv(filename)
        #
        # xfmr_size_map_df["ptf"] = (xfmr_size_map_df["Size"] / xfmr_size_map_df["Size"].sum())*len(df)
        # xfmr_size_map_df['ptf'] = np.where(xfmr_size_map_df['ptf'] < 1, 1, xfmr_size_map_df['ptf'])
        # xfmr_size_map_df['ptf'] = xfmr_size_map_df['ptf'].round()
        # xfmr_size_map_df = xfmr_size_map_df.rename(columns={'ptf': 'EVMaxCountPossible'})

        # create xfrmr df structure
        df_struct = pd.DataFrame()
        for current_year in Years:
            xfmr_size_map_df_original = xfmr_size_map_df.copy(deep=True)
            xfmr_size_map_df_original["Year"] = int(float(current_year))
            xfmr_size_map_df_original["PercentRatingOccupied"] = 0
            xfmr_size_map_df_original["VehicleIDs"] = np.empty((len(xfmr_size_map_df_original), 0)).tolist()
            df_struct = pd.concat([df_struct, xfmr_size_map_df_original])

        df_struct = df_struct.reset_index(drop=True)

        # create xfrmr to dummy location mapping
        list_xfrmr = list(df_struct["Name"].unique())
        map_given_size = {}
        for idxxxr, xfrmr_name in enumerate(list_xfrmr):
            map_given_size[xfrmr_name] = idxxxr+1

        # now assign vehicle inventory of different years to the total available transformer from above for a given grid
        # size.
        df_all_ev_years = pd.DataFrame()
        for year_idx, current_year in enumerate(Years):

            if network_size == "Medium":
                if current_year == 2040:
                    k = 1
            current_year = int(float(current_year))
            str_print = f"{network_size} and {current_year}"
            print(str_print)

            # # create folder for each year and save data into "first" subfolder of each grid size in AZ Tuscon climate
            # # zone
            # path = main_path + f"AZ_Tucson_{network_size}_{customsuffix}_1_fl/Substation_1/{current_year}"
            # os.makedirs(path, exist_ok=True)

            # Load the corresponding vehicle inventory
            filename = f"{vehicle_inventory_path}/vehicle_master_{network_size}_Year_{current_year}.csv"
            try:
                df = pd.read_csv(filename)
                nodataflag = False
                # df_main_copy = df.copy(deep=True)
                df_all_ev_years = pd.concat([df_all_ev_years, df])
                df = df.sort_values("Size of the charger (kw)", ascending=False)
                df['Charger_cumsum'] = df['Size of the charger (kw)'].cumsum()
            except pd.errors.EmptyDataError:
                print(f"{str_print} --> has no EVs to add.")
                collect_no_EV_data_important.append(str_print)
                nodataflag = True

            if not nodataflag:
                # sort the transformers based on smallest size to largest size (this could help cause more violations)

                # now pick the vehicles (vehicle ID) from the current year inventory and assign the a transformer as
                # below:
                # 1. Pick the largest available transformer (this ensures, the results are skewed to cause violations)
                # 2. If the total simultaneous charging of existing EVs at selected transformer > 30% of xfrmr rating
                # then find next available largest transformer. NOTE: 30% is the parameter we can tweak. Increasing it
                # will cause maybe more violation but decreasing it may cause less violations and also results not fully
                # assigning the inventory to the total available transformers.
                # 3. If total simultaneous charging of existing EVs at selected transformer < 30% of xfrmr rating then
                # add the selected EV to the selected transformer and move to the next EV.

                # update "PercentRatingOccupied" and only consider transformers whose value is < threshold (30%)
                # year filter and threshold filter
                mask_1 = (df_struct["Year"] == current_year) & (df_struct["PercentRatingOccupied"] <
                                                                xfrmrrating_evshare / 100)
                df_mask1 = df_struct[mask_1]
                # sort the transformers whose rating is not occupied more than threshold so we know largest xfrmrs
                # Sort this df as ascending or descending or random...to assign EVs to xfrmrs based on their size!!!!
                if EV_placement_on_grid == "ascen":
                    df_mask1 = df_mask1.sort_values("Size", ascending=True)  # ascending strategy
                elif EV_placement_on_grid == "descen":
                    df_mask1 = df_mask1.sort_values("Size", ascending=False)  # descending strategy
                elif EV_placement_on_grid == "random":
                    df_mask1 = df_mask1.sample(frac=1).reset_index(drop=True)  # random strategy

                if current_year == 2040 or current_year == 2039:
                    k = 1

                # assign one vehicle and update the ratings
                xfrmr_idx = 0
                allvehiceassigned = False
                check_this = []
                check_this_dic = {}
                while not allvehiceassigned:
                    donot_double_increment = False

                    xfrmr_name = df_mask1.iloc[xfrmr_idx]["Name"]
                    xfrmr_size = df_mask1.iloc[xfrmr_idx]["Size"]
                    xfrmr_existing_percent_occupied = df_mask1.iloc[xfrmr_idx]["PercentRatingOccupied"]
                    # max_cum_sum = df["Charger_cumsum"].max()
                    # percent_occupied = max_cum_sum/xfrmr_size

                    # first add vehicles from previous years and then add extra vehicles
                    # vehicle list from previous year

                    if year_idx != 0:
                        prev_year_mask = (df_struct["Year"] == current_year - 1) & (df_struct["Name"] == xfrmr_name)
                        add_vids_previous_year = df_struct[prev_year_mask]["VehicleIDs"].values[0]

                        # if add_vids_previous_year != []:
                        #     pass

                        # find the percent occupied from previous year
                        prev_year_percent_occupied = df_struct[prev_year_mask]["PercentRatingOccupied"].values[0]
                        df = df[~df["Vehicle ID"].isin(add_vids_previous_year)]
                        df['Charger_cumsum'] = df['Size of the charger (kw)'].cumsum()
                        # if xfrmr_idx == 59:
                        #     k = 1
                    else:
                        pass

                    cum_sum_values = np.array(list(df["Charger_cumsum"]))
                    vehicle_ids = np.array(list(df["Vehicle ID"]))
                    percent_occupied = prev_year_percent_occupied + xfrmr_existing_percent_occupied + (cum_sum_values/xfrmr_size)



                    # find index of vehicle with
                    vehicle_indices = np.argwhere(percent_occupied < xfrmrrating_evshare/100)

                    # if current xfrmr cannot accomodate even one extra vehicle OR when there are no new vehicles to add
                    # in current year
                    if (len(vehicle_indices)) == 0 or (len(df) == 0):


                        # add previous year vehicles to current xfrmr and move on to next xfrmr
                        add_vids = add_vids_previous_year
                        t1 = prev_year_percent_occupied

                        # if there are leftover vehicles to be added but current xfrmr cannot accomodate them anymore
                        if len(df) != 0:
                            allvehiceassigned = False

                            xfrmr_idx += 1

                            donot_double_increment = True
                        else:
                            allvehiceassigned = True
                            donot_double_increment = False

                    else:
                        add_vids = add_vids_previous_year + np.concatenate(vehicle_ids[vehicle_indices]).ravel().tolist()
                        t1 = percent_occupied[np.max(vehicle_indices)]
                        allvehiceassigned = True


                    # update the vehicle info in the df_struct for all years from current to future
                    mask2 = (df_struct["Year"] == current_year) & (df_struct["Name"] == xfrmr_name)

                    if not donot_double_increment:
                        if len(add_vids) < len(vehicle_ids):  # not all vehicles were added, need to move to next xfrmr to
                            # left out vehicles
                            xfrmr_idx += 1  # move to next xfrmr in next iteration and update the available vehicles to add
                            # as well.
                            # update current vehicle list and proceed to next xfrmr
                            df = df[~df["Vehicle ID"].isin(add_vids)]
                            df['Charger_cumsum'] = df['Size of the charger (kw)'].cumsum()
                            allvehiceassigned = False
                        elif len(vehicle_ids[vehicle_indices]) < len(vehicle_ids):
                            xfrmr_idx += 1  # move to next xfrmr in next iteration and update the available vehicles to add
                            # as well.
                            # update current vehicle list and proceed to next xfrmr
                            df = df[~df["Vehicle ID"].isin(add_vids)]
                            df['Charger_cumsum'] = df['Size of the charger (kw)'].cumsum()
                            allvehiceassigned = False
                            # df = df.iloc[len(add_vids):, :]  # update the vehicle list
                        # else:
                        #     allvehiceassigned = True

                    vals = list(df_struct[mask2]["VehicleIDs"])
                    new_vals = []
                    for x in vals:
                        new_vals.append(x + add_vids)

                    # # r_vals = [x.extend(add_vids) for x in vals]
                    # all_items = [x for xs in new_vals for x in xs]
                    # if xfrmr_name in check_this_dic.keys():
                    #     pass
                    # else:
                    #     check_this_dic[xfrmr_name] = all_items
                    # for hfk in all_items:
                    #     if hfk in check_this:
                    #         ksds = 1
                    #     else:
                    #
                    #         check_this.append(hfk)
                    add_series = pd.Series(new_vals)
                    add_series.index = df_struct[mask2].index
                    df_struct.loc[mask2, "VehicleIDs"] = add_series
                    # df_struct[mask2]["VehicleIDs"] = df_struct[mask2]["VehicleIDs"].apply(lambda x: x.extend(add_vids))
                    largest_cum_sum = t1
                    # # update all years percent occupied. We do not do the same with mask2 because the input vehicle
                    # # inventory files for every year already has repetitive vehicles from one year to other. So in mask2
                    # # we only update for current year instead of current and future years.
                    # mask3 = (df_struct["Year"] >= current_year) & (df_struct["Name"] == xfrmr_name)
                    df_struct.loc[mask2, "PercentRatingOccupied"] = largest_cum_sum

            if not nodataflag:
                # TODO: assign dummy location to each vehicle in current year for a given size and save the updated vehicle
                #  inventory.
                df_inventory_to_update = pd.read_csv(filename)
                current_mapping_df = df_struct[df_struct["Year"] == current_year]
                all_vehicles_current_year = list(current_mapping_df["VehicleIDs"])
                all_xfrmr_names_current_year = list(current_mapping_df["Name"])
                all_vehicles_current_year_nonempty = []
                all_xfrmr_names_current_year_nonempty = []
                for idxhere, valuehere in enumerate(all_vehicles_current_year):
                    if valuehere == []:
                        pass
                    else:
                        all_vehicles_current_year_nonempty.append(valuehere)
                        all_xfrmr_names_current_year_nonempty.append(all_xfrmr_names_current_year[idxhere])
                vehicle_map = {}
                for idxhere, valuehere in enumerate(all_vehicles_current_year_nonempty):
                    for eachvid in valuehere:
                        currnt_xfrmr = all_xfrmr_names_current_year_nonempty[idxhere]
                        dummy_name_currnt_xfrmr = map_given_size[currnt_xfrmr]
                        if dummy_name_currnt_xfrmr == 158:
                            pass
                        vehicle_map[eachvid] = dummy_name_currnt_xfrmr
                df_inventory_to_update["Location"] = df_inventory_to_update["Vehicle ID"].map(vehicle_map)
                df_inventory_to_update["Location"] = df_inventory_to_update["Location"].astype(int)
                # df_inventory_to_update.to_csv(f"final_vehicle_inventory/vehicle_master_{network_size}_Year_{current_year}.csv", index=False)

                # assign ports
                all_ports_info = []
                for idxr, xfrmr_loc in enumerate(all_xfrmr_names_current_year_nonempty):
                    vehicles_at_loc = len(all_vehicles_current_year_nonempty[idxr])
                    ports_at_loc = int(0.7*vehicles_at_loc)
                    if ports_at_loc == 0:
                        ports_at_loc = 2

                    all_ports_info.append(ports_at_loc)

                loc_p_port_df = pd.DataFrame({"LocationName": all_xfrmr_names_current_year_nonempty,
                                              "NumberofPorts": all_ports_info})
                loc_p_port_df["Location"] = loc_p_port_df["LocationName"].map(map_given_size)
                loc_p_port_df = loc_p_port_df.drop('LocationName', axis=1)
                with pd.ExcelWriter(f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}/vehicle_master_{network_size}_Year_{current_year}.xlsx") as writer:
                    df_inventory_to_update.to_excel(writer, sheet_name='main_info', index=False)
                    loc_p_port_df.to_excel(writer, sheet_name='locationAndPorts', index=False)

                with open(f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}/xfrmr_map_{network_size}_Year_{current_year}.json", 'w', encoding='utf-8') as f:
                    json.dump(map_given_size, f, ensure_ascii=False, indent=4)
                k = 1
                # TODO: assign locations to "df_inventory_to_update"
                # TODO: save the data to csv as shown below

                # TODO: save the "map_given_size" dict that maps xfrmr name to dummy location name for plot reasons
                #  (when needed in future)
            # else:
            #     # TODO: add dummy info to match the final format for no data csvs
            #     # save yearly data for a given network size
            #     save_df = df_struct[df_struct["Year"] == current_year]
            #     save_df.to_csv(f"final_vehicle_inventory/vehicle_master_{network_size}_Year_{current_year}.csv")

            # # save yearly data for a given network size
            # save_df = df_struct[df_struct["Year"] == current_year]
            # save_df.to_csv(f"final_vehicle_inventory/vehicle_master_{network_size}_Year_{current_year}.csv")

        # save the data.
        df_struct.to_csv(f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}/ConsolidatedAllYearsInventory.csv")





        k = 1



    return f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}"




def add_two_numbers(a, b):
    return float(a)+b



if __name__ == '__main__':
    Years = [2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038,
             2039, 2040]
    # Years = [2040]
    Networks = ["Small", "Medium", "Large"]
    # Networks = ["Medium"]
    subfolder_count = [2, 10, 17]
    # subfolder_count = [10]
    vehicle_inventory_path = "new_output_data"
    main_path = r"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/"
    xfrmrrating_evshare = 70  # percent
    EV_placement_on_grid = "random"  # "ascen", "descen", "random"
    date_name = "mar31"
    custom_suffix_sim_run = "delete_this"
    output_file_save_loc = main(Years, Networks, subfolder_count, main_path, xfrmrrating_evshare, EV_placement_on_grid,
                                date_name, custom_suffix_sim_run, vehicle_inventory_path)