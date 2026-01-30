import json
import os
from datetime import datetime
from os.path import dirname, abspath, isdir
import shutil
import numpy as np
import logging
import time

import pandas as pd

import tesp_support.dsot.Wh_Energy_Purchases as ep
import tesp_support.dsot.plots as pt
import tesp_support.dsot.dso_quadratic_curves as qc
import tesp_support.dsot.dso_rate_making as rm
import tesp_support.dsot.dso_helper_functions as hf

from concurrent.futures import ProcessPoolExecutor, as_completed

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('run_annual_postprocessing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


''' This script runs key postprocessing functions that warrant execution after every simulation run.  
It has the following elements:

    0. Setup - establish locations and meta data files etc.
    1. Postprocessing that is required per DSO (and can be parallelized)
    2. Postprocessing that is required across all DSOs and is desired for every run
    3. Postprocessing that is needed over the entire year (and will likely need be executed on Constance).
    4. Postprocessing that compares cases (and will likely need to be executed on Constance).
'''


# --------------- Select folder locations for different cases -----------------
'''To run_annual_postprocessing.py, first finish simulating each month for each 
case. Then, move all case folders to datapath. Suggested datapath is to create 
the subfolder: $TESPDIR/examples/analysis/dsot/data/post_processing
Finally, specify the directories of the cases you want to postprocess, adding
each to the case_list below. 
'''

hayden = False

if hayden:
    flat_path = 'C:/Users/reev057/DSOT-DATA/Rates/Flat'
    DSOT_path = 'C:/Users/reev057/DSOT-DATA/Rates/DSOT'
    TOU_path = 'C:/Users/reev057/DSOT-DATA/Rates/TOU'
    transactive_path = 'C:/Users/reev057/DSOT-DATA/Rates/Transactive'
    subscription_path = 'C:/Users/reev057/DSOT-DATA/Rates/Subscription'
    metadata_path = 'C:/Users/reev057/PycharmProjects/TESP_Public/examples/analysis/dsot/data'
else:
    tesp_dir = os.path.expandvars('$TESPDIR')
    datapath = os.path.join(tesp_dir, 'examples/analysis/dsot/data/post_processing')
    flat_path = os.path.join(datapath, 'Flat')
    DSOT_path = os.path.join(datapath, 'DSOT')
    TOU_path = os.path.join(datapath, 'TOU')
    transactive_path = os.path.join(datapath, 'rob-don')
    subscription_path = os.path.join(datapath, 'sub') # duplicate the 'rob-don' folder and rename to 'sub'
    metadata_path = os.path.join(tesp_dir, 'examples/analysis/dsot/data')

# ------------------- Select case_path to post process ------------------------
system_case = "8_hi_system_case_config.json"

# Add cases to case list, in order of dependencies, if any
# Note, do not add the base case to the case_list
case_list = [
    DSOT_path,
    TOU_path,
    transactive_path,
    subscription_path
]


def process_dso(
                dso_num,
                case_path,
                demand_case_path,
                metadata_path,
                month_def,
                agent_prefix,
                metadata_file,
                case_name,
                rate_scenario):
    #pt.tic()
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
    num_ind_cust = (DSOmetadata['DSO_' + str(dso_num)]['number_of_customers'] *
                    DSOmetadata['DSO_' + str(dso_num)]['RCI customer count mix']['industrial'])
    dso_scaling_factor = DSOmetadata['DSO_' + str(dso_num)]['scaling_factor']

    trans_cost_balance_method = None
    include_RT = False   # Do (or do not) include RT cost correction component in customer billing.
    DSO_Cash_Flows, DSO_Revenues_and_Energy_Sales, tariff, surplus_err = rm.DSO_rate_making(
        case_path,
        demand_case_path,
        dso_num,
        GLD_metadata,
        metadata_path,
        dso_scaling_factor,
        num_ind_cust,
        case_name,
        rate_scenario,
        trans_cost_balance_method,
        include_RT
    )

    # Example of getting an annual customer bill in dictionary form:
    customer = list(GLD_metadata['billingmeters'].keys())[0]
    cust_bill_file = case_path + '/bill_dso_' + str(dso_num) + '_data.h5'
    cust_bills = pd.read_hdf(cust_bill_file, key='cust_bill_data', mode='r')
    cust_energy = pd.read_hdf(case_path + '/energy_dso_' + str(dso_num) + '_data.h5', key='energy_data', mode='r')
    customer_bill = rm.get_cust_bill(customer, cust_bills, GLD_metadata, cust_energy, rate_scenario)
    print("DSO " + str(dso_num) + "customer bill: ", customer_bill)

    #print("DSO " + str(dso_num) + ": Surplus error = " + str(surplus_err) + "%")
    pt.toc()

    os.chdir(case_path)
    with open('DSO' + str(dso_num) + '_Cash_Flows.json', 'w') as f:
        json.dump(DSO_Cash_Flows, f, indent=2)
    with open('DSO' + str(dso_num) + '_Revenues_and_Energy_Sales.json', 'w') as f:
        json.dump(DSO_Revenues_and_Energy_Sales, f, indent=2)
    with open('DSO' + str(dso_num) + '_Customer_' + customer + '_Bill.json', 'w') as f:
        json.dump(customer_bill, f, indent=2)
    with open('DSO' + str(dso_num) + '_Customer_Metadata.json', 'w') as f:
        json.dump(GLD_metadata, f, indent=2)

    return dso_num, surplus_err

def run_annual_postprocessing(case_list: list, base_case_path: str, demand_case_path : str, run_base: bool):
    """This function loops through the run_annual_postprocessing script to 
    generate the required metrics files for each case being studied, then 
    square up any revenues and expenses and generates final cash flow statements.


    Args:
        case_list (list): a list of the paths to each case that is NOT the base
            case being post processed
        base_case_path (str): the path to the base case folder (Flat)
        demand_case_path (str): the path to the demand case folder (TOU)
        run_base (bool): whether to run the base case first. Set to true for
            first run. Subsequent runs can set to false.

    Raises:
        Exception: _description_
    """
    logger.info("Starting annual postprocessing with %d cases", len(case_list))
    logger.info("Base case path: %s", base_case_path)
    logger.info("Demand case path: %s", demand_case_path)
    logger.info("Run base: %s", run_base)

    # Process the base case first
    if run_base:
        case_list.insert(0, str(base_case_path))
        logger.info("Added base case to processing list")
    else:
        pass
    # Run each case once to generate required files, once to square up 
    # case_list = np.repeat(case_list, 2)
    
    for case_path in case_list:
        case_start_time = time.time()
        logger.info("Processing case: %s", case_path)
        #  STEP 0 -- Determine which metrics to post-process

        if not os.path.isfile(os.path.join(case_path, 'energy_dso_1_data.h5')):
            logger.info('No annual energy files found, running annual_energy...')
            annual_energy = True
        else: 
            annual_energy = False

        if not os.path.isfile(os.path.join(case_path, 'amenity_dso_1_data.h5')):
            logger.info('No amenity data found, running annual_amenity...')
            annual_amenity = True
        else:
            annual_amenity = False

        if not os.path.isfile(os.path.join(case_path, 'DSO_load_stats.csv')):
            logger.info('No load stats found, running load_stats...')
            load_stats = True
        else:
            load_stats = False

        if not os.path.isfile(os.path.join(case_path, 'Annual_DA_LMP_stats.csv')):
            logger.info("No annual LMP stats found, running annual_lmps")
            annual_lmps = True
        else:
            annual_lmps = False

        if not os.path.isfile(os.path.join(case_path, 'generator_statistics_AMES.csv')):
            logger.info('No AMES generator stats found, running gen_stats')
            gen_stats = True
        else:
            gen_stats = False

        if not os.path.isfile(os.path.join(case_path, 'DSO_quadratic_curves.json')):
            logger.info('No Quadratic Curves found, running train_lmps')
            train_lmps = True
        else:
            train_lmps = True

        if not os.path.isfile(os.path.join(case_path, 'DSO1_Market_Purchases.json')):
            logger.info('No Market Purchases found, running wholesale')
            wholesale = True
        else:
            wholesale = False

        if not os.path.isfile(os.path.join(case_path, 'DSO1_Cash_Flows.json')):
            retail = True
        else:
            # Keep retail turned on for now to square up revenue with re-run
            retail = True

        if not os.path.isfile(os.path.join(case_path, 'Customer_CSF_Summary.csv')):
            customer_cfs = True
        else:
            customer_cfs = True

        if not os.path.isfile(os.path.join(case_path, 'DSO_CSF_Summary.csv')):
            dso_cfs = True
        else:
            dso_cfs = True

        # Set True if you want to automatically determine start and end days of 
        # the month (versus manually set them).
        determine_days = False
        
        # First day in the simulation that data to be analyzed. Run-in days 
        # before this are discarded.
        first_data_day = 4  
        # Number of days at the end of the simulation to be discarded
        discard_end_days = 1  

        config_path = dirname(abspath(__file__))
        case_config = pt.load_json(config_path, system_case)

        renew_forecast_file = metadata_path + "/" + case_config['genForecastHr'][5].split('/')[-1]
        dso_metadata_file = case_config['dsoPopulationFile']
        DSOmetadata = pt.load_json(metadata_path, dso_metadata_file)

        # DSO range for 8 node case.  (for 200 node case we will need to 
        # determine active DSOs from metadata file).
        dso_range = []
        for DSO in DSOmetadata.keys():
            if 'DSO' in DSO:
                if DSOmetadata[DSO]['used']:
                    dso_range.append(int(DSO.split('_')[-1]))

        case_name = ''
        month_def = []
        rate_scenario = None

        # Determine the rate scenario to investigate
        if case_path == flat_path:
            case_name = 'Flat'
            rate_scenario = "flat"
            path_adder = ''
        if case_path == DSOT_path:
            case_name = 'DSOT'
            rate_scenario = "dsot"
            path_adder= ''
        if case_path == TOU_path:
            case_name = 'TOU'
            rate_scenario = "time-of-use"
            path_adder= ''
        if case_path == transactive_path:
            case_name = 'RandD'  # new EandC
            rate_scenario = "transactive"
            path_adder = 'rnd'   # new enc
        if case_path == subscription_path:
            case_name = 'Sub'
            rate_scenario = "subscription"
            path_adder = 'RND_' # Subscription case folder is duplicate of transactive case

        print('---------------Postprocessing ' + str(case_name), 'Case ----------------')
        logger.info('Starting postprocessing for case: %s', case_name)


        #  Month, path of month data, first day of real data, last day of real data + 1
        if case_path == TOU_path:
            month_def = [
                ['Jan', case_path + f'/8_{path_adder}2016_01_pv_bt_fl_ev', 4, 31],
                ['Feb', case_path + f'/8_{path_adder}2016_02_pv_bt_fl_ev', 4, 32],
                ['March', case_path + f'/8_{path_adder}2016_03_pv_bt_fl_ev', 5, 33],   #Start and end a day later due to sim issues
                ['April', case_path + f'/8_{path_adder}2016_04_pv_bt_fl_ev', 6, 35],   #Start and end two days later due to sim issues
                ['May', case_path + f'/8_{path_adder}2016_05_pv_bt_fl_ev', 4, 33],
                ['June', case_path + f'/8_{path_adder}2016_06_pv_bt_fl_ev', 4, 33],
                ['July', case_path + f'/8_{path_adder}2016_07_pv_bt_fl_ev', 4, 33],
                ['August', case_path + f'/8_{path_adder}2016_08_pv_bt_fl_ev', 4, 34],
                ['Sept', case_path + f'/8_{path_adder}2016_09_pv_bt_fl_ev', 4, 33],
                ['Oct', case_path + f'/8_{path_adder}2016_10_pv_bt_fl_ev', 4, 33],
                ['Nov', case_path + f'/8_{path_adder}2016_11_pv_bt_fl_ev', 4, 33],
                ['Dec', case_path + f'/8_{path_adder}2016_12_pv_bt_fl_ev', 4, 31]
            ]
        else:
            month_def = [
                ['Jan', case_path + f'/8_{path_adder}2016_01_pv_bt_fl_ev', 4, 31],
                ['Feb', case_path + f'/8_{path_adder}2016_02_pv_bt_fl_ev', 4, 32],
                ['March', case_path + f'/8_{path_adder}2016_03_pv_bt_fl_ev', 4, 32],
                ['April', case_path + f'/8_{path_adder}2016_04_pv_bt_fl_ev', 4, 33],
                ['May', case_path + f'/8_{path_adder}2016_05_pv_bt_fl_ev', 4, 33],
                ['June', case_path + f'/8_{path_adder}2016_06_pv_bt_fl_ev', 4, 33],
                ['July', case_path + f'/8_{path_adder}2016_07_pv_bt_fl_ev', 4, 33],
                ['August', case_path + f'/8_{path_adder}2016_08_pv_bt_fl_ev', 4, 34],
                ['Sept', case_path + f'/8_{path_adder}2016_09_pv_bt_fl_ev', 4, 33],
                ['Oct', case_path + f'/8_{path_adder}2016_10_pv_bt_fl_ev', 4, 33],
                ['Nov', case_path + f'/8_{path_adder}2016_11_pv_bt_fl_ev', 4, 33],
                ['Dec', case_path + f'/8_{path_adder}2016_12_pv_bt_fl_ev', 4, 31]
            ]


        # Verify and implement actual number of simulation days.
        total_sim_days = 0
        generate_case_config = ''
        if not os.path.isfile(os.path.join(case_path, 'generate_case_config.json')):
                print('Copying generate_case_config.json to annual case folder')
                shutil.copy2(os.path.join(case_path, f'/8_{path_adder}_2016_01_pv_bt_fl_ev/generate_case_config.json'), os.path.join(case_path, 'generate_case_config.json'))

        for month in month_def:
            generate_case_config = pt.load_json(month[1], 'generate_case_config.json')
            num_sim_days = (datetime.strptime(generate_case_config['EndTime'], '%Y-%m-%d %H:%M:%S') -
                            datetime.strptime(generate_case_config['StartTime'], '%Y-%m-%d %H:%M:%S')).days

            # Start at day 'n' after first few days are discarded.  
            # Assumes that simulation runs to end of month with 'm' extra days at the end.
            if determine_days:
                month[2] = first_data_day
                month[3] = num_sim_days - discard_end_days + 1
            month.append(generate_case_config['StartTime'])
            month.append(generate_case_config['EndTime'])
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

        # STEP 3 -- ANNUAL AGGREGATION AND ANALYSIS FUNCTIONS ------------------
        # (to be run once all month aggregation is complete)

        # --------------- AGGREGATE ANNUAL ENERGY SUMMARIES  -------------------
        energy_start = time.time()
        for dso_num in dso_range:
            file_name = 'Substation_' + str(dso_num) + '_glm_dict.json'
            GLD_metadata = pt.load_json(month_def[0][1] + agent_prefix + str(dso_num), file_name)
            if annual_energy:
                logger.info('Starting annual energy aggregation for DSO %d', dso_num)
                pt.tic()
                year_meter_df, year_energysum_df, year_trans_sum_df = \
                    rm.annual_energy(month_def, GLD_prefix, str(dso_num), GLD_metadata)
                os.chdir(case_path)
                year_meter_df.to_hdf('energy_dso_' + str(dso_num) + '_data.h5', key='energy_data')
                year_energysum_df.to_hdf('energy_dso_' + str(dso_num) + '_data.h5', key='energy_sums')
                year_trans_sum_df.to_hdf('transactive_dso_' + str(dso_num) + '_data.h5', key='trans_data')
                print('Annual Customer Energy billing aggregation complete: DSO ' + str(dso_num))
                logger.info('Completed annual energy aggregation for DSO %d', dso_num)
                pt.toc()

            # --------------- AGGREGATE ANNUAL AMENITY SCORES  -----------------
            if annual_amenity:
                logger.info('Starting annual amenity aggregation for DSO %d', dso_num)
                annual_amenity_df = pt.annual_amenity(GLD_metadata, month_def, GLD_prefix, str(dso_num))
                os.chdir(case_path)
                pt.tic()
                annual_amenity_df.to_hdf('amenity_dso_' + str(dso_num) + '_data.h5', key='amenity_data')
                annual_amenity_df.to_csv(path_or_buf=case_path + '/amenity_dso_' + str(dso_num) + '_data.csv')
                print('Annual Customer amenity impact aggregation complete: DSO ' + str(dso_num))
                logger.info('Completed annual amenity aggregation for DSO %d', dso_num)
                pt.toc()
        energy_time = time.time() - energy_start
        logger.info('Total energy and amenity processing time: %.2f minutes', energy_time / 60)

        # --------------- AGGREGATE ANNUAL DSO LOADS and FIND QMAX  ------------
        if load_stats:  # Finds Q_max amongst other things.
            load_start = time.time()
            logger.info('Starting DSO load stats aggregation')
            pt.dso_load_stats(dso_range, month_def, case_path, metadata_path, True)
            logger.info('Completed DSO load stats aggregation')
            load_time = time.time() - load_start
            logger.info('DSO load stats processing time: %.2f minutes', load_time / 60)

        # --------- AGGREGATE ANNUAL LMPS LOADS for FORECASTER RETUNING  -------
        if annual_lmps:
            lmp_start = time.time()
            logger.info('Starting annual LMP stats aggregation')
            for dso_num in dso_range:
                pt.dso_lmp_stats(month_def, case_path, renew_forecast_file, dso_range)

                # Plot comparison of simulation wholesale prices to actual market data
                # pt.plot_lmp_stats(case_path, case_path, dso_num, 7)
            logger.info('Completed annual LMP stats aggregation')
            lmp_time = time.time() - lmp_start
            logger.info('Annual LMP stats processing time: %.2f minutes', lmp_time / 60)

        if gen_stats:
            gen_start = time.time()
            logger.info('Starting generation statistics')
            # Annual LMP needs to be run once to ensure that the annual opf file is created
            # TODO: Check if this means a separate run is needed for gen_stats
            # before metrics flags that follow it.
            GenAMES_df = pt.generation_statistics(case_path, config_path, system_case, total_day_range, False)
            logger.info('Completed generation statistics')
            gen_time = time.time() - gen_start
            logger.info('Generation statistics processing time: %.2f minutes', gen_time / 60)

        if train_lmps:
            train_start = time.time()
            logger.info('Starting LMP training and quadratic curves')
            obj = qc.DSO_LMPs_vs_Q(case_path)
            obj.multiple_fit_calls()
            obj.make_json_out()

            # TODO: Need better workflow to write output coefficients to specific DSO coefficient file of case(s) in question.
            logger.info('Completed LMP training and quadratic curves')
            train_time = time.time() - train_start
            logger.info('LMP training and quadratic curves processing time: %.2f minutes', train_time / 60)

        # --------------- DETERMINE WHOLESALE PURCHASES  -----------------------
        # dso_num = '1'
        if wholesale:
            wholesale_start = time.time()
            logger.info('Starting wholesale purchases calculation')
            for dso_num in dso_range:
                qmax_df = pd.read_csv(case_path + '/Qmax.csv', index_col=[0])
                time_of_system_peak = datetime.fromisoformat(qmax_df.loc['DSO_Total', 'Time of Peak'])
                Market_Purchases = ep.Wh_Energy_Purchases(case_path, str(dso_num), True)
                print(Market_Purchases)
                os.chdir(case_path)
                with open('DSO' + str(dso_num) + '_Market_Purchases.json', 'w') as f:
                    json.dump(Market_Purchases, f, indent=2)
            logger.info('Completed wholesale purchases calculation')
            wholesale_time = time.time() - wholesale_start
            logger.info('Wholesale purchases processing time: %.2f minutes', wholesale_time / 60)

        # TODO: Make month usage consistent 'Mar' versus 'March'
        # --------------- DETERMINE RETAIL BILLING  ----------------------------
        # Run Customer billing code to determine revenues
        # Run DSO cash flow to determine total DSO expense = total DSO required revenue.
        # Run Customer billing code to determine revenues and iterate tariffs to match expenses
        # Run final DSO cash flow with final customer revenues.
        #  TODO: break DSO CFS into two parts and execute first part here to have required revenue ready.
        if retail:
            retail_start = time.time()
            logger.info('Starting retail billing and cash flow calculations')
            dso_df = None

            results = []
            with ProcessPoolExecutor(max_workers=8) as executor:  # adjust max_workers for CPU/memory
                futures = {executor.submit(process_dso, dso_num, case_path, demand_case_path, metadata_path,
                                            month_def, agent_prefix, metadata_file, case_name,
                                            rate_scenario): dso_num for dso_num in dso_range}
                for future in as_completed(futures):
                    dso_num, surplus_err = future.result()
                    print(f"DSO {dso_num}: Surplus error = {surplus_err}%")
                    results.append((dso_num, surplus_err))

            logger.info('Completed retail billing and cash flow calculations')
            retail_time = time.time() - retail_start
            logger.info('Retail billing and cash flow processing time: %.2f minutes', retail_time / 60)

        # --------------- DETERMINE CASHFLOW STATEMENTS  -----------------------
        # Run final DSO cash flow with final customer revenues.

        if customer_cfs:
            customer_cfs_start = time.time()
            logger.info('Starting customer cash flow statements')
            # dso_range = [1]
            create_customer_df = True
            if create_customer_df:
                customer_df = hf.get_customer_df(dso_range, case_path, metadata_path, rate_scenario)
                customer_df.to_hdf(case_path + '/Master_Customer_Dataframe.h5', key='customer_data')
                customer_df.to_csv(path_or_buf=case_path + '/Master_Customer_Dataframe.csv')
            else:
                customer_df = pd.read_hdf(case_path + '/Master_Customer_Dataframe.h5', key='customer_data', mode='r')

            main_variables = ['dso', 'tariff_class', 'building_type', 'cust_participating', 'cooling', 'heating', 'income_level']
            variables_combs = [['tariff_class', 'cust_participating'],
                            ['tariff_class', 'cust_participating', 'cooling', 'heating'],
                            ['building_type', 'cust_participating'],
                            # ['tariff_class', 'pv_participating'],
                            # ['tariff_class', 'ev_participating']
                            ['tariff_class', 'cust_participating', 'pv_participating'],
                            ['tariff_class', 'cust_participating', 'ev_participating']
            ]

            customer_mean_df = hf.get_mean_for_diff_groups(customer_df, main_variables, variables_combs, cfs_start_position=25)
            customer_mean_df.to_csv(path_or_buf=case_path + '/Customer_CFS_Summary.csv')
            logger.info('Completed customer cash flow statements')
            customer_cfs_time = time.time() - customer_cfs_start
            logger.info('Customer cash flow statements processing time: %.2f minutes', customer_cfs_time / 60)

        if dso_cfs:
            dso_cfs_start = time.time()
            logger.info('Starting DSO cash flow statements')
            (
                DSO_df,
                CapitalCosts_dict_list,
                Expenses_dict_list,
                Revenues_dict_list,
                DSO_Cash_Flows_dict_list,
            ) = hf.get_DSO_df(
                dso_range,
                generate_case_config,
                DSOmetadata,
                case_path,
                base_case_path,
                rate_scenario,
            )

            DSO_df.to_csv(path_or_buf=case_path + '/DSO_CFS_Summary.csv')

            os.chdir(case_path)
            i = 0
            for dso_num in dso_range:
                with open('DSO' + str(dso_num) + '_Capital_Costs.json', 'w') as f:
                    json.dump(CapitalCosts_dict_list[i], f, indent=2)
                with open('DSO' + str(dso_num) + '_Expenses.json', 'w') as f:
                    json.dump(Expenses_dict_list[i], f, indent=2)
                i += 1
            logger.info('Completed DSO cash flow statements')
            dso_cfs_time = time.time() - dso_cfs_start
            logger.info('DSO cash flow statements processing time: %.2f minutes', dso_cfs_time / 60)

        # 5. Automated calculation of valuation work-flow:
        #       c. Rerun annual customer billing to square up revenue

        # STEP 4 -- COMPARISON BETWEEN CASES OF ANNUAL RESULTS -----------------
        # (to be run once all cases complete)
        # TODO: Comparison analysis to be completed:
        # 1. Slider settings plots
        stats = True
        if stats:
            stats_start = time.time()
            logger.info('Starting statistical analysis and plots')
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
            logger.info('Completed statistical analysis and plots')
            stats_time = time.time() - stats_start
            logger.info('Statistical analysis and plots processing time: %.2f minutes', stats_time / 60)

        case_time = time.time() - case_start_time
        logger.info('Total processing time for case %s: %.2f minutes', case_name, case_time / 60)

def batch_process():
    base_case_path = flat_path
    demand_case_path = flat_path
    run_base = True
    run_annual_postprocessing(case_list, base_case_path, demand_case_path, run_base)

def one_process(case):
    # Select case to post-process
    case = case
    base_case_path = flat_path
    demand_case_path = case

    run_base = False
    case_list = []
    case_list.append(str(case))
    run_annual_postprocessing(case_list, base_case_path, demand_case_path, run_base)
    

if __name__ == "__main__":
    start_time = time.time()
    logger.info("Starting annual postprocessing script")
    # batch_process()
    one_process(flat_path)  # options are flat_path, TOU_path, RND_path
    end_time = time.time()
    total_time = end_time - start_time
    logger.info("Annual postprocessing script completed in %.2f minutes", total_time / 60)