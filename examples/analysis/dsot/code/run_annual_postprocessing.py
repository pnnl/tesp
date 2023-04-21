import json
import os
from datetime import datetime
from os.path import dirname, abspath, isdir

import pandas as pd

import tesp_support.dsot.Wh_Energy_Purchases as ep
import tesp_support.dsot.plots as pt
import tesp_support.dsot.dso_quadratic_curves as qc
import tesp_support.dsot.dso_rate_making as rm
import tesp_support.dsot.dso_helper_functions as hf

''' This script runs key postprocessing functions that warrant execution after every simulation run.  
It has the following elements:
    0. Setup - establish locations and meta data files etc.
    1. Postprocessing that is required per DSO (and can be parallelized)
    2. Postprocessing that is required across all DSOs and is desired for every run
    3. Postprocessing that is needed over the entire year (and will likely need be executed on Constance).
    4. Postprocessing that compares cases (and will likely need to be executed on Constance).
'''

#  STEP 0 ---------  STEP UP ------------------------------
#  Determine which metrics to post-process
# annual_energy = True
# annual_amenity = True
# load_stats = True
# annual_lmps = True
# gen_stats = True
# train_lmps = True
# wholesale = True
# retail = True
# customer_cfs = True
dso_cfs = True

annual_energy = False
annual_amenity = False
load_stats = False
annual_lmps = False
gen_stats = False
train_lmps = False
wholesale = False
retail = False
customer_cfs = False
# dso_cfs = False

# Only set to True if you have already run cfs once and want to update billing to match expenses.
squareup_revenue = True

first_data_day = 4  # First day in the simulation that data to be analyzed. Run-in days before this are discarded.
discard_end_days = 1  # Number of days at the end of the simulation to be discarded

# ------------ Select folder locations for different cases ---------

mr_bau_path = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2/v1.1-1588-ge941fcf5'
mr_batt_path = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2/v1.1-1676-gc9c18a25'
mr_flex_path = 'TBD'
hr_bau_path = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2/v1.1-1645-g954c150b'
hr_batt_path = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2/v1.1-1694-ge9c9e7fa'
hr_flex_path = 'TBD'
mr_200_bau_path = 'TBD'
mr_200_batt_path = 'TBD'
mr_200_flex_path = 'TBD'

case_path = mr_bau_path

# Load System Case Config

if case_path in [mr_bau_path, mr_batt_path, mr_flex_path]:
    system_case = '8_system_case_config.json'
    base_case_path = mr_bau_path
elif case_path in [hr_bau_path, hr_batt_path, hr_flex_path]:
    system_case = '8_hi_system_case_config.json'
    base_case_path = hr_bau_path
elif case_path in [mr_200_bau_path, mr_200_batt_path, mr_200_flex_path]:
    system_case = '200_system_case_config.json'
    base_case_path = mr_200_bau_path

config_path = dirname(abspath(__file__))
case_config = pt.load_json(config_path, system_case)

# metadata_path = '../dso_data'
metadata_path = 'C:/Users/reev057/PycharmProjects/TESP/src/examples/data'

renew_forecast_file = metadata_path + "/" + case_config['genForecastHr'][5].split('/')[-1]
dso_metadata_file = case_config['dsoPopulationFile']
DSOmetadata = pt.load_json(metadata_path, dso_metadata_file)

# DSO range for 8 node case.  (for 200 node case we will need to determine active DSOs from metadata file).
# dso_range = range(1, 9)
dso_range = []
for DSO in DSOmetadata.keys():
    if 'DSO' in DSO:
        if DSOmetadata[DSO]['used']:
            dso_range.append(int(DSO.split('_')[-1]))

