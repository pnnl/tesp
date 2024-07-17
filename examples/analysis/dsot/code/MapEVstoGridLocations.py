import os
import numpy as np
import pandas as pd
import DSOT_post_processing_aggregated_folders
import json
import random
import math
import sys
import glmanip
import ingest_bld_data
if os.path.abspath("/home/gudd172/tesp/repository/tesp/src/tesp_support/tesp_support/weather") not in sys.path:
    sys.path.append("/home/gudd172/tesp/repository/tesp/src/tesp_support/tesp_support/weather")
import EPWtoDAT
from glm import GLMManager
from DSOT_post_processing_aggregated_folders import load_system_data, get_attributes_from_metrics_data

def get_xfrmr_info_from_all_substations_subfolders(subfolder_count, idx, network_size, customsuffix, main_path):
    xfmr_size_name_mapping = {}
    for i in range(subfolder_count[idx]):
        folder_name = f"AZ_Tucson_{network_size}_{customsuffix}_{i + 1}_fl"
        path = main_path + folder_name + '/Substation_1/'
        # config_to_power_rating_map_dict has ratings in kva!
        load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name, xfrmr_name_to_size = (
            DSOT_post_processing_aggregated_folders.transformer_map(path))
        for key, value in xfrmr_name_to_size.items():
            modified_key = key + f"_set{i + 1}"
            xfmr_size_name_mapping[modified_key] = value

    # convert json info to dataframe
    xfmr_size_map_df = pd.DataFrame(xfmr_size_name_mapping.items(), columns=['Name', 'Size'])

    return xfmr_size_map_df

def get_xfrmr_info_from_all_substations_subfoldersv2(subfolder_count, idx, network_size, customsuffix, main_path,
                                                     weather_folder_names, weather_mappings_bldg_name,
                                                     weather_mappings_bldg_count):
    xfmr_size_name_mapping_withEVs = {}
    xfmr_size_name_mapping_allxfrmrs = {}
    for i in range(subfolder_count[idx]):
        folder_name = f"AZ_Tucson_{network_size}_{customsuffix}_{i + 1}_fl"
        path = main_path + folder_name + '/Substation_1/'
        # config_to_power_rating_map_dict has ratings in kva!
        load_to_xfrmr_config_map_dict, config_to_power_rating_map_dict, load_to_xfrmr_name, xfrmr_name_to_size = (
            DSOT_post_processing_aggregated_folders.transformer_map(path))

        # find the blg dummy name mapped to the commercial load or even better to a commercial transformer.
        # using the glm manager to read glm file
        glm_mgr = GLMManager(os.path.join(path, "Substation_1.glm"),
                             model_is_path=True)
        # # parse through glm info to find the commercial xfrmr and its bldg name to it
        desired_xfrmr_list = []
        for key_gt, value_gt in glm_mgr.model_map["object"]["load"].items():
            load_info = value_gt[1]
            for k_h, v_h in load_info.items():
                if "base_power" in k_h:
                    bldg_name_found_in_glm = v_h.split(".")[0]
                    # find bldgs from shortlisted buildings
                    if bldg_name_found_in_glm in weather_mappings_bldg_name["AZ_Tucson"][network_size].keys():
                        load_to_which_bldg_is_assigned = load_info["name"].split("_streetlights")[0]
                        xfrmr_connected_to_bldg = load_to_xfrmr_name[load_to_which_bldg_is_assigned]
                        desired_xfrmr_list.append(xfrmr_connected_to_bldg)


        for key, value in xfrmr_name_to_size.items():
            modified_key = key + f"_set{i + 1}"
            xfmr_size_name_mapping_allxfrmrs[modified_key] = value
            if key in desired_xfrmr_list:  # only add xfrmrs that have desired bldgs from the manual selection. The rest
                # of the code will work based on the selected xfrmrs.
                xfmr_size_name_mapping_withEVs[modified_key] = value

    # convert json info to dataframe
    xfmr_size_map_df_withEVs = pd.DataFrame(xfmr_size_name_mapping_withEVs.items(), columns=['Name', 'Size'])
    xfmr_size_map_df_allxfrmrs = pd.DataFrame(xfmr_size_name_mapping_allxfrmrs.items(), columns=['Name', 'Size'])
    return xfmr_size_map_df_withEVs, xfmr_size_map_df_allxfrmrs

