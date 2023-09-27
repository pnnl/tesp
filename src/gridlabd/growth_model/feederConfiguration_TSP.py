# Copyright (c) 2017-2023 Battelle Memorial Institute
# file: feederConfiguration_TSP.py

"""
Created on Dec 20, 2016

This file contains three function that help configure specific feeders:

	technologyFunction(case_flag):
		This function creates the use flags dictionary
	feederDefinition(feederName):
		Creates the specific settings for each feeder needed to populate the feeder
	feederConfiguration(config_file, classification):
		Creates the complete configuration dictionary needed to populate the feeder

@author: hans464
"""

def technologyFunction(case_flag):
	"""
	Creates the use flags dictionary

	Inputs
		case_flag - an integer indicating which technology case to tack on to the GridLAB-D model
			 case_flag : technology
			 0 : Load shape case
			 1 : House case
	Outputs
		use_flags - dictionary that contains flags for what technology case to tack on to the GridLAB-D model
	"""
	valid = [0, 1]

	if case_flag not in valid:
		raise Exception('case flag "{:s}" is not defined'.format(case_flag))

	use_flags = {'use_normalized_loadshapes' : 0,
				 'use_homes' : 0,
				 'use_commercial' : 0,}

	# standard settings that apply to all feeders

	# quick case. Use load shapes instead of house objects.
	if case_flag is 0:
		use_flags["use_normalized_loadshapes"] = 1
		use_flags["use_homes"] = 1
		use_flags["use_commercial"] = 0

	# base case. Use house objects.
	if case_flag is 1:
		use_flags["use_normalized_loadshapes"] = 0
		use_flags["use_homes"] = 1
		use_flags["use_commercial"] = 0

	return use_flags