#  Month, path of month data, first day of real data, last day of real data + 1
if case_path == mr_bau_path:
    month_def = [
        ['Jan', case_path + '/2016_01', 3, 34],
        ['Feb', case_path + '/2016_02', 3, 32],
        ['March', case_path + '/2016_03', 3, 34],
        ['April', case_path + '/2016_04', 3, 33],
        ['May', case_path + '/2016_05', 3, 34],
        ['June', case_path + '/2016_06', 3, 33],
        ['July', case_path + '/2016_07', 3, 34],
        ['August', case_path + '/2016_08', 3, 34],
        ['Sept', case_path + '/2016_09', 3, 33],
        ['Oct', case_path + '/2016_10', 3, 34],
        ['Nov', case_path + '/2016_11', 3, 33]
        # ['Dec', case_path + '/2016_12', 3, 34]
    ]
elif case_path == hr_bau_path:
    month_def = [
        ['Jan', case_path + '/2016_01_pv', 3, 34],
        ['Feb', case_path + '/2016_02_pv', 3, 32],
        ['March', case_path + '/2016_03_pv', 3, 34],
        ['April', case_path + '/2016_04_pv', 3, 33],
        ['May', case_path + '/2016_05_pv', 3, 34],
        ['June', case_path + '/2016_06_pv', 3, 33],
        ['July', case_path + '/2016_07_pv', 3, 34],
        ['August', case_path + '/2016_08_pv', 3, 34],
        ['Sept', case_path + '/2016_09_pv', 3, 33],
        ['Oct', case_path + '/2016_10_pv', 3, 34],
        ['Nov', case_path + '/2016_11_pv', 3, 33]
        # ['Dec', case_path + '/2016_12_pv', 3, 34]
    ]

elif case_path == mr_batt_path:
    month_def = [
        ['Jan', case_path + '/2016_01_bt', 3, 34],
        ['Feb', case_path + '/2016_02_bt', 3, 32],
        ['March', case_path + '/2016_03_bt', 3, 34],
        ['April', case_path + '/2016_04_bt', 3, 33],
        ['May', case_path + '/2016_05_bt', 3, 34],
        ['June', case_path + '/2016_06_bt', 3, 33],
        ['July', case_path + '/2016_07_bt', 3, 34],
        ['August', case_path + '/2016_08_bt', 3, 34],
        ['Sept', case_path + '/2016_09_bt', 3, 33],
        ['Oct', case_path + '/2016_10_bt', 3, 34],
        ['Nov', case_path + '/2016_11_bt', 3, 33]
        # ['Dec', case_path + '/2016_12_bt', 3, 34]
    ]

elif case_path == hr_batt_path:
    month_def = [
        ['Jan', case_path + '/8_2016_01_pv_bt_ev', 3, 34],
        ['Feb', case_path + '/8_2016_02_pv_bt_ev', 3, 32],
        ['March', case_path + '/8_2016_03_pv_bt_ev', 3, 34],
        ['April', case_path + '/8_2016_04_pv_bt_ev', 3, 33],
        ['May', case_path + '/8_2016_05_pv_bt_ev', 3, 34],
        ['June', case_path + '/8_2016_06_pv_bt_ev', 3, 33],
        ['July', case_path + '/8_2016_07_pv_bt_ev', 3, 34],
        ['August', case_path + '/8_2016_08_pv_bt_ev', 3, 34],
        ['Sept', case_path + '/8_2016_09_pv_bt_ev', 3, 33],
        ['Oct', case_path + '/8_2016_10_pv_bt_ev', 3, 34],
        ['Nov', case_path + '/8_2016_11_pv_bt_ev', 3, 33]
        # ['Dec', case_path + '/8_2016_12_pv_bt_ev', 3, 34]
    ]

# month_def = [
#             ['Aug', case_path + '/w_lean_aug_8', 3, 34],
#             ['Aug_bt', case_path + '/x_lean_aug_8_pv_bt_ev', 3, 34]
# ]

