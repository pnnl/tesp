import json
import pyjson5
import os
from datetime import datetime
from os.path import dirname, abspath, isdir
from pathlib import Path
import shutil
import pandas as pd

import tesp_support.dsot.Wh_Energy_Purchases as ep
import tesp_support.dsot.plots as pt
import tesp_support.dsot.dso_quadratic_curves as qc
import tesp_support.dsot.dso_rate_making as rm
import tesp_support.dsot.dso_helper_functions as hf
from build_actual_da_q import reconstruct_actual_da_quantities
from calibrate_q_bid_forecast_correction import calibrate_q_bid_forecast_correction
from calibrate_config import merge_calibration_into_config


"""Run annual DSOT postprocessing for one or more rate-scenario cases.

This script aggregates twelve monthly GridLAB-D/AMES co-simulation outputs
into a single annual result set and then runs financial analysis (billing,
cash flows) across the configured rate scenarios.

Prerequisites
-------------
1. Complete all twelve monthly co-simulations for every target case.
2. Confirm that each case's annual output folder exists under the
   post-processing directory defined by ``datapath`` below.
3. Verify the path variables and ``case_list`` match your directory layout.
4. Ensure $TESPDIR is set in your environment (or override paths manually).

Typical usage
-------------
Edit the configuration section below, then run::

    python run_annual_postprocessing.py

By default the script calls ``one_process()``, which processes only the
Flat (base) case. Change the active call in the ``__main__`` block to meet
your needs:

- ``one_process()``          -- Flat base case only (configuration run)
- ``batch_process()``        -- All cases in ``case_list`` plus the base case
- ``base_params_process()``  -- Base case only with Q-bid calibration forced on

Two-pass workflow
-----------------
Each case is processed *twice* in sequence:

  Pass 1 -- Generate missing annual artifacts (energy, amenity, LMPs, etc.).
  Pass 2 -- Re-run retail billing and cash-flow steps to reconcile any
            revenue surplus error introduced by the first pass.

The second pass should be quick because aggregate HDF5 files already exist and
their existence checks prevent redundant recomputation.

Key output files (written to each case folder)
----------------------------------------------
Aggregation outputs (generated on pass 1 if absent):
  energy_dso_<N>_data.h5         -- Annual per-meter energy and billing data
  transactive_dso_<N>_data.h5    -- Annual transactive participation summary
  amenity_dso_<N>_data.h5 / .csv -- Annual comfort/amenity impact scores
  DSO_load_stats.csv / Qmax.csv  -- System peak load and load statistics
  Annual_DA_LMP_stats.csv        -- Day-ahead LMP statistics for all DSOs
  generator_statistics_AMES.csv  -- AMES generator dispatch statistics
  DSO_quadratic_curves.json      -- Fitted LMP-vs-load quadratic curves

Financial outputs (regenerated on every pass):
  DSO<N>_Market_Purchases.json
  DSO<N>_Cash_Flows.json
  DSO<N>_Revenues_and_Energy_Sales.json
  DSO<N>_Customer_<meter>_Bill.json
  DSO<N>_Customer_Metadata.json
  Master_Customer_Dataframe.h5 / .csv
  Customer_CFS_Summary.csv       -- Customer cash-flow summary by group
  DSO_CFS_Summary.csv            -- DSO-level cash-flow summary
  DSO<N>_Capital_Costs.json / DSO<N>_Expenses.json
"""


# --------------- Select folder locations for different cases -----------------
# Edit this section before running the script.
#
# Expected directory layout under datapath (post-processing root):
#   Flat/     -- Base / flat-rate annual case folder
#   DSOT/     -- DSOT dynamic pricing annual case folder
#   TOU/      -- Time-of-use rate annual case folder
#   rob-don/  -- Transactive / EandC scenario annual case folder
#   sub/      -- Subscription rate scenario annual case folder
#
# Each folder must contain the twelve monthly simulation sub-folders
# (e.g., 8_2016_01_pv_bt_fl_ev/) before this script can be run.
#
# To use a different local path layout, add an elif branch below or set
# hayden = True to use hard-coded paths.
hayden = False

if hayden:
    flat_path = 'C:/Users/reev057/DSOT-DATA/Rates/Flat'
    DSOT_path = 'C:/Users/reev057/DSOT-DATA/Rates/DSOT'
    TOU_path = 'C:/Users/reev057/DSOT-DATA/Rates/TOU'
    transactive_path = 'C:/Users/reev057/DSOT-DATA/Rates/Transactive'
    subscription_path = 'C:/Users/reev057/DSOT-DATA/Rates/Subscription'
    metadata_path = 'C:/Users/reev057/PycharmProjects/TESP_Public/examples/analysis/dsot/data'
