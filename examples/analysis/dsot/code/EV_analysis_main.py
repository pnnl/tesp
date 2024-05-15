import os
import random, decimal
import pandas as pd
import numpy as np
import json

import GenerateVehicleInventoryFromAdaptionData
import MapEVstoGridLocations
import ev_times
import EV_uncontrolled_case
import glob
import DSOT_post_processing_aggregated_folders
import scm_main

def implement_assumptions_on_vehicle_inventory(randomsoc, output_file_save_loc, value, year):
    if randomsoc:
        # load the csv file, make changes and save it back
        path = f"{output_file_save_loc}/vehicle_master_{value}_Year_{year}.xlsx"
        data = pd.read_excel(path, sheet_name=['main_info', 'locationAndPorts'])

        EV_info = data['main_info']
        loc_p_port_df = data['locationAndPorts']

        EV_info['max SOC'] = [float(decimal.Decimal(random.randrange(60, 90)) / 100) for k in EV_info.index]

        with pd.ExcelWriter(
                f"{output_file_save_loc}/vehicle_master_{value}_Year_{year}_randmaxsoc.xlsx") as writer:
            EV_info.to_excel(writer, sheet_name='main_info', index=False)
            loc_p_port_df.to_excel(writer, sheet_name='locationAndPorts', index=False)