def assign_vehicles(list_of_vehicleIDs, vehicles_to_add_at_a_location, possible_xfrmrs, df, map_given_size):
    xfrmr_added_idx = 0
    xfrmr_df_indices_to_delete = []
    for batch in range(0, len(list_of_vehicleIDs), vehicles_to_add_at_a_location):
        if xfrmr_added_idx >= possible_xfrmrs.shape[0]:
            if vehicles_to_add_at_a_location == 2:
                charger_type = "L3"
            else:
                charger_type = "L2"
            print(f"Grid expansion needed: Total available xfrmrs = {possible_xfrmrs.shape[0]}, "
                  f"only {possible_xfrmrs.shape[0]*vehicles_to_add_at_a_location} vehicles can "
                  f"be accomodated as per user charger infra plan but, {len(list_of_vehicleIDs)} vehicles are asked to "
                  f"be assigned. Skipping the "
                  f"excess vehicles. Type of charger location = {charger_type}")
        else:
            xfrmr_to_assign_for_current_batch = possible_xfrmrs.iloc[xfrmr_added_idx]["Name"]
            xfrmr_df_indices_to_delete.append(possible_xfrmrs.index[xfrmr_added_idx])
            # for k in xfmr_loading_df.columns.tolist():
            min_id = batch
            max_id = min(batch + vehicles_to_add_at_a_location, len(list_of_vehicleIDs))

            vehicles_in_current_batch = list_of_vehicleIDs[min_id:max_id]

            # update xfrmr assignment
            mask_current_batch = df["Vehicle ID"].isin(vehicles_in_current_batch)
            df.loc[mask_current_batch, "Location"] = map_given_size[xfrmr_to_assign_for_current_batch]

            # move to next possible xfrmr
            xfrmr_added_idx += 1

    return df, xfrmr_df_indices_to_delete

def perform_commonsense_check(possible_xfrmrs, vehicles_to_add_at_a_location, network_size, xfmr_size_map_df, type_l,
                              df_vehicles):
    vehicle_batches = math.ceil(
        len(possible_xfrmrs) / vehicles_to_add_at_a_location)  # number of xfrmrs required to assign all

    if len(possible_xfrmrs) < vehicle_batches:
        print("Too many vehicles per charging location, not enough xfrmrs to assign EVs. Reduce the vehicles per"
              " port or max ports. Suggestion, reduce max ports. Exiting..")
        exit()
    else:
        print(f"Grid size = {network_size}. Available xfrmrs with right sizes/ selected xfrmrs ="
              f" {len(possible_xfrmrs)}/{len(xfmr_size_map_df)}. Vehicle assignment to grid possible, proceeding"
              f" to next steps. Number of vehicles per xfrmr with {type_l} = {vehicles_to_add_at_a_location}. Total "
              f"vehicles to assign on grid = {len(df_vehicles)}")

cache_output = {}
cache_df = {}
def load_json(dir_path, file_name):
    """Utility to open Json files."""
    name = os.path.join(dir_path, file_name)
    try:
        cache = cache_output[name]
        return cache
    except:
        with open(name) as json_file:
            cache_output[name] = json.load(json_file)
    return cache_output[name]