# Verify and implement actual number of simulation days.
total_sim_days = 0
for month in month_def:
    generate_case_config = pt.load_json(month[1], 'generate_case_config.json')

    num_sim_days = (datetime.strptime(generate_case_config['EndTime'], '%Y-%m-%d %H:%M:%S') -
                    datetime.strptime(generate_case_config['StartTime'], '%Y-%m-%d %H:%M:%S')).days

    # Start at day 'n' after first few days are discarded.  
    # Assumes that simulation runs to end of month with 'm' extra days at the end.
    month[2] = first_data_day
    month[3] = num_sim_days - discard_end_days + 1
    total_sim_days += month[3] - month[2]

total_day_range = range(1, total_sim_days + 1)
metadata_file = case_config['dsoPopulationFile']
dso_meta_file = metadata_path + '/' + metadata_file
agent_prefix = '/DSO_'
GLD_prefix = '/Substation_'

# Check if there is a plots folder - create if not.
check_folder = isdir(case_path + '/plots')
if not check_folder:
    os.makedirs(case_path + '/plots')

# STEP 3 --------- ANNUAL AGGREGATION AND ANALYSIS FUNCTIONS (to be run once all month aggregation is complete) ------

# --------------- AGGREGATE ANNUAL ENERGY SUMMARIES  ------------------------------
for dso_num in dso_range:
    file_name = 'Substation_' + str(dso_num) + '_glm_dict.json'
    GLD_metadata = pt.load_json(month_def[0][1] + agent_prefix + str(dso_num), file_name)
    if annual_energy:
        pt.tic()
        year_meter_df, year_energysum_df, year_trans_sum_df = \
            rm.annual_energy(month_def, GLD_prefix, str(dso_num), GLD_metadata)
        os.chdir(case_path)
        year_meter_df.to_hdf('energy_dso_' + str(dso_num) + '_data.h5', key='energy_data')
        year_energysum_df.to_hdf('energy_dso_' + str(dso_num) + '_data.h5', key='energy_sums')
        year_trans_sum_df.to_hdf('transactive_dso_' + str(dso_num) + '_data.h5', key='trans_data')
        print('Annual Customer Energy billing aggregation complete: DSO ' + str(dso_num))
        pt.toc()

    # --------------- AGGREGATE ANNUAL AMENITY SCORES  ------------------------------
    if annual_amenity:
        annual_amenity_df = pt.annual_amenity(GLD_metadata, month_def, GLD_prefix, str(dso_num))
        os.chdir(case_path)
        pt.tic()
        annual_amenity_df.to_hdf('amenity_dso_' + str(dso_num) + '_data.h5', key='amenity_data')
        annual_amenity_df.to_csv(path_or_buf=case_path + '/amenity_dso_' + str(dso_num) + '_data.csv')
        print('Annual Customer amenity impact aggregation complete: DSO ' + str(dso_num))
        pt.toc()

# --------------- AGGREGATE ANNUAL DSO LOADS and FIND QMAX  ------------------------------
if load_stats:  # Finds Q_max amongst other things.
    pt.dso_load_stats(dso_range, month_def, case_path, metadata_path, True)

# --------------- AGGREGATE ANNUAL LMPS LOADS for FORECASTER RETUNING  ------------------------------
if annual_lmps:
    dso_num = '3'
    pt.dso_lmp_stats(month_def, case_path, renew_forecast_file)
    pt.plot_lmp_stats(case_path, case_path, dso_num, 7)

if gen_stats:
    # Annual LMP needs to be run once to ensure that the annual opf file is created
    GenAMES_df = pt.generation_statistics(case_path, config_path, system_case, total_day_range, False)

if train_lmps:
    obj = qc.DSO_LMPs_vs_Q(case_path)
    obj.multiple_fit_calls()
    obj.make_json_out()

# --------------- DETERMINE WHOLESALE PURCHASES  ------------------------------
# dso_num = '1'
if wholesale:
    for dso_num in dso_range:
        Market_Purchases = ep.Wh_Energy_Purchases(case_path, str(dso_num), True)
        print(Market_Purchases)
        os.chdir(case_path)
        with open('DSO' + str(dso_num) + '_Market_Purchases.json', 'w') as f:
            json.dump(Market_Purchases, f, indent=2)