def feederDefinition(feederName):
	"""
	Creates the specific settings for each feeder needed to populate the feeder

	Inputs
		feederName - name of the specific feeder we are working on
	Outputs
		data - dictionary that contains information about the current feeder. Can be obtained by running feederDefinition
	"""
	data = dict()

	# standard settings that apply to all feeders
	data["timezone"] = 'PST8'
	data['startdate'] = '2013-01-01 0:00:00'
	data['stopdate'] = '2013-01-03 0:00:00'

	data['record_in'] = '2013-01-01 23:59:00'
	data['record_out'] = '2013-01-03 0:00:00'

	# data['startdate'] = '2013-08-01 0:00:00'
	# data['stopdate'] = '2013-08-03 0:00:00'
	#
	# data['record_in'] = '2013-08-01 23:59:00'
	# data['record_out'] = '2013-08-03 0:00:00'

	data['minimum_timestep'] = 30

	data['measure_interval'] = 60

	data["load_shape_norm"] = 'load_shape_player.player'

	# recorders
	data["recorders"] = ['water_heaters',		# record properties from the electric water heaters
						'responsive_load',		# record power drawn by responsive zip loads
						'unresponsive_load', 	# record power drawn by non responsive loads
						'HVAC',
						'swing_node',
						'climate']
	# feeder specific settings
	if feederName is '4BusSystem':
		# Nominal voltage of the trunk of the feeder
		data["nom_volt"] = 14400

		# substation rating in MVA - add'l 15% gives rated kW & pf = 0.87
		data["feeder_rating"] = 1.15 * 14.0

		# Scale the load shape
		data["normalized_loadshape_scalar"] = 1

		# Region Identifier (1:West Coast (temperate), 2:North Central/Northeast (cold/cold), 3:Southwest (hot/arid), 4:Southeast/Central (hot/cold), 5:Southeast Coastal (hot/humid), 6: Hawaii (sub-tropical))
		data["region"] = 4

		# Please specify what weather file you would like to use (either .csv or .tmy). If not specified, region weather file will be used!
		data["weather"] = ''

		# Determines how many houses to populate (bigger avg_house = less houses)
		data["avg_house"] = 3000

		# Scale the responsive and unresponsive loads (percentage)
		data["base_load_scalar"] = 1.0

		# variable to shift the residential schedule skew (seconds)
		data["residential_skew_shift"] = 0

		# maximum schedule skew (seconds) [-residential_skew_max, residential_skew_max]
		data["residential_skew_max"] = 8100

		# widen schedule skew (seconds)
		data["residential_skew_std"] = 2700

		# heating offset, 1 is default
		data["heating_offset"] = 1

		# cooling offset, 1 is default
		data["cooling_offset"] = 1

		# COP high scalar, 1 is default
		data["COP_high_scalar"] = 1

		# COP low scalar, 1 is default
		data["COP_low_scalar"] = 1

		# residential zip fractions for loadshapes
		data["r_heat_fraction"] = 0.9
		data["r_z_pf"] = 0.97
		data["r_i_pf"] = 0.97
		data["r_p_pf"] = 0.97
		data["r_zfrac"] = 0.2
		data["r_ifrac"] = 0.4
		data["r_pfrac"] = 1 - data["r_zfrac"] - data["r_ifrac"]

		# percentage of house that use Gas for heating. If not set default will be pulled from region specific values
		data["perc_gas"] = 1

		# percentage of house that use Heat pumps. If not set default will be pulled from region specific values
		data["perc_pump"] = 0

		# percentage of house that use AC systems. If not set default will be pulled from region specific values
		data["perc_AC"] = 1

		# percentage of house that have an electric water heater. If not set default will be pulled from region specific values
		data["wh_electric"] = 0

		# percentage of house that have a pool pump. Will only affect SFH. If not set default will be pulled from region specific values
		data["perc_poolpumps"] = 0


		# Determines sizing of commercial loads (bigger avg_commercial = less houses)
		data["avg_commercial"] = 35000

		# maximum schedule skew (seconds) [-commercial_skew_max, commercial_skew_max]
		data["commercial_skew_max"] = 8100

		# widen schedule skew (seconds)
		data["commercial_skew_std"] = 2700

		# commercial cooling COP
		data["cooling_COP"] = 3

		# commercial zip fractions for loadshapes
		data["c_z_pf"] = 0.97
		data["c_i_pf"] = 0.97
		data["c_p_pf"] = 0.97
		data["c_zfrac"] = 0.2
		data["c_ifrac"] = 0.4
		data["c_pfrac"] = 1 - data["c_zfrac"] - data["c_ifrac"]

	else:
		raise Exception('"{:s}" is not a known feeder!'.format(feederName))

	# ----------------- Some under the hood things to take care of ------------------------------
	regionWeatherFiles = ['CA-San_francisco.tmy2',
						  'IL-Chicago.tmy2',
						  'AZ-Phoenix.tmy2',
						  'TN-Nashville.tmy2',
						  'FL-Miami.tmy2',
						  'HI-Honolulu.tmy2']

	if data["weather"] is '':
		data["weather"] = regionWeatherFiles[data["region"]-1]

	return data

