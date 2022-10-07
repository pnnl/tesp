# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: commbldgenerator.py

import os
import json
import math
import numpy as np
from datetime import datetime

import matplotlib.pyplot as plt

from .helpers import gld_strict_name
import tesp_support.feederGenerator_dsot as res_FG


def define_comm_bldg(bldg_metadata, dso_type, num_bldgs):
    """Randomly selects a set number of buildings by type and size (sq. ft.)
        Args:
        bldg_metadata: dictionary of DSO+T specific building parameter data
        dso_type: 'Urban', 'Suburban', or 'Rural'
        num_bldgs: scalar value of number of buildings to be selected
    """
    bldgs = {}
    bldg_types = normalize_dict_prob(dso_type, bldg_metadata['general']['building_type'][dso_type])
    i = 0
    while i < num_bldgs:
        bldg_type = rand_bin_select(bldg_types, np.random.uniform(0, 1))
        if bldg_type not in ['large_office']:
            area = normalize_dict_prob('total_area', bldg_metadata['building_model_specifics'][bldg_type]['total_area'])
            bldg_area_bin = rand_bin_select(area, np.random.uniform(0, 1))
            bldg_area = sub_bin_select(bldg_area_bin, 'total_area', np.random.uniform(0, 1))
            bldgs['bldg_' + str(i + 1)] = [bldg_type, bldg_area]
            i += 1

    return bldgs