def main_cyclic_pov_assignments(df, sizes, custom_suffix, subfolder_count, idx, map_given_size):
    df["Location"] = 99999
    df["chargertype"] = 2  # all povs will have level 2 charger

    # for the given grid size, identify all the residential xfrmrs
    # identify how many houses are present under each xfrmr. Assume two ports per house and identify total vehicles
    # per each residential xfrmr
    main_names = 'AZ_Tucson'
    folder_count = subfolder_count[idx]
    half_name = f"{main_names}_{sizes}_{custom_suffix}"
    pure_res_xfmr_dict = {}  # keys = res xfrmr names and values = total houses under the res xfrmr
    pure_res_xfrmr_size_mapping = {}
    for xio in range(folder_count):
        folder_name = f"{half_name}_{xio+1}_fl"

        curr_dir = os.getcwd()
        base_case = f"{curr_dir}/" + folder_name
        basedir = f"{base_case}/Substation_1/"
        # below file is generated when "update_pov_xfrmrs_after_tesp.py" is executed
        asset_str = '_hse_'
        res_xfmr_file_name = 'asset_map_' + 'Substation_1' + asset_str + '.json'  # obtained using networkx and
        # com_loads json
        res_xfmr_dict = load_json(basedir, res_xfmr_file_name)

        # above dictionary has both residential and commercial xfrmrs as keys but commercial xfrmr keys have values as
        # empty. lets remove them first before assigning unique location id.

        glm_lines = glmanip.read(basedir + 'Substation_1.glm', basedir, buf=[])
        [model, clock, directives, modules, classes] = glmanip.parse(glm_lines)

        for key, value in res_xfmr_dict.items():
            if value != [] and key != "substation_transformer":
                if "R2" in key:
                    key_h = f"feeder1_{key}"
                elif "R4" in key:
                    key_h = f"feeder2_{key}"
                else:
                    print(key)
                    print("unexpected feeder...exiting")
                    exit()

                pure_res_xfmr_dict[key_h + f"_set{xio + 1}"] = len(value)

                # also lets grab the size of the residential xfrmr. This was not done during gov analysis. So this data
                # needs to be appended to the ALL commerical xfrmrs dictionary at the end.
                pure_res_xfrmr_size_mapping[key_h + f"_set{xio + 1}"] = float((
                    model)["transformer_configuration"][model["transformer"][key]["configuration"]]["power_rating"])

    # assign unique location ids by considering whats already assigned for govs
    if len([x for x in pure_res_xfmr_dict if x in map_given_size]) != 0:
        print("There is intersection between res xfrmr and commercial xfrmr dictionaries, this should never happen....check this, exiting")
        exit()
    gov_ids = max(map_given_size.values())

    # create unique xfrmr names as we iterate through all subfolders
    # create xfrmr to dummy location mapping
    id_counter = gov_ids
    for key, value in pure_res_xfmr_dict.items():
        id_counter += 1
        map_given_size[key] = id_counter

    # in a cyclic manner assign povs one per house (half of pov capacity of a xfrmr) and if all xfrmrs are filled then
    # start utilizing the second port in each house until all povs are assigned to the xfrmrs
    list_of_vehicleIDs = list(df["Vehicle ID"])  # has only povs at residential xfrmrs
    possible_xfrmrs = pd.DataFrame(pure_res_xfmr_dict.items(), columns=['Name', 'HouseCount'])
    possible_xfrmrs = possible_xfrmrs.sample(frac=1).reset_index(drop=True)
    df = assign_pov_vehicles(list_of_vehicleIDs, possible_xfrmrs, df, map_given_size)

    k = 1

    return map_given_size, df, pure_res_xfrmr_size_mapping, pure_res_xfmr_dict, possible_xfrmrs

def assign_pov_vehicles(list_of_vehicleIDs, possible_xfrmrs, df, map_given_size):
    vehicle_counter = 0
    for xfrmr_id in range(possible_xfrmrs.shape[0]):
        current_xfrmr = possible_xfrmrs.iloc[xfrmr_id]["Name"]
        vehicles_to_assign_at_current_xfrmr = possible_xfrmrs.iloc[xfrmr_id]["HouseCount"]  # because we
        # first assign 1 vehicle per house and move to next xfrmr and if all xfrmrs for evs one per house then we go
        # back to the first xfrmrx.
        vehicle_counter_min = vehicle_counter
        vehicle_counter_max = vehicle_counter_min + min(vehicles_to_assign_at_current_xfrmr, len(list_of_vehicleIDs)-vehicle_counter_min)
        if vehicle_counter_max > len(list_of_vehicleIDs):
            # finished assigning all vehicles to the xfrmrs, exiting the for loop
            break
        vehicles_in_current_batch = list_of_vehicleIDs[vehicle_counter_min:vehicle_counter_max]
        vehicle_counter = vehicle_counter_max

        # update xfrmr assignment
        mask_current_batch = df["Vehicle ID"].isin(vehicles_in_current_batch)
        df.loc[mask_current_batch, "Location"] = map_given_size[current_xfrmr]
        # move to next possible xfrmr through for loop

        # conditions to check
        # if vehicles to assign are less than the available xfrmrs then "vehicles_in_current_batch" will have error
        # (handled this scenario if condition and break).

        # if vehicles are more than available xfrmrs then for loop will not through error but some vehicles will not be
        # assigned to any transformer and their location will have 99999 (this case will likely never happen in this
        # project so not handling the edge case...if error occurs then this will need to be fixed)

    return df


