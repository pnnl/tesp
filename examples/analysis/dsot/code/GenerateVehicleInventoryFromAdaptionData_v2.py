
import pandas as pd
import json
import openpyxl
import os

from vehicle_df_create_v2 import vehicle_sample_df

sampling_povs = True

def create_vehicle_name_ls():
    MHDV_name_dict = {"Ambulance": ["HD Vehicle (ambulance)"],
                 "Buses": ["HD Vehicle (bus)"],
                 "Vans": ["MD Van (cargo)", "MD Van (passenger)"],
                 "Trucks": ["HD Truck", "MD Vehicle", "MD Pickup", "MD SUV"]
                 }

    LDV_name_dict = {"Ambulance": [],
                 "AllOther": ["LD vehicle 4x2", "LD Pickup 4x2", "LD Pickup 4x4", "LD SUV 4x4"],
                 "Vans": ["LD Minivan 4x2 (cargo)", "LD Minivan 4x2 (passenger)","LD Van 4x2 (cargo)",
                          "LD Van 4x2 (passenger)"],
                 "Sedan": ["sedan/St Wgn compact", "sedan/St Wgn midsize", "sedan/St Wgn subcompact"]
                 }

    _vehicle_name_dict = {"MHDV_name_dict": MHDV_name_dict, "LDV_name_dict": LDV_name_dict}
    dump_json_file('input_data/vehicle_name_dict.json', _vehicle_name_dict)


def read_excel_sheets(xlsx_file, sheet_name=None):
    _df = pd.read_excel(xlsx_file, sheet_name=sheet_name)
    return _df

def dump_json_file(file_path, json_data):
    with open(file_path, 'w') as file:
        json.dump(json_data, file, indent=4)

def read_json_file(file):
    with open(file, 'r') as f:
        data = json.load(f)
    return data