def define_comm_loads(bldg_type, bldg_size, dso_type, climate, bldg_metadata):
    """Determines building parameters based on building type, dso type, and (ASHRAE) climate zone
        Args:
        bldg_type (str): class of building (e.g. 'strip_mall', etc)
        bldg_size: size of the building in sq. ft.
        dso_type (str): whether the dso is 'Urban', 'Suburban', or 'Rural'
        climate (str): ASHRAE climate zone that the DSO resides in (e.g. '2A')
        bldg_metadata: dictionary of DSO+T specific building parameter data
    """
    bldg = {'type': bldg_type}

    if bldg_type not in ['large_office', 'ZIPLOAD']:
        # Randomly determine the age (year of construction) of the building
        data = bldg_metadata['building_model_specifics'][bldg_type]
        age = normalize_dict_prob('vintage', data['vintage'])
        age_bin = rand_bin_select(age, np.random.uniform(0, 1))
        bldg['age'] = sub_bin_select(age_bin, 'vintage', np.random.uniform(0, 1))

        #  ---  Assumed values from feeder generator
        c_z_pf = 0.97
        c_i_pf = 0.97
        c_p_pf = 0.97
        c_z_frac = 0.2
        c_i_frac = 0.4
        c_p_frac = 1.0 - c_z_frac - c_i_frac
        bldg['c_z_frac'] = c_z_frac
        bldg['c_i_frac'] = c_i_frac
        bldg['c_p_frac'] = c_p_frac
        bldg['c_z_pf'] = c_z_pf
        bldg['c_i_pf'] = c_i_pf
        bldg['c_p_pf'] = c_p_pf

        # Set the HVAC properties of the building
        bldg['fan_type'] = 'ONE_SPEED'
        if np.random.uniform(0, 1) <= data['primary_electric_heating'][dso_type]:
            bldg['heating_system_type'] = rand_bin_select(data['electric_heating_system_type'], np.random.uniform(0, 1))
        else:
            bldg['heating_system_type'] = 'GAS'
        bldg['cool_type'] = 'ELECTRIC'
        bldg['aux_type'] = 'NONE'
        bldg['airchange_per_hour'] = data['ventilation_requirements']['air_change_per_hour']
        bldg['COP_A'] = bldg_metadata['general']['HVAC']['COP'][str(bldg['age'])] * np.random.normal(1, 0.05)
        #  HVAC oversizing factor
        bldg['os_rand'] = np.random.normal(bldg_metadata['general']['HVAC']['oversizing_factor']['mean'],
                                           bldg_metadata['general']['HVAC']['oversizing_factor']['std_dev'])
        bldg['os_rand'] = min(bldg_metadata['general']['HVAC']['oversizing_factor']['upper_bound'], max(bldg['os_rand'],
                              bldg_metadata['general']['HVAC']['oversizing_factor']['lower_bound']))

        # Set form of the building
        bldg['floor_area'] = bldg_size
        bldg['ceiling_height'] = data['ceiling_height']
        if np.random.uniform(0, 1) <= data['num_stories']['one']:
            bldg['no_of_stories'] = 1
        else:
            bldg['no_of_stories'] = 2
        bldg['window_wall_ratio'] = data['window-wall_ratio'] * np.random.normal(1, 0.2)
        bldg['aspect_ratio'] = data['aspect_ratio'] * np.random.normal(1, 0.1)

        # Set thermal integrity of the building
        # bldg['surface_heat_trans_coeff'] = data['Hm']  # NOT USED IN GLD.
        wall_area = bldg['ceiling_height'] * \
                    2 * math.sqrt(bldg['floor_area'] / bldg['no_of_stories'] / bldg['aspect_ratio']) * \
                    (bldg['aspect_ratio'] + 1)
        ratio = wall_area * (1 - bldg['window_wall_ratio']) / bldg['floor_area']

        bldg['thermal_mass_per_floor_area'] = (0.9 *
                                               np.random.normal(bldg_metadata['general']['interior_mass']['mean'], 0.2)
                                               + 0.5 * ratio *
                                               bldg_metadata['general']['wall_thermal_mass'][str(bldg['age'])])
        bldg['exterior_ceiling_fraction'] = 1
        bldg['roof_type'] = rand_bin_select(data['roof_construction_insulation'], np.random.uniform(0, 1))
        bldg['wall_type'] = rand_bin_select(data['wall_construction'], np.random.uniform(0, 1))
        bldg['Rroof'] = 1 / find_envelope_prop(bldg['roof_type'], bldg['age'],
                                               bldg_metadata['general']['thermal_integrity'], climate) \
                        * 1.3 * np.random.normal(1, 0.1)
        bldg['Rwall'] = 1 / find_envelope_prop(bldg['wall_type'], bldg['age'],
                                               bldg_metadata['general']['thermal_integrity'], climate) \
                        * 1.3 * np.random.normal(1, 0.1)
        bldg['Rfloor'] = 22.  # Values from previous studies
        bldg['Rdoors'] = 3.  # Values from previous studies
        bldg['no_of_doors'] = 3  # Values from previous studies

        bldg['Rwindows'] = 1 / (find_envelope_prop('u_windows', bldg['age'],
                                                   bldg_metadata['general']['thermal_integrity'], climate)
                                * 1.15 * np.random.normal(1, 0.05))
        bldg['glazing_shgc'] = find_envelope_prop('window_SHGC', bldg['age'],
                                                  bldg_metadata['general']['thermal_integrity'], climate) \
                               * 1.15 * np.random.normal(1, 0.05)
        if data['fraction_awnings'] > np.random.uniform(0, 1):
            bldg['window_exterior_transmission_coefficient'] = np.random.normal(0.5, 0.1)
        else:
            bldg['window_exterior_transmission_coefficient'] = 1

        # --------  SCHEDULES  ---------------
        # bldg['base_schedule'] = 'office'   # http://gridlab-d.shoutwiki.com/wiki/Schedule
        # if bldg_type in ['lodging']:
        #     bldg['start_time_weekdays'] = 0
        #     bldg['duration_weekdays'] = 24
        #     bldg['end_time_weekdays'] = 24
        #     bldg['start_time_sat'] = 0
        #     bldg['duration_sat'] = 24
        #     bldg['end_time_sat'] = 24
        #     bldg['start_time_sun'] = 0
        #     bldg['duration_sun'] = 24
        #     bldg['end_time_sun'] = 24
        # else:
        #     hours_bin = rand_bin_select(data['occupancy']['weekly_hours_distribution'], np.random.uniform(0, 1))
        #     bldg['occ_hours'] = sub_bin_select(hours_bin, 'occupancy', np.random.uniform(0, 1))
        #     start_mf = data['occupancy']['occupancy_start_time']['weekdays'] + np.random.uniform(-1.5, 0)
        #     bldg['start_time_weekdays'] = start_mf * \
        #                                   (1 - (bldg['occ_hours'] - data['occupancy']['mean_hours'])
        #                                    / (168 - data['occupancy']['mean_hours']))
        #     bldg['duration_weekdays'] = min((data['occupancy']['occupancy_duration']['weekdays']*bldg['occ_hours'] /
        #                                      data['occupancy']['mean_hours']), (24-bldg['start_time_weekdays']))
        #     bldg['end_time_weekdays'] = bldg['start_time_weekdays'] + bldg['duration_weekdays']
        #
        #     if data['occupancy']['occupancy_start_time']['saturday'] is None:
        #         bldg['start_time_sat'] = None
        #         bldg['duration_sat'] = None
        #         bldg['end_time_sat'] = None
        #     else:
        #         start_sat = data['occupancy']['occupancy_start_time']['saturday'] + np.random.uniform(-1.5, 0)
        #         bldg['start_time_sat'] = start_sat * \
        #                                       (1 - (bldg['occ_hours'] - data['occupancy']['mean_hours'])
        #                                        / (168 - data['occupancy']['mean_hours']))
        #         bldg['duration_sat'] = min((data['occupancy']['occupancy_duration']['saturday']*bldg['occ_hours'] /
        #                                          data['occupancy']['mean_hours']), (24-bldg['start_time_sat']))
        #         bldg['end_time_sat'] = bldg['start_time_sat'] + bldg['duration_sat']
        #
        #     if data['occupancy']['occupancy_start_time']['sunday'] is None:
        #         bldg['start_time_sun'] = None
        #         bldg['duration_sun'] = None
        #         bldg['end_time_sun'] = None
        #     else:
        #         start_sun = data['occupancy']['occupancy_start_time']['sunday'] + np.random.uniform(-1.5, 0)
        #         bldg['start_time_sun'] = start_sun * \
        #                                       (1 - (bldg['occ_hours'] - data['occupancy']['mean_hours'])
        #                                        / (168 - data['occupancy']['mean_hours']))
        #         bldg['duration_sun'] = min((data['occupancy']['occupancy_duration']['sunday']*bldg['occ_hours'] /
        #                                          data['occupancy']['mean_hours']), (24-bldg['start_time_sun']))
        #         bldg['end_time_sun'] = bldg['start_time_sun'] + bldg['duration_sun']

        # For each building type select schedule (lodging and some buildings with 168 hours a week are always occupied)
        hours_bin = rand_bin_select(data['occupancy']['weekly_hours_distribution'], np.random.uniform(0, 1))
        if bldg_type in ['lodging']:
            hours_bin = '168'
        if hours_bin == '168':
            bldg['base_schedule'] = 'alwaysocc'
            bldg['skew_value'] = 0
        elif bldg_type in ['office', 'warehouse_storage', 'education']:
            bldg['base_schedule'] = 'office'
            bldg['skew_value'] = res_FG.randomize_commercial_skew()
        elif bldg_type in ['big_box', 'strip_mall', 'food_service', 'food_sales']:
            bldg['base_schedule'] = 'retail'
            bldg['skew_value'] = res_FG.randomize_commercial_skew()
        elif bldg_type == 'low_occupancy':
            bldg['base_schedule'] = 'lowocc'
            bldg['skew_value'] = res_FG.randomize_commercial_skew()

        # randomize 10# then convert W/sf -> kW
        floor_area = bldg['floor_area']
        bldg['adj_lights'] = data['internal_heat_gains']['lighting'] * \
                             (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
        bldg['adj_plugs'] = data['internal_heat_gains']['MEL'] * (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
        bldg['adj_refrig'] = data['internal_heat_gains']['large_refrigeration'] \
                             * (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
        # ---------------- Setting gas water heating to zero ----------------
        bldg['adj_gas'] = 0
        # bldg['adj_gas'] = (0.9 + 0.2 * np.random.random())
        # Set exterior lighting to zero as plug and light parameters capture all of CBECS loads.
        bldg['adj_ext'] = 0  # (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
        occ_load = 73  # Assumes 73 watts / occupant from Caney Fork study
        bldg['adj_occ'] = data['internal_heat_gains']['occupancy'] * occ_load \
                          * (0.9 + 0.1 * np.random.random()) * floor_area / 1000.

        bldg['int_gains'] = bldg['adj_lights'] + bldg['adj_plugs'] + bldg['adj_occ'] + bldg['adj_gas']

    return bldg


def create_comm_zones(bldg, comm_loads, key, op, batt_metadata, storage_percentage, ev_metadata, ev_percentage,
                      solar_percentage, pv_rating_MW, solar_Q_player, case_type, metrics, metrics_interval, mode=None):
    """For large buildings, breaks building up into multiple zones.  For all buildings sends definition dictionary to
    function that writes out building definition to GLD file format.
        Args:
        bldg (dict): dictionary of building parameters for the building to be processed.
        key (str): name of feeder node or meter being used
        op (str): GLD output file
        mode (str): if 'test' will ensure that GLD output function does not set parent - allows buildings to be run in
        GLD without feeder info
        """
    mtr = comm_loads[key][0]
    comm_type = comm_loads[key][1]
    comm_size = int(comm_loads[key][2])
    kva = float(comm_loads[key][3])
    nphs = int(comm_loads[key][4])
    phases = comm_loads[key][5]
    vln = float(comm_loads[key][6])
    loadnum = int(comm_loads[key][7])
    comm_name = comm_loads[key][8]

    c_z_pf = 0.97
    c_i_pf = 0.97
    c_p_pf = 0.97
    c_z_frac = 0.2
    c_i_frac = 0.4
    c_p_frac = 1.0 - c_z_frac - c_i_frac
    light_scalar_comm = 0.0  # Turned off street lights - set to 1.0 to turn on.

    if bldg['type'] not in ['large_office', 'ZIPLOAD']:
        bldg_size = bldg['floor_area']

        bldg['mtr'] = mtr
        bldg['groupid'] = comm_type  # + '_' + str(loadnum)

        # Need to create a buffer version of bldg so zip loads do not get over ridden in the multi-zone for loops
        buff = bldg.copy()
        print('// load', key, 'parent', bldg['mtr'], 'type', comm_type, 'sqft', comm_size, 'kva', '{:.3f}'.format(kva),
              'nphs', nphs, 'phases', phases, 'vln', '{:.3f}'.format(vln), file=op)

        #  ---------- Subdivide into zones for large buildings  -------------------
        if bldg_size < 10000:
            floor_area = bldg_size
            bldg['exterior_wall_fraction'] = 1
            bldg['exterior_floor_fraction'] = 1
            bldg['exterior_wall_fraction'] = 1
            bldg['exterior_floor_fraction'] = 1
            bldg['interior_exterior_wall_ratio'] = 1
            bldg['init_temp'] = 68. + 4. * np.random.random()
            zone = 'all'
            bldg['zonename'] = gld_strict_name(key + '_' + comm_name + '_zone_' + str(zone))
            write_one_commercial_zone(bldg, op, metrics, metrics_interval, mode)

        # For buildings between 10k and 30k sq. ft. break into six zones using method for big box store in previous work
        elif bldg_size < 30000:
            floor_area = bldg_size / 6.
            bldg['aspect_ratio'] = 1.28
            bldg['floor_area'] = floor_area
            total_depth = math.sqrt(bldg_size / bldg['aspect_ratio'])
            total_width = bldg['aspect_ratio'] * total_depth
            d = total_width / 3.
            w = total_depth / 2.

            for zone in range(1, 7):
                if zone == 2 or zone == 5:
                    bldg['exterior_wall_fraction'] = d / (2. * (d + w))
                    bldg['exterior_floor_fraction'] = (0. + d) / (2. * (total_width + total_depth)) / (
                            floor_area / bldg_size)
                else:
                    bldg['exterior_wall_fraction'] = 0.5
                    bldg['exterior_floor_fraction'] = (w + d) / (2. * (total_width + total_depth)) / (
                            floor_area / bldg_size)

                # bldg['interior_exterior_wall_ratio'] = (floor_area + bldg['no_of_doors'] * 20.) \
                #                                         / (bldg['ceiling_height'] * 2. * (w + d)) - 1. \
                #                                         + bldg['window_wall_ratio'] * bldg['exterior_wall_fraction']
                bldg['interior_exterior_wall_ratio'] = 1
                bldg['init_temp'] = 68. + 4. * np.random.random()

                bldg['adj_lights'] = buff['adj_lights'] * floor_area / bldg_size
                bldg['adj_plugs'] = buff['adj_plugs'] * floor_area / bldg_size
                bldg['adj_refrig'] = buff['adj_refrig'] * floor_area / bldg_size
                bldg['adj_gas'] = buff['adj_gas'] * floor_area / bldg_size
                bldg['adj_ext'] = buff['adj_ext'] * floor_area / bldg_size
                bldg['adj_occ'] = buff['adj_occ'] * floor_area / bldg_size
                bldg['int_gains'] = buff['int_gains'] * floor_area / bldg_size

                bldg['zonename'] = gld_strict_name(key + '_' + comm_name + '_zone_' + str(zone))
                write_one_commercial_zone(bldg, op, metrics, metrics_interval, mode)
        elif bldg_size > 30000:
            floor_area_choose = bldg_size
            bldg['no_of_stories'] = 1
            for floor in range(1, 4):
                bldg['aspect_ratio'] = 1.5  # Moving aspect ratio here so it is not overwritten below
                total_depth = math.sqrt(floor_area_choose / (3. * bldg['aspect_ratio']))
                total_width = bldg['aspect_ratio'] * total_depth
                if floor == 3:
                    bldg['exterior_ceiling_fraction'] = 1
                else:
                    bldg['exterior_ceiling_fraction'] = 0
                for zone in range(1, 6):
                    if zone == 5:
                        bldg['window_wall_ratio'] = 0  # this was not in the CCSI version
                        bldg['exterior_wall_fraction'] = 0
                        w = total_depth - 60.  # Increased from 30 to avoid zone 5 being over 10k sq ft
                        d = total_width - 60.  # Increased from 30 to avoid zone 5 being over 10k sq ft
                    else:
                        d = 30.  # Increased from 15 to avoid zone 5 being over 10k sq ft when building over 50k sqft
                        if zone == 1 or zone == 3:
                            w = total_width - 30.
                        else:
                            w = total_depth - 30.
                        bldg['exterior_wall_fraction'] = w / (2. * (w + d))
                    floor_area = w * d
                    bldg['floor_area'] = floor_area
                    bldg['aspect_ratio'] = w / d

                    if floor > 1:
                        bldg['exterior_floor_fraction'] = 0
                    else:
                        bldg['exterior_floor_fraction'] = w / (2. * (w + d)) / (
                                floor_area / (floor_area_choose / 3.))

                    #  bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * np.random.random())
                    # bldg['interior_exterior_wall_ratio'] = floor_area / (bldg['ceiling_height'] * 2. * (w + d)) - 1. \
                    #                                         + bldg['window_wall_ratio'] * bldg[
                    #                                             'exterior_wall_fraction']
                    bldg['interior_exterior_wall_ratio'] = 1
                    # will round to zero, presumably the exterior doors are treated like windows
                    bldg['no_of_doors'] = 0.1

                    bldg['init_temp'] = 68. + 4. * np.random.random()

                    bldg['adj_lights'] = buff['adj_lights'] * floor_area / bldg_size
                    bldg['adj_plugs'] = buff['adj_plugs'] * floor_area / bldg_size
                    bldg['adj_refrig'] = buff['adj_refrig'] * floor_area / bldg_size
                    bldg['adj_gas'] = buff['adj_gas'] * floor_area / bldg_size
                    bldg['adj_ext'] = buff['adj_ext'] * floor_area / bldg_size
                    bldg['adj_occ'] = buff['adj_occ'] * floor_area / bldg_size
                    bldg['int_gains'] = buff['int_gains'] * floor_area / bldg_size

                    bldg['zonename'] = gld_strict_name(
                        key + '_' + comm_name + '_floor_' + str(floor) + '_zone_' + str(zone))
                    write_one_commercial_zone(bldg, op, metrics, metrics_interval, mode)

        if np.random.uniform(0, 1) <= storage_percentage:
            # TODO: Review battery results to see if one battery per 10000 sq ft. is appropriate.
            num_batt = math.floor(bldg_size / 10000) + 1
            battery_capacity = num_batt * res_FG.get_dist(batt_metadata['capacity(kWh)']['mean'],
                                                       batt_metadata['capacity(kWh)']['deviation_range_per']) * 1000
            max_charge_rate = res_FG.get_dist(batt_metadata['rated_charging_power(kW)']['mean'],
                                            batt_metadata['rated_charging_power(kW)']['deviation_range_per']) * 1000
            max_discharge_rate = max_charge_rate
            inverter_efficiency = batt_metadata['inv_efficiency(per)'] / 100
            charging_loss = res_FG.get_dist(batt_metadata['rated_charging_loss(per)']['mean'],
                                            batt_metadata['rated_charging_loss(per)']['deviation_range_per']) / 100
            discharging_loss = charging_loss
            round_trip_efficiency = charging_loss * discharging_loss
            rated_power = max(max_charge_rate, max_discharge_rate)

            basenode = mtr
            bat_m_name = gld_strict_name(basenode + '_mbat')
            batname = gld_strict_name(basenode + '_bat')
            bat_i_name = gld_strict_name(basenode + '_ibat')
            storage_inv_mode = 'CONSTANT_PQ'

            if case_type['bt']:
                # battery_count += 1
                print('object meter {', file=op)
                print('  name', bat_m_name + ';', file=op)
                print('  parent', mtr + ';', file=op)
                print('  phases', phases + ';', file=op)
                print('  nominal_voltage ' + str(vln) + ';', file=op)
                print('  object inverter {', file=op)
                print('    name', bat_i_name + ';', file=op)
                print('    phases', phases + ';', file=op)
                print('    groupid batt_inverter;', file=op)
                print('    generator_status ONLINE;', file=op)
                print('    generator_mode CONSTANT_PQ;', file=op)
                print('    inverter_type FOUR_QUADRANT;', file=op)
                print('    four_quadrant_control_mode', storage_inv_mode + ';', file=op)
                print('    charge_lockout_time 1;', file=op)
                print('    discharge_lockout_time 1;', file=op)
                print('    rated_power', '{:.2f}'.format(rated_power) + ';', file=op)
                print('    max_charge_rate', '{:.2f}'.format(max_charge_rate) + ';', file=op)
                print('    max_discharge_rate', '{:.2f}'.format(max_discharge_rate) + ';', file=op)
                print('    sense_object', mtr + ';', file=op)
                # print ('    charge_on_threshold -100;', file=op)
                # print ('    charge_off_threshold 0;', file=op)
                # print ('    discharge_off_threshold 2000;', file=op)
                # print ('    discharge_on_threshold 3000;', file=op)
                print('    inverter_efficiency', '{:.2f}'.format(inverter_efficiency) + ';', file=op)
                print('    power_factor 1.0;', file=op)
                print('    object battery { // Tesla Powerwall 2', file=op)
                print('      name', batname + ';', file=op)
                print('      use_internal_battery_model true;', file=op)
                print('      battery_type LI_ION;', file=op)
                print('      nominal_voltage 480;', file=op)
                print('      battery_capacity', '{:.2f}'.format(battery_capacity) + ';', file=op)
                print('      round_trip_efficiency', '{:.2f}'.format(round_trip_efficiency) + ';', file=op)
                print('      state_of_charge 0.50;', file=op)
                print('    };', file=op)
                if metrics_interval > 0 and "meter" in metrics:
                    print('    object metrics_collector {', file=op)
                    print('      interval', str(metrics_interval) + ';', file=op)
                    print('    };', file=op)
                print('  };', file=op)
                print('}', file=op)

        if np.random.uniform(0, 1) <= solar_percentage:
            # typical PV panel is 350 Watts and avg home has 5kW installed.
            # If we assume 2500 sq. ft as avg area of a single family house, we can say:
            # one 350 W panel for every 175 sq. ft.
            num_panel = np.floor(bldg_size / 175)
            inverter_undersizing = 1.0
            inv_power = num_panel * 350 * inverter_undersizing
            pv_scaling_factor = inv_power / pv_rating_MW

            basenode = mtr
            sol_m_name = gld_strict_name(basenode + '_msol')
            solname = gld_strict_name(basenode + '_sol')
            sol_i_name = gld_strict_name(basenode + '_isol')
            metrics_interval = 300
            solar_inv_mode = 'CONSTANT_PQ'
            if case_type['pv']:
                # solar_count += 1
                # solar_kw += 0.001 * inv_power
                print('object meter {', file=op)
                print('  name', sol_m_name + ';', file=op)
                print('  parent', basenode + ';', file=op)
                print('  phases', phases + ';', file=op)
                print('  nominal_voltage ' + str(vln) + ';', file=op)
                print('  object inverter {', file=op)
                print('    name', sol_i_name + ';', file=op)
                print('    phases', phases + ';', file=op)
                print('    groupid sol_inverter;', file=op)
                print('    generator_status ONLINE;', file=op)
                print('    inverter_type FOUR_QUADRANT;', file=op)
                print('    inverter_efficiency 1;', file=op)
                print('    rated_power', '{:.0f}'.format(inv_power) + ';', file=op)
                print('    generator_mode', solar_inv_mode + ';', file=op)
                print('    four_quadrant_control_mode', solar_inv_mode + ';', file=op)
                print('    P_Out', 'P_out_inj.value * {}'.format(pv_scaling_factor), ';', file=op)
                if 'no_file' not in solar_Q_player:
                    print('    Q_Out Q_out_inj.value * 0.00;', file=op)
                else:
                    print('    Q_Out 0;', file=op)
                # Instead of solar object, write a fake V_in and I_in sufficient high so
                # that it doesnt limit the player output
                print('     V_In 10000000;', file=op)
                print('     I_In 10000000;', file=op)
                if metrics_interval > 0:
                    print('    object metrics_collector {', file=op)
                    print('      interval', str(metrics_interval) + ';', file=op)
                    print('    };', file=op)
                print('  };', file=op)
                print('}', file=op)

        if np.random.uniform(0, 1) <= ev_percentage:
            # first lets select an ev model:
            ev_name = res_FG.selectEVmodel(ev_metadata['sale_probability'], np.random.uniform(0, 1))
            ev_range = ev_metadata['Range (miles)'][ev_name]
            ev_mileage = ev_metadata['Miles per kWh'][ev_name]
            ev_charge_eff = ev_metadata['charging efficiency']
            # check if level 1 charger is used or level 2
            if np.random.uniform(0, 1) <= ev_metadata['Level_1_usage']:
                ev_max_charge = ev_metadata['Level_1 max power (kW)']
                volt_conf = 'IS110'  # for level 1 charger, 110 V is good
            else:
                ev_max_charge = ev_metadata['Level_2 max power (kW)'][ev_name]
                volt_conf = 'IS220'  # for level 2 charger, 220 V is must
            # now, let's map a random driving schedule with this vehicle ensuring daily miles
            # doesn't exceed the vehicle range and home duration is enough to charge the vehicle
            drive_sch = res_FG.match_driving_schedule(ev_range, ev_mileage, ev_max_charge)
            # ['daily_miles','home_arr_time','home_duration','work_arr_time','work_duration']

            # few sanity checks
            if drive_sch['daily_miles'] > ev_range:
                raise UserWarning('daily travel miles for EV can not be more than range of the vehicle!')
            if not res_FG.is_hhmm_valid(drive_sch['home_arr_time']) or \
                    not res_FG.is_hhmm_valid(drive_sch['home_leave_time']) or \
                    not res_FG.is_hhmm_valid(drive_sch['work_arr_time']):
                raise UserWarning('invalid HHMM format of driving time!')
            if drive_sch['home_duration'] > 24 * 3600 or drive_sch['home_duration'] < 0 or drive_sch[
                'work_duration'] > 24 * 3600 or drive_sch['work_duration'] < 0:
                raise UserWarning('invalid home or work duration for ev!')
            if not res_FG.is_drive_time_valid(drive_sch):
                raise UserWarning('home and work arrival time are not consistent with durations!')

            basenode = mtr
            evname = gld_strict_name(basenode + '_ev')
            hsename = gld_strict_name(basenode + '_ev_hse')
            parent_zone = bldg['zonename']
            if case_type['pv']:  # all pvCases(HR) have ev populated
                print('object evcharger_det {', file=op)
                print('    name', evname + ';', file=op)
                print('    parent', parent_zone + ';', file=op)
                print('    configuration', volt_conf + ';', file=op)  #
                print('    breaker_amps 1000;', file=op)
                print('    battery_SOC 100.0; //initial soc', file=op)
                print('    travel_distance', '{};'.format(drive_sch['daily_miles']), file=op)
                print('    arrival_at_work', '{};'.format(drive_sch['work_arr_time']), file=op)
                print('    duration_at_work', '{}; // (secs)'.format(drive_sch['work_duration']), file=op)
                print('    arrival_at_home', '{};'.format(drive_sch['home_arr_time']), file=op)
                print('    duration_at_home', '{}; // (secs)'.format(drive_sch['home_duration']), file=op)
                print('    work_charging_available FALSE;', file=op)
                print('    maximum_charge_rate', '{:.2f}; //(watts)'.format(ev_max_charge * 1000), file=op)
                print('    mileage_efficiency', '{:.3f}; // miles per kWh'.format(ev_mileage), file=op)
                print('    mileage_classification', '{:.3f}; // range in miles'.format(ev_range), file=op)
                print('    charging_efficiency', '{:.3f};'.format(ev_charge_eff), file=op)
                if metrics_interval > 0:
                    print('    object metrics_collector {', file=op)
                    print('      interval', str(metrics_interval) + ';', file=op)
                    print('    };', file=op)
                print('}', file=op)

    elif comm_type == 'ZIPLOAD':
        phsva = 1000.0 * kva / nphs
        print('object load { // street lights', file=op)
        print('  name {:s};'.format(key + '_streetlights'), file=op)
        print('  parent {:s};'.format(mtr), file=op)
        print('  groupid STREETLIGHTS;', file=op)
        print('  nominal_voltage {:2f};'.format(vln), file=op)
        print('  phases {:s};'.format(phases), file=op)
        for phs in ['A', 'B', 'C']:
            if phs in phases:
                print('  impedance_fraction_{:s} {:f};'.format(phs, c_z_frac), file=op)
                print('  current_fraction_{:s} {:f};'.format(phs, c_i_frac), file=op)
                print('  power_fraction_{:s} {:f};'.format(phs, c_p_frac), file=op)
                print('  impedance_pf_{:s} {:f};'.format(phs, c_z_pf), file=op)
                print('  current_pf_{:s} {:f};'.format(phs, c_i_pf), file=op)
                print('  power_pf_{:s} {:f};'.format(phs, c_p_pf), file=op)
                print('  base_power_{:s} street_lighting*{:.2f};'.format(phs, light_scalar_comm * phsva), file=op)
        print('};', file=op)
    else:
        print('object load { // accumulate zones', file=op)
        print('  name {:s};'.format(key), file=op)
        print('  parent {:s};'.format(mtr), file=op)
        print('  groupid {:s};'.format(comm_type), file=op)
        print('  nominal_voltage {:2f};'.format(vln), file=op)
        print('  phases {:s};'.format(phases), file=op)
        print('};', file=op)


def find_envelope_prop(prop, age, env_data, climate):
    """Returns the envelope value for a given type of property based on the age and (ASHRAE) climate zone of the
        building
    Args:
        prop (str): envelope material property of interest (e.g. 'wood-framed' or 'u-windows')
        age (int): age of the building in question (typically between 1945 and present).
        env_data (dict): Dictionary of envelope property data
        climate ('string'): ASHRAE climate zone of building (e.g. '2A')
    Returns:
        val (float): property value - typically a U-value.
    """
    # Find age bin for properties
    if age < 1960:
        age_bin = '1960'
    elif age < 1980:
        age_bin = '1960-1979'
    elif age < 2000:
        age_bin = '1980-1999'
    elif age < 2010:
        age_bin = '2000-2009'
    elif age < 2016:
        age_bin = '2010-2015'
    else:
        age_bin = '2015'

    if prop in ['insulation_above_deck', 'insulation_in_attic_and_other']:
        if age_bin in ['1960', '1960-1979', '1980-1999', '2000-2009']:
            val = env_data[climate]['u_roof_all_types'][age_bin]
        else:
            val = env_data[climate]['u_roof_all_types'][age_bin][prop]

    if prop in ['steel_framed', 'mass_wall', 'metal_building', 'wood_framed']:
        if age_bin in ['1960', '1960-1979', '1980-1999']:
            val = env_data[climate]['u_walls_above_grade'][age_bin]
        else:
            val = env_data[climate]['u_walls_above_grade'][age_bin][prop]

    if prop == 'u_windows':
        val = env_data[climate]['u_windows'][age_bin]

    if prop == 'window_SHGC':
        val = env_data[climate]['window_SHGC'][age_bin]

    return val


def normalize_dict_prob(name, dict):
    """Ensures that the probably distribution of values in a dictionary effectively sums to one
        Args:
        dict: dictionary of elements and associated non-cumulative probabilities
    """
    sum1 = 0
    sum2 = 0
    for i in dict:
        sum1 += dict[i]
    for y in dict:
        dict[y] = dict[y] / sum1
    for z in dict:
        sum2 += dict[z]
    if sum1 != sum2:
        print("WARNING " + name + " dictionary normalize to 1, value are > ", dict)
    return dict


def rand_bin_select(dict, prob):
    """Returns the element (bin) in a dictionary given a certain probability
    Args:
        dict: dictionary of elements and associated non-cumulative probabilities
        prob: scalar value between 0 and 1
    """
    total = 0

    for bin in dict:
        total += dict[bin]
        if total >= prob:
            return bin
    return bin


def sub_bin_select(bin, type, prob):
    """Returns a scalar value within a bin range based on a uniform probability within that bin range
    Args:
        bin: name of bin
        type: building parameter describing set of bins
        prob: scalar value between 0 and 1
    """
    if type == 'vintage':
        bins = {'pre_1960': [1945, 1959],
                '1960-1979': [1960, 1979],
                '1980-1999': [1980, 1999],
                '2000-2009': [2000, 2009],
                '2010-2015': [2010, 2015]}
    elif type == 'total_area':
        bins = {'1-5': [1000, 5000],
                '5-10': [5001, 10000],
                '10-25': [10001, 25000],
                '25-50': [25001, 50000],
                '50_more': [50001, 55000]}
    elif type == 'occupancy':
        bins = {'0': [0, 0],
                '1-39': [1, 39.99],
                '40-48': [40, 48.99],
                '49-60': [49, 60.99],
                '61-84': [61, 84.99],
                '85-167': [85, 167.99],
                '168': [168, 168]}
    val = bins[bin][0] + prob * (bins[bin][1] - bins[bin][0])
    if type in ['vintage']:
        val = int(val)
    return val


def write_one_commercial_zone(bldg, op, metrics, metrics_interval, mode=None):
    """Write one pre-configured commercial zone as a house

    Args:
      bldg: dictionary of GridLAB-D house and zipload attributes
      op (file): open file to write to
      mode (str): if in 'test' mode will not write out parent info.
    """
    print('object house {', file=op)
    print('  name', bldg['zonename'] + ';', file=op)
    print('//  type', bldg['type'] + ';', file=op)
    if mode != 'test':
        print('  parent', bldg['mtr'] + ';', file=op)
    print('  groupid', bldg['groupid'] + ';', file=op)
    print('  motor_model BASIC;', file=op)
    print('  schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('  floor_area {:.0f};'.format(bldg['floor_area']), file=op)
    # Internal gains need to be converted from kW to BTU-hr.
    print('  design_internal_gains {:.2f};'.format(bldg['int_gains'] * 1000 * 3.413), file=op)
    print('  number_of_doors {:.0f};'.format(bldg['no_of_doors']), file=op)
    print('  aspect_ratio {:.2f};'.format(bldg['aspect_ratio']), file=op)
    print('  total_thermal_mass_per_floor_area {:1.2f};'.format(bldg['thermal_mass_per_floor_area']), file=op)
    # print ('  interior_surface_heat_transfer_coeff {:1.2f};'.format(bldg['surface_heat_trans_coeff']), file=op)
    print('  interior_exterior_wall_ratio {:.2f};'.format(bldg['interior_exterior_wall_ratio']), file=op)
    print('  exterior_floor_fraction {:.3f};'.format(bldg['exterior_floor_fraction']), file=op)
    print('  exterior_ceiling_fraction {:.3f};'.format(bldg['exterior_ceiling_fraction']), file=op)
    print('  Rwall {:3.2f};'.format(bldg['Rwall']), file=op)
    print('  Rroof {:3.2f};'.format(bldg['Rroof']), file=op)
    print('  Rfloor {:.2f};'.format(bldg['Rfloor']), file=op)
    print('  Rdoors {:2.1f};'.format(bldg['Rdoors']), file=op)
    print('  exterior_wall_fraction {:.2f};'.format(bldg['exterior_wall_fraction']), file=op)
    # print ('  glazing_layers {:s};'.format(bldg['glazing_layers']), file=op)
    # print ('  glass_type {:s};'.format(bldg['glass_type']), file=op)
    # print ('  glazing_treatment {:s};'.format(bldg['glazing_treatment']), file=op)
    # print ('  window_frame {:s};'.format(bldg['window_frame']), file=op)
    print('  Rwindows {:.2f};'.format(bldg['Rwindows']), file=op)
    #  GLD uses the term window_sharing to assign 'glazing_shgc'
    print('  window_shading {:.2f};'.format(bldg['glazing_shgc']), file=op)
    print('  window_exterior_transmission_coefficient {:.2f};'.format(bldg['window_exterior_transmission_coefficient']),
          file=op)
    print('  airchange_per_hour {:.2f};'.format(bldg['airchange_per_hour']), file=op)
    print('  window_wall_ratio {:0.3f};'.format(bldg['window_wall_ratio']), file=op)
    print('  heating_system_type {:s};'.format(bldg['heating_system_type']), file=op)
    print('  auxiliary_system_type {:s};'.format(bldg['aux_type']), file=op)
    print('  fan_type {:s};'.format(bldg['fan_type']), file=op)
    print('  cooling_system_type {:s};'.format(bldg['cool_type']), file=op)
    print('  air_temperature {:.2f};'.format(bldg['init_temp']), file=op)
    print('  mass_temperature {:.2f};'.format(bldg['init_temp']), file=op)
    print('  over_sizing_factor {:.2f};'.format(bldg['os_rand']), file=op)
    print('  cooling_COP {:2.2f};'.format(bldg['COP_A']), file=op)
    print('  cooling_setpoint 80.0; // {:s}_cooling'.format(bldg['base_schedule']), file=op)
    print('  heating_setpoint 60.0; // {:s}_heating'.format(bldg['base_schedule']), file=op)
    print('  object ZIPload { // lights', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 0.8;', file=op)
    print('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
    print('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
    print('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
    print('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
    print('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
    print('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
    print('    base_power {:s}_lights*{:.2f};'.format(bldg['base_schedule'], bldg['adj_lights']), file=op)
    print('  };', file=op)
    print('  object ZIPload { // plug loads', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 0.9;', file=op)
    print('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
    print('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
    print('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
    print('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
    print('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
    print('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
    print('    base_power {:s}_plugs*{:.2f};'.format(bldg['base_schedule'], bldg['adj_plugs']), file=op)
    print('  };', file=op)
    print('  object ZIPload { // gas waterheater', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 1.0;', file=op)
    print('    power_fraction 0;', file=op)
    print('    impedance_fraction 0;', file=op)
    print('    current_fraction 0;', file=op)
    print('    power_pf 1;', file=op)
    print('    base_power {:s}_gas*{:.2f};'.format(bldg['base_schedule'], bldg['adj_gas']), file=op)
    print('  };', file=op)
    print('  object ZIPload { // exterior lights', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 0.0;', file=op)
    print('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
    print('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
    print('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
    print('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
    print('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
    print('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
    print('    base_power {:s}_exterior*{:.2f};'.format(bldg['base_schedule'], bldg['adj_ext']), file=op)
    print('  };', file=op)
    print('  object ZIPload { // occupancy', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 1.0;', file=op)
    print('    power_fraction 0;', file=op)
    print('    impedance_fraction 0;', file=op)
    print('    current_fraction 0;', file=op)
    print('    power_pf 1;', file=op)
    print('    base_power {:s}_occupancy*{:.2f};'.format(bldg['base_schedule'], bldg['adj_occ']), file=op)
    print('  };', file=op)
    if bldg['adj_refrig'] != 0:
        print('  object ZIPload { // large refrigeration electrical load', file=op)
        # print ('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
        # TODO: set to 0.01 to avoid a divide by zero issue in the agent code.  Should be set to zero after that is fixed.
        print('    heatgain_fraction 0.01;', file=op)
        print('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
        print('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
        print('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
        print('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
        print('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
        print('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
        print('    base_power {:.2f};'.format(bldg['adj_refrig']), file=op)
        print('  };', file=op)
    if metrics_interval > 0 and "house" in metrics:
        print('  object metrics_collector {', file=op)
        print('    interval', str(metrics_interval) + ';', file=op)
        print('  };', file=op)
    print('}', file=op)


# ----------------------   MAIN  ------------------------


if __name__ == '__main__':

    metadata_path = 'C:\\Users\\reev057\\PycharmProjects\TESP\src\examples\dsot_v1\\analysis_metadata'
    with open(os.path.join(metadata_path, 'DSOT_commercial_metadata.json')) as json_file:
        comm_bldg_data = json.load(json_file)

    # TODO: Ensure that there is a strategy to set a random seed that is different for each DSO.
    # np.random.seed(30)
    dso = 'Suburban'
    climate = '2A'  # ASHRAE climate zone
    num_bldg = 30

    outpath = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Dummy/'
    outname = 'test_comm_' + str(num_bldg) + '_bldg_' + climate
    op = open(outpath + outname + '.glm', 'w')

    #  1 - define random population of building types and sizes
    comm_bldgs = define_comm_bldg(comm_bldg_data, dso, num_bldg)

    #  2 - set parameters for each defined building
    comm_bldg = {}
    comm_zones = {}
    comm_loads = {}
    for i in comm_bldgs:
        comm_bldg[i] = define_comm_loads(comm_bldgs[i][0], comm_bldgs[i][1], dso, climate, comm_bldg_data)

        comm_zones[i] = comm_bldg[i].copy()

        #  3 - for large buildings subdivide into subzones.  Write all buildings and zones out to GLD format
        key = i
        comm_loads[key] = [i, comm_bldgs[i][0], 3, 20, 3, 'A', 240, 200]
        # comm_loads[key][1] = bldgs[i][0]
        # comm_loads[key][2] = 3  # Dummy number for number of zones
        # comm_loads[key][3] = 20  # Dummy number for kVA
        # comm_loads[key][4] = 3  # Dummy number for nphs
        # comm_loads[key][5] = 'A'  # Dummy number for phases
        # comm_loads[key][6] = 240  # dummy number for vln
        # comm_loads[key][7] = 200  # Dummy number for load number

        create_comm_zones(comm_zones[i], comm_loads, key, op, 'test')

    #   PLOT OUTPUT AND SAVE PLOTS TO FILE
    plot_path = 'C:\\Users\\reev057\\OneDrive - PNNL\\Documents\\GMLC\\DSO+T\\building distribution'
    vars = ['age', 'os_rand', 'COP_A', 'airchange_per_hour', 'floor_area', 'ceiling_height', 'window_wall_ratio',
            'aspect_ratio', 'Rroof', 'Rwall', 'thermal_mass_per_floor_area', 'window_exterior_transmission_coefficient',
            'Rwindows', 'glazing_shgc', 'int_gains']
    # vars = ['start_time_weekdays', 'duration_weekdays', 'end_time_weekdays', 'start_time_sat', 'duration_sat',
    #         'end_time_sat', 'start_time_sun', 'duration_sun', 'end_time_sun']
    outputs = ['total', 'office', 'warehouse_storage', 'big_box', 'strip_mall', 'education',
               'food_service', 'healthcare_inpatient', 'food_sales', 'lodging', 'low_occupancy']

    dist = {}

    for var in vars:
        for out in outputs:
            dist[out] = []

        for i in comm_bldgs:
            if comm_bldg[i]['type'] not in ['large_office']:
                if comm_bldg[i][var] is not None:
                    dist['total'].append(comm_bldg[i][var])
                    dist[comm_bldg[i]['type']].append(comm_bldg[i][var])

        # Plot distribution of variable for total distribution
        label = var
        plt.figure(figsize=(8, 6))
        plt.hist(dist['total'], bins=20, alpha=0.5, edgecolor='k', label=label)
        plt.title(var + ' distribution')
        plt.legend(loc='upper right')
        plt.xlabel(var)
        plt.ylabel('Count')

        plot_filename = datetime.now().strftime('%Y%m%d') + '-total_bldg_distribution_' + var + '.png'
        file_path_fig = os.path.join(plot_path, plot_filename)

        plt.savefig(file_path_fig, bbox_inches='tight')

        # Plot distribution of variable for each building type
        fig, axes = plt.subplots(nrows=5, ncols=2, figsize=(10, 10))
        fig.suptitle('Distributions of ' + var)
        for ax, each in zip(axes.flatten(), dist):
            ax.hist(dist[each], bins=10, alpha=0.5, edgecolor='k', label=label)
            ax.set_title(label=each, pad=-9, )

        plot_filename = datetime.now().strftime('%Y%m%d') + '-bldg_sub-distributions_' + var + '.png'
        file_path_fig = os.path.join(plot_path, plot_filename)

        fig.savefig(file_path_fig, bbox_inches='tight')

    print(comm_bldg)