def main_cyclic_selective_locs_for_chargers(vehicles_per_port, Years, Networks, subfolder_count,
                                            main_path, xfrmrrating_evshare,
         custom_suffix_sim_run_uncontrolled, vehicle_inventory_path, final_year, max_ports,
                                            load_existing_mapping_bldg_no_to_manually_selected_EVbldgs, date_name):
    # PART 1:
    # Shortlist location of transformers where EVs will be placed. The names of the buildings are selected manually.
    # Now:
    # 1) Names of buildings in glm need to be found based on building names that got shortlisted
    # 2) Need to find the transformer names or transformer identifier that the identified transformer bldg numbers
    # 3) This information need to be used when loading the transformer locations to assign EVs in the next step.

    # item (1):
    weather_folder_names, weather_mappings_bldg_name, weather_mappings_bldg_count = \
        find_bldg_map_names(load_existing_mapping_data=load_existing_mapping_bldg_no_to_manually_selected_EVbldgs)

    # PART 2:
    # assign logic of cyclic version instead of size based option like above function. This function adds xfrmrs
    # based on selected locations and number of charging locations available in a cyclic manner.
    #----------------------------------------------------------------------------------------------------------


    # need to know which xfrmrs are down selected for placement of EVs

    # use user input that says how many charging locations are available on grid for commercial side of course

    # 2 to 2.5 vehicles per port and 5 ports at a location. NOTE: make number of chargers at a location as user input

    # level 3 chargers may have their own transformers

    # keep the size option still open, but it can be turned off, it will be a simple check.

    #---------------------
    # Loop through Size followed by years and generate the location mapping. This location mapping remains constant for
    # all climate zones given a specific Size and year!
    os.makedirs(f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}", exist_ok=True)
    collect_no_EV_data_important = []
    random.seed(42)
    df_struct = pd.DataFrame()
    for idx, network_size in enumerate(Networks):

        xfmrs_assigned_for_current_grid_names = []

        # todo: note this logic for simulation purposes!
        if network_size == "Large":
            customsuffix = date_name.split("_")[0]+"_runs"  # "jul14_runs"  #"feb12_runs" - this wont work anymore after
            # pov addition results on jul9_runs
        else:
            customsuffix = date_name.split("_")[0]+"_runs"  # "jul14_runs"  # "feb14_runs"

        # # Load the commercial transformers and their sizes from all subfolders for a given size.
        # # Create subfolder location paths (assume arizona as references - it maybe an issue if other climate zones have
        # # 16 subfolders instead of 17 subfolders, right now, it's fine because all success cases have 17 subfolders)
        # xfmr_size_map_df = get_xfrmr_info_from_all_substations_subfolders(subfolder_count, idx, network_size,
        #                                                                   customsuffix, main_path)
        # func v2 update: this function not only loads the commercial xfrms like above commented function but it also
        # uses the bldg map to short list the xfrmrs those bldgs are connected to, which is the step one requirement of
        # cyclic ev assignment logic.
        # NOTE: "xfmr_size_map_df" has xfrmrs that can potentially have EVs. The actual xfrmrs that have EVs are
        # dependent on the charging infrastructure inputs and it is done in below code later in this function.
        xfmr_size_map_df, xfmr_size_map_df_allxfrmrs = get_xfrmr_info_from_all_substations_subfoldersv2(subfolder_count, idx, network_size,
                                                                          customsuffix, main_path, weather_folder_names,
                                                                            weather_mappings_bldg_name,
                                                                            weather_mappings_bldg_count)
        # xfmr_size_map_df = xfmr_size_map_df.sample(frac=1).reset_index(drop=True)
        # create xfrmr to dummy location mapping
        list_xfrmr = list(xfmr_size_map_df_allxfrmrs["Name"].unique())
        map_given_size = {}
        for idxxxr, xfrmr_name in enumerate(list_xfrmr):
            map_given_size[xfrmr_name] = idxxxr + 1


        # take the 2040 vehicle inventory and assign vehicles as per the logic
            # Load the corresponding vehicle inventory
        filename = f"{vehicle_inventory_path}/vehicle_master_{network_size}_Year_{final_year}.csv"
        # this function is for GOVs, so filter out the POVs from the above df and proceed to assign GOVs to the
        # commercial transformer.
        # NOTE: There are specific POVs (comuters) who charge at commercial transformer. include those also into the
        # GOVs df
        df_all = pd.read_csv(filename)
        gov_and_cummuter_mask = ((df_all["POVs/GOVs"] == "HD_GOV")|(df_all["POVs/GOVs"] == "MD_GOV")|
                                 (df_all["POVs/GOVs"] == "LD_GOV")|((df_all["POVs/GOVs"] == "POV_civilian")&
                                                                (df_all["Reach office (24h)"] == 15)&
                                                                (df_all["Reach home (24h)"] == 12)))
        df = df_all[gov_and_cummuter_mask]

        # assign povs to residential xfrmrs. At the end we will concate the pov assignment results and gov assignment
        # results. It can be concated because both vehicle set are exclusive hence independent
        df_povs = df_all[~gov_and_cummuter_mask]
        map_given_size, df_povs, pure_res_xfrmr_size_mapping, pure_res_xfmr_housecount_dict, pure_res_xfmr_housecount_df\
            = main_cyclic_pov_assignments(df_povs, network_size, customsuffix, subfolder_count, idx, map_given_size)

        # pure_res_xfrmr_size_mapping
        # with open(os.getcwd() + f"/Forecast_from_gld_{date_name}/" + f"{zone_name}_grid_dummy_to_size_mapping.json", 'w',
        #                   encoding='utf-8') as f:
        #     json.dump(map_given_size, f, ensure_ascii=False, indent=4)

        map_given_size_reverse = {}
        for key, value in map_given_size.items():
            map_given_size_reverse[value] = key

        # continue to assign govs and cummuters to commercial xfrmrs
        df["Location"] = 99999

        # perform cyclic assignment
            # number of vehicles at a charging location that can charge at given point = max_ports
        vehicles_max_at_a_location = max_ports


        # assign type of charger needed for each vehicleId first
        df["chargertype"] = 2
        # https://www.power-sonic.com/blog/levels-of-ev-charging/
        mask_level_3 = df["Size of the charger (kw)"] > 30
        df.loc[mask_level_3, "chargertype"] = 3

        # perform a common sense check with user inputs
        if xfrmrrating_evshare == None:
            # EVs will occupy 100% of the xfrmr or less
            required_rough_kva = vehicles_max_at_a_location*20  # 20 is 20kw of a L2 charger
        else:  # just an option if needed when SCM fails lots of xfrmrs
            # EVs will occupy xfrmrrating_evshare of the xfrmr rating
            required_rough_kva = (vehicles_max_at_a_location * 20)/(xfrmrrating_evshare/100)
        # ensuring there is buffer for base demand
        # # as well. otherwise its a problem with SCM optimization (no feasible solution). UPDATE: not including this
        # # because SCM should handle different times and charge all vehicles as needed.

        # separate L2 and L3 vehicles
        df_L2 = df[df["chargertype"] == 2]
        df_L3 = df[df["chargertype"] == 3]

            # find number of xfrmrs whos kva rating satisfies required rough kva
        possible_xfrmrs = xfmr_size_map_df[xfmr_size_map_df["Size"] >= required_rough_kva]
        # L2 charger required vehicles
        type_l = "L2"
        perform_commonsense_check(possible_xfrmrs, vehicles_max_at_a_location, network_size, xfmr_size_map_df,
                                  type_l, df_L2)
        # if len(possible_xfrmrs) < vehicle_batches:
        #     print("Too many vehicles per charging location, not enough xfrmrs to assign EVs. Reduce the vehicles per"
        #           " port or max ports. Suggestion, reduce max ports. Exiting..")
        #     exit()
        # else:
        #     print(f"Grid size = {network_size}. Available xfrmrs with right sizes/ selected xfrmrs ="
        #           f" {len(possible_xfrmrs)}/{len(xfmr_size_map_df)}. Vehicle assignment to grid possible, proceeding"
        #           f" to next steps. Number of vehicles per xfrmr with {type_l} = {vehicles_max_at_a_location}")

        # for every location in a cyclic manner. First assign all level 2 charging type vehicles and then assign
        # all level 3 charging vehicles


        # For a given network, go through all years


        list_of_vehicleIDs = list(df_L2["Vehicle ID"])
        df, xfrmr_df_indices_to_delete1 = assign_vehicles(list_of_vehicleIDs, vehicles_max_at_a_location,
                                                         possible_xfrmrs, df, map_given_size)
        names1 = list(possible_xfrmrs.loc[xfrmr_df_indices_to_delete1]["Name"])
        xfmrs_assigned_for_current_grid_names.extend(names1)

        # assign vehicles that require L3 chargers. Each L3 charger gets a dedicated xfrmr. Continue from xfrmr left
        # off by the L2 charger assignments from above. as move through possible xfrmrs one by one in cyclic manner.
        possible_xfrmrs = possible_xfrmrs.drop(xfrmr_df_indices_to_delete1)  # remove already assigned xfrmrs
        # make sure the possible xfrmrs have atleast the size requested by the charger in vehicle inventory
        if xfrmrrating_evshare == None:
            # EVs will occupy 100% of the xfrmr or less
            required_rough_kva = df_L3["Size of the charger (kw)"].min()*2  # times 2 because there are 2 ports at one L3 charger
        else:  # just an option if needed when SCM fails lots of xfrmrs
            # EVs will occupy xfrmrrating_evshare of the xfrmr rating
            required_rough_kva = (df_L3["Size of the charger (kw)"].min())/(xfrmrrating_evshare/100)
        # ensuring there is buffer for base demand
        # # as well. otherwise its a problem with SCM optimization (no feasible solution). UPDATE: not including this
        # # because SCM should handle different times and charge all vehicles as needed.
        possible_xfrmrs = possible_xfrmrs[possible_xfrmrs["Size"] >= required_rough_kva]
        type_l = "L3"
        # second argument in below function call is 2 because there will be two vehicles maximum that can charge at
        # any given point at a single L3 charger. We also have an assumption that L3 charger gets its own xfrmrs so we
        # assigned only one L3 charger at a location.
        perform_commonsense_check(possible_xfrmrs, 2, network_size, xfmr_size_map_df,
                                  type_l, df_L3)
        list_of_vehicleIDs = list(df_L3["Vehicle ID"])

        df, xfrmr_df_indices_to_delete = assign_vehicles(list_of_vehicleIDs, 2,
                                                         possible_xfrmrs, df, map_given_size)

        # removing any vehicles that are not assigned to the grid from the inventory. This will never happen unless
        # "grid expansion needed" print message shows up.
        print(f"Total vehicles not considered due to grid expansion needed situation = "
              f"{df[df['Location'] == 99999].shape[0]}")
        df = df[~(df["Location"] == 99999)]

        names2 = list(possible_xfrmrs.loc[xfrmr_df_indices_to_delete]["Name"])
        xfmrs_assigned_for_current_grid_names.extend(names2)

        # combine both govs and povs
        df_gov_pov = pd.concat([df, df_povs])

        # now all vehicles are assigned to a transformer. Generate the vehicle inventory for different years with
        # desired formatting. generate the new vehicle inventory files with ports and other information as
        # needed for the follow up process in the project/study.
        for current_year in Years:
            filename = f"{vehicle_inventory_path}/vehicle_master_{network_size}_Year_{current_year}.csv"
            str_print = f"{network_size} and {current_year}"
            try:
                df_current_year_vinfo = pd.read_csv(filename)
                nodataflag = False
            except pd.errors.EmptyDataError:
                print(f"{str_print} --> has no EVs to add.")
                collect_no_EV_data_important.append(str_print)
                nodataflag = True

            if not nodataflag:
                updated_df_current_year = df_gov_pov[df_gov_pov["Vehicle ID"].isin(df_current_year_vinfo["Vehicle ID"])]
                sav_df = updated_df_current_year.copy(deep=True)
                sav_df["Year of adoption"] = int(float(current_year))
                sav_df["Grid size"] = network_size
                df_struct = pd.concat([df_struct, sav_df])
                locs_gov = df[df["Vehicle ID"].isin(df_current_year_vinfo["Vehicle ID"])]
                loc_p_port_df_gov = pd.DataFrame({"Location": list(locs_gov["Location"].unique()),
                                                                            "NumberofPorts": max_ports/vehicles_per_port})
                # update the L3 locations to have only two ports because above line of code add ports as if L3
                # locations are L2
                l3_location_info = df[df["chargertype"] == 3]["Location"]
                mask_ll3_current_year = loc_p_port_df_gov["Location"].isin(l3_location_info)
                loc_p_port_df_gov.loc[mask_ll3_current_year, "NumberofPorts"] = 2

                locs_pov = df_povs[df_povs["Vehicle ID"].isin(df_current_year_vinfo["Vehicle ID"])]
                locs_pov_unique = list(locs_pov["Location"].unique())
                loc_p_port_df_pov = pd.DataFrame({"Location": locs_pov_unique,
                                                  "NumberofPorts": [pure_res_xfmr_housecount_dict[map_given_size_reverse[x]]*2 for x in locs_pov_unique]})
                loc_p_port_df = pd.concat([loc_p_port_df_gov, loc_p_port_df_pov])
                with pd.ExcelWriter(
                        f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}/vehicle_master_{network_size}_Year_{current_year}.xlsx") as writer:
                    updated_df_current_year.to_excel(writer, sheet_name='main_info', index=False)
                    loc_p_port_df.to_excel(writer, sheet_name='locationAndPorts', index=False)

                with open(f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}/xfrmr_map_{network_size}_Year_{current_year}.json", 'w', encoding='utf-8') as f:
                    json.dump(map_given_size, f, ensure_ascii=False, indent=4)

    df_struct.to_csv(f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}/ConsolidatedAllYearsInventory.csv", index=False)

    return f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}"

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