# --------------- DETERMINE RETAIL BILLING  ------------------------------
# Run Customer billing code to determine revenues
# Run DSO cash flow to determine total DSO expense = total DSO required revenue.
# Run Customer billing code to determine revenues and iterate tariffs to match expenses
# Run final DSO cash flow with final customer revenues.

if retail:
    if squareup_revenue:
        dso_df = pd.read_csv(case_path + "/DSO_CFS_Summary.csv")
        # TODO: Fix this: dso_df = dso_df.set_index(dso_df.columns[0])
    for dso_num in dso_range:
        file_name = 'Substation_' + str(dso_num) + '_glm_dict.json'
        GLD_metadata = pt.load_json(month_def[0][1] + agent_prefix + str(dso_num), file_name)

        DSOmetadata = pt.load_json(metadata_path, metadata_file)
        commdata = pt.load_json(metadata_path, 'DSOT_commercial_metadata.json')
        commbldglist = []
        for bldg in commdata['building_model_specifics']:
            commbldglist.append(bldg)
        residbldglist = ['SINGLE_FAMILY', 'MOBILE_HOME', 'APARTMENTS', 'MULTI_FAMILY']

        for each in GLD_metadata['billingmeters']:
            GLD_metadata['billingmeters'][each]['tariff_class'] = None
            for bldg in commbldglist:
                if bldg in GLD_metadata['billingmeters'][each]['building_type']:
                    GLD_metadata['billingmeters'][each]['tariff_class'] = 'commercial'
            for bldg in residbldglist:
                if bldg in GLD_metadata['billingmeters'][each]['building_type']:
                    GLD_metadata['billingmeters'][each]['tariff_class'] = 'residential'
            if GLD_metadata['billingmeters'][each]['building_type'] == 'UNKNOWN':
                GLD_metadata['billingmeters'][each]['tariff_class'] = 'industrial'
            if GLD_metadata['billingmeters'][each]['tariff_class'] is None:
                raise Exception('Tariff class was not successfully determined for meter ' + each)

        # Placeholder code to add whether a customer is participating or not.
        # TODO: this should be done in prepare case and read in as part of GLD meter metadata.
        agent_file_name = 'Substation_' + str(dso_num) + '_agent_dict.json'
        agent_metadata = pt.load_json(month_def[0][1] + agent_prefix + str(dso_num), agent_file_name)

        GLD_metadata = pt.customer_meta_data(GLD_metadata, agent_metadata, metadata_path)
        num_ind_cust = DSOmetadata['DSO_' + str(dso_num)]['number_of_customers'] * \
                       DSOmetadata['DSO_' + str(dso_num)]['RCI customer count mix']['industrial']
        dso_scaling_factor = DSOmetadata['DSO_' + str(dso_num)]['scaling_factor']
        if squareup_revenue:
            required_revenue = (float(dso_df.iloc[13, dso_num]) + float(dso_df.iloc[30, dso_num])) * 1000
        else:
            required_revenue = 4e6
        DSO_Cash_Flows, DSO_Revenues_and_Energy_Sales, tariff, surplus = \
            rm.DSO_rate_making(case_path, dso_num, GLD_metadata, required_revenue,
                               metadata_path, dso_scaling_factor, num_ind_cust)

        # Example of getting an annual customer bill in dictionary form:
        customer = list(GLD_metadata['billingmeters'].keys())[0]
        cust_bill_file = case_path + '/bill_dso_' + str(dso_num) + '_data.h5'
        cust_bills = pd.read_hdf(cust_bill_file, key='cust_bill_data', mode='r')
        customer_bill = rm.get_cust_bill(customer, cust_bills, GLD_metadata)
        print(customer_bill)

        os.chdir(case_path)
        with open('DSO' + str(dso_num) + '_Cash_Flows.json', 'w') as f:
            json.dump(DSO_Cash_Flows, f, indent=2)
        with open('DSO' + str(dso_num) + '_Revenues_and_Energy_Sales.json', 'w') as f:
            json.dump(DSO_Revenues_and_Energy_Sales, f, indent=2)
        with open('DSO' + str(dso_num) + '_Customer_' + customer + '_Bill.json', 'w') as f:
            json.dump(customer_bill, f, indent=2)
        with open('DSO' + str(dso_num) + '_Customer_Metadata.json', 'w') as f:
            json.dump(GLD_metadata, f, indent=2)