def main(date_name, EV_preprocess_localization_skip, EV_placement_on_grid, extract_load_forecast, uncontrolled,
         xfrmrrating_evshare, num_days, num_hours, depletionassumption, sens_flag, size_of_batch, randomsoc,
         customsuffix_list, size_name_list, zone_name_list_list, state_list_list, folder_list_list,
         custom_suffix_sim_run, custom_suffix_sim_run_uncontrolled, controlled, threshold_cutoff, smooth):

    if not EV_preprocess_localization_skip:
        # generate the EV inventory based on adaption data. This will create a folder "output_data" that will have vehicle
        # inventory for large, medium, small and all years worth of inventory.
        output_path = "output_data"
        input_path = "input_data"
        Years, Networks = GenerateVehicleInventoryFromAdaptionData.main(output_path, input_path)

        # Remove a column that is not used and also adjust the "start time" and "end time" of vehicle inventory data's
        # charging time such that it follows NREL's fleet DNA data.
        output_path = "new_" + output_path
        os.makedirs(output_path, exist_ok=True)
        offset_main_logic = True  # impact peak EV demand significantly.
        ev_times.main(offset_main_logic)

        # Add location and port information to each vehicle inventory file and keep it consistent across years (a vehicle if
        # introduced in 2030 goes to location A then it always goes to location A until year 2040).
        subfolder_count = [subfolder_count_dic[value] for value in Networks]  # [2, 10, 17]
        main_path = r"/home/gudd172/tesp/repository/tesp/examples/analysis/dsot/code/"

        # my_main_loc = os.getcwd()
        # os.chdir(f"{output_path}/")
        # all_files = glob.glob('./*.csv')
        # Networks_updt = [x.split("_")[2] for x in all_files]
        # Years_updt = [x.split("_")[4].split(".")[0] for x in all_files]
        # os.chdir(my_main_loc)
        # this function not only adds xfrms to the grid but it also create the load forecast files for SCM
        output_file_save_loc = MapEVstoGridLocations.main(Years, Networks, subfolder_count, main_path,
                                                          xfrmrrating_evshare, EV_placement_on_grid, date_name,
                                                          custom_suffix_sim_run_uncontrolled, vehicle_inventory_path = output_path)
    else:
        output_file_save_loc = f"final_vehicle_inventory_{custom_suffix_sim_run_uncontrolled}"


    # loop through all xlsx files (for all years and sizes)
    my_main_loc = os.getcwd()
    os.chdir(f"{output_file_save_loc}/")
    all_files = glob.glob('./*.xlsx')
    size_list = [x.split("_")[2] for x in all_files]
    year_list = [x.split("_")[4].split(".")[0] for x in all_files]
    os.chdir(my_main_loc)

    # size_list = ["Small", "Medium", "Large", "Small", "Medium", "Large", "Small", "Medium", "Large"]
    # year_list = [2027, 2027, 2027, 2035, 2035, 2035, 2040, 2040, 2040]

    random.seed(42)  # Set the random number generator to a fixed sequence.

    # if not uncontrolled:

    if not depletionassumption:
        print(
            "do not make depletionassumption flag False. because then SCM depletion assumption constraint also needs "
            "a proper fix which is currently not automated.")
        exit()
    if extract_load_forecast:
        # extract load forecast in all subfolders
        # create load forecast input for SCM planning

        os.makedirs(f"Forecast_from_gld_{date_name}", exist_ok=True)
        for main_loop_idx, customsuffix in enumerate(customsuffix_list):
            size_name = size_name_list[main_loop_idx]
            zone_name_list = zone_name_list_list[main_loop_idx]
            state_list = state_list_list[main_loop_idx]
            folder_list = folder_list_list[main_loop_idx]

            for iiidxx, zone_name in enumerate(zone_name_list):
                state = state_list[iiidxx]
                total_folders = folder_list[iiidxx]
                # folder_names = [f"{zone_name}_{customsuffix}_{ji + 1}_fl" for ji in range(0, total_folders)]

                consolidated_df_in_va = pd.DataFrame()
                cnsolidated_xfrmr_to_size_map = dict()
                for ji in range(0, total_folders):

                    each_subfolder_name = f"{zone_name}_{customsuffix}_{ji + 1}_fl"
                    print(f"Processing = {each_subfolder_name}")
                    path = os.getcwd() + '/' + each_subfolder_name + '/Substation_1/'

                    subfolder_df_in_VA, sub_xfrmr_tosize_map = DSOT_post_processing_aggregated_folders.extract_demand_forecast_from_gld(path, ji+1)
                    cnsolidated_xfrmr_to_size_map.update(sub_xfrmr_tosize_map)
                    if ji == 0:
                        consolidated_df_in_va = pd.concat([consolidated_df_in_va, subfolder_df_in_VA])
                    else:
                        subfolder_df_in_VA = subfolder_df_in_VA.drop('# timestamp', axis=1)
                        consolidated_df_in_va = pd.concat([consolidated_df_in_va, subfolder_df_in_VA], axis=1)

                # convert the transformer names into dummy names using the mapping generated from ev localization on
                # grid.
                # PS: The mapping of xfrmr to dummy locations is same for all years...thats how I coded it in
                # MapEVstoGridLocations.main().
                # load 2040 xfrmr mapping size for "given size" (mapping of real to dummy names remains same across
                # different climate zones, years).
                size_here = zone_name.split("_")[2]
                map_filename_here = f"{output_file_save_loc}/xfrmr_map_{size_here}_Year_2040.json"
                with open(os.getcwd() + '/' + map_filename_here, 'r') as fp:
                    real_to_dummy_mapping = json.load(fp)

                consolidated_df_in_va = consolidated_df_in_va.rename(columns=real_to_dummy_mapping)
                # base load has one extra time stamp at the end, need to drop it
                n = 1
                consolidated_df_in_va.drop(consolidated_df_in_va.tail(n).index, inplace=True)  # drop last n rows

                # make it hourly
                consolidated_df_in_va['# timestamp'] = pd.to_datetime(consolidated_df_in_va['# timestamp'])
                consolidated_df_in_va = consolidated_df_in_va.groupby(
                    consolidated_df_in_va['# timestamp'].dt.to_period('H')).first()

                # add "day" and "hour" columns
                consolidated_df_in_va["hour"] = consolidated_df_in_va['# timestamp'].dt.hour
                consolidated_df_in_va["day"] = consolidated_df_in_va['# timestamp'].dt.day

                # reorder the rows of pandas so the SCM does not need to reorder its inputs.
                reordered_df = pd.DataFrame()
                all_days = list(np.unique(list(consolidated_df_in_va["day"])))
                for day in all_days:
                    day_mask = consolidated_df_in_va["day"] == day
                    day_df = consolidated_df_in_va[day_mask]
                    # slice from 8 to 24
                    day_reorder = pd.concat([day_df[8:24:1], day_df[0:8:1]])
                    reordered_df = pd.concat([reordered_df, day_reorder])
                reordered_df.reset_index(drop=True)
                # k = 1

                reordered_df.to_csv(os.getcwd() + f"/Forecast_from_gld_{date_name}/" + f"{zone_name}_grid_forecast.csv",
                                             index=False)
                with open(os.getcwd() + f"/Forecast_from_gld_{date_name}/" + f"{zone_name}_grid_real_to_dummy_mapping.json", 'w',
                          encoding='utf-8') as f:
                    json.dump(real_to_dummy_mapping, f, ensure_ascii=False, indent=4)

                # cnsolidated_xfrmr_to_size_map
                xfrmr_dummy_to_size_map = dict()
                for real_name, dummy_name in real_to_dummy_mapping.items():
                    size_corres_here = cnsolidated_xfrmr_to_size_map[real_name]
                    xfrmr_dummy_to_size_map[dummy_name] = size_corres_here

                with open(os.getcwd() + f"/Forecast_from_gld_{date_name}/" + f"{zone_name}_grid_dummy_to_size_mapping.json", 'w',
                          encoding='utf-8') as f:
                    json.dump(xfrmr_dummy_to_size_map, f, ensure_ascii=False, indent=4)

                    # k = 1
    # exit()
    if randomsoc:
        for idx, value in enumerate(size_list):
            # implement randomsoc assumption to each year's vehicle inventory. fix the random seed. So the
            # conditions remain same everytime its run and both uncontrolled+controlled have same setup.
            implement_assumptions_on_vehicle_inventory(randomsoc, output_file_save_loc, value, year_list[idx])


    if uncontrolled:
        for idx, value in enumerate(size_list):

            if randomsoc:
                path = f"{output_file_save_loc}/vehicle_master_{value}_Year_{year_list[idx]}_randmaxsoc.xlsx"
            else:
                path = f"{output_file_save_loc}/vehicle_master_{value}_Year_{year_list[idx]}.xlsx"


            os.makedirs(f"Uncontrolled_results_{custom_suffix_sim_run_uncontrolled}", exist_ok=True)
            outputfilename = f"Uncontrolled_results_{custom_suffix_sim_run_uncontrolled}/uncontrolled_{value}_Year_{year_list[idx]}.csv"
            # NOTE: made EVs deplete 70% of their soc during their travel time: assumption i.e., depletion assumption = True!!!
            all_load_days, per_day_profile, loads_at_locations, main_output_df = (
                EV_uncontrolled_case.main(path, num_days, num_hours, outputfilename, depletionassumption))

    if controlled:
        failed_xfrmr_df = pd.DataFrame()
        for idx, value in enumerate(size_list):

            if randomsoc:
                path = f"{output_file_save_loc}/vehicle_master_{value}_Year_{year_list[idx]}_randmaxsoc.xlsx"
            else:
                path = f"{output_file_save_loc}/vehicle_master_{value}_Year_{year_list[idx]}.xlsx"

            os.makedirs(f"Controlled_results_{custom_suffix_sim_run}", exist_ok=True)


            if value == 'Large':
                zone_name_list_h = ["AZ_Tucson_Large", "WA_Tacoma_Large", "AL_Dothan_Large", "LA_Alexandria_Large"]
            elif value == 'Small':
                zone_name_list_h = ["AZ_Tucson_Small", "WA_Tacoma_Small", "AL_Dothan_Small", "IA_Johnston_Small",
                                    "LA_Alexandria_Small", "AK_Anchorage_Small", "MT_Greatfalls_Small"]
            elif value == 'Medium':
                zone_name_list_h = ["AZ_Tucson_Medium", "WA_Tacoma_Medium", "AL_Dothan_Medium", "IA_Johnston_Medium",
                                    "LA_Alexandria_Medium", "AK_Anchorage_Medium",
                                    "MT_Greatfalls_Medium"]
            else:
                zone_name_list_h = None


            for each_zone in zone_name_list_h:
                main_path_h = os.getcwd()

                inventory_filename = path
                grid_forecast_filename = f"Forecast_from_gld_{date_name}/{each_zone}_grid_forecast.csv"

                xfmr_rating_data_filename = f"Forecast_from_gld_{date_name}/{each_zone}_grid_dummy_to_size_mapping.json"

                outputfilename1 = f"Controlled_results_{custom_suffix_sim_run}/controlled_xfrmr_{each_zone}_Year_{year_list[idx]}.csv"
                outputfilename2 = f"Controlled_results_{custom_suffix_sim_run}/controlled_ev_{each_zone}_Year_{year_list[idx]}.csv"
                outputfilename3 = f"Controlled_results_{custom_suffix_sim_run}/controlled_ev_energy_{each_zone}_Year_{year_list[idx]}.csv"

                print(f"Processing year = {year_list[idx]}, grid size and climate zone = {each_zone}...")

                failed_xfrmrs = scm_main.main(inventory_filename, grid_forecast_filename, size_of_batch, xfmr_rating_data_filename,
                              outputfilename1, outputfilename2, sens_flag, threshold_cutoff, smooth, outputfilename3)

                current_df = pd.DataFrame()
                if len(failed_xfrmrs) != 0:
                    current_df["Dummy name"] = failed_xfrmrs
                    current_df["Zone and size"] = each_zone
                    current_df["Year"] = year_list[idx]
                    failed_xfrmr_df = pd.concat([failed_xfrmr_df, current_df])


        failed_xfrmr_df.to_csv(f"Controlled_results_{custom_suffix_sim_run}/failed_xfrmr_SCM_info.csv")

            # folder_path_gld
            # DSOT_post_processing_aggregated_folders.extract_demand_forecast_from_gld(path, num_days, num_hours,
            #                                                                          outputfilename,
            #                                                                          depletionassumption)

            # check if vehicle inventory input is in correct standard format. It is created by "MapEVstoGridLocations".
            # run the scm main
            # save results in the same format as uncontrolled so the plotting scripts can work without many modifications.

    # Save data appropriates at correct locations. This way, the plotting script does its job easily when plotting the
    # results.

