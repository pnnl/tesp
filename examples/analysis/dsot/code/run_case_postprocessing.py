import os
from os.path import dirname, abspath, isdir

from datetime import datetime, timedelta
from joblib import Parallel, delayed

import tesp_support.dsot.plots as pt
import tesp_support.dsot.dso_rate_making as rm

''' This script runs key postprocessing functions that warrant execution after every simulation run.  
It has the following elements:
    0. Setup - establish locations and meta data files etc.
    1. Postprocessing that is required per DSO (and can be parallelized)
    2. Postprocessing that is required across all DSOs and is desired for every run
    3. Postprocessing that is needed over the entire year (and will likely need be executed on Constance).
    4. Postprocessing that compares cases (and will likely need to be executed on Constance).
'''

# Supported backends are:
# “loky” used by default, can induce some communication and memory overhead when exchanging input and
#    output data with the worker Python processes.
# “multiprocessing” previous process-based backend based on multiprocessing.Pool. Less robust than loky.
# “threading” is a very low-overhead backend, but it suffers from the Python Global Interpreter Lock
#    if the called function relies a lot on Python objects. “threading” is mostly useful when the execution
#    bottleneck is a compiled extension that explicitly releases the GIL (for instance a Cython loop
#    wrapped in a “with nogil” block or an expensive call to a library such as NumPy).
# finally, you can register backends by calling register_parallel_backend.
#   This will allow you to implement a backend of your liking.
_NUM_CORE = -1
_backend = 'loky'  # 'multiprocessing'  had some problems
_verbose = 10