else:
    # Root of the annual post-processing output tree, resolved from $TESPDIR.
    datapath = os.path.expandvars('$TESPDIR/examples/analysis/glm_dsot/data/post_processing')
    flat_path        = os.path.join(datapath, 'Flat')     # Base / flat-rate scenario
    DSOT_path        = os.path.join(datapath, 'DSOT')     # DSOT dynamic pricing
    TOU_path         = os.path.join(datapath, 'TOU')      # Time-of-use rate
    transactive_path = os.path.join(datapath, 'rob-don')  # Transactive / EandC scenario
    subscription_path = os.path.join(datapath, 'sub')     # Subscription rate scenario
    #   (create 'sub' by duplicating the 'rob-don' folder and renaming it)
    # Shared metadata and configuration files used by all rate scenarios.
    metadata_path = os.path.expandvars('$TESPDIR/examples/analysis/glm_dsot/data')
    DSOT_metadata_path = os.path.expandvars('$TESPDIR/examples/analysis/dsot/data')

# ------------------- Select system-case definition ---------------------------
# nodes: number of DSO nodes in the network model (8-node or 200-node case).
nodes = 8
# scenario: load/generation scenario label embedded in configuration file names
# ('hi' = wind and solar, else just wind).
scenario = "hi"
# rcs: residential customer survey dataset used for population scaling.
# 'RECS' refers to the EIA Residential Energy Consumption Survey.
rcs = "RECS"

# Top-level system configuration file (AMES grid topology, generator data, etc.).
# Expected at: metadata_path/<nodes>_<scenario>_system_config.json5
system_config_file = f'{nodes}_{scenario}_system_config.json5'
# Rates and DSO configuration file shared across all rate scenarios.
# Expected at: metadata_path/rates_config.json5
case = "rates_config.json5"

# case_list: annual output folders for the non-base rate scenarios to process.
# - Do NOT include the base case (flat_path) here; it is prepended automatically
#   when run_base=True is passed to run_annual_postprocessing().
# - Order items so that cases with dependencies occur after their pre-req cases.
case_list = [
    DSOT_path,
    TOU_path,
    transactive_path,
    subscription_path
]

# -------- Optional integrated Q-bid forecast-correction calibration ----------
# When integrate_q_bid_calibration=True, the postprocessing loop will:
#   1. Reconstruct the actual day-ahead quantity (DA-Q) time series from
#      DA_Q_forecast.csv and DA_Q_error.csv in the annual case folder.
#   2. Fit per-DSO weekday/weekend correction coefficients:
#        Q_gain         -- overall quantity scaling factor
#        t_65           -- primary temperature response threshold
#        t_65_2         -- secondary temperature response threshold
#        DC_change_Q_DA -- baseline shift adjustment
#   3. Write the fitted coefficients to qbid_calibration_output_file.
#   4. Optionally merge the calibrated values back into a new rates_config file.
#
# Required inputs (must already exist in the annual case folder):
#   DA_Q_forecast.csv  -- Day-ahead quantity forecast from the simulation
#   DA_Q_error.csv     -- Forecast error time series
#   weather.dat        -- Hourly temperature (auto-discovered or configured below)
#
# Disabled by default to preserve existing run behavior.
# Required to calibrate a NEW scenario (i.e., new distribution of houses and DER)
integrate_q_bid_calibration = True

# --- Temperature data source (required when calibration is enabled) -----------
# Configure exactly ONE of the three options below:
#   Option A: a single CSV/DAT file with temperatures for all DSOs
qbid_temperature_csv = ''  # e.g. 'C:/path/to/temperature_hourly.csv'
#   Option B: a per-DSO path template; {dso} is replaced with the DSO number
qbid_temperature_csv_template = None  # e.g. 'C:/path/to/DSO_{dso}/weather.dat'
#   Option C: automatic search for weather.dat in the monthly simulation folders
qbid_auto_discover_weather_dat = True   # looks in DSO_<N>/weather.dat and variants

qbid_temperature_column = 'temperature'    # column name in the temperature file
qbid_temperature_column_template = None    # per-DSO column name override (rarely needed)
qbid_temperature_unit = 'F'                # 'C' for Celsius; set 'F' if already Fahrenheit
qbid_min_samples = 72                      # minimum hourly samples required for a valid fit
qbid_include_diagnostics = True            # write residual/diagnostic columns to output
qbid_drop_total = True                     # exclude the aggregate 'total' row from DA-Q

# Output file names written to the annual case folder:
qbid_actual_output_file = 'actual_da_q.csv'
qbid_calibration_output_file = 'Q_bid_forecast_correction_calibrated.json'

# Optional: merge calibrated coefficients into a new rates_config.json5 file.
# Set qbid_auto_merge_to_new_config=True to activate this step.
qbid_auto_merge_to_new_config = True
qbid_source_config_json5 = 'rates_config.json5'    # config file to update
qbid_output_config_json5 = 'rates_config_calibrated.json5' # merged output config
qbid_diff_report_json = 'rates_config_calibration_diff_report.json'  # change report


def _find_da_q_datetime_column(columns):
    """Return the most likely timestamp column name, if present."""
    lowered = {str(col).strip().lower(): col for col in columns}
    for candidate in ('date_time', 'datetime', 'timestamp', 'time'):
        if candidate in lowered:
            return lowered[candidate]
    return None