if __name__ == '__main__':
    # sens_flag_list = ["tight", "relax"]

    sens_flag_list = ["tight"]

    # threshold_list = [1, 0.9, 0.8, 0.5]

    threshold_list = [1]

    for sens_flag2 in sens_flag_list:
        # sens_flag2 = "tight"
        # idx_loop = 0
        for idx_loop, threshold_cutoff in enumerate(threshold_list):

            # ------------------------ parameters ---------------------------------------------------
            date_name = f"april21_{sens_flag2}"
            # ------------------------- vehicle inventory and EV placement on grid parameters ------------------------------
            subfolder_count_dic = {"Small": 2, "Medium": 10, "Large": 17}  # vehicle inventory
            if idx_loop == 0:
                EV_preprocess_localization_skip = False
            else:
                EV_preprocess_localization_skip = True

            EV_placement_on_grid = "ascen"  # "ascen", "descen", "random"
            # -------------------------- load forecast from gridlabd parameters -------------------------
            if idx_loop == 0:
                extract_load_forecast = True  # NOTE: make sure the length of timestamp column is same for uncontroleld and SCM!
            # 7*24 = 168 rows of timestamp needed in gld load forecast csv file from each subfolder.
            # NOTE: If load forecast has 169 rows (expected behavior from gld), the last row is "ALWAYS" removed (search for
            # ".tail" in this .py file) from the load forecast to match 168 (as in this example). Simple tip would be look for
            # 169 timestamp values in gld output and expect last timestamp to be hour of nextday for which rest of hours dont
            # exist.
            else:
                extract_load_forecast = False

            customsuffix_l = "feb12_runs"
            customsuffix_m = "feb24_runs"
            customsuffix_s = "feb24_runs"
            size_name_l = "large"
            size_name_m = "medium"
            size_name_s = "small"
            zone_name_list_l = ["AZ_Tucson_Large", "WA_Tacoma_Large", "AL_Dothan_Large", "LA_Alexandria_Large"]
            zone_name_list_s = ["AZ_Tucson_Small", "WA_Tacoma_Small", "AL_Dothan_Small", "IA_Johnston_Small",
                                "LA_Alexandria_Small", "AK_Anchorage_Small", "MT_Greatfalls_Small"]
            zone_name_list_m = ["AZ_Tucson_Medium", "WA_Tacoma_Medium", "AL_Dothan_Medium", "IA_Johnston_Medium",
                                "LA_Alexandria_Medium", "AK_Anchorage_Medium",
                                "MT_Greatfalls_Medium"]  # ["AZ_Tucson_Medium", "WA_Tacoma_Medium"]
            state_list_l = ["az", "wa", "al", "la"]
            state_list_m = ["az", "wa", "al", "ia", "la", "ak", "mt"]
            state_list_s = ["az", "wa", "al", "ia", "la", "ak", "mt"]
            folder_list_l = [17, 17, 17, 17]
            folder_list_s = [2, 2, 2, 2, 2, 2, 2]
            folder_list_m = [10, 10, 10, 10, 10, 10, 10]

            customsuffix_list = [customsuffix_l, customsuffix_m, customsuffix_s]
            size_name_list = [size_name_l, size_name_m, size_name_s]
            zone_name_list_list = [zone_name_list_l, zone_name_list_m, zone_name_list_s]
            state_list_list = [state_list_l, state_list_m, state_list_s]
            folder_list_list = [folder_list_l, folder_list_m, folder_list_s]

            # ---------------------- uncontrolled parameters ----------------------------------------
            if idx_loop == 0:
                uncontrolled = True
            else:
                uncontrolled = False

            xfrmrrating_evshare = 70  # percent, for EV assignment on grid or xfrmrs
            num_days = 7  # Defining number of days for uncontrolled
            num_hours = 24  # Defining number of hours in each day for uncontrolled
            depletionassumption = True  # this assumption is separately handled in both uncontrolled and controlled script.
            # Always leave it True for now.

            # -----------------------------SCM parameters --------------------------------------------
            controlled = True
            sens_flag = sens_flag2  # "tight"  # "relax", "tight" for SCM optimization on overload constraint at 100%
            # decide on size of batch SCM
            size_of_batch = 50  # for scm optimization to parallel xfrmrs

            # ------------ shared between uncontrolled and SCM ------------
            randomsoc = True  # this assumption is modified consitently for both uncontrolled and controlled by modifying the
            # common shared input vehicle inventory file.

            # distribute soc growth over available time for peak reduction
            smooth = True

            # custom_suffix_sim_run = f"randsoc{randomsoc}_sensflag{sens_flag}_evongrid{xfrmrrating_evshare}{EV_placement_on_grid}_{date_name}"
            # custom_suffix_sim_run_uncontrolled = f"randsoc{randomsoc}_evongrid{xfrmrrating_evshare}{EV_placement_on_grid}_{date_name}"

            custom_suffix_sim_run = (f"randsoc{randomsoc}_sensflag{sens_flag}_evongrid{xfrmrrating_evshare}"
                                     f"{EV_placement_on_grid}_threshold{threshold_cutoff}_{date_name}")
            custom_suffix_sim_run_uncontrolled = (f"randsoc{randomsoc}_evongrid{xfrmrrating_evshare}"
                                                  f"{EV_placement_on_grid}_{date_name}")

            main(date_name, EV_preprocess_localization_skip, EV_placement_on_grid, extract_load_forecast, uncontrolled,
                 xfrmrrating_evshare, num_days, num_hours, depletionassumption, sens_flag, size_of_batch, randomsoc,
                 customsuffix_list, size_name_list, zone_name_list_list, state_list_list, folder_list_list,
                 custom_suffix_sim_run, custom_suffix_sim_run_uncontrolled, controlled, threshold_cutoff, smooth)