def post_process():
    # Document on joblib
    # https://joblib.readthedocs.io/en/latest/generated/joblib.Parallel.html#joblib.Parallel
    parallel = Parallel(n_jobs=_NUM_CORE, backend=_backend, verbose=_verbose)

    def worker(arg1, arg2):
        print("arg2->" + str(arg2))
        worker_results = arg1(arg2)
        # return arg2
        return worker_results

    def DSO_bldg_loads(dso_number):
        os.chdir(config_path)
        pt.bldg_load_stack(dso_number, day_range, case_path, agent_prefix, GLD_prefix, metadata_path)

    def DSO_der_loads(dso_number):
        os.chdir(config_path)
        pt.der_load_stack(dso_number, day_range, case_path, GLD_prefix, metadata_path)

    def Daily_market_plot(day_number):
        os.chdir(config_path)
        pt.dso_market_plot(dso_range, str(day_number), case_path, dso_metadata_file, metadata_path)

    def DSO_specific_cost(dso_number):
        # load DSO metadata
        file_name = 'Substation_' + str(dso_number) + '_glm_dict.json'
        GLD_metadata = pt.load_json(case_path + agent_prefix + str(dso_number), file_name)

        dso_scaling_factor = DSOmetadata['DSO_' + str(dso_number)]['scaling_factor']
        # Determine tariff rate class of each meter up front ---- This won't be needed once this is done in prepare case
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
        agent_file_name = 'Substation_' + str(dso_number) + '_agent_dict.json'
        agent_metadata = pt.load_json(case_path + agent_prefix + str(dso_number), agent_file_name)

        GLD_metadata = pt.customer_meta_data(GLD_metadata, agent_metadata, metadata_path)

        # Need to preprocess agent retail data prior to calculating customer energy meter data.
        # This function saves a h5.
        if read_meters:
            pt.tic()
            for day_number in day_range:
                retail_data_df, retail_index_df = \
                    pt.load_retail_data(case_path, agent_prefix, str(dso_number), str(day_number), 'retail_site')
            print('Retail agent data processing complete: DSO ' + str(dso_number) + ', Month ' + month_name)
            pt.toc()

        # This function calculates the energy consumption every day for every customer and saves it to a h5 file.
        if read_meters:
            pt.tic()
            meter_df, energysum_df = rm.read_meters(GLD_metadata, case_path, GLD_prefix, str(dso_number),
                                                    day_range, dso_scaling_factor, metadata_path)
            print('Meter reading complete: DSO ' + str(dso_number) + ', Month ' + month_name)
            pt.toc()
        # --------------- CALCULATE AMENITY SCORES  ------------------------------

        # This function calculates the amenity scores (HVAC and WH unmet hours or gallons) and saves it to a h5 file.
        if calc_amenity:
            pt.tic()
            amenity_df = pt.amenity_loss(GLD_metadata, case_path, GLD_prefix, str(dso_number), day_range)
            print('Amenity scores complete: DSO ' + str(dso_number) + ', Month ' + month_name)
            pt.toc()

    #  STEP 0 ---------  STEP UP ------------------------------
    #  Determine which metrics to post-process
    read_meters = True
    calc_amenity = True
    pop_stats = True
    gen_plots = True
    der_stack_plots = True
    bldg_stack_plots = True
    forecast_plots = True
    # read_meters = False
    # calc_amenity = False
    # pop_stats = False
    # gen_plots = False
    # der_stack_plots = False
    # bldg_stack_plots = False
    # forecast_plots = False

    system_case = 'generate_case_config.json'
    first_data_day = 4  # First day in the simulation that data to be analyzed. Run-in days before this are discarded.
    discard_end_days = 1  # Number of days at the end of the simulation to be discarded

    # ------------ Select folder locations for different cases ---------
    # Load System Case Config
    config_path = os.getcwd()
    case_config = pt.load_json(config_path, system_case)

    case_path = dirname(abspath(__file__)) + '/' + case_config['caseName']    
    metadata_path = case_config['dataPath']
    dso_metadata_file = case_config['dsoPopulationFile']
    agent_prefix = '/DSO_'
    GLD_prefix = '/Substation_'

    # Check if there is a plots' folder - create if not.
    check_folder = isdir(case_path + '/plots')
    if not check_folder:
        os.makedirs(case_path + '/plots')

    # STEP 1 --------- DSO Specific Post-Processing -------------------------

    # --------------- PROCESS BILLING METERS  ------------------------------
    # Not sure how to find dso number that is running on a compute node
    DSOmetadata = pt.load_json(metadata_path, dso_metadata_file)

    num_sim_days = (datetime.strptime(case_config['EndTime'], '%Y-%m-%d %H:%M:%S') -
                    datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')).days
    month_dict = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July",
                  8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}
    month_name = month_dict[(datetime.strptime(case_config['StartTime'],
                                               '%Y-%m-%d %H:%M:%S') + timedelta(days=first_data_day)).month]

    day_range = range(first_data_day, num_sim_days - discard_end_days + 1)

    dso_range = []
    for DSO in DSOmetadata.keys():
        if 'DSO' in DSO:
            if DSOmetadata[DSO]['used']:
                dso_range.append(int(DSO.split('_')[-1]))

    processlist = list()
    for dso_num in dso_range:
        processlist.append([DSO_specific_cost, dso_num])

    if der_stack_plots:
        for dso_num in dso_range:
            processlist.append([DSO_der_loads, dso_num])

    if bldg_stack_plots:
        for dso_num in dso_range:
            processlist.append([DSO_bldg_loads, dso_num])

    if forecast_plots:
        for day_num in day_range:
            processlist.append([Daily_market_plot, day_num])

    if len(processlist) > 0:
        print('About to parallelize {} processes'.format(len(processlist)))
        results = parallel(delayed(worker)(p[0], p[1]) for p in processlist)
    else:
        print('No  process list')
        results = []

    # STEP 2 --------- Month Specific (all DSOs/TSO) Post-Processing -------------------------

    # ----------- CALCULATE POPULATION STATISTICS AND OUTPUT ---------------------------
    if pop_stats:
        bill = False
        rci_df = pt.RCI_analysis(dso_range, case_path, case_path, metadata_path, dso_metadata_file, bill)

    # ------------  PLOT TSO GENERATION AND AMES DATA  ------------------
    if gen_plots:
        pt.generation_load_profiles(case_path, metadata_path, case_path, day_range, True)
        pt.generation_load_profiles(case_path, metadata_path, case_path, day_range, False)
        GenAMES_df = pt.generation_statistics(case_path, config_path, system_case, day_range, False)
        GenPYPower_df = pt.generation_statistics(case_path, config_path, system_case, day_range, True)

    if der_stack_plots:
        pt.tic()
        pt.der_stack_plot(dso_range, day_range, metadata_path, case_path)
        print('DER Load Stack Data Aggregation and Plot complete')
        pt.toc()

    if bldg_stack_plots:
        pt.bldg_stack_plot(dso_range, day_range, case_path, metadata_path)

    if forecast_plots:
        pt.dso_forecast_stats(dso_range, day_range, case_path, dso_metadata_file, metadata_path)

    # STEP 3 ------- ANNUAL AGGREGATION AND ANALYSIS FUNCTIONS (to be run once all month aggregation is complete) ------
    # This step is performed in run_annual_postprocessing.py


post_process()