def _build_annual_da_q_file(month_def, case_path, filename):
    """Concatenate monthly DA_Q CSVs into one annual CSV in case_path."""
    annual_path = Path(case_path) / filename
    if annual_path.is_file():
        return annual_path

    monthly_frames = []
    missing_files = []

    for month in month_def:
        month_name = month[0]
        month_path = Path(month[1])
        monthly_file = month_path / filename

        if not monthly_file.is_file():
            missing_files.append(str(monthly_file))
            continue

        month_df = pd.read_csv(monthly_file)
        if month_df.empty:
            print(f'Warning: {monthly_file} is empty; skipping')
            continue

        monthly_frames.append(month_df)

    if missing_files:
        print(f'Cannot build annual {filename}: missing {len(missing_files)} monthly file(s)')
        for missing_file in missing_files:
            print(f'  missing: {missing_file}')
        return annual_path

    if not monthly_frames:
        print(f'Cannot build annual {filename}: no monthly data found')
        return annual_path

    annual_df = pd.concat(monthly_frames, ignore_index=True)

    dt_col = _find_da_q_datetime_column(annual_df.columns)
    if dt_col is not None:
        annual_df[dt_col] = pd.to_datetime(annual_df[dt_col], errors='coerce')
        bad_rows = annual_df[dt_col].isna().sum()
        if bad_rows:
            print(f'Warning: dropping {bad_rows} row(s) with invalid timestamps while building {filename}')
            annual_df = annual_df.dropna(subset=[dt_col])

        annual_df = annual_df.sort_values(dt_col).drop_duplicates(subset=[dt_col], keep='last')
        annual_df[dt_col] = annual_df[dt_col].dt.strftime('%Y-%m-%d %H:%M:%S')

    annual_df.to_csv(annual_path, index=False)
    print(f'Built annual {filename} from {len(monthly_frames)} monthly file(s): {annual_path}')
    return annual_path

def _build_annual_weather_files(month_def, case_path, dso_range,
                                weather_subdir_template):
    """Concatenate monthly weather.dat files into one annual file per DSO.

    weather_subdir_template: e.g. 'weather_Substation_{dso}' or 'DSO_{dso}',
    relative to each monthly folder.

    Returns a path template (with {dso}) to the annual per-DSO files, or None
    if the monthly weather files can't be found.
    """
    out_dir = Path(case_path) / 'annual_weather'
    out_dir.mkdir(parents=True, exist_ok=True)
    annual_template = str(out_dir / 'weather_dso_{dso}.csv')

    for dso in dso_range:
        frames = []
        for month in month_def:
            wf = Path(month[1]) / weather_subdir_template.format(dso=dso) / 'weather.dat'
            if not wf.is_file():
                print(f'  missing weather file: {wf}')
                return None
            wdf = pd.read_csv(wf, index_col=0, parse_dates=True)
            frames.append(wdf)
        annual = pd.concat(frames)
        annual = annual[~annual.index.duplicated(keep='last')].sort_index()
        annual.to_csv(Path(annual_template.format(dso=dso)))
    print(f'Built annual weather for {len(dso_range)} DSO(s) -> {annual_template}')
    return annual_template