# --------------- DETERMINE CASHFLOW STATEMENTS  ------------------------------
# Run final DSO cash flow with final customer revenues.

if customer_cfs:
    # dso_range = [1]
    customer_df = hf.get_customer_df(dso_range, case_path, metadata_path)
    customer_df.to_hdf(case_path + '/Master_Customer_Dataframe.h5', key='customer_data')
    customer_df.to_csv(path_or_buf=case_path + '/Master_Customer_Dataframe.csv')

    main_variables = ['dso', 'tariff_class', 'building_type', 'cust_participating', 'cooling', 'heating']
    variables_combs = [['tariff_class', 'cust_participating'],
                       ['tariff_class', 'cust_participating', 'cooling', 'heating'],
                       ['building_type', 'cust_participating']]

    customer_mean_df = hf.get_mean_for_diff_groups(customer_df, main_variables, variables_combs, cfs_start_position=24)
    customer_mean_df.to_csv(path_or_buf=case_path + '/Customer_CFS_Summary.csv')

if dso_cfs:
    DSO_df, CapitalCosts_dict_list, Expenses_dict_list, Revenues_dict_list, DSO_Cash_Flows_dict_list = \
        hf.get_DSO_df(dso_range, generate_case_config, DSOmetadata, case_path, base_case_path)

    DSO_df.to_csv(path_or_buf=case_path + '/DSO_CFS_Summary.csv')

    os.chdir(case_path)
    i = 0
    for dso_num in dso_range:
        with open('DSO' + str(dso_num) + '_Capital_Costs.json', 'w') as f:
            json.dump(CapitalCosts_dict_list[i], f, indent=2)
        with open('DSO' + str(dso_num) + '_Expenses.json', 'w') as f:
            json.dump(Expenses_dict_list[i], f, indent=2)
        i += 1

# 5. Automated calculation of valuation work-flow:
#       c. Rerun annual customer billing to square up revenue

# STEP 4 --------- COMPARISON BETWEEN CASES OF ANNUAL RESULTS (to be run once all cases complete) ------
# TODO: Comparison analysis to be completed:
# 1. Slider settings plots
stats = True
if stats:
    bill = True
    rci_df = pt.RCI_analysis(dso_range, month_def[0][1], case_path, metadata_path, dso_metadata_file, bill)
    params = [
        # ['houses', 'SINGLE_FAMILY', 'cooling_COP'],
        ['billingmeters', 'commercial', 'sqft'],
        ['billingmeters', 'residential', 'sqft'],
        ['billingmeters', 'residential', 'kw-hr'],
        ['billingmeters', 'residential', 'max_kw'],
        ['billingmeters', 'residential', 'avg_load'],
        ['billingmeters', 'residential', 'load_factor'],
        ['billingmeters', 'commercial', 'kw-hr'],
        ['billingmeters', 'commercial', 'max_kw'],
        ['billingmeters', 'commercial', 'avg_load'],
        ['billingmeters', 'commercial', 'load_factor']
    ]

    for para in params:
        pt.metadata_dist_plots(system=para[0], sys_class=para[1], variable=para[2], dso_range=dso_range,
                               case=month_def[0][1], data_path=case_path, metadata_path=metadata_path,
                               agent_prefix=agent_prefix)