def feederConfiguration(config_file, classification):
	"""
	Creates the complete configuration dictionary needed to populate the feeder

	Inputs
		config_file - dictionary that contains information about the current feeder. Can be obtained by running feederDefinition
		classification -  The classification for which you would like the function to pull configuration data.
                              Integer value from 1 to 9. 
	Outputs
		data - dictionary with full configuration specifications
	"""
	data = config_file

	# Load Classifications
	data["load_classifications"] = ['Residential1', 'Residential2', 'Residential3', 'Residential4', 'Residential5',
									'Residential6', 'Commercial1', 'Commercial2', 'Commercial3']
	# Thermal Percentages by Region
	# - The "columns" represent load classifications. The "rows" represent the breakdown within that classification of building age.
	#   1:<1940     2:1980-89   3:<1940     4:1980-89   5:<1960     6:<1960     7:<2010 8:<2010 9:<2010
	#   1:1940-49   2:>1990     3:1940-49   4:>1990     5:1960-89   6:1960-89   7:-     8:-     9:-
	#   1:1950-59   2:-         3:1950-59   4:-         5:>1990     6:>1990     7:-     8:-     9:-
	#   1:1960-69   2:-         3:1960-69   4:-         5:-         6:-         7:-     8:-     9:-
	#   1:1970-79   2:-         3:1970-79   4:-         5:-         6:-         7:-     8:-     9:-
	#   1:-         2:-         3:-   		4:-         5:-         6:-         7:-     8:-     9:-
	# Using values from the old regionalization.m script.
	# Retooled the old thermal percentages values into this new "matrix" form for classifications.
	if data["region"] == 1:
		thermal_percentages = [[0.1652, 0.4935, 0.1652, 0.4935, 0.0000, 0.1940, 1, 1, 1],  # 1
							   [0.1486, 0.5064, 0.1486, 0.5064, 0.7535, 0.6664, 0, 0, 0],  # 2
							   [0.2238, 0.0000, 0.2238, 0.0000, 0.2462, 0.1395, 0, 0, 0],  # 3
							   [0.1780, 0.0000, 0.1780, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 4
							   [0.2841, 0.0000, 0.2841, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 5
							   [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]]  # 6
		data["floor_area"] = [2209, 2209, 2209, 2209, 1054, 820, 0, 0, 0]
		data["one_story"] = [0.6887] * 9
		data["window_wall_ratio"] = 0.15
		perc_gas = [0.7051] * 9
		perc_pump = [0.0321] * 9
		perc_AC = [0.4348] * 9
		wh_electric = [0.7455] * 9
		wh_size = [[0.0000, 0.3333, 0.6667]] * 9
		AC_type = [[1, 1, 1, 1, 1, 1, 0, 0, 0],  # central
				   [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		over_sizing_factor = [[0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0, 0, 0],  # central
							  [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		perc_pool_pumps = [0.0904] * 9
	elif data["region"] == 2:
		thermal_percentages = [[0.2873, 0.3268, 0.2873, 0.3268, 0.0000, 0.2878, 1, 1, 1],  # 1
							   [0.1281, 0.6731, 0.1281, 0.6731, 0.6480, 0.5308, 0, 0, 0],  # 2
							   [0.2354, 0.0000, 0.2354, 0.0000, 0.3519, 0.1813, 0, 0, 0],  # 3
							   [0.1772, 0.0000, 0.1772, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 4
							   [0.1717, 0.0000, 0.1717, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 5
							   [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]]  # 6
		data["floor_area"] = [2951] * 9
		data["one_story"] = [0.5210] * 9
		data["window_wall_ratio"] = 0.15
		perc_gas = [0.8927] * 9
		perc_pump = [0.0177] * 9
		perc_AC = [0.7528] * 9
		wh_electric = [0.7485] * 9
		wh_size = [[0.1459, 0.5836, 0.2706]] * 9
		AC_type = [[1, 1, 1, 1, 1, 1, 0, 0, 0],  # central
				   [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		over_sizing_factor = [[0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0, 0, 0],  # central
							  [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		perc_pool_pumps = [0.0591] * 9
	elif data["region"] == 3:
		thermal_percentages = [[0.1240, 0.3529, 0.1240, 0.3529, 0.0000, 0.1079, 1, 1, 1],  # 1
							   [0.0697, 0.6470, 0.0697, 0.6470, 0.6343, 0.6316, 0, 0, 0],  # 2
							   [0.2445, 0.0000, 0.2445, 0.0000, 0.3656, 0.2604, 0, 0, 0],  # 3
							   [0.2334, 0.0000, 0.2334, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 4
							   [0.3281, 0.0000, 0.3281, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 5
							   [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]]  # 6
		data["floor_area"] = [2370] * 9
		data["one_story"] = [0.7745] * 9
		data["window_wall_ratio"] = 0.15
		perc_gas = [0.6723] * 9
		perc_pump = [0.0559] * 9
		perc_AC = [0.5259] * 9
		wh_electric = [0.6520] * 9
		wh_size = [[0.2072, 0.5135, 0.2793]] * 9
		AC_type = [[1, 1, 1, 1, 1, 1, 0, 0, 0],  # central
				   [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		over_sizing_factor = [[0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0, 0, 0],  # central
							  [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		perc_pool_pumps = [0.0818] * 9
	elif data["region"] == 4:
		thermal_percentages = [[0.1470, 0.3297, 0.1470, 0.3297, 0.0000, 0.1198, 1, 1, 1],  # 1
							   [0.0942, 0.6702, 0.0942, 0.6702, 0.5958, 0.6027, 0, 0, 0],  # 2
							   [0.2253, 0.0000, 0.2253, 0.0000, 0.4041, 0.2773, 0, 0, 0],  # 3
							   [0.2311, 0.0000, 0.2311, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 4
							   [0.3022, 0.0000, 0.3022, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 5
							   [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]]  # 6
		data["floor_area"] = [2655] * 9
		data["one_story"] = [0.7043] * 9
		data["window_wall_ratio"] = 0.15
		perc_gas = [0.4425] * 9
		perc_pump = [0.1983] * 9
		perc_AC = [0.9673] * 9
		wh_electric = [0.3572] * 9
		wh_size = [[0.2259, 0.5267, 0.2475]] * 9
		AC_type = [[1, 1, 1, 1, 1, 1, 0, 0, 0],  # central
				   [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		over_sizing_factor = [[0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0, 0, 0],  # central
							  [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		perc_pool_pumps = [0.0657] * 9
	elif data["region"] == 5:
		thermal_percentages = [[0.1470, 0.3297, 0.1470, 0.3297, 0.0000, 0.1198, 1, 1, 1],  # 1
							   [0.0942, 0.6702, 0.0942, 0.6702, 0.5958, 0.6027, 0, 0, 0],  # 2
							   [0.2253, 0.0000, 0.2253, 0.0000, 0.4041, 0.2773, 0, 0, 0],  # 3
							   [0.2311, 0.0000, 0.2311, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 4
							   [0.3022, 0.0000, 0.3022, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 5
							   [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]]  # 6
		data["floor_area"] = [2655] * 9
		data["one_story"] = [0.7043] * 9
		data["window_wall_ratio"] = 0.15
		perc_gas = [0.4425] * 9
		perc_pump = [0.1983] * 9
		perc_AC = [0.9673] * 9
		wh_electric = [0.3572] * 9
		wh_size = [[0.2259, 0.5267, 0.2475]] * 9
		AC_type = [[1, 1, 1, 1, 1, 1, 0, 0, 0],  # central
				   [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		over_sizing_factor = [[0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0, 0, 0],  # central
							  [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		perc_pool_pumps = [0.0657] * 9
	elif data["region"] == 6:
		thermal_percentages = [[0.2184, 0.3545, 0.2184, 0.3545, 0.0289, 0.2919, 1, 1, 1],  # 1
							   [0.0818, 0.6454, 0.0818, 0.6454, 0.6057, 0.5169, 0, 0, 0],  # 2
							   [0.2390, 0.0000, 0.2390, 0.0000, 0.3652, 0.1911, 0, 0, 0],  # 3
							   [0.2049, 0.0000, 0.2049, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 4
							   [0.2556, 0.0000, 0.2556, 0.0000, 0.0000, 0.0000, 0, 0, 0],  # 5
							   [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0, 0, 0]]  # 6
		data["floor_area"] = [2655] * 9
		data["one_story"] = [0.7043] * 9
		data["window_wall_ratio"] = 0.15
		perc_gas = [0.4425] * 9
		perc_pump = [0.1983] * 9
		perc_AC = [0.9673] * 9
		wh_electric = [0.3572] * 9
		wh_size = [[0.2259, 0.5267, 0.2475]] * 9
		AC_type = [[1, 1, 1, 1, 1, 1, 0, 0, 0],  # central
				   [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		over_sizing_factor = [[0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0, 0, 0],  # central
							  [0, 0, 0, 0, 0, 0, 0, 0, 0]]  # window/wall unit
		perc_pool_pumps = [0.0657] * 9
	else:
		raise Exception('region "{:s}" is not defined'.format(data["region"]))

	# Single-Family Homes
	# - Designate the percentage of SFH in each classification
	SFH = [[1, 1, 1, 1, 0, 0, 0, 0, 0],  # Res1-Res4 are 100% SFH.
		   [1, 1, 1, 1, 0, 0, 0, 0, 0],
		   [1, 1, 1, 1, 0, 0, 0, 0, 0],
		   [1, 1, 1, 1, 0, 0, 0, 0, 0],
		   [1, 1, 1, 1, 0, 0, 0, 0, 0],
		   [1, 1, 1, 1, 0, 0, 0, 0, 0]]

	# Commercial Buildings
	# - Designate what type of commercial building each classification represents.
	com_buildings = [[0, 0, 0, 0, 0, 0, 0, 0, 1],  # office buildings
					 [0, 0, 0, 0, 0, 0, 0, 1, 0],  # big box
					 [0, 0, 0, 0, 0, 0, 1, 0, 0]]  # strip mall

	# COP High/Low Values
	# - "columns" represent load classifications. The "rows" represent the sub-classifications (See thermal_percentages).
	cop_high = [[2.8, 3.8, 2.8, 3.8, 0.0, 2.8, 0, 0, 0],
				[3.0, 4.0, 3.0, 4.0, 2.8, 3.0, 0, 0, 0],
				[3.2, 0.0, 3.2, 0.0, 3.5, 3.2, 0, 0, 0],
				[3.4, 0.0, 3.4, 0.0, 0.0, 0.0, 0, 0, 0],
				[3.6, 0.0, 3.6, 0.0, 0.0, 0.0, 0, 0, 0],
				[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0]]

	cop_low = [[2.4, 3.0, 2.4, 3.0, 0.0, 1.9, 0, 0, 0],
			   [2.5, 3.0, 2.5, 3.0, 1.9, 2.0, 0, 0, 0],
			   [2.6, 0.0, 2.6, 0.0, 2.2, 2.1, 0, 0, 0],
			   [2.8, 0.0, 2.8, 0.0, 0.0, 0.0, 0, 0, 0],
			   [3.0, 0.0, 3.0, 0.0, 0.0, 0.0, 0, 0, 0],
			   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0]]

	# Thermal Properties
	# - There should be a list of properties for each entry in thermal_percentages. (Each sub-classification in each classification)
	# - thermal_properties[i][j] = [ R-ceil,R-wall,R-floor,window layers,window glass, glazing treatment, window frame, R-door, Air infiltrationS ]
	# - for i = subclassficaiton, j = classification
	thermal_properties = [None] * 6
	for i in range(6):
		thermal_properties[i] = [None] * 9
	# Now we have a list of 6 lists of "None"

	# For each non-zero entry for a classification ("column") in thermal_percentages, fill in thermal properties.
	# Res 1 (sfh pre-1980, <2000sf)
	thermal_properties[0][0] = [16, 10, 10, 1, 1, 1, 1, 3, 0.75]  # <1940
	thermal_properties[1][0] = [19, 11, 12, 2, 1, 1, 1, 3, 0.75]  # 1940-49
	thermal_properties[2][0] = [19, 14, 16, 2, 1, 1, 1, 3, 0.50]  # 1950-59
	thermal_properties[3][0] = [30, 17, 19, 2, 1, 1, 2, 3, 0.50]  # 1960-69
	thermal_properties[4][0] = [34, 19, 20, 2, 1, 1, 2, 3, 0.50]  # 1970-79
	thermal_properties[5][0] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a

	# Res2 (sfh post-1980, <2000sf)
	thermal_properties[0][1] = [36, 22, 22, 2, 2, 1, 2, 5, 0.25]  # 1980-89
	thermal_properties[1][1] = [48, 28, 30, 3, 2, 2, 4, 11, 0.25]  # >1990
	thermal_properties[2][1] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[3][1] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[4][1] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[5][1] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a

	# Res3 (sfh pre-1980, >2000sf, val's identical to Res1)
	thermal_properties[0][2] = [16, 10, 10, 1, 1, 1, 1, 3, 0.75]  # <1940
	thermal_properties[1][2] = [19, 11, 12, 2, 1, 1, 1, 3, 0.75]  # 1940-49
	thermal_properties[2][2] = [19, 14, 16, 2, 1, 1, 1, 3, 0.50]  # 1950-59
	thermal_properties[3][2] = [30, 17, 19, 2, 1, 1, 2, 3, 0.50]  # 1960-69
	thermal_properties[4][2] = [34, 19, 20, 2, 1, 1, 2, 3, 0.50]  # 1970-79
	thermal_properties[5][2] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a

	# Res4 (sfh post-1980, >2000sf, val's identical to Res2)
	thermal_properties[0][3] = [36, 22, 22, 2, 2, 1, 2, 5, 0.25]  # 1980-89
	thermal_properties[1][3] = [48, 28, 30, 3, 2, 2, 4, 11, 0.25]  # >1990
	thermal_properties[2][3] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[3][3] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[4][3] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[5][3] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a

	# Res5 (mobile homes)
	thermal_properties[0][4] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # <1960
	thermal_properties[1][4] = [13.4, 9.2, 11.7, 1, 1, 1, 1, 2.2, .75]  # 1960-1989
	thermal_properties[2][4] = [24.1, 11.7, 18.1, 2, 2, 1, 2, 3.0, .75]  # >1990
	thermal_properties[3][4] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[4][4] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[5][4] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a

	# Res6 (apartments)
	thermal_properties[0][5] = [13.4, 11.7, 9.4, 1, 1, 1, 1, 2.2, .75]  # <1960
	thermal_properties[1][5] = [20.3, 11.7, 12.7, 2, 1, 2, 2, 2.7, 0.25]  # 1960-1989
	thermal_properties[2][5] = [28.7, 14.3, 12.7, 2, 2, 3, 4, 6.3, 0.125]  # >1990
	thermal_properties[3][5] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[4][5] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[5][5] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a

	# Com3
	thermal_properties[0][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[1][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[2][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[3][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[4][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[5][6] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a

	# Com2
	thermal_properties[0][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[1][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[2][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[3][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[4][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[5][7] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a

	# Com1
	thermal_properties[0][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[1][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[2][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[3][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[4][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a
	thermal_properties[5][8] = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # n/a

	# Floor Area by Classification
	# data["floor_area"] = [1200, 1200, 2400, 2400, 1710, 820, 0, 0, 0]

	# Percentage One Story Homes by Classification
	# data["one_story"] = [0.6295, 0.5357, 0.6295, 0.5357, 1.0000, 0.9073, 0, 0, 0]

	# Cooling Setpoint Bins by Classification
	# [nighttime percentage, high bin value, low bin value]
	cooling_setpoint = [None] * 9

	cooling_setpoint[0] = [[0.098, 69, 65],  # Res1
						   [0.140, 70, 70],
						   [0.166, 73, 71],
						   [0.306, 76, 74],
						   [0.206, 79, 77],
						   [0.084, 85, 80]]

	cooling_setpoint[1] = [[0.098, 69, 65],  # Res2
						   [0.140, 70, 70],
						   [0.166, 73, 71],
						   [0.306, 76, 74],
						   [0.206, 79, 77],
						   [0.084, 85, 80]]

	cooling_setpoint[2] = [[0.098, 69, 65],  # Res3
						   [0.140, 70, 70],
						   [0.166, 73, 71],
						   [0.306, 76, 74],
						   [0.206, 79, 77],
						   [0.084, 85, 80]]

	cooling_setpoint[3] = [[0.098, 69, 65],  # Res4
						   [0.140, 70, 70],
						   [0.166, 73, 71],
						   [0.306, 76, 74],
						   [0.206, 79, 77],
						   [0.084, 85, 80]]

	cooling_setpoint[4] = [[0.138, 69, 65],  # Res5
						   [0.172, 70, 70],
						   [0.172, 73, 71],
						   [0.276, 76, 74],
						   [0.138, 79, 77],
						   [0.103, 85, 80]]

	cooling_setpoint[5] = [[0.155, 69, 65],  # Res6
						   [0.207, 70, 70],
						   [0.103, 73, 71],
						   [0.310, 76, 74],
						   [0.155, 79, 77],
						   [0.069, 85, 80]]

	cooling_setpoint[6] = [[0.098, 69, 65],  # Com1
						   [0.140, 70, 70],
						   [0.166, 73, 71],
						   [0.306, 76, 74],
						   [0.206, 79, 77],
						   [0.084, 85, 80]]

	cooling_setpoint[7] = [[0.098, 69, 65],  # Com2
						   [0.140, 70, 70],
						   [0.166, 73, 71],
						   [0.306, 76, 74],
						   [0.206, 79, 77],
						   [0.084, 85, 80]]

	cooling_setpoint[8] = [[0.098, 69, 65],  # Com3
						   [0.140, 70, 70],
						   [0.166, 73, 71],
						   [0.306, 76, 74],
						   [0.206, 79, 77],
						   [0.084, 85, 80]]

	# Heating Setpoint Bins by Classification
	heating_setpoint = [None] * 9

	heating_setpoint[0] = [[0.141, 63, 59],  # Res1
						   [0.204, 66, 64],
						   [0.231, 69, 67],
						   [0.163, 70, 70],
						   [0.120, 73, 71],
						   [0.141, 79, 74]]

	heating_setpoint[1] = [[0.141, 63, 59],  # Res2
						   [0.204, 66, 64],
						   [0.231, 69, 67],
						   [0.163, 70, 70],
						   [0.120, 73, 71],
						   [0.141, 79, 74]]

	heating_setpoint[2] = [[0.141, 63, 59],  # Res3
						   [0.204, 66, 64],
						   [0.231, 69, 67],
						   [0.163, 70, 70],
						   [0.120, 73, 71],
						   [0.141, 79, 74]]

	heating_setpoint[3] = [[0.141, 63, 59],  # Res4
						   [0.204, 66, 64],
						   [0.231, 69, 67],
						   [0.163, 70, 70],
						   [0.120, 73, 71],
						   [0.141, 79, 74]]

	heating_setpoint[4] = [[0.129, 63, 59],  # Res5
						   [0.177, 66, 64],
						   [0.161, 69, 67],
						   [0.274, 70, 70],
						   [0.081, 73, 71],
						   [0.177, 79, 74]]

	heating_setpoint[5] = [[0.085, 63, 59],  # Res6
						   [0.132, 66, 64],
						   [0.147, 69, 67],
						   [0.279, 70, 70],
						   [0.109, 73, 71],
						   [0.248, 79, 74]]

	heating_setpoint[6] = [[0.141, 63, 59],  # Com1
						   [0.204, 66, 64],
						   [0.231, 69, 67],
						   [0.163, 70, 70],
						   [0.120, 73, 71],
						   [0.141, 79, 74]]

	heating_setpoint[7] = [[0.141, 63, 59],  # Com2
						   [0.204, 66, 64],
						   [0.231, 69, 67],
						   [0.163, 70, 70],
						   [0.120, 73, 71],
						   [0.141, 79, 74]]

	heating_setpoint[8] = [[0.141, 63, 59],  # Com3
						   [0.204, 66, 64],
						   [0.231, 69, 67],
						   [0.163, 70, 70],
						   [0.120, 73, 71],
						   [0.141, 79, 74]]

	# Heating
	# - Percentage breakdown of heating system type by classification.
	# perc_gas     = [0.52, 0.36, 0.52, 0.36, 0.16, 0.33, 0, 0, 0]

	# perc_pump    = [0.37, 0.57, 0.37, 0.57, 0.34, 0.53, 0, 0, 0]

	perc_res = list(map(lambda xx, yy: 1 - xx - yy, perc_pump, perc_gas))

	# Cooling
	# - Percentage AC
	# - Breakdown AC unit types([central AC; window/wall units])
	# - Oversizing factor of AC units by load classification and unit type (central/window wall)
	# perc_AC = [0.94, 1.00, 0.94, 1.00, 0.94, 0.93, 0, 0, 0]

	# AC_type = [[0.90, 1.00, 0.90, 1.00, 0.88, 0.87, 0, 0, 0],
	# [0.10, 0.00, 0.10, 0.00, 0.12, 0.13, 0, 0, 0]]

	# over_sizing_factor = [[ 0, 0, 0, 0, 0, 0, 0, 0, 0],
	# [ 0, 0, 0, 0, 0, 0, 0, 0, 0]]

	# Percent Pool Pumps by Classification
	# perc_pool_pumps = [0, 0, 0, 0, 0, 0, 0, 0, 0]

	# Waterheater
	# - Percentage electric water heaters by classificaition
	# - Waterheater sizing breakdown  [<30, 31-49, >50] by classification
	# wh_electric = [0.67, 0.49, 0.67, 0.49, 0.73, 0.96, 0, 0, 0]

	# wh_size = [[0.2259,0.5267, 0.2475],  #Res1
	# [0.2259, 0.5267, 0.2475], #Res2
	# [0.2259, 0.5267, 0.2475], #Res3
	# [0.2259, 0.5267, 0.2475], #Res4
	# [0.2259, 0.5267, 0.2475], #Res5
	# [0.2259, 0.5267, 0.2475], #Res6
	# [0, 0, 0],                #Com1
	# [0, 0, 0],                #Com2
	# [0, 0, 0]]                #Com3

	# map some variable because I am lazy...
	allsame_h = data["heating_offset"]
	allsame_c = data["cooling_offset"]
	COP_high = data["COP_high_scalar"]
	COP_low = data["COP_low_scalar"]

	# Apply calibration scalars
	for x in cooling_setpoint:
		if x is None:
			pass
		else:
			for j in range(len(x)):
				x[j].insert(1, allsame_c)

	for x in heating_setpoint:
		if x is None:
			pass
		else:
			for j in range(len(x)):
				x[j].insert(1, allsame_h)

	cop_high_new = []

	for x in cop_high:
		cop_high_new.append([round(COP_high * y, 2) for y in x])

	cop_low_new = []

	for x in cop_low:
		cop_low_new.append([round(COP_low * y, 2) for y in x])

	for i in range(len(thermal_properties)):
		if thermal_properties[i] is None:
			pass
		else:
			for j in range(len(thermal_properties[i])):
				if thermal_properties[i][j] is None:
					pass
				else:
					thermal_properties[i][j].extend([cop_high_new[i][j], cop_low_new[i][j]])

	data["thermal_percentages"] = [None] * len(thermal_percentages)
	for x in range(len(thermal_percentages)):
		data["thermal_percentages"][x] = thermal_percentages[x][classification]

	data["thermal_properties"] = [None] * len(thermal_properties)
	for x in range(len(thermal_properties)):
		data["thermal_properties"][x] = thermal_properties[x][classification]

	data["cooling_setpoint"] = cooling_setpoint[classification]
	data["heating_setpoint"] = heating_setpoint[classification]
	if 'perc_gas' not in data:
		data["perc_gas"] = perc_gas[classification]
	if 'perc_pump' not in data:
		data["perc_pump"] = perc_pump[classification]
	if 'perc_res' not in data:
		data["perc_res"] = perc_res[classification]
	if 'perc_AC' not in data:
		data["perc_AC"] = perc_AC[classification]
	if 'perc_poolpumps' not in data:
		data["perc_poolpumps"] = perc_pool_pumps[classification]
	if 'wh_electric' not in data:
		data["wh_electric"] = wh_electric[classification]
	if 'wh_size' not in data:
		data["wh_size"] = wh_size[classification]

	data["over_sizing_factor"] = [None] * len(over_sizing_factor)
	for x in range(len(over_sizing_factor)):
		data["over_sizing_factor"][x] = over_sizing_factor[x][classification]

	data["AC_type"] = [None] * len(AC_type)
	for x in range(len(AC_type)):
		data["AC_type"][x] = AC_type[x][classification]

	data["SFH"] = [None] * len(SFH)
	for x in range(len(SFH)):
		data["SFH"][x] = SFH[x][classification]

	data["com_buildings"] = com_buildings
	data["no_cool_sch"] = 8
	data["no_heat_sch"] = 6
	data["no_water_sch"] = 6
	return data

if __name__ == '__main__':
	pass
