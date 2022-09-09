# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: dso_map.py

import csv
import json

import pandas as pd
import requests
import xlrd

'''
This script automatically creates the 200 bus meta data files.


The following DSO specific parameters are instantiated

"bus_number"
"name"
"climate_zone" - feeder taxonomy climate zone
"latitude" 
"longitude" 
"time_zone_offset" 
"BLM_zone" TODO: add BLM Zone
"utility_type" : "Urban", "Suburban", Rural
"ownership_type" :   TODO: add ownership type to inputs
"peak_season" : "Summer",
"substation": 
"random_seed": Used to ensure each DSO is different and repeatable.
"feeders": {"feeder1" : { "name": "",  "ercot": false }},
"RCI energy mix" : {
      "residential" : ,
      "commercial" : ,
      "industrial" : },
"number_of_customers" 
"number_of_gld_homes" 
"comm_customers_per_bldg"
"number_of_substations" 
"MVA_growth_rate" 
"weather_file" 
"ashrae_zone" - ASHRAE Climate Zone
"RCI customer count mix" : {
      "residential" : ,
      "commercial" : ,
      "industrial" : },
"average_load_MW" : 
"total_load_time_series_file" : "",
"industrial_load_time_series_file" : "",
"winter_peak_MW" : 
"summer_peak_MW" : 
"capacity_limit_MW" : 
"scaling_factor" : DEPRECATE?
"substation_upgrade" : {
      "greenfield_MVA" : [
        111,
        111
      ],
      "brownfield_MVA" : [
        111,
        111
      ]
    },
    "substation_transformer_count" : 111,
    "bilaterals" : {
      "price" : 11.11,
      "load_fraction" : 0.11
    },
    "DSO_system_energy_fraction" : 0.11

'''

# ========   INPUT SETTINGS  ========================
data_path = '../../../examples/analysis/dsot/data/'
case_path = '../../../examples/analysis/dsot/code/'
# case_path = '../../../examples/capabilities/ercot/case8/dsostub/'
# case_path = '../../../examples/capabilities/ercot/case8/'

write_case_config = True  # Set true when wanting to update the QMax values in the system_case_config FNCS array
find_county = False  # Set True if you need to use API to find county as a function of latitude and longitude
write_industrials = False  # Set True if you want to write out the industrial load tape.


# ========   END INPUT SETTINGS  ========================


