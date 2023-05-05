import sys
from os.path import dirname, abspath, isdir
import os
sys.path.insert(0, dirname(abspath(__file__)))
from datetime import datetime

import tesp_support.dsot.plots
import tesp_support.dsot.dso_rate_making

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
read_meters = True
calc_amenity = True
pop_stats = True
gen_plots = True
load_stack_plots = True

# ------------ Select folder locations for different cases ---------
# Load System Case Config
config_path = dirname(abspath(__file__))
case_config = tesp_support.dsot.plots.load_json(config_path, 'system_case_config.json')

num_sim_days = (datetime.strptime(case_config['EndTime'], '%Y-%m-%d %H:%M:%S') -
                datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')).days
month_dict = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July",
              8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}
month_name = month_dict[datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S').month]

# Start at day two assuming first day is discarded.  In future 2-3 days may be discarded.
day_range = range(2, num_sim_days)
# day_range = range(2, 3)
# DSO range for 8 node case.  (for 200 node case we will need to determine active DSOs from metadata file).
dso_range = range(1, 9)
# dso_range = range(1, 2)

# case_path = dirname(abspath(__file__)) + '\\' + case_config['caseName']
case_path = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\May\\Aug7_20day_base_lean_a03902c7'
# metadata_path = '..\\dso_data'
metadata_path = 'C:\\Users\\reev057\\PycharmProjects\TESP\src\examples\\dsot_data'
metadata_file = case_config['dsoPopulationFile']
dso_meta_file = metadata_path + '\\' + metadata_file
agent_prefix = '\DSO_'
GLD_prefix = '\Substation_'

# Check if there is a plots folder - create if not.
check_folder = isdir(case_path + '\\plots')
if not check_folder:
    os.makedirs(case_path + '\\plots')


# STEP 1 --------- DSO Specfic Post-Processing -------------------------

# --------------- PROCESS BILLING METERS  ------------------------------
# Not sure how to find dso number that is running on a compute node
DSOmetadata = tesp_support.dsot.plots.load_json(metadata_path, metadata_file)

for dso_num in dso_range:
    # load DSO metadata
    file_name = 'Substation_' + str(dso_num) + '_glm_dict.json'
    metadata = tesp_support.dsot.plots.load_json(case_path + agent_prefix + str(dso_num), file_name)

    # In the future the scaling factor should come from system_case_config or 8-node meta_data
    # TODO: In a future update this will be done in the 200- and 8-node_metadata file.
    dso_scaling_factor = DSOmetadata['DSO_' + str(dso_num)]['number_of_customers'] \
                       * DSOmetadata['DSO_' + str(dso_num)]['RCI customer count mix']['residential'] \
                       / DSOmetadata['DSO_' + str(dso_num)]['number_of_gld_homes']

    # Determine tariff rate class of each meter up front ---- This wont be needed once this is done in prepare case
    commdata = tesp_support.dsot.plots.load_json(metadata_path, 'DSOT_commercial_metadata.json')
    commbldglist = []
    for bldg in commdata['building_model_specifics']:
        commbldglist.append(bldg)
    residbldglist = ['SINGLE_FAMILY', 'MOBILE_HOME', 'APARTMENTS', 'MULTI_FAMILY']

    for each in metadata['billingmeters']:
        metadata['billingmeters'][each]['tariff_class'] = None
        for bldg in commbldglist:
            if bldg in metadata['billingmeters'][each]['building_type']:
                metadata['billingmeters'][each]['tariff_class'] = 'commercial'
        for bldg in residbldglist:
            if bldg in metadata['billingmeters'][each]['building_type']:
                metadata['billingmeters'][each]['tariff_class'] = 'residential'
        if metadata['billingmeters'][each]['building_type'] == 'UNKNOWN':
            metadata['billingmeters'][each]['tariff_class'] = 'industrial'
        if metadata['billingmeters'][each]['tariff_class'] is None:
            raise Exception('Tariff class was not successfully determined for meter ' + each)

    # Place holder code to add whether a customer is participating or not.
    # TODO: this should be done in prepare case and read in as part of GLD meter metadata.
    agent_file_name = 'Substation_' + str(dso_num) + '_agent_dict.json'
    agent_metadata = tesp_support.dsot.plots.load_json(case_path + agent_prefix + str(dso_num), agent_file_name)

    metadata = tesp_support.dsot.plots.customer_meta_data(metadata, agent_metadata, True)

    # Need to preprocess agent retail data prior to calculating customer energy meter data.  This function saves an h5.
    if read_meters:
        tesp_support.dsot.plots.tic()
        for day_num in day_range:
            retail_data_df, retail_index_df = tesp_support.dsot.plots.load_retail_data(case_path, agent_prefix,
                                                                                       str(dso_num), str(day_num), 'retail_site')
        print('Retail agent data processing complete: DSO ' + str(dso_num) + ', Month ' + month_name)
        tesp_support.dsot.plots.toc()

    # This function calculates the energy consumption every day for every customer and saves it to an h5 file.
    if read_meters:
        tesp_support.dsot.plots.tic()
        meter_df, energysum_df = tesp_support.dsot.DSO_rate_making.read_meters(metadata, case_path, '\Substation_', str(dso_num),
                                                                               day_range, dso_scaling_factor)
        print('Meter reading complete: DSO ' + str(dso_num) + ', Month ' + month_name)
        tesp_support.dsot.plots.toc()
# --------------- CALCULATE AMENITY SCORES  ------------------------------

    # This function calculates the amenity scores (HVAC and WH unmet hours or gallons) and saves it to an h5 file.
    if calc_amenity:
        tesp_support.dsot.plots.tic()
        amenity_df = tesp_support.dsot.plots.amenity_loss(metadata, case_path, '\Substation_', str(dso_num),
                                                          day_range)
        print('Amenity scores complete: DSO ' + str(dso_num) + ', Month ' + month_name)
        tesp_support.dsot.plots.toc()

# STEP 2 --------- Month Specfic (all DSOs/TSO) Post-Processing -------------------------

# ----------- CALCULATE POPULATION STATISTICS AND OUTPUT ---------------------------
if pop_stats:
        bill = False
        rci_df = tesp_support.dsot.plots.RCI_analysis(dso_range, case_path, case_path, metadata_path, dso_meta_file, bill)


# ------------  PLOT TSO GENERATION AND AMES DATA
if gen_plots:

    tesp_support.dsot.plots.generation_load_profiles(case_path, config_path, metadata_path, case_path, day_range, True)

    tesp_support.dsot.plots.generation_load_profiles(case_path, config_path, metadata_path, case_path, day_range, False)

    GenAMES_df = tesp_support.dsot.plots.generation_statistics(case_path, config_path, metadata_path, day_range, False)

    GenPYPower_df = tesp_support.dsot.plots.generation_statistics(case_path, config_path, metadata_path, day_range, True)

if load_stack_plots:
    tesp_support.dsot.plots.tic()
    tesp_support.dsot.plots.der_load_stack(dso_range, day_range, case_path, agent_prefix, GLD_prefix,
                                           (metadata_path+'\\'+ metadata_file), metadata_path)
    print('Amenity scores complete: DSO ' + str(dso_num) + ', Month ' + month_name)
    tesp_support.dsot.plots.toc()