def saveintojson(data_to_save, filename_to_be_saved_as, data_Path):
    with open(os.path.join(data_Path, filename_to_be_saved_as), 'w') as fp:
        json.dump(data_to_save, fp, sort_keys=True, indent=4)

def loadjson(filename_to_load, data_path):
    with open(os.path.join(data_path, filename_to_load)) as f:
        return json.load(f)
def find_bldg_map_names(load_existing_mapping_data):
    if not load_existing_mapping_data:
        file_name_dict1 = {'AZ_Tucson': 'Largesite_az.xlsx',
                           'WA_Tacoma': 'Largesite_wa.xlsx',
                           'AL_Dothan': 'Largesite_al.xlsx',
                           'IA_Johnston': 'Largesite_ia.xlsx',
                           'LA_Alexandria': 'Largesite_la.xlsx',
                           'AK_Anchorage': 'Largesite_ak.xlsx',
                           'MT_Greatfalls': 'Largesite_mt.xlsx'}
        file_name_dict2 = {'AZ_Tucson': 'Mediumsite_az.xlsx',
                           'WA_Tacoma': 'Mediumsite_wa.xlsx',
                           'AL_Dothan': 'Mediumsite_al.xlsx',
                           'IA_Johnston': 'Mediumsite_ia.xlsx',
                           'LA_Alexandria': 'Mediumsite_la.xlsx',
                           'AK_Anchorage': 'Mediumsite_ak.xlsx',
                           'MT_Greatfalls': 'Mediumsite_mt.xlsx'}
        file_name_dict3 = {'AZ_Tucson': 'Smallsite_az.xlsx',
                           'WA_Tacoma': 'Smallsite_wa.xlsx',
                           'AL_Dothan': 'Smallsite_al.xlsx',
                           'IA_Johnston': 'Smallsite_ia.xlsx',
                           'LA_Alexandria': 'Smallsite_la.xlsx',
                           'AK_Anchorage': 'Smallsite_ak.xlsx',
                           'MT_Greatfalls': 'Smallsite_mt.xlsx'}
        list_of_names = [file_name_dict1, file_name_dict2, file_name_dict3]

        weather_path_inputs = "/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/data/8-node data/"
        bus_loc = {'AZ_Tucson': ['AZ_file', '_'],
                   'WA_Tacoma': ['WA_file', '_'],
                   'AL_Dothan': ['AL_file', '_'],
                   'IA_Johnston': ['IA_file', '_'],
                   'LA_Alexandria': ['LA_file', '_'],
                   'AK_Anchorage': ['AK_file', '_'],
                   'MT_Greatfalls': ['MT_file', '_']}

        weatherdat_filenames = EPWtoDAT.main(weather_path_inputs, bus_loc, extract=False, getnames=True,
                                             YYYY_MM_DD="")

        weather_folder_names = {}
        weather_mappings_bldg_name = {}
        weather_mappings_bldg_count = {}
        for list_idx, file_name_dict in enumerate(list_of_names):

            for weather_zone_idx, each_weather_zone in enumerate(weatherdat_filenames):
                t1 = each_weather_zone.split("_")[1] + "_" + each_weather_zone.split("_")[2]
                t1_h = each_weather_zone.split("_")[1] + "_" + each_weather_zone.split("_")[2]
                if t1 not in weather_folder_names.keys():
                    weather_folder_names[t1] = {}
                    weather_mappings_bldg_name[t1] = {}
                    weather_mappings_bldg_count[t1] = {}

                file_name = file_name_dict[t1_h]

                site_folder_names, mappings_bldg_name, mappings_bldg_count = ingest_bld_data.main(
                    "", "",
                    os.getcwd() + '/',
                    weather_loc='FilesfromFEDS',
                    file_name=file_name,
                    weather_header=t1_h, extract=False, mapping=True)

                for key_p, value_p in mappings_bldg_name.items():
                    weather_folder_names[t1][key_p] = site_folder_names
                    weather_mappings_bldg_name[t1][key_p] = value_p
                    weather_mappings_bldg_count[t1][key_p] = mappings_bldg_count[key_p]

        saveintojson(weather_folder_names, "weather_folder_names.json", os.getcwd())
        saveintojson(weather_mappings_bldg_name, "weather_mappings_bldg_name.json", os.getcwd())
        saveintojson(weather_mappings_bldg_count, "weather_mappings_bldg_count.json", os.getcwd())



    else:
        weather_folder_names = loadjson("weather_folder_names.json", os.getcwd())
        weather_mappings_bldg_name = loadjson("weather_mappings_bldg_name.json", os.getcwd())
        weather_mappings_bldg_count = loadjson("weather_mappings_bldg_count.json", os.getcwd())

    return weather_folder_names, weather_mappings_bldg_name, weather_mappings_bldg_count