def prepare_metadata(node, end_row, feeder_mode, high_renewables_case, DSO_Load_Threshold):
    sheet_name = node + 'BusValues'
    if high_renewables_case:
        case_file = node + "-hi-metadata-" + feeder_mode
        config_file = node + "_hi_system_case_config"
    else:
        case_file = node + "-metadata-" + feeder_mode
        config_file = node + "_system_case_config"

    if find_county:
        out = csv.writer(open("county.csv", "w"), delimiter=',', lineterminator='\n')
    if write_industrials:
        dso_list = []
        indust_load_list = []
    use_dso_list = []

    book = xlrd.open_workbook(data_path + 'bus_mapping.xlsx')
    sheet = book.sheet_by_name(sheet_name)

    # os.rename(case_path + case_file + '.json', case_path + case_file + '_old.json')

    with open(data_path + 'metadata-general.json') as json_file:
        data = json.load(json_file)

        # # Clear out all existing DSOs in the file
        # for key in list(data.keys()):
        #     if 'DSO' in key:
        #         del data[key]

        # Get values from spreadsheet
        for irow in range(2, end_row):
            busid = int(sheet.cell(irow, 4).value)
            busname = sheet.cell(irow, 6).value
            climatezone = int(sheet.cell(irow, 7).value)
            ashrae_zone = sheet.cell(irow, 10).value
            blm_zone = int(sheet.cell(irow, 11).value)
            latitude = sheet.cell(irow, 0).value
            longitude = sheet.cell(irow, 1).value
            utiltype = sheet.cell(irow, 8).value
            if utiltype == 'Town':
                utiltype = 'Suburban'
            ownership_type = sheet.cell(irow, 9).value
            peakseason = sheet.cell(irow, 14).value
            county = sheet.cell(irow, 34).value
            roof_top_PV_MW = sheet.cell(irow, 38).value

            if high_renewables_case:
                max_load = sheet.cell(irow, 40).value
            else:
                max_load = sheet.cell(irow, 39).value
            congestion_factor = sheet.cell(irow, 41).value
            bus_simulated = sheet.cell(irow, 42).value

            total_average_load = sheet.cell(irow, 16).value
            if total_average_load == 0:
                total_average_load = 0.001
            res_average_load = sheet.cell(irow, 19).value
            comm_average_load = sheet.cell(irow, 20).value
            indust_average_load = sheet.cell(irow, 21).value

            res_customers = int(sheet.cell(irow, 25).value)
            comm_customers = int(sheet.cell(irow, 26).value)
            indust_customers = int(sheet.cell(irow, 27).value)
            total_customers = res_customers + comm_customers + indust_customers
            # Need to have non-zero residential customers for prepare case to run
            if total_customers == 0:
                total_customers = 1
                res_customers = 1
            if write_industrials:
                dso_list.append("Bus" + str(busid))
                indust_load_list.append(round(indust_average_load, 1))

            if find_county:
                # Find county by lat and longitude
                # From https://geo.fcc.gov/api/census/
                response = requests.get("https://geo.fcc.gov/api/census/area?lat=" + str(latitude) + "&lon=" + str(longitude) + "&format=json")
                test = json.loads(response.content.decode("utf-8"))
                county = test['results'][0]['county_name']
                out.writerow([latitude, longitude, county])

            # Values for lean version
            if feeder_mode == 'lean':
            #     if utiltype == "Rural":
            #         feeders = {"feeder1": {"name": "R4-25.00-1", "ercot": False},
            #                    "feeder2": {"name": "R5-12.47-3", "ercot": False}}
            #         num_gld_homes = 2192
            #     elif utiltype == "Suburban":
            #         if climatezone == 3:
            #             feeders = {"feeder1": {"name": "R3-12.47-3", "ercot": False}}
            #             num_gld_homes = 1326
            #         if climatezone == 4:
            #             feeders = {"feeder1": {"name": "R3-12.47-3", "ercot": False},
            #                        "feeder2": {"name": "R5-12.47-3", "ercot": False}}
            #             num_gld_homes = 2865
            #         if climatezone == 5:
            #             feeders = {"feeder1": {"name": "R5-12.47-1", "ercot": False},
            #                        "feeder2": {"name": "R5-12.47-5", "ercot": False}}
            #             num_gld_homes = 2541
            #     elif utiltype == "Urban":
            #         if climatezone == 3:
            #             # Omitted for now as feeder R3-12.47-1 has large static load
            #             # feeders = {"feeder1": {"name": "R3-12.47-1", "ercot": False},
            #             #            "feeder2": {"name": "R4-12.47-1", "ercot": False}}
            #             # num_gld_homes = 980
            #             feeders = {"feeder1": {"name": "R4-12.47-1", "ercot": False},
            #                        "feeder2": {"name": "R5-12.47-1", "ercot": False}}
            #             num_gld_homes = 1525
            #         if climatezone == 4:
            #             feeders = {"feeder1": {"name": "R4-12.47-1", "ercot": False},
            #                        "feeder2": {"name": "R4-12.47-2", "ercot": False}}
            #             num_gld_homes = 893
            #         if climatezone == 5:
            #             # Omitted for now as feeder R5-12.47-4 has large static load
            #             # feeders = {"feeder1": {"name": "R5-12.47-1", "ercot": False},
            #             #            "feeder2": {"name": "R5-12.47-2", "ercot": False},
            #             #            "feeder3": {"name": "R5-12.47-4", "ercot": False}}
            #             # num_gld_homes = 2234
            #             feeders = {"feeder1": {"name": "R5-12.47-1", "ercot": False},
            #                        "feeder2": {"name": "R5-12.47-2", "ercot": False},
            #                        "feeder3": {"name": "R5-12.47-5", "ercot": False}}
            #             num_gld_homes = 2847
            #
            # # Values for lean version
            # if feeder_mode == 'test':
                if utiltype == "Rural":
                    # feeders = {"feeder1": {"name": "R4-25.00-1", "ercot": False},
                    #            "feeder2": {"name": "R5-12.47-5", "ercot": False}}
                    feeders = {"feeder1": {"name": "R5-12.47-5", "ercot": False}}
                    num_gld_homes = 1539
                elif utiltype == "Suburban":
                    feeders = {"feeder1": {"name": "R5-12.47-5", "ercot": False}}
                    num_gld_homes = 1539
                    # if climatezone == 3:
                    #     feeders = {"feeder1": {"name": "R3-12.47-3", "ercot": False}}
                    #     num_gld_homes = 1326
                    # if climatezone == 4:
                    #     feeders = {"feeder1": {"name": "R3-12.47-3", "ercot": False}}
                    #     num_gld_homes = 1326
                    # if climatezone == 5:
                    #     feeders = {"feeder1": {"name": "R5-12.47-5", "ercot": False}}
                    #     num_gld_homes = 1539
                elif utiltype == "Urban":
                    if climatezone == 3:
                        feeders = {"feeder1": {"name": "R4-12.47-1", "ercot": False},
                                   "feeder2": {"name": "R5-12.47-1", "ercot": False}}
                        num_gld_homes = 1525
                    if climatezone == 4:
                        feeders = {"feeder1": {"name": "R4-12.47-1", "ercot": False},
                                   "feeder2": {"name": "R4-12.47-2", "ercot": False}}
                        num_gld_homes = 893
                    if climatezone == 5:
                        feeders = {"feeder1": {"name": "R5-12.47-1", "ercot": False},
                                   "feeder2": {"name": "R5-12.47-2", "ercot": False}}
                        num_gld_homes = 1308

            elif feeder_mode == 'stub':
                feeders = {"feeder1": {
                    "name": "GC-12.47-1",
                    "ercot": False
                }}
                num_gld_homes = 0.1

            elif feeder_mode == 'skinny':
                feeders = {
                    "feeder1": {
                        "name": "R4-25.00-1",
                        "ercot": False
                    }}
                num_gld_homes = 168

            elif feeder_mode == 'slim':
                if busid == 2:
                    feeders = {
                        "feeder1": {
                            "name": "R4-12.47-1",
                            "ercot": False
                        }}
                    num_gld_homes = 523
                else:
                    feeders = {"feeder1": {
                        "name": "GC-12.47-1",
                        "ercot": False
                    }}
                    num_gld_homes = 0.1

            if write_case_config:
                # [bus id, name, gld_scale, Pnom, Qnom, curve_scale, curve_skew, Pinit, Qinit]
                if bus_simulated:
                    use_dso_list.append([busid, "Substation_" + str(busid),
                                         (res_customers / num_gld_homes),
                                         max_load * congestion_factor, 0, 0.5, 0, total_average_load, 0])
                else:
                    use_dso_list.append([busid, "Substation_" + str(busid),
                                         (res_customers / num_gld_homes),
                                         0, 0, 0.5, 0, total_average_load, 0])

            if DSO_Load_Threshold == 'File':
                if bus_simulated:
                    dso_simulate = True
                else:
                    dso_simulate = False
            else:
                if total_average_load >= DSO_Load_Threshold:
                    dso_simulate = True
                else:
                    dso_simulate = False

            data["DSO_" + str(busid)] = {
                "bus_number": busid,
                "used": dso_simulate,  # If true the DSO will be instantiated in prepare case and simulated
                "name": busname,
                "climate_zone": climatezone,
                "county": county,
                "latitude": latitude,
                "longitude": longitude,
                "time_zone_offset": -6,
                "utility_type": utiltype,
                "ownership_type": ownership_type,
                "ashrae_zone": ashrae_zone,
                "blm_zone": blm_zone,
                "peak_season": peakseason,
                "substation": "Substation_" + str(busid),
                "random_seed": busid,
                "feeders": feeders,
                "RCI energy mix": {
                    "residential": round(res_average_load / total_average_load, 4),
                    "commercial": round(comm_average_load / total_average_load, 4),
                    "industrial": round(indust_average_load / total_average_load, 4)
                },
                "number_of_customers": total_customers,
                "number_of_gld_homes": num_gld_homes,
                "comm_customers_per_bldg": 2.09,
                "number_of_substations": 1,
                "MVA_growth_rate": 0.01,
                "weather_file": "weather_Bus_" + str(busid) + "_" + str(latitude) + "_" + str(longitude) + ".dat",
                "RCI customer count mix": {
                    "residential": round(res_customers / total_customers, 4),
                    "commercial": round(comm_customers / total_customers, 4),
                    "industrial": round(indust_customers / total_customers, 4)
                },
                "average_load_MW": total_average_load,
                "rooftop_pv_rating_MW": roof_top_PV_MW,
                "winter_peak_MW": 0,
                "summer_peak_MW": 0,
                "capacity_limit_MW": 0,
                "scaling_factor": res_customers / num_gld_homes,
                "total_other_O&M": 0,
                "bilaterals": {
                    "price": 11.11,
                    "load_fraction": 0.11
                },
                "DSO_system_energy_fraction": 0.11
            }
        print("\n=== {0:d} DSOs Defined in Metadata File =====".format(len(data) - 1))

    json_file.close()
    # write it in the original data file
    with open(data_path + case_file + '.json', 'w') as outfile:
        json.dump(data, outfile, indent=2)

    # write out FNCS array in system_config
    if write_case_config:
        with open(case_path + config_file + '.json') as caseconfig_file:
            case_data = json.load(caseconfig_file)
            case_data['DSO'] = use_dso_list
            for i in range(len(case_data['bus'])):
                if len(case_data['bus'][i]) == 13:
                    case_data['bus'][i].append(0)
                    case_data['bus'][i].append(0)
        caseconfig_file.close()
        with open(case_path + config_file + '.json', 'w') as caseoutfile:
            json.dump(case_data, caseoutfile, indent=2)

    # write out industrial load file
    if write_industrials:
        days = 35
        num_stamps = 35 * 24 * 12
        time_stamps = [n * 300 for n in range(num_stamps)]
        array = [indust_load_list for i in range(len(time_stamps))]
        indust_df = pd.DataFrame(array,
                                 index=time_stamps,
                                 columns=dso_list)
        indust_df.index.name = 'seconds'
        indust_df.to_csv(data_path + '/200_indust_p.csv')


# def prepare_metadata(node, end_row, feeder_mode, high_renewables_case, DSO_Load_Threshold):
prepare_metadata('8', 10, 'lean', True, 0)
# prepare_metadata('8', 10, 'skinny', True, 0)
# prepare_metadata('8', 10, 'stub', True, 0)
prepare_metadata('8', 10, 'lean', False, 0)
# prepare_metadata('8', 10, 'skinny', False, 0)
# prepare_metadata('8', 10, 'test', False, 0)
# prepare_metadata('8', 10, 'stub', False, 0)
# prepare_metadata('200', 202, 'lean', True, 1130)
# prepare_metadata('200', 202, 'skinny', True, 300)
# prepare_metadata('200', 202, 'stub', True, 300)
# prepare_metadata('200', 202, 'lean', False, 1130)
# prepare_metadata('200', 202, 'test', False, 1130)
prepare_metadata('200', 202, 'lean', False, 'File')
prepare_metadata('200', 202, 'lean', True, 'File')
# prepare_metadata('200', 202, 'skinny', False, 300)
# prepare_metadata('200', 202, 'stub', False, 300)
