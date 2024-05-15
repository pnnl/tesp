import pandas as pd
import json
import copy
import random
import math


def read_excel_sheets(xlsx_file, sheet_name=None):
    _df = pd.read_excel(xlsx_file, sheet_name=sheet_name)
    return _df


def _vehicle_number_dict_create(_distribution_df, _tot_number, _year ,_network, vehicle_type):

    _dist_row = _distribution_df.loc[_distribution_df["GridSize"] == _network]
    _vehicle_number_dict = {}
    _distribution_col_names = _distribution_df.columns
    _tot_number_init = _tot_number
    _tot_vehicle_count = 0

    if _tot_number_init == 0:
        mult_by = 0
    else:
        mult_by = 1


    # if vehicle_type == "MHDV":
    #     slack_vehicle = "Trucks"
    # elif  vehicle_type == "LDV":
    #     slack_vehicle = "AllOther"
    # else:
    #     print("Error in vehicle type: use (i) 'MHDV' or (ii) 'LDV' ")
    #     exit()


    # First calculate the number of Ambulances:
    for col_name in _distribution_col_names[1:len(_distribution_col_names)]:
        split_string = col_name.split(' ')
        grid_size_idx = _dist_row[col_name].index[0]
        num = _dist_row[col_name][grid_size_idx]
        if split_string[0] == 'Ambulance':
            # number = num
            # if int(_year) == 2030 and number > 1:
            if (int(_year) == 2030) or (int(_year) == 2035):
                number = 1
            else:
                number = 0
            _vehicle_number_dict[split_string[0]] = number*mult_by
            _tot_vehicle_count += (number*mult_by)
            _tot_number += - (number*mult_by)

    # Then calculate the number of Vehicles that are not Trucks from remaining # of vehicles after # Ambulances:
    for col_name in _distribution_col_names[1:len(_distribution_col_names)]:
        split_string = col_name.split(' ')
        grid_size_idx = _dist_row[col_name].index[0]
        num = _dist_row[col_name][grid_size_idx]
        # if split_string[1] == '%' and split_string[0] != slack_vehicle:
        if split_string[1] == '%':
            number = int(math.floor(_tot_number * (num / 100)))
            _vehicle_number_dict[split_string[0]] = number
            _tot_vehicle_count += number

    # Rest of them should be trucks only
    # for col_name in _distribution_col_names[1:len(_distribution_col_names)]:
    #     split_string = col_name.split(' ')
    #     if split_string[0] == slack_vehicle:
    #         _vehicle_number_dict[split_string[0]] = _tot_number_init-_tot_vehicle_count

    return _vehicle_number_dict

def _select_vehicles(vehicle_master_df, _vehicle_name_dict, _vehicle_number_dict, vehicle_type):

    if vehicle_type == "MHDV":
        dict_name_key = "MHDV_name_dict"
    elif vehicle_type == "LDV":
        dict_name_key = "LDV_name_dict"
    else:
        print("Error in vehicle type: use (i) 'MHDV' or (ii) 'LDV' ")
        exit()

    selected_df = pd.DataFrame()

    for _vehicle in  _vehicle_number_dict:
        curr_vehicle_ls_case_sensative = _vehicle_name_dict[dict_name_key][_vehicle]
        curr_vehicle_ls = [i.casefold() for i in curr_vehicle_ls_case_sensative]

        curr_vehicle_tot_number = _vehicle_number_dict[_vehicle]
        if any(vehicle_master_df['Vehicle type (POV, M/H)'].isin(curr_vehicle_ls)) == False:
            continue

        vehicle_select_df = vehicle_master_df.loc[vehicle_master_df['Vehicle type (POV, M/H)'].isin(curr_vehicle_ls)]
        all_vehicle_idx = list(vehicle_select_df['Vehicle ID'].values)
        if curr_vehicle_tot_number != 0:
            vehicle_idx = random.sample(all_vehicle_idx, curr_vehicle_tot_number)
            included_filtered_df = vehicle_master_df[vehicle_master_df['Vehicle ID'].isin(vehicle_idx)]
            excluded_filtered_df = vehicle_master_df[~vehicle_master_df['Vehicle ID'].isin(vehicle_idx)]
            vehicle_master_df = excluded_filtered_df.copy(deep=False)
            selected_df = pd.concat([selected_df, included_filtered_df], ignore_index=True)
        else:
            continue

    return vehicle_master_df, selected_df

def vehicle_sample_df( _vehicle_name_dict, _vehicle_master_df, _vehicle_config_data, year, network):

    vehicle_master_df = _vehicle_master_df.copy(deep=True)
    vehicle_name_dict = copy.deepcopy(_vehicle_name_dict)
    MHDV_distribution_df = read_excel_sheets(_vehicle_config_data, sheet_name='MHDV_distribution')
    LDV_distribution_df = read_excel_sheets(_vehicle_config_data, sheet_name='LDV_distribution')
    MHDV_tot_number_year_df = read_excel_sheets(_vehicle_config_data, sheet_name='MHDV')
    LDV_tot_number_year_df = read_excel_sheets(_vehicle_config_data, sheet_name='LDV')

    MHDV_tot_number = MHDV_tot_number_year_df.loc[MHDV_tot_number_year_df['Year'] == year, network].values[0]
    LDV_tot_number = LDV_tot_number_year_df.loc[LDV_tot_number_year_df['Year'] == year, network].values[0]

    MHDV_vehicle_number_dict = _vehicle_number_dict_create(MHDV_distribution_df, MHDV_tot_number, year, network, vehicle_type="MHDV")
    LDV_vehicle_number_dict = _vehicle_number_dict_create(LDV_distribution_df, LDV_tot_number, year, network, vehicle_type="LDV")

    vehicle_master_df, MHDV_selected_df = _select_vehicles(vehicle_master_df, vehicle_name_dict,
                                                          MHDV_vehicle_number_dict, vehicle_type="MHDV")
    vehicle_master_df, LDV_selected_df = _select_vehicles(vehicle_master_df, vehicle_name_dict, LDV_vehicle_number_dict,
                                                         vehicle_type="LDV")

    all_selected_df = pd.concat([MHDV_selected_df, LDV_selected_df], ignore_index=True)

    return vehicle_master_df, all_selected_df