def main(output_path, input_path):
    vehicle_master_file = f"{input_path}/ev_data_input_scm_07_09_24.xlsx"
    # vehicle_master_file = "input_data/vehicle_master_file.xlsx"
    os.makedirs(f"{output_path}", exist_ok=True)

    # create_vehicle_name_ls()
    # vehicle_name_dict_gov = read_json_file("input_data/vehicle_name_dict_gov.json")
    # vehicle_config_data_gov = "input_data/vehicle_config_data_gov.xlsx"

    vehicle_name_dict_gov = read_json_file(f"{input_path}/vehicle_name_dict_gov.json")
    vehicle_config_data_gov = f"{input_path}/vehicle_config_data_gov.xlsx"

    vehicle_name_dict_pov = read_json_file(f"{input_path}/vehicle_name_dict_pov.json")
    vehicle_config_data_pov = f"{input_path}/vehicle_config_data_pov.xlsx"

    Networks = ["Small", "Medium", "Large"]
    # year = 2025
    # network = "Large"
    for network in Networks:
        if network == "Large":
            sheet_name = 'load_large'
        elif network == "Medium":
            sheet_name = 'load_medium'
        elif network == "Small":
            sheet_name = 'load_small'

        vehicle_master_df_case_sensative = read_excel_sheets(vehicle_master_file, sheet_name=sheet_name)

        vehicle_master_df_case_sensative.loc[:, 'Vehicle type (POV, M/H)'] = [i.casefold() for i in
                                                                              vehicle_master_df_case_sensative.loc[:,
                                                                              'Vehicle type (POV, M/H)']]
        vehicle_master_df_case_sensative['Vehicle type (POV, M/H)'] = vehicle_master_df_case_sensative[
            'Vehicle type (POV, M/H)'].str.strip()
        vehicle_master_df = vehicle_master_df_case_sensative.copy(deep=True)

        if sampling_povs:
            vehicle_master_df_case_sensative_pov = read_excel_sheets(vehicle_master_file, sheet_name=sheet_name)
            vehicle_master_df_case_sensative_pov.loc[:, 'POVs/GOVs'] = [i.casefold() for i in
                                                                        vehicle_master_df_case_sensative_pov.loc[:,
                                                                        'POVs/GOVs']]
            vehicle_master_df_case_sensative_pov['POVs/GOVs'] = vehicle_master_df_case_sensative[
                'POVs/GOVs'].str.strip()
            vehicle_master_df_pov = vehicle_master_df_case_sensative_pov.copy(deep=True)

        # create_vehicle_name_ls()
        # vehicle_name_dict = read_json_file("input_data/vehicle_name_dict.json")
        # vehicle_config_data = "input_data/vehicle_config_data.xlsx"

        # For loop in here ---
        Years = [2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038, 2039,
                 2040, 2041, 2042]
        all_selected_df_prev = pd.DataFrame()
        all_selected_df_prev_pov = pd.DataFrame()

        for year in Years:

            vehicle_master_edited_df, all_selected_df = vehicle_sample_df(vehicle_name_dict_gov, vehicle_master_df,
                                                                          vehicle_config_data_gov, year=year,
                                                                          network=network, pov_flag=0)

            save_file_name = network + "_GOV_Year_" + str(year)
            output_file = f"{output_path}/vehicle_master_" + save_file_name + ".csv"
            all_selected_df = pd.concat([all_selected_df, all_selected_df_prev], ignore_index=True)

            # all_selected_df.to_csv(output_file, index=False)

            vehicle_master_df = vehicle_master_edited_df.copy(deep=True)
            all_selected_df_prev = all_selected_df.copy(deep=True)

            if sampling_povs:
                vehicle_master_edited_df_pov, all_selected_df_pov = vehicle_sample_df(vehicle_name_dict_pov,
                                                                                      vehicle_master_df_pov,
                                                                                      vehicle_config_data_pov,
                                                                                      year=year, network=network,
                                                                                      pov_flag=1)
                save_file_name = network + "_POV_Year_" + str(year)
                output_file = f"{output_path}/vehicle_master_" + save_file_name + ".csv"
                all_selected_df_pov = pd.concat([all_selected_df_pov, all_selected_df_prev_pov], ignore_index=True)

                # all_selected_df_pov.to_csv(output_file, index=False)

                vehicle_master_df_pov = vehicle_master_edited_df_pov.copy(deep=True)
                all_selected_df_prev_pov = all_selected_df_pov.copy(deep=True)

        # finished GOV and POV generation for a particular grid size. Merge both POV and GOV data into single file with
        # a column that shows GOV or POV
            all_selected_gov_pov_current_year = pd.concat([all_selected_df, all_selected_df_pov], ignore_index=True)
            output_file = f"{output_path}/vehicle_master_" + network + "_Year_" + str(year) + ".csv"
            all_selected_gov_pov_current_year.to_csv(output_file, index=False)


    print("here")
    return Years, Networks

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    vehicle_master_file = "input_data/ev_data_input_scm_07_09_24.xlsx"
    # vehicle_master_file = "input_data/vehicle_master_file.xlsx"
    os.makedirs("output_data", exist_ok=True)

    # create_vehicle_name_ls()
    # vehicle_name_dict_gov = read_json_file("input_data/vehicle_name_dict_gov.json")
    # vehicle_config_data_gov = "input_data/vehicle_config_data_gov.xlsx"
    
    vehicle_name_dict_gov = read_json_file("input_data/vehicle_name_dict_gov.json")
    vehicle_config_data_gov = "input_data/vehicle_config_data_gov.xlsx"
    
    vehicle_name_dict_pov = read_json_file("input_data/vehicle_name_dict_pov.json")
    vehicle_config_data_pov = "input_data/vehicle_config_data_pov.xlsx"

    Networks = ["Small", "Medium", "Large"]
    # year = 2025
    # network = "Large"
    for network in Networks:
        if network == "Large":
            sheet_name = 'load_large'
        elif network == "Medium":
            sheet_name = 'load_medium'
        elif network == "Small":
            sheet_name = 'load_small'

        vehicle_master_df_case_sensative = read_excel_sheets(vehicle_master_file, sheet_name=sheet_name)

        vehicle_master_df_case_sensative.loc[: ,'Vehicle type (POV, M/H)'] =[ i.casefold() for i in vehicle_master_df_case_sensative.loc[: ,'Vehicle type (POV, M/H)'] ]
        vehicle_master_df_case_sensative['Vehicle type (POV, M/H)'] = vehicle_master_df_case_sensative['Vehicle type (POV, M/H)'].str.strip()
        vehicle_master_df = vehicle_master_df_case_sensative.copy(deep=True)
        
        if sampling_povs:
            vehicle_master_df_case_sensative_pov = read_excel_sheets(vehicle_master_file, sheet_name=sheet_name)
            vehicle_master_df_case_sensative_pov.loc[: ,'POVs/GOVs'] =[ i.casefold() for i in vehicle_master_df_case_sensative_pov.loc[: ,'POVs/GOVs'] ]
            vehicle_master_df_case_sensative_pov['POVs/GOVs'] = vehicle_master_df_case_sensative['POVs/GOVs'].str.strip()
            vehicle_master_df_pov = vehicle_master_df_case_sensative_pov.copy(deep=True)
                


        # create_vehicle_name_ls()
        # vehicle_name_dict = read_json_file("input_data/vehicle_name_dict.json")
        # vehicle_config_data = "input_data/vehicle_config_data.xlsx"


        # For loop in here ---
        Years = [2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038, 2039, 2040, 2041, 2042]
        all_selected_df_prev = pd.DataFrame()
        all_selected_df_prev_pov = pd.DataFrame()
        
        for year in Years:
            
            vehicle_master_edited_df, all_selected_df = vehicle_sample_df(vehicle_name_dict_gov, vehicle_master_df, vehicle_config_data_gov, year = year, network= network, pov_flag = 0)

            save_file_name = network + "_GOV_Year_" + str(year)
            output_file = "output_data/vehicle_master_"+save_file_name+".csv"
            all_selected_df = pd.concat([all_selected_df, all_selected_df_prev], ignore_index=True)

            all_selected_df.to_csv(output_file, index=False)

            vehicle_master_df = vehicle_master_edited_df.copy(deep=True)
            all_selected_df_prev = all_selected_df.copy(deep=True)
            
            if sampling_povs:
                vehicle_master_edited_df_pov, all_selected_df_pov = vehicle_sample_df(vehicle_name_dict_pov, vehicle_master_df_pov, vehicle_config_data_pov, year = year, network= network, pov_flag = 1)
                save_file_name = network + "_POV_Year_" + str(year)
                output_file = "output_data/vehicle_master_"+save_file_name+".csv"
                all_selected_df_pov = pd.concat([all_selected_df_pov, all_selected_df_prev_pov], ignore_index=True)
                
                all_selected_df_pov.to_csv(output_file, index=False)
                
                vehicle_master_df_pov = vehicle_master_edited_df_pov.copy(deep=True)
                all_selected_df_prev_pov = all_selected_df_pov.copy(deep=True)



    print("here")