def _ensure_annual_da_q_inputs(month_def, case_path):
    """Build annual DA_Q_forecast.csv and DA_Q_error.csv if missing."""
    forecast_csv = _build_annual_da_q_file(month_def, case_path, 'DA_Q_forecast.csv')
    error_csv = _build_annual_da_q_file(month_def, case_path, 'DA_Q_error.csv')
    return forecast_csv, error_csv


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

    # Work on a private copy so the caller's list is not mutated.
    case_list = list(case_list)
    # Prepend the base case so it is processed before the comparison cases.
    if run_base:
        case_list.insert(0, str(base_case_path))
    # Each case is processed twice:
    #   Pass 1 -- build missing annual aggregation files.
    #   Pass 2 -- re-run billing/cash-flow to reconcile the revenue surplus
    #             error that arises when rate tables change between passes.
    # File-existence checks at the start of each pass prevent redundant work.
    case_list = [c for c in case_list for _ in range(2)]
    
    for case_path in case_list:
        # ------------------------------------------------------------------ 
        # STEP 0 -- Determine which processing steps to run for this case. 
        #                                                                   
        # Each flag below is set True when the corresponding output file is 
        # absent from case_path. This makes the script re-entrant: if it   
        # was interrupted, only the remaining outputs will be regenerated on
        # the next run.                                                    
        #                                                                    
        # Exception: retail, customer_cfs, and dso_cfs are always True so  
        # that the billing reconciliation re-runs on every pass.            
        # ------------------------------------------------------------------ 

        if not os.path.isfile(os.path.join(case_path, 'energy_dso_8_data.h5')):
            print('No or incomplete annual energy files found, running annual_energy...')
            annual_energy = True
        else: 
            annual_energy = False

        if not os.path.isfile(os.path.join(case_path, 'amenity_dso_8_data.h5')):
            print('No or incomplete amenity data found, running annual_amenity...')
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

        # wholesale: set provisionally True here; refined after dso_range is
        # determined below (requires knowing which DSO files to check).
        # retail: always True -- re-runs on every pass to reconcile revenue.
        wholesale = True  # provisional
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

        # Load the shared rates configuration (rates_config.json5). This file
        # defines DSO population file paths, generator forecast filenames, and
        # other system parameters that are common to all rate scenarios.
        # The file lives in metadata_path (glm_dsot/data/), not in case_path.
        config_path = os.path.join(metadata_path, case)
        
        with open(config_path, 'r', encoding='utf-8') as json5_file:
            case_config = pyjson5.load(json5_file)

        # Index 5 of genForecastHr is the renewable (solar/wind) forecast file;
        # only the filename portion is needed since it lives in metadata_path.
        system_config_path = os.path.join(metadata_path, system_config_file)
        with open(system_config_path, 'r', encoding='utf-8') as json5_file:
            system_config = pyjson5.load(json5_file)

        renew_forecast_file = DSOT_metadata_path + "/" + system_config['genForecastHr'][5].split('/')[-1]
        # Load RECS-based DSO population metadata to identify which DSO nodes
        # are active in this network configuration.
        dso_metadata_file = case_config['population_file_RECS']
        DSOmetadata = pt.load_json(DSOT_metadata_path, dso_metadata_file)

        # Build the ordered list of active DSO indices from the population
        # metadata. The 'used' flag marks DSOs that participate in the
        # simulation; unused entries are topology placeholders only.
        # For the 8-node case this should yield dso_range = [1..8].
        dso_range = []
        for DSO in DSOmetadata.keys():
            if 'DSO' in DSO:
                if DSOmetadata[DSO]['used']:
                    dso_range.append(int(DSO.split('_')[-1]))

        # Now that dso_range is known, check whether wholesale market-purchase
        # files exist for ALL active DSOs. If any are missing, regenerate all.
        if all(os.path.isfile(os.path.join(case_path, 'DSO' + str(n) + '_Market_Purchases.json')) for n in dso_range):
            wholesale = False
        else:
            print('No Market Purchases found, running wholesale')

        # case_name: shorthand case name; to be used in plots and output filenames.
        # rate_scenario: string key that selects the correct tariff table inside
        #   dso_rate_making (must match the keys defined in that module).
        case_name = ''
        month_def = []
        rate_scenario = None

        # Map the case folder path to its label and rate-scenario string.
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


        # month_def: list of per-month run descriptors, one entry per calendar month.
        # Each entry is a list with the following elements (indices 0-3 initially;
        # indices 4-5 are appended later from generate_case_config.json):
        #   [0] month_name       -- Short label string (e.g. 'Jan', 'Feb', ...)
        #   [1] month_path       -- Absolute path to the monthly simulation folder
        #   [2] first_data_day   -- First simulation day to include (1-based);
        #                          days before this are treated as model run-in
        #   [3] end_day_plus_one -- One past the last day to include; the usable
        #                          day count is (end_day_plus_one - first_data_day)
        #   [4] StartTime        -- Appended below: simulation start timestamp
        #   [5] EndTime          -- Appended below: simulation end timestamp
        #
        # For the glm_dsot Flat case the monthly folders are named 8_Flat_2016_NN_pv and
        # live in dirname(flat_path) (= glm_dsot/code/). They are referenced with their
        # full path so no symlinks or data movement is required.
        if case_path == flat_path:
            # Monthly case folders live in glm_dsot/code/ alongside this script.
            # flat_path is in glm_dsot/data/post_processing/Flat so we cannot derive
            # the monthly folder location from it; use the script directory directly.
            monthly_base = dirname(abspath(__file__))  # glm_dsot/code/
            month_def = [
                ['Jan',    os.path.join(monthly_base, '8_Flat_2016_01_pv'), 4, 31],
                ['Feb',    os.path.join(monthly_base, '8_Flat_2016_02_pv'), 4, 32],
                ['March',  os.path.join(monthly_base, '8_Flat_2016_03_pv'), 4, 32],
                ['April',  os.path.join(monthly_base, '8_Flat_2016_04_pv'), 4, 33],
                ['May',    os.path.join(monthly_base, '8_Flat_2016_05_pv'), 4, 33],
                ['June',   os.path.join(monthly_base, '8_Flat_2016_06_pv'), 4, 33],
                ['July',   os.path.join(monthly_base, '8_Flat_2016_07_pv'), 4, 33],
                ['August', os.path.join(monthly_base, '8_Flat_2016_08_pv'), 4, 34],
                ['Sept',   os.path.join(monthly_base, '8_Flat_2016_09_pv'), 4, 33],
                ['Oct',    os.path.join(monthly_base, '8_Flat_2016_10_pv'), 4, 33],
                ['Nov',    os.path.join(monthly_base, '8_Flat_2016_11_pv'), 4, 33],
                ['Dec',    os.path.join(monthly_base, '8_Flat_2016_12_pv'), 4, 31],
            ]
        elif case_path == TOU_path:
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


        # Read generate_case_config.json from each monthly simulation folder to
        # obtain the exact start/end timestamps and total simulated day count.
        # Also copies the file to the annual case folder for reference.
        total_sim_days = 0
        # generate_case_config holds the last month's config after this loop;
        # it is used later by get_DSO_df() for simulation metadata.
        generate_case_config = None
        if not os.path.isfile(os.path.join(case_path, 'generate_case_config.json')):
                print('Copying generate_case_config.json to annual case folder')
                shutil.copy2(os.path.join(month_def[0][1], 'generate_case_config.json'), os.path.join(case_path, 'generate_case_config.json'))

        for month in month_def:
            generate_case_config = pt.load_json(month[1], 'generate_case_config.json')
            num_sim_days = (datetime.strptime(generate_case_config['EndTime'], '%Y-%m-%d %H:%M:%S') -
                            datetime.strptime(generate_case_config['StartTime'], '%Y-%m-%d %H:%M:%S')).days

            if determine_days:
                # Dynamically derive analysis window from the simulation timestamps,
                # discarding the run-in period (first_data_day) and trailing days.
                month[2] = first_data_day
                month[3] = num_sim_days - discard_end_days + 1
            # Append timestamps so downstream functions can reconstruct time axes.
            month.append(generate_case_config['StartTime'])
            month.append(generate_case_config['EndTime'])
            total_sim_days += month[3] - month[2]

        # 1-based day index spanning the full analysis year; used by
        # generation_statistics to label the AMES generator dispatch series.
        total_day_range = range(1, total_sim_days + 1)

        # Sub-folder prefix fragments for building per-DSO output paths.
        # Agent outputs live in  <monthly_path>/DSO_<N>/
        # GLD outputs live in    <monthly_path>/Substation_<N>/
        agent_prefix = '/DSO_'
        GLD_prefix = '/Substation_'

        # Create a plots/ subdirectory in the annual case folder if absent.
        check_folder = isdir(case_path + '/plots')
        if not check_folder:
            os.makedirs(case_path + '/plots')

        # ------------------------------------------------------------------
        # STEP 1 -- Annual aggregation and analysis                          
        # All steps in this section read already-completed monthly outputs   
        # and write annual summary files into case_path.                    
        # ------------------------------------------------------------------

        # --------------- AGGREGATE ANNUAL ENERGY SUMMARIES  -------------------
        # Load the GLD billing-meter dictionary (maps meter names to building
        # and customer metadata) from the first month's DSO subfolder; it is
        # identical across months and is reused for all annual aggregation steps.
        for dso_num in dso_range:
            file_name = 'Substation_' + str(dso_num) + '_glm_dict.json'
            GLD_metadata = pt.load_json(month_def[0][1] + agent_prefix + str(dso_num), file_name)
            if annual_energy:
                pt.tic()
                year_meter_df, year_energysum_df, year_trans_sum_df = \
                    rm.annual_energy(month_def, GLD_prefix, str(dso_num), GLD_metadata)
                year_meter_df.to_hdf(os.path.join(case_path, 'energy_dso_' + str(dso_num) + '_data.h5'), key='energy_data')
                year_energysum_df.to_hdf(os.path.join(case_path, 'energy_dso_' + str(dso_num) + '_data.h5'), key='energy_sums')
                year_trans_sum_df.to_hdf(os.path.join(case_path, 'transactive_dso_' + str(dso_num) + '_data.h5'), key='trans_data')
                print('Annual Customer Energy billing aggregation complete: DSO ' + str(dso_num))
                pt.toc()

            # --------------- AGGREGATE ANNUAL AMENITY SCORES  -----------------
            # Amenity scores quantify the comfort impact of demand-response
            # events on each customer (e.g., thermostat setpoint overrides, EV
            # charge delays). Lower scores indicate greater disruption.
            if annual_amenity:
                annual_amenity_df = pt.annual_amenity(GLD_metadata, month_def, GLD_prefix, str(dso_num))
                pt.tic()
                annual_amenity_df.to_hdf(os.path.join(case_path, 'amenity_dso_' + str(dso_num) + '_data.h5'), key='amenity_data')
                annual_amenity_df.to_csv(path_or_buf=case_path + '/amenity_dso_' + str(dso_num) + '_data.csv')
                print('Annual Customer amenity impact aggregation complete: DSO ' + str(dso_num))
                pt.toc()

        # --------------- Aggregate annual DSO loads and compute Qmax ----------
        # Computes the annual system peak load (Qmax) and load duration curves
        # for each DSO. Qmax.csv produced here is a required input for the
        # wholesale market-purchases step below.
        if load_stats:
            pt.dso_load_stats(dso_range, month_def, case_path, DSOT_metadata_path, True)

        # --------- Aggregate annual LMP/load data for forecaster retuning -----
        # dso_lmp_stats combines monthly day-ahead LMP and load data across all
        # DSOs into Annual_DA_LMP_stats.csv. This output can be used to
        # re-tune the LMP forecast model coefficients between simulation years.
        # plot_lmp_stats generates diagnostic scatter plots per DSO.
        if annual_lmps:
            pt.dso_lmp_stats(month_def, case_path, renew_forecast_file, dso_range)
            for dso_num in dso_range:
                pt.plot_lmp_stats(case_path, case_path, dso_num, 7)

        if gen_stats:
            # Reads the annual OPF (Optimal Power Flow) solution file written
            # by AMES and computes per-generator statistics (capacity factor,
            # total dispatch, cost). Requires the annual OPF file, which is
            # produced as a side-effect of annual_lmps; run that step first if
            # generator_statistics_AMES.csv is missing.
            #GenAMES_df = pt.generation_statistics(case_path, config_path, system_config_file, total_day_range, False)
            GenAMES_df = pt.generation_statistics(case_path, metadata_path, system_config_file, total_day_range, False)

        if integrate_q_bid_calibration:
            # Reconstruct the actual DA quantity series and fit correction
            # coefficients (Q_gain, t_65, t_65_2, DC_change_Q_DA) per DSO.
            # These coefficients adjust the DSO's day-ahead quantity bid to
            # match the observed system response under different temperature
            # conditions. See the qbid_* settings at the top of this file.
            print('Integrated Q-bid calibration enabled; preparing actual and calibrated coefficient files')
            try:
                baseline_csv, da_error_csv = _ensure_annual_da_q_inputs(month_def, case_path)

                if not baseline_csv.is_file() or not da_error_csv.is_file():
                    print('Skipping integrated Q-bid calibration: annual DA_Q_forecast.csv and/or DA_Q_error.csv could not be built')
                else:
                    temperature_csv_template = None
                    if qbid_temperature_csv_template:
                        temperature_csv_template = os.path.expandvars(qbid_temperature_csv_template)

                    # Gathers all per-DSO weather.dat files across the entire year
                    if not qbid_temperature_csv and not temperature_csv_template and qbid_auto_discover_weather_dat and dso_range:
                        subdir_candidates = ['DSO_{dso}', 'weather_Substation_{dso}']
                        chosen_subdir = None
                        for sub in subdir_candidates:
                            probe = Path(month_def[0][1]) / sub.format(dso=dso_range[0]) / 'weather.dat'
                            if probe.is_file():
                                chosen_subdir = sub
                                break
                        if chosen_subdir is not None:
                            temperature_csv_template = _build_annual_weather_files(
                                month_def, case_path, dso_range, chosen_subdir
                            )
                            if temperature_csv_template:
                                print(f'Using annual weather template: {temperature_csv_template}')

                    if not qbid_temperature_csv and not temperature_csv_template:
                        print('Skipping integrated Q-bid calibration: no temperature source configured or discovered')
                    else:
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
                            source_cfg = Path(os.path.join(os.path.expandvars('$TESPDIR/examples/analysis/glm_dsot/data/'), qbid_source_config_json5))
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
            # Fit quadratic curves to the annual LMP-vs-load scatter data.
            # The resulting curves map a quantity bid (MW) to a day-ahead price
            # for each DSO and are used by the DSO bidding model in subsequent
            # simulation years. Output: DSO_quadratic_curves.json
            obj = qc.DSO_LMPs_vs_Q(case_path)
            obj.multiple_fit_calls()
            obj.make_json_out()

        # --------------- Determine wholesale purchases -------------------------
        # Calculates the energy and capacity volumes each DSO purchases from the
        # wholesale market over the year, using the system peak (Qmax) and the
        # full-year day-ahead LMP series. Qmax.csv must already exist
        # (produced by the load_stats step above).
        # Output per DSO: DSO<N>_Market_Purchases.json
        if wholesale:
            for dso_num in dso_range:
                qmax_df = pd.read_csv(case_path + '/Qmax.csv', index_col=[0])
                # time_of_system_peak is read here for potential future use in
                # coincident-peak billing calculations.
                time_of_system_peak = datetime.fromisoformat(qmax_df.loc['DSO_Total', 'Time of Peak'])
                Market_Purchases = ep.Wh_Energy_Purchases(case_path, str(dso_num), True)
                print(Market_Purchases)
                with open(os.path.join(case_path, 'DSO' + str(dso_num) + '_Market_Purchases.json'), 'w') as f:
                    json.dump(Market_Purchases, f, indent=2)
        # TODO: Make month naming consistent ('Mar' vs 'March').
        # --------------- Determine retail billing and reconciliation -----------
        # Runs on every pass (retail=True always) to reconcile revenues and
        # expenses across the two-pass workflow.
        #
        # Steps performed per DSO:
        #   1. Load GLD billing-meter and agent metadata.
        #   2. Classify each billing meter as 'commercial', 'residential', or
        #      'industrial' based on its building_type field.
        #   3. Add customer participation flags (price-responsive, PV, EV) from 
        #      the agent dictionary to the meter metadata.
        #   4. Call DSO_rate_making() to compute customer bills and the DSO
        #      revenue statement, returning a surplus-error percentage.
        #   5. Write cash-flow, revenue, customer-bill, and metadata files.
        #
        # TODO: Split DSO CFS into staged components for clearer dependency order.
        if retail:
            # Load the DSO population metadata (customer counts, income mix,
            # scaling factors) once for all DSOs in this case.
            for dso_num in dso_range:
                pt.tic()
                file_name = 'Substation_' + str(dso_num) + '_glm_dict.json'
                GLD_metadata = pt.load_json(month_def[0][1] + agent_prefix + str(dso_num), file_name)

                # Build the list of commercial building type strings from the
                # shared commercial metadata file so we can classify meters.
                # NOTE: these metadata could eventually be moved over to glm_dsot/data
                # TODO: Why is DSOT_commercial_metadata.json for Miami, FL?
                commdata = pt.load_json(DSOT_metadata_path, 'DSOT_commercial_metadata.json')
                commbldglist = []
                for bldg in commdata['building_model_specifics']:
                    commbldglist.append(bldg)
                residbldglist = ['SINGLE_FAMILY', 'MOBILE_HOME', 'APARTMENTS', 'MULTI_FAMILY']

                # Assign a tariff_class ('commercial', 'residential', or
                # 'industrial') to every billing meter. This field is used by
                # DSO_rate_making() to select the correct rate schedule.
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

                # Add per-customer participation flags (price-responsive, PV, EV)
                # by merging the GLD billing-meter metadata with the agent
                # dictionary. This step will eventually be folded into case
                # preparation so the flags can be read directly from GLD metadata.
                # TODO: Move this to case preparation and load directly from GLD metadata.
                agent_file_name = 'Substation_' + str(dso_num) + '_agent_dict.json'
                agent_metadata = pt.load_json(month_def[0][1] + agent_prefix + str(dso_num), agent_file_name)

                GLD_metadata = pt.customer_meta_data(GLD_metadata, agent_metadata, DSOT_metadata_path)
                # Industrial customer count derived from the population mix ratio.
                num_ind_cust = (DSOmetadata['DSO_' + str(dso_num)]['number_of_customers'] *
                                DSOmetadata['DSO_' + str(dso_num)]['RCI customer count mix']['industrial'])
                # Scaling factor accounts for the ratio of simulated to real customers.
                dso_scaling_factor = DSOmetadata['DSO_' + str(dso_num)]['scaling_factor']

                # trans_cost_balance_method=None uses the default cost allocation.
                # include_RT=False excludes real-time price correction from bills.
                trans_cost_balance_method = None
                include_RT = False
                # DSO_rate_making() computes customer bills under rate_scenario,
                # then derives the DSO revenue statement and the surplus error
                # (surplus_err = (revenue - required_revenue) / required_revenue %).
                DSO_Cash_Flows, DSO_Revenues_and_Energy_Sales, tariff, surplus_err = rm.DSO_rate_making(
                    case_path,
                    demand_case_path,
                    dso_num,
                    GLD_metadata,
                    DSOT_metadata_path,
                    dso_scaling_factor,
                    num_ind_cust,
                    case_name,
                    rate_scenario,
                    trans_cost_balance_method,
                    include_RT
                )

                # Generate a sample annual bill for the first billing meter as a
                # diagnostic output. The meter key is arbitrary; swap it for a
                # specific meter name to inspect a different customer's bill.
                customer = list(GLD_metadata['billingmeters'].keys())[0]
                cust_bill_file = case_path + '/bill_dso_' + str(dso_num) + '_data.h5'
                cust_bills = pd.read_hdf(cust_bill_file, key='cust_bill_data', mode='r')
                cust_energy = pd.read_hdf(case_path + '/energy_dso_' + str(dso_num) + '_data.h5', key='energy_data', mode='r')
                customer_bill = rm.get_cust_bill(customer, cust_bills, GLD_metadata, cust_energy, rate_scenario)
                print(customer_bill)

                print("DSO " + str(dso_num) + ": Surplus error = " + str(surplus_err) + "%")
                pt.toc()

                with open(os.path.join(case_path, 'DSO' + str(dso_num) + '_Cash_Flows.json'), 'w') as f:
                    json.dump(DSO_Cash_Flows, f, indent=2)
                with open(os.path.join(case_path, 'DSO' + str(dso_num) + '_Revenues_and_Energy_Sales.json'), 'w') as f:
                    json.dump(DSO_Revenues_and_Energy_Sales, f, indent=2)
                with open(os.path.join(case_path, 'DSO' + str(dso_num) + '_Customer_' + customer + '_Bill.json'), 'w') as f:
                    json.dump(customer_bill, f, indent=2)
                with open(os.path.join(case_path, 'DSO' + str(dso_num) + '_Customer_Metadata.json'), 'w') as f:
                    json.dump(GLD_metadata, f, indent=2)

        # --------------- Determine customer/DSO cash-flow summaries ------------
        # Aggregate the per-DSO billing results into cross-DSO summary tables
        # that group customers by key demographic and equipment attributes.

        if customer_cfs:
            # Set create_customer_df=True (default) to rebuild the master
            # customer dataframe from the per-DSO bill HDF5 files. Set False
            # to reload an existing Master_Customer_Dataframe.h5, which is
            # faster when only the summary statistics need to be regenerated.
            create_customer_df = True
            if create_customer_df:
                customer_df = hf.get_customer_df(dso_range, case_path, DSOT_metadata_path, rate_scenario)
                customer_df.to_hdf(case_path + '/Master_Customer_Dataframe.h5', key='customer_data')
                customer_df.to_csv(path_or_buf=case_path + '/Master_Customer_Dataframe.csv')
            else:
                customer_df = pd.read_hdf(case_path + '/Master_Customer_Dataframe.h5', key='customer_data', mode='r')

            # main_variables: all customer attributes available for grouping.
            main_variables = ['dso', 'tariff_class', 'building_type', 'cust_participating', 'cooling', 'heating', 'income_level']
            # variables_combs: each inner list defines one grouping combination
            # for which mean bill components are computed. Add or remove entries
            # to expand or narrow the summary table.
            variables_combs = [['tariff_class', 'cust_participating'],
                              ['tariff_class', 'cust_participating', 'cooling', 'heating'],
                              ['building_type', 'cust_participating'],
                            # ['tariff_class', 'pv_participating'],
                            # ['tariff_class', 'ev_participating']
                              ['tariff_class', 'cust_participating', 'pv_participating'],
                              ['tariff_class', 'cust_participating', 'ev_participating']
            ]

            # cfs_start_position=25: column index where the cash-flow (billing)
            # columns begin in the customer dataframe; columns before this index
            # are metadata attributes and are excluded from the mean calculation.
            customer_mean_df = hf.get_mean_for_diff_groups(customer_df, main_variables, variables_combs, cfs_start_position=25)
            customer_mean_df.to_csv(path_or_buf=case_path + '/Customer_CFS_Summary.csv')

        if dso_cfs:
            # Computes the DSO-level cash-flow statement by comparing annual
            # revenues (from retail billing) against capital costs and
            # operating expenses for each DSO.
            # Output: DSO_CFS_Summary.csv, DSO<N>_Capital_Costs.json,
            #         DSO<N>_Expenses.json
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

            i = 0
            for dso_num in dso_range:
                with open(os.path.join(case_path, 'DSO' + str(dso_num) + '_Capital_Costs.json'), 'w') as f:
                    json.dump(CapitalCosts_dict_list[i], f, indent=2)
                with open(os.path.join(case_path, 'DSO' + str(dso_num) + '_Expenses.json'), 'w') as f:
                    json.dump(Expenses_dict_list[i], f, indent=2)
                i += 1

        # ------------------------------------------------------------------ 
        # STEP 2 -- Cross-case comparison and distribution outputs            
        # These run on every pass for every case. They produce RCI           
        # (residential/commercial/industrial) bill distributions and          
        # metadata attribute histograms used for cross-scenario comparison.  
        # TODO: Complete comparison analysis additions (e.g. slider settings).
        # ------------------------------------------------------------------ 

        # RCI_analysis: computes income-weighted bill distributions by customer
        # class (residential, commercial, industrial) across all active DSOs.
        bill = True
        rci_df = pt.RCI_analysis(dso_range, month_def[0][1], case_path, DSOT_metadata_path, dso_metadata_file, bill)

        # params: list of [metadata_system, customer_class, attribute] tuples
        # that drive metadata_dist_plots. Each entry produces one histogram
        # showing the distribution of that attribute across all simulated
        # customers. Add entries here to expand the comparison plot set.
        params = [
            # ['houses', 'SINGLE_FAMILY', 'cooling_COP'],  # example: COP distribution
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
                                case=month_def[0][1], data_path=case_path, metadata_path=DSOT_metadata_path,
                                agent_prefix=agent_prefix)

