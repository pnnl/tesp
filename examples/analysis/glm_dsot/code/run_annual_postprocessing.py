import json
import os
from datetime import datetime
from os.path import dirname, abspath, isdir
from pathlib import Path
import shutil
import numpy as np

import pandas as pd

import tesp_support.dsot.Wh_Energy_Purchases as ep
import tesp_support.dsot.plots as pt
import tesp_support.dsot.dso_quadratic_curves as qc
import tesp_support.dsot.dso_rate_making as rm
import tesp_support.dsot.dso_helper_functions as hf
from build_actual_da_q_from_case_outputs import reconstruct_actual_da_quantities
from calibrate_q_bid_forecast_correction import calibrate_q_bid_forecast_correction
from calibrate_config import merge_calibration_into_config


"""Run annual DSOT postprocessing for one or more cases.

High-level workflow:

1. Resolve paths and metadata.
2. Determine which annual products are missing for each case.
3. Run annual aggregation and analysis utilities (energy, amenity, load/LMP stats, etc.).
4. Recompute retail/DSO cash-flow outputs and summary files.
5. Produce comparison-style plots and metadata distributions.

Notes:
- The function can process multiple cases in sequence.
- The current implementation intentionally repeats each case twice to support
    a "generate then square-up" style workflow used by downstream billing logic.
"""


# --------------- Select folder locations for different cases -----------------
"""Setup guidance.

Before running this script:
1. Complete all monthly simulations for each target case.
2. Place the case folders under a shared annual post-processing directory,
   typically: $TESPDIR/examples/analysis/dsot/data/post_processing
3. Update the paths and case_list definitions below.
"""

hayden = False

if hayden:
    flat_path = 'C:/Users/reev057/DSOT-DATA/Rates/Flat'
    DSOT_path = 'C:/Users/reev057/DSOT-DATA/Rates/DSOT'
    TOU_path = 'C:/Users/reev057/DSOT-DATA/Rates/TOU'
    transactive_path = 'C:/Users/reev057/DSOT-DATA/Rates/Transactive'
    subscription_path = 'C:/Users/reev057/DSOT-DATA/Rates/Subscription'
    metadata_path = 'C:/Users/reev057/PycharmProjects/TESP_Public/examples/analysis/dsot/data'
else:
    datapath = os.path.expandvars('$TESPDIR/examples/analysis/dsot/data/post_processing') 
    flat_path = os.path.join(datapath, 'Flat')
    DSOT_path = os.path.join(datapath, 'DSOT')
    TOU_path = os.path.join(datapath, 'TOU')
    transactive_path = os.path.join(datapath, 'rob-don')
    subscription_path = os.path.join(datapath, 'sub') # duplicate the 'rob-don' folder and rename to 'sub'
    metadata_path = os.path.expandvars('$TESPDIR/examples/analysis/dsot/data') 

# ------------------- Select system-case definition ---------------------------
system_case = "8_hi_system_case_config.json"

# Add non-base cases to process, in dependency order if needed.
# Do not include the base case in this list.
case_list = [
    DSOT_path,
    TOU_path,
    transactive_path,
    subscription_path
]

# -------- Optional integrated Q-bid correction calibration --------
# Optional helper chain:
#   1) build actual_da_q.csv from DA_Q_forecast.csv + DA_Q_error.csv
#   2) calibrate Q_gain, t_65, t_65_2, and DC_change_Q_DA
#
# Keep disabled by default to preserve existing run behavior.
integrate_q_bid_calibration = False
qbid_temperature_csv = ''  # e.g. C:/path/to/temperature_hourly.csv or weather.dat
qbid_temperature_csv_template = None  # e.g. C:/path/to/DSO_{dso}/weather.dat
qbid_temperature_column = 'temperature'  # weather.dat uses 'temperature'
qbid_temperature_column_template = None
qbid_temperature_unit = 'C'  # set to 'F' if source temperature is already Fahrenheit
qbid_auto_discover_weather_dat = True
qbid_min_samples = 72
qbid_include_diagnostics = True
qbid_drop_total = True
qbid_actual_output_file = 'actual_da_q.csv'
qbid_calibration_output_file = 'Q_bid_forecast_correction_calibrated.json'
qbid_auto_merge_to_new_config = False
qbid_source_config_json5 = '../data/rates_config.json5'
qbid_output_config_json5 = 'rates_config_calibrated.json5'
qbid_diff_report_json = 'rates_config_calibration_diff_report.json'

