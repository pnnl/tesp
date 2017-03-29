# Copyright (C) 2017 Battelle Memorial Institute
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan  9 09:48:08 2017

@author: Trevor Hardy

Reads in a GLD .glm file and applies growth specified in provided text file.

"""
import feeder  # PNNL's .glm parser written by Andy Fischer
import feederConfiguration_TSP as fc  # Jacob H.'s Python Feeder_Generator.m
import logging
import pprint
import matplotlib.pyplot as plt
import random
import re
import copy

# Setting up logging
logger = logging.getLogger(__name__)

# Setting up pretty printing, mostly for debugging.
pp = pprint.PrettyPrinter(indent=4)


def find_parent_xfmr(input_glm_dict, starting_key):
    '''Crawls .glm to identify a given object's parent transformer.'''
    # Searching for distribution transformer
    logger.debug("Beginning parent transformer search for {}.".format(
                 input_glm_dict[starting_key]['name']))
    key2 = starting_key
    parent = input_glm_dict[starting_key]['parent']
    while input_glm_dict[key2]['object'] != 'transformer':
        logger.debug('Searching for parent named {}.'.format(parent))
        for key2 in input_glm_dict:
            if 'parent' in input_glm_dict[key2]:
                if input_glm_dict[key2]['object'] == 'triplex_node':
                    # Is a triplex node with a parent, signature for expansion
                    # node based on taxonomy feeder architecture.
                    expansion_node = input_glm_dict[key2]['name']
                if 'name' in input_glm_dict[key2]:
                    if input_glm_dict[key2]['name'] == parent:
                            parent = input_glm_dict[key2]['parent']
                            break
            elif 'to' in input_glm_dict[key2]:
                if input_glm_dict[key2]['to'] == parent:
                        parent = input_glm_dict[key2]['from']
                        break
    logger.info("Parent transformer for {} found: {}.".format(
                 input_glm_dict[starting_key]['name'],
                 input_glm_dict[key2]['name']))
    return key2, expansion_node


def gather_house_stats(input_glm_dict):
    '''Crawls .glm gathering data on houses and their parent transformers.'''
    logger.info("Beginning data collection from parsed .glm model.")
    house_stats = []
    xfmr_configs = []
    for key in input_glm_dict:
        if 'object' in input_glm_dict[key]:
            # Saving transformer configurations ratings for later use
            if input_glm_dict[key]['object'] == 'transformer_configuration':
                logger.debug("Capturing {}, key {}.".format(
                             input_glm_dict[key]['name'], key))
                xfmr_configs.append({})
                xfmr_configs[-1]['name'] = input_glm_dict[key]['name']
                if 'power_rating' in input_glm_dict[key]:
                    logger.debug("Found power_rating of {}".format(
                                 input_glm_dict[key]['power_rating']))
                    xfmr_configs[-1]['power_rating'] =\
                        input_glm_dict[key]['power_rating']
                elif 'powerA_rating' in input_glm_dict[key]:
                    logger.debug("Found powerA_rating of {}".format(
                                 input_glm_dict[key]['powerA_rating']))
                    xfmr_configs[-1]['power_rating'] =\
                        input_glm_dict[key]['powerA_rating']
                elif 'powerB_rating' in input_glm_dict[key]:
                    logger.debug("Found powerB_rating of {}".format(
                                 input_glm_dict[key]['powerB_rating']))
                    xfmr_configs[-1]['power_rating'] =\
                        input_glm_dict[key]['powerB_rating']
                elif 'powerC_rating' in input_glm_dict[key]:
                    logger.debug("Found powerC_rating of {}".format(
                                 input_glm_dict[key]['powerC_rating']))
                    xfmr_configs[-1]['power_rating'] =\
                        input_glm_dict[key]['powerC_rating']
            # Grabbing all the house info we'll need
            if (input_glm_dict[key]['object'] == 'house') and\
                    (input_glm_dict[key]['groupid'] == 'Residential'):
                house_stats.append({})
                house_stats[-1]['name'] = input_glm_dict[key]['name']
                house_stats[-1]['floor_area'] =\
                    input_glm_dict[key]['floor_area']
                # Pulling in parent transformer information
                parent_xfmr_key, expansion_node =\
                    find_parent_xfmr(input_glm_dict, key)
                house_stats[-1]['dist_xfmr_name'] =\
                    input_glm_dict[parent_xfmr_key]['name']
                house_stats[-1]['expansion_node'] = expansion_node
                house_stats[-1]['groupid'] = input_glm_dict[key]['groupid']
                house_stats[-1]['phases'] =\
                    input_glm_dict[parent_xfmr_key]['phases']
                for key2, item in enumerate(xfmr_configs):
                    if xfmr_configs[key2]['name'] ==\
                            input_glm_dict[parent_xfmr_key]['configuration']:
                        logger.debug("{} has configuration {}.".format(
                                     house_stats[-1]['dist_xfmr_name'],
                                     input_glm_dict[parent_xfmr_key]
                                     ['configuration']))
                        house_stats[-1]['dist_xfmr_rating'] =\
                            xfmr_configs[key2]['power_rating']
                        break
    logger.debug("house_stats list:")
    logger.debug(pp.pformat(house_stats))
    logger.info("Done collecting data from parsed .glm model.")
    return house_stats


def summarize_xfmr_stats(house_stats):
    '''
    Creates summarized data dictionary of transformer data from dictionary
    of collected data from .glm.
    '''
    logger.info("Beginning summarization of data on transformers in model.")
    xfmr_summary = {}
    for key, item in enumerate(house_stats):
        logger.debug("Processing data from house {} on transformer {}".format(
                     house_stats[key]['name'],
                     house_stats[key]['dist_xfmr_name']))
        dist_xfmr_name = house_stats[key]['dist_xfmr_name']
        if house_stats[key]['dist_xfmr_name'] in xfmr_summary:
            logger.debug("{} already in summary.".format(
                         house_stats[key]['dist_xfmr_name']))
            xfmr_summary[dist_xfmr_name]['house_count'] += 1
            xfmr_summary[dist_xfmr_name]['total_sf'] +=\
                float(house_stats[key]['floor_area'])
            xfmr_summary[dist_xfmr_name]['rating_per_house'] =\
                xfmr_summary[dist_xfmr_name]['power_rating'] /\
                xfmr_summary[dist_xfmr_name]['house_count']
            xfmr_summary[dist_xfmr_name]['rating_per_sf'] =\
                xfmr_summary[dist_xfmr_name]['power_rating'] /\
                xfmr_summary[dist_xfmr_name]['total_sf']
        else:
            logger.debug("Adding {} to summary.".format(dist_xfmr_name))
            xfmr_summary[dist_xfmr_name] = {}
            xfmr_summary[dist_xfmr_name]['house_count'] = 1
            xfmr_summary[dist_xfmr_name]['power_rating'] =\
                float(house_stats[key]['dist_xfmr_rating']
                      .replace('kVA', '')) * 1000
            xfmr_summary[dist_xfmr_name]['total_sf'] =\
                float(house_stats[key]['floor_area'])
            xfmr_summary[dist_xfmr_name]['rating_per_house'] =\
                xfmr_summary[dist_xfmr_name]['power_rating']
            xfmr_summary[dist_xfmr_name]['rating_per_sf'] =\
                xfmr_summary[dist_xfmr_name]['power_rating'] /\
                xfmr_summary[dist_xfmr_name]['total_sf']
    logger.debug(pp.pformat(xfmr_summary))
    logger.info("Completed summarization of transformer data.")
    return xfmr_summary


def make_list(xfmr_summary, key_string):
    '''Extracts pre-defined data gathered from .glm for ease of processing. '''
    value_list = []
    for key in xfmr_summary:
        value_list.append(xfmr_summary[key][key_string])
    logger.info("Created list for {}.".format(key_string))
    logger.debug(pp.pformat(value_list))
    return value_list


def make_histograms(xfmr_summary):
    '''Creates histograms of pre-defined data gathered from .glm'''
    logger.info("Making histograms.")
    rating_per_house = make_list(xfmr_summary, 'rating_per_house')
    plt.hist(rating_per_house, bins='auto')
    plt.title("Distrubtion transformer rating per number of attached houses")
    plt.xlabel("Transformer rating per attached house, W/house")
    plt.ylabel("Count")
    plt.show()
    rating_per_sf = make_list(xfmr_summary, 'rating_per_sf')
    plt.hist(rating_per_sf, bins='auto')
    plt.xlabel("Transformer rating per square footage of attached houses,"
               " W/sf")
    plt.ylabel("Count")
    plt.show()


def update_brownfield_loads(mod_glm_dict, growth_rate):
    '''Grows existing loads in model at ramdom rates specified by average'''
    logger.info('Starting growth of brownfield loads...')
    for key in mod_glm_dict:
        if 'object' in mod_glm_dict[key]:
            if mod_glm_dict[key]['object'] == 'ZIPload':
                logger.debug('Found ZIPload {}.'.format(
                             mod_glm_dict[key]['name']))
                mod_str = grow_ZIPload(mod_glm_dict[key]['base_power'],
                                       growth_rate)
                mod_glm_dict[key]['base_power'] = mod_str
            if mod_glm_dict[key]['object'] == 'waterheater':
                # Only add increased water demand in some of the houses
                if random.random() < 0.25:
                    logger.debug('Demand on water heater {} selected for '
                                 'increase'.format(
                                      mod_glm_dict[key]['name']))
                    mod_str = grow_water_heater(mod_glm_dict[key]['demand'],
                                                growth_rate*4)
                    mod_glm_dict[key]['demand'] = mod_str
                else:
                    logger.debug('Demand on water heater {} not selected for '
                                 'increase'.format(
                                      mod_glm_dict[key]['name']))


def grow_ZIPload(power_str, growth_rate):
    '''Grows ZIPload by random value from a Guassian distribution'''
    mu = 1 + growth_rate
    sigma = growth_rate/2
    pattern = re.compile('[\d.]+')
    match = pattern.search(power_str)
    power_factor = float(match.group())
    random_val = random.gauss(mu, sigma)
    power_factor_new = power_factor * (random_val)
    new_power_str = pattern.sub(str(power_factor_new), power_str)
    logger.debug('Load factor {} became {}'.format(
                 power_factor, power_factor_new))
    return new_power_str


def grow_water_heater(demand_str, growth_rate):
    '''Grows water heater load  by random value from a Gaussian distribution'''
    mu = 1 + growth_rate
    sigma = growth_rate/8
    pattern = re.compile('[\d.]{3,}')
    match = pattern.search(demand_str)
    demand_factor = float(match.group())
    random_val = random.gauss(mu, sigma)
    demand_factor_new = demand_factor * (random_val)
    new_demand_str = pattern.sub(str(demand_factor_new), demand_str)
    logger.debug('Water heater demand factor {} became {}'.format(
                 demand_factor, demand_factor_new))
    return new_demand_str


def add_greenfield_loads(mod_glm_dict, house_stats, growth_rate):
    '''
    Generates an appropriate number of new house models and supporting
    infrastructure (triplex lines, meters) to grow the feeder load by the
    provided factor
    '''
    logger.info("Adding houses as greenfield loads to feeder.")
    house_count = len(house_stats)
    num_new_houses = int(house_count * growth_rate)
    logger.info('{} new houses being added'.format(num_new_houses))
    if num_new_houses >= 1:
        for idx in range(1, num_new_houses):
            rand_location = int(random.uniform(1, house_count))
            new_house_exp_node = house_stats[rand_location]['expansion_node']
            logger.info('Adding new house off of node {} ({} of {})'.format(
                         new_house_exp_node, idx, num_new_houses))
            mod_glm_dict, house_stats = add_new_house_infrastructure(
                                                        house_stats,
                                                        rand_location,
                                                        new_house_exp_node,
                                                        mod_glm_dict)
    logger.debug('Fully modified house_stats:')
    logger.debug(pp.pformat(house_stats))
    return mod_glm_dict, house_stats


def add_new_house_infrastructure(house_stats, new_house_stats_key,
                                 new_house_exp_node, mod_glm_dict):
    '''
    Adds in all the power flow infrastructure from the expansion node,
    adds the house proper and all the supporting loads (ZIPloads, water
    heaters, etc...)
    '''
    # Getting parts of new house name
    new_house_name_parts = {}
    pattern = re.compile('[a-zA-Z0-9-]*')
    match = pattern.search(new_house_exp_node)
    root_name = match.group()
    new_house_name_parts['root'] = root_name
    pattern = re.compile('_tm_[0-9]+')
    match = pattern.search(house_stats[new_house_stats_key]['name'])
    suffix = match.group()
    new_house_name_parts['suffix'] = suffix
    pattern = re.compile('[0-9]')
    match = pattern.search(new_house_name_parts['root'])
    region = match.group()
    new_house_name_parts['region'] = region

    # Defining next house at expansion node based on the existing feeder model
    house_count_at_exp_node = 0
    logger.debug('Number of found houses: {}'.format(house_count_at_exp_node))
    for key, value in enumerate(house_stats):
        if house_stats[key]['expansion_node'] == new_house_exp_node:
            house_count_at_exp_node += 1
            logger.debug('Found house at expansion node: {}'.format(
                         house_stats[key]['name']))
            logger.debug('Number of found houses: {}'.format(
                         house_count_at_exp_node))
    new_house_name_parts['number'] = str(house_count_at_exp_node + 1)
    full_name = 'house{}_{}{}'.format(new_house_name_parts['number'],
                                      new_house_name_parts['root'],
                                      new_house_name_parts['suffix'])
    new_house_name_parts['full_name'] = full_name
    logger.info('New house name {}'.format(new_house_name_parts['full_name']))

    # Adding new house to house_stats list
    house_stats.append({})
    house_stats[-1]['dist_xfmr_name'] =\
        house_stats[new_house_stats_key]['dist_xfmr_name']
    house_stats[-1]['dist_xfmr_rating'] =\
        house_stats[new_house_stats_key]['dist_xfmr_rating']
    house_stats[-1]['expansion_node'] = new_house_exp_node
    house_stats[-1]['groupid'] = 'Residential'
    house_stats[-1]['name'] = new_house_name_parts['full_name']
    house_stats[-1]['phases'] = house_stats[new_house_stats_key]['phases']

    # Defining fixed residential ZIPload parameters
    ZIPload_params = {}
    ZIPload_params['heat_fraction'] = 0.9
    ZIPload_params['p_pf'] = 1
    ZIPload_params['i_pf'] = 1
    ZIPload_params['z_pf'] = 1
    ZIPload_params['z_fraction'] = 0.2
    ZIPload_params['i_fraction'] = 0.4
    ZIPload_params['p_fraction'] = 1 - ZIPload_params['z_fraction'] -\
        ZIPload_params['i_fraction']

    # Adding new infrastructure
    mod_glm_dict = add_triplex_line(mod_glm_dict, new_house_exp_node,
                                    house_stats, new_house_name_parts,
                                    new_house_stats_key)
    mod_glm_dict = add_triplex_meter(mod_glm_dict, new_house_name_parts, 1)
    mod_glm_dict = add_triplex_meter(mod_glm_dict, new_house_name_parts, 2)
    mod_glm_dict, new_house_params =\
        add_house(mod_glm_dict, new_house_name_parts)
    house_stats[-1]['floor_area'] =\
        mod_glm_dict[len(mod_glm_dict)]['floor_area']
    logger.debug("Values for new house added to house_stats:")
    logger.debug(pp.pformat(house_stats[-1]))
    parent_house_key = len(mod_glm_dict)
    mod_glm_dict = add_ZIPLoad(mod_glm_dict, new_house_name_parts,
                               parent_house_key, 'responsive', ZIPload_params,
                               new_house_params)
    mod_glm_dict = add_ZIPLoad(mod_glm_dict, new_house_name_parts,
                               parent_house_key, 'unresponsive',
                               ZIPload_params, new_house_params)
    if random.random() <= new_house_params['perc_poolpumps']:
        mod_glm_dict = add_pool_pump(mod_glm_dict, new_house_name_parts,
                                     parent_house_key, ZIPload_params)
    if random.random() <= new_house_params['wh_electric']:
        mod_glm_dict = add_water_heater(mod_glm_dict, new_house_name_parts,
                                        parent_house_key, new_house_params)
    return mod_glm_dict, house_stats


def add_triplex_line(mod_glm_dict, new_house_exp_node, house_stats,
                     new_house_name_parts, new_house_stats_key):
    '''Adds a triplex line following the customary format for houses.'''
    key = len(mod_glm_dict)+1
    mod_glm_dict[key] = {}
    mod_glm_dict[key]['object'] = 'triplex_line'
    mod_glm_dict[key]['groupid'] = 'Triplex_Line'
    mod_glm_dict[key]['phases'] = house_stats[new_house_stats_key]['phases']
    mod_glm_dict[key]['from'] = new_house_exp_node
    mod_glm_dict[key]['to'] = 'tpm' + new_house_name_parts['number'] + '_' +\
        new_house_name_parts['root'] + new_house_name_parts['suffix']  
    mod_glm_dict[key]['length'] = '10'
    mod_glm_dict[key]['configuration'] = 'triplex_line_configuration_1'
    logger.info("Added new triplex line from {} to {}.".format(
                 mod_glm_dict[key]['from'], mod_glm_dict[key]['to']))
    return mod_glm_dict


def add_triplex_meter(mod_glm_dict, new_house_name_parts, meter_num):
    '''Adds the triplex meters following the customary form.'''
    # Finding parallel house meters to steal paramter values from
    parallel_meter_num = int(new_house_name_parts['number']) - 1
    if meter_num == 1:
        parallel_meter_name = 'tpm' + str(parallel_meter_num) + '_' +\
            new_house_name_parts['root'] + new_house_name_parts['suffix']
    else:
        parallel_meter_name = 'house_meter' + str(parallel_meter_num) + '_' +\
            new_house_name_parts['root'] + new_house_name_parts['suffix']
    for key2 in mod_glm_dict:
        if 'name' in mod_glm_dict[key2]:
            if mod_glm_dict[key2]['name'] == parallel_meter_name:
                parallel_meter_key = key2
                break
    try:
        parallel_meter_key
    except NameError as error:
        logger.debug("Could not find {} meter to copy.".format(
                     parallel_meter_name))
    key = len(mod_glm_dict)+1
    mod_glm_dict[key] = copy.deepcopy(mod_glm_dict[parallel_meter_key])
    logger.debug("Copying from triplex node {} (key {}).".format(
                 mod_glm_dict[parallel_meter_key]['name'], parallel_meter_key))
    pattern = re.compile('tm_[0-9]{1,3}')
    match = pattern.search(mod_glm_dict[parallel_meter_key]['name'])
    meter_suffix = match.group()
    if meter_num == 1:
        mod_glm_dict[key]['name'] = 'tpm' + new_house_name_parts['number'] +\
            '_' + new_house_name_parts['root'] + '_' + meter_suffix
    else:
        mod_glm_dict[key]['name'] = 'house_meter' +\
            new_house_name_parts['number'] + '_' +\
            new_house_name_parts['root'] + '_' + meter_suffix
        mod_glm_dict[key]['parent'] = 'tpm' + new_house_name_parts['number'] +\
            '_' + new_house_name_parts['root'] + '_' + meter_suffix
    logger.info("Added new triplex node {}.".format(mod_glm_dict[key]['name']))
    return mod_glm_dict


def add_house(mod_glm_dict, new_house_name_parts):
    '''
    Generates the new house model parameters and calls the function that
    actually fully defines those parameters for the model.
    '''

#==============================================================================
#     # Finding house to copy and doing so
#     parallel_house_num = int(new_house_name_parts['number']) - 1
#     parallel_house_name = 'house' + str(parallel_house_num) + '_' +\
#         new_house_name_parts['root'] + '_tm_' + str(parallel_house_num)
#     for key2 in mod_glm_dict:
#         if 'name' in mod_glm_dict[key2]:
#             if mod_glm_dict[key2]['name'] == parallel_house_name:
#                 parallel_house_key = key2
#                 break
#     key = len(mod_glm_dict)+1
#     mod_glm_dict[key] = mod_glm_dict[parallel_house_key]
#     logger.debug("Copying house %s.", mod_glm_dict[parallel_house_key]['name'])
#==============================================================================
    key = len(mod_glm_dict) + 1
    mod_glm_dict[key] = {}

    new_params = generate_new_params(new_house_name_parts['region'])

    # Defining the easy (admin) part of the new house parameters
    mod_glm_dict[key]['object'] = 'house'
    mod_glm_dict[key]['name'] = new_house_name_parts['full_name']
    mod_glm_dict[key]['parent'] = mod_glm_dict[key - 1]['name']
    mod_glm_dict[key]['groupid'] = 'Residential'

    mod_glm_dict = generate_new_house(mod_glm_dict, key, new_params)

    return mod_glm_dict, new_params


def generate_new_params(region):
    '''Generates house model parameters as MATLAB Feeder_Generator.m does'''
    reg_data = {}
    # Setting a few parameters by hand
    reg_data['residential_skew_max'] = 8100
    reg_data['residential_skew_std'] = 2700
    reg_data['heating_offset'] = 1
    reg_data['cooling_offset'] = 1
    reg_data['COP_high_scalar'] = 1
    reg_data['COP_low_scalar'] = 1
    reg_data['region'] = int(region)
    # Based on comments in feederConfiguration.py (l.212 ff), a new house on
    # the feeder would only fall into classifications = 2, 4, 5, and 6
    classification_num = 1
    classification_num_list = [2, 4, 5, 6]
    while classification_num not in classification_num_list:
        classification_num = int(random.uniform(2, 7))
    logger.debug("Randomly chosen clasification number: {}.".format(
                 classification_num))
    classification_idx = classification_num - 1
    reg_data = fc.feederConfiguration(reg_data, classification_idx)
    # logger.debug("Regional house data parameters....")
    # logger.debug(pp.pformat(reg_data))

    # ************************************************************************
    # The format of the regional data is non-obvious. Working from the original
    # Feeder_generator.m, feederConfiguration.py, regionalization.m, and
    # TechnologyParameters.m to figure this out...
    #
    # The source data has been classified by several fastors:
    #   region (1-6)
    #   type of building (single-family home, apartment, commercial, ...)
    #   age of building
    #
    # Unfortunately, it appears that the only independent axis is region. The
    # rest have been all muddled together. I have no idea why.
    #
    # The main classifications work as follows
    #   0 - Residential 1 - single-family homes, pre-1980, < 2000 sq. ft.
    #       0 - pre-1940
    #       1 - 1940-1949
    #       2 - 1950-1959
    #       3 - 1960-1969
    #       4 - 1970-1979
    #   1 - Residential 2 - single-family homes, post-1980, < 2000 sq. ft.
    #       0 - 1980-1989
    #       1 - post-1989
    #   2 - Residential 3 - single-family homes, pre 1980, > 2000 sq. ft.
    #       0 - pre-1940
    #       1 - 1940-1949
    #       2 - 1950-1959
    #       3 - 1960-1969
    #       4 - 1970-1979
    #   3 - Residential 4 - single-family homes, pre 1980, > 2000 sq. ft.
    #       0 - 1980-1989
    #       1 - post-1990
    #   4 - Residential 5 - mobile homes, < 2000 sq. ft.
    #       0 - pre-1960
    #       1 - 1960-1989
    #       2 - post-1989
    #   5 - Residential 6 - apartments, pre 1980, < 2000 sq. ft.
    #       0 - pre-1960
    #       1 - 1960-1989
    #       2 - post-1989
    #   6 - Commercial 3
    #   7 - Commercial 2
    #   8 - Commercial 1
    #
    # Given that the temporal resolution is variable between groups, (and that
    # this was original written in MATLAB), a vector/matrix with that fits the
    # maximum size of the data was used, filling in with zeros all unused
    # entries. For reasons that are not clear, this vector/matrix has SIX, not
    # five spaces for the sub-catergories. This can be confusing since there
    # are also six regions.
    #
    # AC_type - [central boolean, window unit boolean]
    # COP_high_scaler -
    # COP_low_scaler -
    # SFH (single family home) - percentage of single family homes for each
    #       sub-category
    # com_buildings - Designates the type of commercial buildings in a
    #       9-category long vector. The first six entries will always be zero
    #       since they correspond to residential structures
    #       [Res. 1-5, strip mall, big box, office building]
    # cooling_offset - ASSUMED nighttime cooling offset value
    # cooling_setpoint - [nighttime %, nighttime offset, high limit, low limit]
    #       Each row of the matrix represents a specific type of resident; only
    #       six for the whole US. The values in the first column are the %
    #       of that type of resident in the entire population.
    #       The offset value is assumed in this data. The original values in
    #       Feeder_Generator are all slightly less than 1.
    #       Positive values indicate lower setpoint (cooler).
    # floor_area: sq. ft of building in this region for all classifications
    # heating_offset - same as cooling_offset above
    # heating_setpoint - same as cooling_setpoint above
    # load_clasifications - Names of the 9 structure classifications
    # no_cool_sch - number of possible cooling schedules
    # no_heat_sch - number of possible heating schedules
    # no_water_sch - number of possible water schedules
    # one_story - % of buildings that are single-story, one vector element for
    #       each building classification
    # over_sizing_factor - Air-conditioner over-sizing factors
    #       [central AC factor, window unit AC factor]
    # perc_AC - scalar, percentage of buildings that have AC
    # perc_gas -  scalar, percentage of buildings that heat with natural gas
    # perc_poolpumps - scalar, percentage of buildings with pool pumps
    # perc_pump - scalar, percentage of buildings with heat pumps
    # perc_res - scalar, percentage of buildings with resistance heating
    # region - Region number
    # residential_skew_max - maximum schedule skew (seconds)
    # residential_skew_std - standard dev. of schedul skew
    # thermal_percentages - Don't know what these are used for specifically
    #       Values are a vector with each element corresponding to the
    #       sub-category for the selected structure classification. These
    #       sub-categories correspond to the age of the building (see table
    #       above.)
    # thermal_properties - Vector of vearious building thermal properties:
    #       [ R-ceil,           0
    #       R-wall,             1
    #       R-floor,            2
    #       window layers,      3
    #       window glass,       4
    #       glazing treatment,  5
    #       window frame,       6
    #       R-door,             7
    #       Air infiltrationS,  8
    #       cop_high_new        9
    #       cop_low_new]        10
    #
    #       Values are a vector with each element corresponding to the
    #       sub-category for the selected structure classification. These
    #       sub-categories correspond to the age of the building (see table
    #       above.)
    # wh_electric - percentage of houses with electric water heaters
    # wh_size - percentage of water heaters in three size bins for selected
    #       classification
    #       [<30 gal. (?), 30-49 gal., >= 50 gal.]
    # window_wall_ratio - scalar, ratio of windwo to wall area of building
    #
    # ************************************************************************

    # Using the data from the reg_data structure, we'll pick out the actual
    # parameters for the new house.
    # We will assume the new house that we're adding is a residential structure
    # with thermal characteristics of a new building constructed by today's
    # standards.
    house_params = copy.deepcopy(reg_data)
    # Refining data returned from feederConfiguration for this house instance

    # Defining new-building sub-catergory for each building classification
    # Categories 1 and 3 (indices 0 and 2) are for old houses so we don't plan
    # on using those classifications. Additionally, classifications 7-9
    # indices 6-8) are for commercial buildings.
    sub_class = [4, 1, 4, 1, 2, 2, 0, 0, 0]
    sub_class_idx = sub_class[classification_idx]

    # Randomly deciding whether AC is central or window unit
    if random.random() <= house_params['AC_type'][0]:
        house_params['AC_type'] = ['central']
    else:
        house_params['AC_type'] = ['window']

    # Defining if new house will be a single family home
    if random.random() <= house_params['SFH'][0]:
        house_params['SFH'] = [1]
    else:
        house_params['SFH'] = [1]

    # Defining type of commerical building being added.
    if classification_num < 7:
        house_params['com_building'] = ['residential']
    elif classification_num == 7:
        house_params['com_building'] = ['office building']
    elif classification_num == 8:
        house_params['com_building'] = ['big box']
    elif classification_num == 9:
        house_params['com_building'] = ['strip mall']

    # Defining cooling setpoint
    cooling_setpoint_limits = []
    cooling_setpoint_limits.append(reg_data['cooling_setpoint'][0][0])
    for idx in range(1, 6):
        cooling_setpoint_limits.append(cooling_setpoint_limits[idx-1] +
                                       reg_data['cooling_setpoint'][idx][0])
    resident_type = int(random.random())
    # Adding one to help seperate the heating and cooling setpoints.
    house_params['cool_night'] = random.uniform(
                        reg_data['cooling_setpoint'][resident_type][2],
                        reg_data['cooling_setpoint'][resident_type][3]) + 1
    house_params['cool_night_diff'] = random.random() * 2 *\
        reg_data['cooling_setpoint'][resident_type][1]
    house_params['cooling_schedule_num'] = int(random.uniform(1,
                                               reg_data['no_cool_sch'] + 1))

    # Defining heating setpoint
    heating_setpoint_limits = []
    heating_setpoint_limits.append(reg_data['heating_setpoint'][0][0])
    for idx in range(1, 6):
        heating_setpoint_limits.append(heating_setpoint_limits[idx-1] +
                                       reg_data['heating_setpoint'][idx][0])
    resident_type = int(random.random())
    # Adding one to help seperate the heating and cooling setpoints.
    house_params['heat_night'] = random.uniform(
                        reg_data['heating_setpoint'][resident_type][2],
                        reg_data['heating_setpoint'][resident_type][3]) - 1
    house_params['heat_night_diff'] = random.random() * 2 *\
        reg_data['heating_setpoint'][resident_type][1]
    house_params['heating_schedule_num'] = int(random.uniform(1,
                                               reg_data['no_heat_sch'] + 1))

    # Defining floor area
    base_floor_area = reg_data['floor_area'][classification_idx]
    if classification_num <= 4:  # Single family homes
        # Lower classifcation nums are for older houses (1 and 3) and smaller
        #   houses (2). Classification number 4 is for the newest largest house
        #   thus the shrink factor will be
        shrink_factor = (classification_num - 4) / 3
        house_params['floor_area'] = base_floor_area +\
            shrink_factor * (base_floor_area/2) * random.random() *\
            shrink_factor
    else:
        house_params['floor_area'] = base_floor_area +\
            (base_floor_area/2) * (0.5 - random.random())

    # Defining the number of stories of building
    if classification_num <= 4:  # Single family homes
        if random.random() < reg_data['one_story'][classification_idx]:
            house_params['number_of_stories'] = 1
        else:
            house_params['number_of_stories'] = 2
    else:
        house_params['number_of_stories'] = 1

    # Defining ceiling height
    if classification_num <= 4:  # Single family homes
        house_params['ceiling_height'] = 8 + random.choice([1, 2])
    else:
        house_params['ceiling_height'] = 8

    # Defining schedule skew
    house_skew = 128 * reg_data['residential_skew_std'] * random.random()
    if -1 * house_skew < -1 * reg_data['residential_skew_max']:
        house_skew = -1 * reg_data['residential_skew_max']
    elif house_skew > reg_data['residential_skew_max']:
        house_skew = reg_data['residential_skew_max']
    house_params['schedule_skew'] = house_skew

    # Defining over-sizing factor
    if house_params['AC_type'] == 'central':
        over_sizing_factor = reg_data['over_sizing_factor'][0]
    else:
        over_sizing_factor = reg_data['over_sizing_factor'][1]
    house_params['over_sizing_factor'] = over_sizing_factor *\
        (0.8 + 0.4 * random.random())

    # Defining thermal percentages
    house_params['thermal_percentages'] =\
        reg_data['thermal_percentages'][sub_class_idx]

    # Defining thermal properties
    house_params['thermal_properties'] =\
        reg_data['thermal_properties'][sub_class_idx]

    logger.info("Refined and expanded house data parameters.")
    logger.debug(pp.pformat(house_params))
    return house_params


def generate_new_house(mod_glm_dict, key, new_params):
    '''
    Fully defines the house model based on the newly generated regionalized
    parameters. The values added to the dictionary should be the literal
    values that show up in the .glm
    '''
    mod_glm_dict[key]['schedule_skew'] = new_params['schedule_skew']

    # Defining building thermal parameters
    mod_glm_dict[key]['floor_area'] = new_params['floor_area']
    mod_glm_dict[key]['number_of_stories'] = new_params['number_of_stories']
    mod_glm_dict[key]['ceiling_height'] = new_params['ceiling_height']
    mod_glm_dict[key]['over_sizing_factor'] = new_params['over_sizing_factor']
    mod_glm_dict[key]['Rroof'] = new_params['thermal_properties'][0]
    mod_glm_dict[key]['Rwall'] = new_params['thermal_properties'][1]
    mod_glm_dict[key]['Rfloor'] = new_params['thermal_properties'][2]
    mod_glm_dict[key]['glazing_layers'] = new_params['thermal_properties'][3]
    mod_glm_dict[key]['glass_type'] = new_params['thermal_properties'][4]
    mod_glm_dict[key]['glazing_treatment'] =\
        new_params['thermal_properties'][5]
    mod_glm_dict[key]['window_frame'] = new_params['thermal_properties'][6]
    mod_glm_dict[key]['Rdoors'] = new_params['thermal_properties'][7]
    mod_glm_dict[key]['airchange_per_hour'] =\
        new_params['thermal_properties'][8]

    # Defining HVAC parameters
    cooling_COP = random.uniform(new_params['thermal_properties'][10],
                                 new_params['thermal_properties'][9])
    mod_glm_dict[key]['cooling_COP'] = cooling_COP
    inint_temp = 68 + random.uniform(1, 4)
    mod_glm_dict[key]['air_temperature'] = inint_temp
    mod_glm_dict[key]['mass_temperature'] = inint_temp
    mod_glm_dict[key]['total_thermal_mass_per_floor_area'] =\
        2.5 + (1.5 * random.random())
    heating_rand = random.random()
    cooling_rand = random.random()
    if heating_rand <= new_params['perc_gas']:
        mod_glm_dict[key]['heating_system_type'] = 'GAS'
        if cooling_rand <= new_params['perc_AC']:
            mod_glm_dict[key]['cooling_system_type'] = 'ELECTRIC'
        else:
            mod_glm_dict[key]['cooling_system_type'] = 'NONE'
    elif heating_rand <= (new_params['perc_gas'] + new_params['perc_pump']):
        mod_glm_dict[key]['heating_system_type'] = 'HEAT_PUMP'
        mod_glm_dict[key]['heating_COP'] = cooling_COP
        mod_glm_dict[key]['cooling_system_type'] = 'ELECTRIC'
        mod_glm_dict[key]['auxiliary_strategy'] = 'DEADBAND'
        mod_glm_dict[key]['auxiliary_system_type'] = 'ELECTRIC'
        mod_glm_dict[key]['motor_model'] = 'BASIC'
        mod_glm_dict[key]['motor_efficiency'] = 'GOOD'
    elif mod_glm_dict[key]['floor_area'] *\
            mod_glm_dict[key]['ceiling_height'] > 12000:
        mod_glm_dict[key]['heating_system_type'] = 'GAS'
        if cooling_rand <= new_params['perc_AC']:
            mod_glm_dict[key]['cooling_system_type'] = 'ELECTRIC'
            mod_glm_dict[key]['motor_model'] = 'BASIC'
            mod_glm_dict[key]['motor_efficiency'] = 'GOOD'
        else:
            mod_glm_dict[key]['cooling_system_type'] = 'NONE'
    else:
        mod_glm_dict[key]['heating_system_type'] = 'RESISTANCE'
        mod_glm_dict[key]['cooling_system_type'] = 'ELECTRIC'
        mod_glm_dict[key]['motor_model'] = 'BASIC'
        mod_glm_dict[key]['motor_efficiency'] = 'GOOD'
    mod_glm_dict[key]['breaker_amps'] = 1000
    mod_glm_dict[key]['hvac_breaker_rating'] = 1000

    # Defining thermostat setpoints
    mod_glm_dict[key]['cooling_setpoint'] = "cooling{}*{:.2f}+{:.2f}".format(
        new_params['cooling_schedule_num'], new_params['cool_night_diff'],
        new_params['cool_night'])
    mod_glm_dict[key]['heating_setpoint'] = 'heating{}*{:.2f}+{:.2f}'.format(
        new_params['heating_schedule_num'], new_params['heat_night_diff'],
        new_params['heat_night'])

    logger.info("Generated new house model proper for {}.".format(
                mod_glm_dict[key]['name']))
    logger.debug(pp.pformat(mod_glm_dict[key]))
    return mod_glm_dict


def add_ZIPLoad(mod_glm_dict, new_house_name_parts, parent_house_key,
                price_responsivity, ZIPload_params, new_house_params):
    '''
    Adds the price responsive and unresponsive loads as new objects to the
    feeder model (doesn't embed them in the house object).
    '''
    key = len(mod_glm_dict) + 1
    mod_glm_dict[key] = {}

    # Setting up randomly generated values
    scalar1 = (324.9 / 8907) * (new_house_params['floor_area'] ** 0.442)
    scalar2 = 0.8 + (0.4 * random.random())
    scalar3 = 0.8 + (0.4 * random.random())
    resp_scalar = scalar1 * scalar2
    unresp_scalar = scalar1 * scalar3

    # Defining ZIPloads
    mod_glm_dict[key]['object'] = 'ZIPload'
    mod_glm_dict[key]['name'] = '{}_{}'.format(
        mod_glm_dict[parent_house_key]['name'], price_responsivity)
    mod_glm_dict[key]['parent'] = mod_glm_dict[parent_house_key]['name']
    mod_glm_dict[key]['schedule_skew'] =\
        mod_glm_dict[parent_house_key]['schedule_skew']
    if price_responsivity == 'responsive':
        mod_glm_dict[key]['base_power'] = 'responsive_loads*{:.2f}'.format(
            resp_scalar)
    else:
        mod_glm_dict[key]['base_power'] = 'unresponsive_loads*{:.2f}'.format(
                unresp_scalar)
    mod_glm_dict[key]['heatgain_fraction'] =\
        str(ZIPload_params['heat_fraction'])
    mod_glm_dict[key]['power_pf'] = str(ZIPload_params['p_pf'])
    mod_glm_dict[key]['current_pf'] = str(ZIPload_params['i_pf'])
    mod_glm_dict[key]['impedance_pf'] = str(ZIPload_params['z_pf'])
    mod_glm_dict[key]['power_fraction'] = str(ZIPload_params['p_fraction'])
    mod_glm_dict[key]['current_fraction'] = str(ZIPload_params['i_fraction'])
    mod_glm_dict[key]['impedance_fraction'] = str(ZIPload_params['z_fraction'])

    logger.info("Generated new house ZIPload {}".format(
                    mod_glm_dict[key]['name']))
    logger.debug(pp.pformat(mod_glm_dict[key]))
    return mod_glm_dict


def add_pool_pump(mod_glm_dict, new_house_name_parts, parent_house_key,
                  ZIPload_params):
    '''Adds a pool pump as an explicit child of the house object.'''
    key = len(mod_glm_dict) + 1
    mod_glm_dict[key] = {}

    # Defining randomized load parameters
    pp_power = 1.36 + (0.36 * random.random())
    pp_dutycycle = 1/6 + (1/2 - 1/6) * random.random()
    pp_period = 4 + (4 * random.random())
    pp_init_phase = random.random()

    mod_glm_dict[key]['object'] = 'ZIPload'
    mod_glm_dict[key]['name'] = '{}_pool_pump'.format(
        mod_glm_dict[parent_house_key]['name'])
    mod_glm_dict[key]['parent'] = mod_glm_dict[parent_house_key]['name']
    mod_glm_dict[key]['schedule_skew'] =\
        mod_glm_dict[parent_house_key]['schedule_skew']
    mod_glm_dict[key]['base_power'] = 'pool_pump_season*{:.2f}'.format(
        pp_power)
    mod_glm_dict[key]['duty_cycle'] = '{:.2f}'.format(pp_dutycycle)
    mod_glm_dict[key]['phase'] = '{:.2f}'.format(pp_init_phase)
    mod_glm_dict[key]['period'] = '{:.2f}'.format(pp_period)
    mod_glm_dict[key]['heatgain_fraction'] =\
        str(ZIPload_params['heat_fraction'])
    mod_glm_dict[key]['power_pf'] = str(ZIPload_params['p_pf'])
    mod_glm_dict[key]['current_pf'] = str(ZIPload_params['i_pf'])
    mod_glm_dict[key]['impedance_pf'] = str(ZIPload_params['z_pf'])
    mod_glm_dict[key]['power_fraction'] = str(ZIPload_params['p_fraction'])
    mod_glm_dict[key]['current_fraction'] = str(ZIPload_params['i_fraction'])
    mod_glm_dict[key]['impedance_fraction'] = str(ZIPload_params['z_fraction'])
    mod_glm_dict[key]['is_240'] = 'TRUE'

    logger.info("Generated new house pool pump load {}".format(
                mod_glm_dict[key]['name']))
    logger.debug(pp.pformat(mod_glm_dict[key]))
    return mod_glm_dict


def add_water_heater(mod_glm_dict, new_house_name_parts, parent_house_key,
                     new_house_params):
    '''Adds a water heater as an explicit child of the house object.'''
    key = len(mod_glm_dict) + 1
    mod_glm_dict[key] = {}

    # Defining randomized water heater parameters
    heating_element_power = 3 + (0.5 * random.uniform(1, 6))
    tank_setpoint = 120 + (16 * random.random())
    thermo_deadband = 4 + (4 * random.random())
    tank_UA = 2 + (2 * random.random())
    water_schedule_num = int(
                    random.uniform(1, new_house_params['no_water_sch'] + 1))
    water_variability = 0.95 + (random.random() * 0.1)
    wh_size_test = random.random()
    wh_size_rand = random.uniform(1, 4)

    mod_glm_dict[key]['object'] = 'waterheater'
    mod_glm_dict[key]['name'] = '{}_waterheater'.format(
        mod_glm_dict[parent_house_key]['name'])
    mod_glm_dict[key]['parent'] = mod_glm_dict[parent_house_key]['name']
    mod_glm_dict[key]['schedule_skew'] =\
        mod_glm_dict[parent_house_key]['schedule_skew']
    mod_glm_dict[key]['heating_element_capacity'] = '{:.1f} kW'.format(
        heating_element_power)
    mod_glm_dict[key]['tank_setpoint'] = '{:.1f}'.format(tank_setpoint)
    mod_glm_dict[key]['temperature'] = '132'
    mod_glm_dict[key]['thermostat_deadband'] = '{:.1f}'.format(thermo_deadband)
    mod_glm_dict[key]['location'] = 'INSIDE'
    mod_glm_dict[key]['tank_UA'] = '{:.1f}'.format(tank_UA)

    # Defining size and demand
    if wh_size_test < new_house_params['wh_size'][0]:
        mod_glm_dict[key]['demand'] = 'small_{}*{:.2f}'.format(
            water_schedule_num, water_variability)
        mod_glm_dict[key]['tank_volume'] = 20 + ((wh_size_rand - 1) * 5)
    elif wh_size_test < (new_house_params['wh_size'][0] +
                         new_house_params['wh_size'][0]):
        if new_house_params['floor_area'] < 2000:
            mod_glm_dict[key]['demand'] = 'small_{}*{:.2f}'.format(
                water_schedule_num, water_variability)
        else:
            mod_glm_dict[key]['demand'] = 'large_{}*{:.2f}'.format(
                water_schedule_num, water_variability)
        mod_glm_dict[key]['tank_volume'] = 30 + ((wh_size_rand - 1) * 10)
    elif new_house_params['floor_area'] > 2000:
        mod_glm_dict[key]['demand'] = 'large_{}*{:.2f}'.format(
                water_schedule_num, water_variability)
        mod_glm_dict[key]['tank_volume'] = 50 + ((wh_size_rand - 1) * 10)
    else:
        mod_glm_dict[key]['demand'] = 'large_{}*{:.2f}'.format(
                water_schedule_num, water_variability)
        mod_glm_dict[key]['tank_volume'] = 30 + ((wh_size_rand - 1) * 10)

    logger.info("Generated new house water heater load {}".format(
                mod_glm_dict[key]['name']))
    logger.debug(pp.pformat(mod_glm_dict[key]))
    return mod_glm_dict


def _tests():
    '''Self-test to verify module functions correctly.'''
    logger.info('Started parsing .glm...')
    input_glm_dict = feeder.parse("/Users/hard312/Documents/Projects/TSP/rev0/"
                                  "models/gridlabd/testbed2/"
                                  "R2_1247_2_t0_growth.glm", filePath=True)
    logger.info('Done parsing .glm. Now de-embedding')
    feeder.fullyDeEmbed(input_glm_dict)
    logger.info('Completed de-embedding.')
    logger.debug('Final input .glm dictionary...')
    logger.debug(pp.pformat(input_glm_dict))
    house_stats = gather_house_stats(input_glm_dict)
    # xfmr_summary = summarize_xfmr_stats(house_stats)
    mod_glm_dict = copy.deepcopy(input_glm_dict)
    mod_glm_dict = update_brownfield_loads(mod_glm_dict, 0.05)
    mod_glm_dict, house_stats = add_greenfield_loads(input_glm_dict,
                                                     house_stats, 0.90)
    logger.info('Completed modification of feeder.')
    logger.debug(pp.pformat(mod_glm_dict))
    feeder_str = feeder.sortedWrite(mod_glm_dict)
    glm_file = open('./modified_feeder.glm', 'w')
    glm_file.write(feeder_str)
    glm_file.close()
    # make_histograms(xfmr_summary)


if __name__ == '__main__':
    logging.basicConfig(filename="gld model updater.log", filemode='w',
                    level=logging.INFO)
    _tests()