def batch_process():
    """Process all rate scenarios in a single run.

    Runs the full case_list (DSOT, TOU, Transactive, Subscription) plus the
    Flat base case. Used after completing all twelve monthly co-simulations for 
    every case.

    The TOU case serves as the demand reference for billing calculations
    (demand_case_path) because its load shapes best represent the baseline
    customer response assumed in the rate design.
    """
    base_case_path = flat_path
    demand_case_path = TOU_path  # TOU provides the demand reference for billing
    run_base = True
    run_annual_postprocessing(case_list, base_case_path, demand_case_path, run_base)

def one_process(case_path):
    """Process one case only.

    Useful for a quick end-to-end pipeline check or when only one case's
    outputs need refreshing. 

    Before running, create the case annual output directory if it does not
    exist. E.g., 
        mkdir <post_processing_root>/Flat 
    """
    base_case_path = case_path
    if case_path == flat_path:
        demand_case_path = flat_path  # Flat used as its own demand reference
    else:
        demand_case_path = TOU_path  # TOU provides the demand reference for billing
    
    run_base = True
    run_annual_postprocessing([], base_case_path, demand_case_path, run_base)


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
    # Choose the appropriate entry point for your run:
    #   one_process()         -- Single case processing (default; good for testing)
    #   batch_process()       -- All cases in case_list plus the base case
    #   base_params_process() -- Base case with Q-bid calibration forced on
    #batch_process()
    #one_process(flat_path)
    base_params_process()