def run_annual_postprocessing(case_list: list, base_case_path: str, demand_case_path : str, run_base: bool):
    """Execute annual postprocessing for a list of cases.

    The function checks for expected annual artifacts and computes only missing
    outputs where possible. It also reruns selected financial steps to align
    revenues/expenses and regenerate case-level summary products.


    Args:
        case_list (list): Paths to non-base cases to process.
        base_case_path (str): Path to the base-case folder (typically Flat).
        demand_case_path (str): Path to the demand reference case (typically TOU).
        run_base (bool): If True, prepend the base case for processing.

    Returns:
        None
    """

    # Optionally process the base case first.
    if run_base:
        case_list.insert(0, str(base_case_path))
    else: 
        pass
    # Repeat each case: first pass generates artifacts; second pass supports
    # revenue/expense reconciliation logic.
    case_list = np.repeat(case_list, 2)  
    
    for case_path in case_list:
        #  STEP 0 -- Determine which metrics to post-process

        if not os.path.isfile(os.path.join(case_path, 'energy_dso_1_data.h5')):
            print('No annual energy files found, running annual_energy...')
            annual_energy = True
        else: 
            annual_energy = False

        if not os.path.isfile(os.path.join(case_path, 'amenity_dso_1_data.h5')):
            print('No amenity data found, running annual_amenity...')
            annual_amenity = True
        else:
            annual_amenity = False

        if not os.path.isfile(os.path.join(case_path, 'DSO_load_stats.csv')):
            print('No load stats found, running load_stats...')
            load_stats = True
        else:
            load_stats = False

        if not os.path.isfile(os.path.join(case_path, 'Annual_DA_LMP_stats.csv')):
            print("No annual LMP stats found, running annual_lmps")
            annual_lmps = True
        else:
            annual_lmps = False

        if not os.path.isfile(os.path.join(case_path, 'generator_statistics_AMES.csv')):
            print('No AMES generator stats found, running gen_stats')
            gen_stats = True
        else:
            gen_stats = False

        if not os.path.isfile(os.path.join(case_path, 'DSO_quadratic_curves.json')):
            print('No Quadratic Curves found, running train_lmps')
            train_lmps = True
        else:
            train_lmps = False

        if not os.path.isfile(os.path.join(case_path, 'DSO1_Market_Purchases.json')):
            print('No Market Purchases found, running wholesale')
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

        # If True, derive first/last analysis day from each monthly simulation.
        # If False, use the fixed day values below.
        determine_days = False
        
        # First simulation day to analyze (run-in days before this are dropped).
        first_data_day = 4  
        # Number of trailing simulation days to discard.
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

        # Determine the case/rate scenario label.
        if case_path == flat_path:
            case_name = 'Flat'
            rate_scenario = "flat"
        if case_path == DSOT_path:
            case_name = 'DSOT'
            rate_scenario = "dsot"
        if case_path == TOU_path:
            case_name = 'TOU'
            rate_scenario = "time-of-use"
        if case_path == transactive_path:
            case_name = 'EandC'
            rate_scenario = "transactive"
        if case_path == subscription_path:
            case_name = 'Sub'
            rate_scenario = "subscription"

        print('---------------Postprocessing ' + str(case_name), 'Case ----------------')


        # Monthly definitions:
        # [month_name, month_path, first_analysis_day, end_day_plus_one]
        if case_path == TOU_path:
            month_def = [
                ['Jan', case_path + '/8_2016_01_pv_bt_fl_ev', 4, 31],
                ['Feb', case_path + '/8_2016_02_pv_bt_fl_ev', 4, 32],
                ['March', case_path + '/8_2016_03_pv_bt_fl_ev', 5, 33],   # Shifted by one day due to simulation issues.
                ['April', case_path + '/8_2016_04_pv_bt_fl_ev', 6, 35],   # Shifted by two days due to simulation issues.
                ['May', case_path + '/8_2016_05_pv_bt_fl_ev', 4, 33],
                ['June', case_path + '/8_2016_06_pv_bt_fl_ev', 4, 33],
                ['July', case_path + '/8_2016_07_pv_bt_fl_ev', 4, 33],
                ['August', case_path + '/8_2016_08_pv_bt_fl_ev', 4, 34],
                ['Sept', case_path + '/8_2016_09_pv_bt_fl_ev', 4, 33],
                ['Oct', case_path + '/8_2016_10_pv_bt_fl_ev', 4, 33],
                ['Nov', case_path + '/8_2016_11_pv_bt_fl_ev', 4, 33],
                ['Dec', case_path + '/8_2016_12_pv_bt_fl_ev', 4, 31]
            ]
        else:
            month_def = [
                ['Jan', case_path + '/8_rnd_2016_01_pv_bt_fl_ev', 4, 31],
                ['Feb', case_path + '/8_rnd_2016_02_pv_bt_fl_ev', 4, 32],
                ['March', case_path + '/8_rnd_2016_03_pv_bt_fl_ev', 4, 32],
                ['April', case_path + '/8_rnd_2016_04_pv_bt_fl_ev', 4, 33],
                ['May', case_path + '/8_rnd_2016_05_pv_bt_fl_ev', 4, 33],
                ['June', case_path + '/8_rnd_2016_06_pv_bt_fl_ev', 4, 33],
                ['July', case_path + '/8_rnd_2016_07_pv_bt_fl_ev', 4, 33],
                ['August', case_path + '/8_rnd_2016_08_pv_bt_fl_ev', 4, 34],
                ['Sept', case_path + '/8_rnd_2016_09_pv_bt_fl_ev', 4, 33],
                ['Oct', case_path + '/8_rnd_2016_10_pv_bt_fl_ev', 4, 33],
                ['Nov', case_path + '/8_rnd_2016_11_pv_bt_fl_ev', 4, 33],
                ['Dec', case_path + '/8_rnd_2016_12_pv_bt_fl_ev', 4, 31]
            ]


        # Verify and apply actual monthly simulation day counts.
        total_sim_days = 0
        generate_case_config = ''
        if not os.path.isfile(os.path.join(case_path, 'generate_case_config.json')):
                print('Copying generate_case_config.json to annual case folder')
                shutil.copy2(os.path.join(case_path, '8_2016_01_pv_bt_fl_ev/generate_case_config.json'), os.path.join(case_path, 'generate_case_config.json'))

        for month in month_def:
            generate_case_config = pt.load_json(month[1], 'generate_case_config.json')
            num_sim_days = (datetime.strptime(generate_case_config['EndTime'], '%Y-%m-%d %H:%M:%S') -
                            datetime.strptime(generate_case_config['StartTime'], '%Y-%m-%d %H:%M:%S')).days

            # Start from day n after dropping run-in days.
            # Assumes each monthly run includes extra trailing days.
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

        # Ensure plot output directory exists.
        check_folder = isdir(case_path + '/plots')
        if not check_folder:
            os.makedirs(case_path + '/plots')

        # STEP 3 -- Annual aggregation and analysis
        # (run after monthly outputs are available)

        # --------------- AGGREGATE ANNUAL ENERGY SUMMARIES  -------------------
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

            # --------------- AGGREGATE ANNUAL AMENITY SCORES  -----------------
            if annual_amenity:
                annual_amenity_df = pt.annual_amenity(GLD_metadata, month_def, GLD_prefix, str(dso_num))
                os.chdir(case_path)
                pt.tic()
                annual_amenity_df.to_hdf('amenity_dso_' + str(dso_num) + '_data.h5', key='amenity_data')
                annual_amenity_df.to_csv(path_or_buf=case_path + '/amenity_dso_' + str(dso_num) + '_data.csv')
                print('Annual Customer amenity impact aggregation complete: DSO ' + str(dso_num))
                pt.toc()

        # --------------- Aggregate annual DSO loads and compute Qmax ----------
        if load_stats:  # Also computes additional summary statistics.
            pt.dso_load_stats(dso_range, month_def, case_path, metadata_path, True)

        # --------- Aggregate annual LMP/load data for forecaster retuning -----
        if annual_lmps:
            for dso_num in dso_range:
                pt.dso_lmp_stats(month_def, case_path, renew_forecast_file, dso_range)
                pt.plot_lmp_stats(case_path, case_path, dso_num, 7)

        if gen_stats:
            # Annual LMP processing must run at least once so the annual OPF file exists.
            # TODO: Check if this means a separate run is needed for gen_stats
            # before metrics flags that follow it.
            GenAMES_df = pt.generation_statistics(case_path, config_path, system_case, total_day_range, False)

        if integrate_q_bid_calibration:
            print('Integrated Q-bid calibration enabled; preparing actual and calibrated coefficient files')
            try:
                baseline_csv = Path(case_path) / 'DA_Q_forecast.csv'
                da_error_csv = Path(case_path) / 'DA_Q_error.csv'
                if not baseline_csv.is_file() or not da_error_csv.is_file():
                    print('Skipping integrated Q-bid calibration: DA_Q_forecast.csv and/or DA_Q_error.csv missing')
                else:
                    temperature_csv_template = None
                    if qbid_temperature_csv_template:
                        temperature_csv_template = os.path.expandvars(qbid_temperature_csv_template)

                    # Auto-discover per-DSO weather.dat file layout when no explicit
                    # temperature source is configured.
                    if not qbid_temperature_csv and not temperature_csv_template and qbid_auto_discover_weather_dat and dso_range:
                        candidate_templates = [
                            str(Path(month_def[0][1]) / 'DSO_{dso}' / 'weather.dat'),
                            str(Path(month_def[0][1]) / 'weather_Substation_{dso}' / 'weather.dat'),
                        ]
                        for candidate in candidate_templates:
                            probe = Path(candidate.format(dso=dso_range[0]))
                            if probe.is_file():
                                temperature_csv_template = candidate
                                print(f'Auto-discovered weather.dat template: {temperature_csv_template}')
                                break

                    if not qbid_temperature_csv and not temperature_csv_template:
                        print('Skipping integrated Q-bid calibration: no temperature source configured or discovered')
                        continue

                    actual_csv = reconstruct_actual_da_quantities(
                        case_path=Path(case_path),
                        forecast_file='DA_Q_forecast.csv',
                        error_file='DA_Q_error.csv',
                        output_file=qbid_actual_output_file,
                        drop_total=qbid_drop_total,
                    )

                    temperature_csv = None
                    if qbid_temperature_csv:
                        temperature_csv = Path(os.path.expandvars(qbid_temperature_csv))

                    output_json = Path(case_path) / qbid_calibration_output_file

                    _, fit_results = calibrate_q_bid_forecast_correction(
                        baseline_csv=baseline_csv,
                        actual_csv=actual_csv,
                        temperature_csv=temperature_csv,
                        temperature_csv_template=temperature_csv_template,
                        temperature_column=qbid_temperature_column,
                        temperature_column_template=qbid_temperature_column_template,
                        temperature_unit=qbid_temperature_unit,
                        dsos=dso_range,
                        min_samples=qbid_min_samples,
                        include_diagnostics=qbid_include_diagnostics,
                        output=output_json,
                    )
                    print(
                        f'Integrated Q-bid calibration complete for {len(fit_results)} DSO(s); '
                        f'output: {output_json}'
                    )

                    if qbid_auto_merge_to_new_config:
                        source_cfg = Path(os.path.expandvars(qbid_source_config_json5))
                        output_cfg = Path(case_path) / qbid_output_config_json5
                        diff_report = Path(case_path) / qbid_diff_report_json
                        merge_calibration_into_config(
                            source_config_json5=source_cfg,
                            calibration_json=output_json,
                            output_config_json5=output_cfg,
                            report_json=diff_report,
                        )
                        print(f'Wrote calibrated config file: {output_cfg}')
                        print(f'Wrote calibration comparison report: {diff_report}')
            except Exception as ex:
                print(f'Integrated Q-bid calibration failed: {ex}')

        if train_lmps:
            obj = qc.DSO_LMPs_vs_Q(case_path)
            obj.multiple_fit_calls()
            obj.make_json_out()

        # --------------- Determine wholesale purchases -------------------------
        if wholesale:
            for dso_num in dso_range:
                qmax_df = pd.read_csv(case_path + '/Qmax.csv', index_col=[0])
                time_of_system_peak = datetime.fromisoformat(qmax_df.loc['DSO_Total', 'Time of Peak'])
                Market_Purchases = ep.Wh_Energy_Purchases(case_path, str(dso_num), True)
                print(Market_Purchases)
                os.chdir(case_path)
                with open('DSO' + str(dso_num) + '_Market_Purchases.json', 'w') as f:
                    json.dump(Market_Purchases, f, indent=2)
        # TODO: Make month naming consistent ('Mar' vs 'March').
        # --------------- Determine retail billing and reconciliation -----------
        # Workflow summary:
        # 1) Run customer billing to estimate revenues.
        # 2) Run DSO cash-flow to estimate required revenue.
        # 3) Re-run billing/cash-flow as needed to reconcile surplus error.
        # TODO: Split DSO CFS into staged components for clearer dependency order (prep required revenue first).
        if retail:
            dso_df = None
            for dso_num in dso_range:
                pt.tic()
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

                # Placeholder: add participation status to customer metadata.
                # TODO: Move this to case preparation and load directly from GLD metadata.
                agent_file_name = 'Substation_' + str(dso_num) + '_agent_dict.json'
                agent_metadata = pt.load_json(month_def[0][1] + agent_prefix + str(dso_num), agent_file_name)

                GLD_metadata = pt.customer_meta_data(GLD_metadata, agent_metadata, metadata_path)
                num_ind_cust = (DSOmetadata['DSO_' + str(dso_num)]['number_of_customers'] *
                                DSOmetadata['DSO_' + str(dso_num)]['RCI customer count mix']['industrial'])
                dso_scaling_factor = DSOmetadata['DSO_' + str(dso_num)]['scaling_factor']

                trans_cost_balance_method = None
                include_RT = False   # Include/exclude RT cost correction in customer billing.
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

                # Example: generate an annual customer bill dictionary for one meter.
                customer = list(GLD_metadata['billingmeters'].keys())[0]
                cust_bill_file = case_path + '/bill_dso_' + str(dso_num) + '_data.h5'
                cust_bills = pd.read_hdf(cust_bill_file, key='cust_bill_data', mode='r')
                cust_energy = pd.read_hdf(case_path + '/energy_dso_' + str(dso_num) + '_data.h5', key='energy_data', mode='r')
                customer_bill = rm.get_cust_bill(customer, cust_bills, GLD_metadata, cust_energy, rate_scenario)
                print(customer_bill)

                print("DSO " + str(dso_num) + ": Surplus error = " + str(surplus_err) + "%")
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

        # --------------- Determine customer/DSO cash-flow summaries ------------
        # Run final cash-flow summaries with current case revenue outputs.

        if customer_cfs:
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

        if dso_cfs:
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

        # 5) Automated valuation workflow hook.
        #    c) Re-run annual customer billing to reconcile revenue, if needed.

        # STEP 4 -- Cross-case annual comparison outputs
        # (intended to run once all target cases complete)
        # TODO: Complete comparison analysis additions (for example slider settings).
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