if __name__ == '__main__':
    # Years = [2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038,
    #          2039, 2040]
    # # Years = [2040]
    # Networks = ["Small", "Medium", "Large"]
    # # Networks = ["Medium"]
    # subfolder_count = [2, 10, 17]
    # # subfolder_count = [10]
    # vehicle_inventory_path = "new_output_data"
    # main_path = r"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/"
    # xfrmrrating_evshare = None  # 70  # percent
    # EV_placement_on_grid = "ascen"  # "ascen", "descen", "random"
    # date_name = "mar31"
    # custom_suffix_sim_run = "delete_this2"
    # Approach based on transformer sizes
    #-------------------------------------------------------------------------------------------------------------------
    # # this function adds xfrms to the grid based on size of xfrmr. This function works for ascending and
    # # descending order of xfrmr assignments but not for random assignments.
    # output_file_save_loc = main(Years, Networks, subfolder_count, main_path, xfrmrrating_evshare, EV_placement_on_grid,
    #                             date_name, custom_suffix_sim_run, vehicle_inventory_path)



    #-------------------------------------------------------------------------------------------------------------------
    Years = [2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038,
             2039, 2040]
    # Years = [2040]
    Networks = ["Small", "Medium", "Large"]
    # Networks = ["Medium"]
    subfolder_count = [2, 10, 17]
    # subfolder_count = [10]
    vehicle_inventory_path = "new_output_data"
    main_path = r"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/"
    custom_suffix_sim_run = "delete_this2"
    xfrmrrating_evshare = None
    final_year = 2040
    vehicles_per_port = 2
    no_of_chargers = 3
    no_of_ports_per_charger = 2
    vehicle_at_a_location = no_of_chargers * no_of_ports_per_charger * vehicles_per_port
    load_existing_mapping_bldg_no_to_manually_selected_EVbldgs = True


    # Approach based on cyclic assignment of EVs at selected transformer locations with a knob to adjust infrastructure
    # at each EV charging location (transformer).

    output_file_save_loc = main_cyclic_selective_locs_for_chargers(vehicles_per_port, Years, Networks,
                                                                   subfolder_count, main_path,
                                                                   xfrmrrating_evshare, custom_suffix_sim_run,
                                                                   vehicle_inventory_path, final_year=final_year,
                                                                   max_ports=vehicle_at_a_location, load_existing_mapping_bldg_no_to_manually_selected_EVbldgs= load_existing_mapping_bldg_no_to_manually_selected_EVbldgs)