def batch_process():
    base_case_path = flat_path
    demand_case_path = TOU_path
    run_base = True
    run_annual_postprocessing(case_list, base_case_path, demand_case_path, run_base)

def one_process():
    # Select case to post-process
    case = transactive_path

    base_case_path = flat_path
    demand_case_path = transactive_path
    run_base = False
    case_list = []
    case_list.append(str(case))
    run_annual_postprocessing(case_list, base_case_path, demand_case_path, run_base)


def base_params_process():
        """Generate base-case Q-bid forecast-correction parameters.

        -------------------------------------------------------------------------------
        Note: this function was generated by an AI assistant to reproduce the forecast
        correction calibration process used in previous iterations of the DSOT analysis.
        -------------------------------------------------------------------------------      
        This wrapper runs a base-only annual postprocessing pass focused on
        producing calibration artifacts for:

        - Q_gain
        - t_65
        - t_65_2
        - DC_change_Q_DA

        Workflow performed by the integrated calibration block:

        1. Reads precomputed forecast files in the base annual case folder:
             - DA_Q_forecast.csv
             - DA_Q_error.csv
        2. Reconstructs actual DA quantity series to:
             - actual_da_q.csv (configurable via qbid_actual_output_file)
        3. Loads temperature data from one of the following sources:
             - qbid_temperature_csv, or
             - qbid_temperature_csv_template, or
             - auto-discovered per-DSO weather.dat paths when
                 qbid_auto_discover_weather_dat is True.
        4. Calibrates weekday/weekend coefficients per DSO.
        5. Writes calibration output to:
             - Q_bid_forecast_correction_calibrated.json
                 (configurable via qbid_calibration_output_file)

        Prerequisites:
        - Monthly case postprocessing should already have generated
            DA_Q_forecast.csv and DA_Q_error.csv for the target base annual folder.
        - Weather inputs (weather.dat) should be present if relying on
            auto-discovery.

        Notes:
        - This wrapper temporarily forces integrate_q_bid_calibration=True and
            restores its previous value afterwards.
        - It processes only the base case by calling run_annual_postprocessing
            with an empty case list and run_base=True.
        """
        global integrate_q_bid_calibration

        base_case_path = flat_path
        demand_case_path = TOU_path
        run_base = True

        prior_flag = integrate_q_bid_calibration
        integrate_q_bid_calibration = True
        try:
                run_annual_postprocessing([], base_case_path, demand_case_path, run_base)
        finally:
                integrate_q_bid_calibration = prior_flag
    

if __name__ == "__main__":
    #batch_process()
    #one_process()
    base_params_process()