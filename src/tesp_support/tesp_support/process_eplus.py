#   Copyright (C) 2017-2022 Battelle Memorial Institute
# file: process_eplus.py
"""Functions to plot data from the EnergyPlus agent

Public Functions:
        :process_eplus: Reads the data and metadata, then makes the plots.  

"""
import logging
import json
import os

import numpy as np
import matplotlib.pyplot as plt

# Setting up logging
logger = logging.getLogger(__name__)


def read_eplus_metrics(path, name_root, quiet=False):
    eplus_dict_path = os.path.join(path, f'eplus_{name_root}_metrics.json')

    # read the JSON file
    try:
        lp = open(eplus_dict_path).read()
        lst = json.loads(lp)
        if not quiet:
            print('Metrics data starting', lst['StartTime'])
    except:
        logger.error(f'Unable to open eplus metrics file {eplus_dict_path}')
        return

    # make a sorted list of the times
    lst.pop('StartTime')
    load_scale = 1.0
    if 'LoadScale' in lst:
        load_scale = lst.pop('LoadScale')
    print('LoadScale is', load_scale)
    meta = lst.pop('Metadata')
    times = list(map(int, list(lst.keys())))
    times.sort()
    if not quiet:
        print('There are', len(times), 'sample times')

    # parse the metadata for things of specific interest
    idx_e = {}
    for key, val in meta.items():
        if key == 'electric_demand_power_avg':
            idx_e['ELECTRIC_DEMAND_IDX'] = val['index']
            idx_e['ELECTRIC_DEMAND_UNITS'] = val['units']
        elif key == 'hvac_demand_power_avg':
            idx_e['HVAC_DEMAND_IDX'] = val['index']
            idx_e['HVAC_DEMAND_UNITS'] = val['units']
        elif key == 'occupants_total_avg':
            idx_e['OCCUPANTS_IDX'] = val['index']
            idx_e['OCCUPANTS_UNITS'] = val['units']
        elif key == 'kwhr_price_avg':
            idx_e['PRICE_IDX'] = val['index']
            idx_e['PRICE_UNITS'] = val['units']
        elif key == 'ashrae_uncomfortable_hours_avg':
            idx_e['ASHRAE_HOURS_IDX'] = val['index']
            idx_e['ASHRAE_HOURS_UNITS'] = val['units']
        elif key == 'cooling_schedule_temperature_avg':
            idx_e['COOLING_SCHEDULE_IDX'] = val['index']
            idx_e['COOLING_SCHEDULE_UNITS'] = val['units']
        elif key == 'cooling_setpoint_temperature_avg':
            idx_e['COOLING_SETPOINT_IDX'] = val['index']
            idx_e['COOLING_SETPOINT_UNITS'] = val['units']
        elif key == 'cooling_current_temperature_avg':
            idx_e['COOLING_TEMPERATURE_IDX'] = val['index']
            idx_e['COOLING_TEMPERATURE_UNITS'] = val['units']
        elif key == 'cooling_setpoint_delta_avg':
            idx_e['COOLING_DELTA_IDX'] = val['index']
            idx_e['COOLING_DELTA_UNITS'] = val['units']
        elif key == 'cooling_controlled_load_avg':
            idx_e['COOLING_POWER_IDX'] = val['index']
            idx_e['COOLING_POWER_UNITS'] = val['units']
        elif key == 'cooling_power_state_avg':
            idx_e['COOLING_STATE_IDX'] = val['index']
            idx_e['COOLING_STATE_UNITS'] = val['units']
        elif key == 'heating_schedule_temperature_avg':
            idx_e['HEATING_SCHEDULE_IDX'] = val['index']
            idx_e['HEATING_SCHEDULE_UNITS'] = val['units']
        elif key == 'heating_setpoint_temperature_avg':
            idx_e['HEATING_SETPOINT_IDX'] = val['index']
            idx_e['HEATING_SETPOINT_UNITS'] = val['units']
        elif key == 'heating_current_temperature_avg':
            idx_e['HEATING_TEMPERATURE_IDX'] = val['index']
            idx_e['HEATING_TEMPERATURE_UNITS'] = val['units']
        elif key == 'heating_setpoint_delta_avg':
            idx_e['HEATING_DELTA_IDX'] = val['index']
            idx_e['HEATING_DELTA_UNITS'] = val['units']
        elif key == 'heating_controlled_load_avg':
            idx_e['HEATING_POWER_IDX'] = val['index']
            idx_e['HEATING_POWER_UNITS'] = val['units']
        elif key == 'heating_power_state_avg':
            idx_e['HEATING_STATE_IDX'] = val['index']
            idx_e['HEATING_STATE_UNITS'] = val['units']
        elif key == 'outdoor_air_avg':
            idx_e['OUTDOOR_AIR_IDX'] = val['index']
            idx_e['OUTDOOR_AIR_UNITS'] = val['units']
        elif key == 'indoor_air_avg':
            idx_e['INDOOR_AIR_IDX'] = val['index']
            idx_e['INDOOR_AIR_UNITS'] = val['units']
        elif key == 'heating_volume_avg':
            idx_e['HEATING_VOLUME_IDX'] = val['index']
            idx_e['HEATING_VOLUME_UNITS'] = val['units']
        elif key == 'cooling_volume_avg':
            idx_e['COOLING_VOLUME_IDX'] = val['index']
            idx_e['COOLING_VOLUME_UNITS'] = val['units']
        elif key == 'offer_kw_avg':
            idx_e['OFFER_KW_IDX'] = val['index']
            idx_e['OFFER_KW_UNITS'] = val['units']
        elif key == 'offer_cleared_price_avg':
            idx_e['OFFER_CLEARED_PRICE_IDX'] = val['index']
            idx_e['OFFER_CLEARED_PRICE_UNITS'] = val['units']
        elif key == 'offer_cleared_kw_avg':
            idx_e['OFFER_CLEARED_KW_IDX'] = val['index']
            idx_e['OFFER_CLEARED_KW_UNITS'] = val['units']
        elif key == 'offer_cleared_degF_avg':
            idx_e['OFFER_CLEARED_DEGF_IDX'] = val['index']
            idx_e['OFFER_CLEARED_DEGF_UNITS'] = val['units']

    # make sure we found the metric indices of interest
    building = list(lst['3600'].keys())[0]
    ary = lst['3600'][building]
    if not quiet:
        print('There are', len(ary), 'metrics for', building)
        print('1st hour price =', ary[idx_e['PRICE_IDX']], idx_e['PRICE_UNITS'])

    # create a NumPy array of all metrics for the first building, 8760*39 doubles
    # we also want a NumPy array of times in hours
    data = np.empty(shape=(len(times), len(ary)), dtype=np.float)
    if not quiet:
        print('Constructed', data.shape, 'NumPy array')
    i = 0
    for t in times:
        ary = lst[str(t)][building]
        data[i, :] = ary
        i = i + 1
    hrs = np.array(times, dtype=np.float)
    denom = 3600.0
    hrs /= denom

    # display some averages
    if not quiet:
        print('Average price  = {:.5f}'.format(data[:, idx_e['PRICE_IDX']].mean()), idx_e['PRICE_UNITS'])
        print('Average demand = {:.2f}'.format(data[:, idx_e['ELECTRIC_DEMAND_IDX']].mean()),
              idx_e['ELECTRIC_DEMAND_UNITS'])
        print('Average HVAC   = {:.2f}'.format(data[:, idx_e['HVAC_DEMAND_IDX']].mean()), idx_e['HVAC_DEMAND_UNITS'])
        print('Average uncomf = {:.5f}'.format(data[:, idx_e['ASHRAE_HOURS_IDX']].mean()), idx_e['ASHRAE_HOURS_UNITS'])
        print('Average people = {:.2f}'.format(data[:, idx_e['OCCUPANTS_IDX']].mean()), idx_e['OCCUPANTS_UNITS'])

        print('Average cooling power = {:9.2f}'.format(data[:, idx_e['COOLING_POWER_IDX']].mean()),
              idx_e['COOLING_POWER_UNITS'])
        print('Average cooling temp  = {:9.2f}'.format(data[:, idx_e['COOLING_TEMPERATURE_IDX']].mean()),
              idx_e['COOLING_TEMPERATURE_UNITS'])
        print('Average cooling sched = {:9.2f}'.format(data[:, idx_e['COOLING_SCHEDULE_IDX']].mean()),
              idx_e['COOLING_SCHEDULE_UNITS'])
        print('Average cooling delta = {:9.2f}'.format(data[:, idx_e['COOLING_DELTA_IDX']].mean()),
              idx_e['COOLING_DELTA_UNITS'])
        print('Average cooling setpt = {:9.2f}'.format(data[:, idx_e['COOLING_SETPOINT_IDX']].mean()),
              idx_e['COOLING_SETPOINT_UNITS'])
        print('Average cooling vol   = {:9.2f}'.format(data[:, idx_e['COOLING_VOLUME_IDX']].mean()),
              idx_e['COOLING_VOLUME_UNITS'])

        print('Average heating power = {:9.2f}'.format(data[:, idx_e['HEATING_POWER_IDX']].mean()),
              idx_e['HEATING_POWER_UNITS'])
        print('Average heating temp  = {:9.2f}'.format(data[:, idx_e['HEATING_TEMPERATURE_IDX']].mean()),
              idx_e['HEATING_TEMPERATURE_UNITS'])
        print('Average heating sched = {:9.2f}'.format(data[:, idx_e['HEATING_SCHEDULE_IDX']].mean()),
              idx_e['HEATING_SCHEDULE_UNITS'])
        print('Average heating delta = {:9.2f}'.format(data[:, idx_e['HEATING_DELTA_IDX']].mean()),
              idx_e['HEATING_DELTA_UNITS'])
        print('Average heating setpt = {:9.2f}'.format(data[:, idx_e['HEATING_SETPOINT_IDX']].mean()),
              idx_e['HEATING_SETPOINT_UNITS'])
        print('Average heating vol   = {:9.2f}'.format(data[:, idx_e['HEATING_VOLUME_IDX']].mean()),
              idx_e['HEATING_VOLUME_UNITS'])

        print('Average outdoor air   = {:9.2f}'.format(data[:, idx_e['OUTDOOR_AIR_IDX']].mean()),
              idx_e['OUTDOOR_AIR_UNITS'])
        print('Average indoor air    = {:9.2f}'.format(data[:, idx_e['INDOOR_AIR_IDX']].mean()),
              idx_e['INDOOR_AIR_UNITS'])

        if ('OFFER_KW_IDX' in idx_e) and ('OFFER_CLEARED_KW_IDX' in idx_e) and ('OFFER_CLEARED_DEGF_IDX' in idx_e) and (
                'OFFER_CLEARED_PRICE_IDX' in idx_e):
            print('Consensus Market     Mean       Max')
            print('   Offer kW     {:9.2f} {:9.2f}'.format(data[:, idx_e['OFFER_KW_IDX']].mean(),
                                                           np.amax(data[:, idx_e['OFFER_KW_IDX']])))
            print('   Local kW     {:9.2f} {:9.2f}'.format(abs(data[:, idx_e['OFFER_CLEARED_KW_IDX']].mean()),
                                                           np.amax(np.abs(data[:, idx_e['OFFER_CLEARED_KW_IDX']]))))
            print('   Local dDegF  {:9.2f} {:9.2f}'.format(data[:, idx_e['OFFER_CLEARED_DEGF_IDX']].mean(),
                                                           np.amax(data[:, idx_e['OFFER_CLEARED_DEGF_IDX']])))
            print('   Clear Price  {:9.2f} {:9.2f}'.format(data[:, idx_e['OFFER_CLEARED_PRICE_IDX']].mean(),
                                                           np.amax(data[:, idx_e['OFFER_CLEARED_PRICE_IDX']])))

    # limit out-of-range initial values
    np.clip(data[:, idx_e['COOLING_TEMPERATURE_IDX']], 0, 100, data[:, idx_e['COOLING_TEMPERATURE_IDX']])
    np.clip(data[:, idx_e['COOLING_SETPOINT_IDX']], 0, 100, data[:, idx_e['COOLING_SETPOINT_IDX']])
    np.clip(data[:, idx_e['COOLING_SCHEDULE_IDX']], 0, 100, data[:, idx_e['COOLING_SCHEDULE_IDX']])
    np.clip(data[:, idx_e['HEATING_TEMPERATURE_IDX']], 0, 100, data[:, idx_e['HEATING_TEMPERATURE_IDX']])
    np.clip(data[:, idx_e['HEATING_SETPOINT_IDX']], 0, 100, data[:, idx_e['HEATING_SETPOINT_IDX']])
    np.clip(data[:, idx_e['HEATING_SCHEDULE_IDX']], 0, 100, data[:, idx_e['HEATING_SCHEDULE_IDX']])

    return {
        'hrs': hrs,
        'data_e': data,
        'idx_e': idx_e
    }


def plot_eplus(diction, title=None, save_file=None, save_only=False):
    hrs = diction['hrs']
    data = diction['data_e']
    idx_e = diction['idx_e']
    ncols = 3
    bConsensus = False

    if ('OFFER_KW_IDX' in idx_e) and ('OFFER_CLEARED_KW_IDX' in idx_e) and ('OFFER_CLEARED_DEGF_IDX' in idx_e) and (
            'OFFER_CLEARED_PRICE_IDX' in idx_e):
        bConsensus = True
        ncols += 1

    # display a plot
    width = 12.0
    height = 8.0
    fig, ax = plt.subplots(3, ncols, sharex='col', figsize=(width, height), constrained_layout=True)
    if title is not None:
        fig.suptitle(title)

    ax[0, 0].plot(hrs, data[:, idx_e['COOLING_TEMPERATURE_IDX']], color='blue', label='Actual')
    ax[0, 0].plot(hrs, data[:, idx_e['COOLING_SETPOINT_IDX']], color='red', label='Setpoint')
    ax[0, 0].plot(hrs, data[:, idx_e['COOLING_SCHEDULE_IDX']], color='green', label='Schedule')
    #    ax[0,0].plot(hrs, data[:,idx_e['INDOOR_AIR_IDX']], color='magenta', label='Indoor')
    ax[0, 0].set_ylabel(idx_e['COOLING_TEMPERATURE_UNITS'])
    ax[0, 0].set_title('Volume Average Cooling')
    ax[0, 0].legend(loc='best')

    ax[1, 0].plot(hrs, data[:, idx_e['HEATING_TEMPERATURE_IDX']], color='blue', label='Actual')
    ax[1, 0].plot(hrs, data[:, idx_e['HEATING_SETPOINT_IDX']], color='red', label='Setpoint')
    ax[1, 0].plot(hrs, data[:, idx_e['HEATING_SCHEDULE_IDX']], color='green', label='Schedule')
    #    ax[1,0].plot(hrs, data[:,idx_e['INDOOR_AIR_IDX']], color='magenta', label='Indoor')
    ax[1, 0].set_ylabel(idx_e['HEATING_TEMPERATURE_UNITS'])
    ax[1, 0].set_title('Volume Average Heating')
    ax[1, 0].legend(loc='best')

    ax[2, 0].plot(hrs, data[:, idx_e['OUTDOOR_AIR_IDX']], color='blue', label='Outdoor')
    ax[2, 0].plot(hrs, data[:, idx_e['INDOOR_AIR_IDX']], color='red', label='Indoor')
    ax[2, 0].set_ylabel(idx_e['OUTDOOR_AIR_UNITS'])
    ax[2, 0].set_title('Average Temperatures')
    ax[2, 0].legend(loc='best')

    ax[0, 1].plot(hrs, data[:, idx_e['PRICE_IDX']], color='blue', label='Actual')
    ax[0, 1].set_ylabel(idx_e['PRICE_UNITS'])
    ax[0, 1].set_title('Real-time Price')

    ax[1, 1].plot(hrs, 0.001 * data[:, idx_e['ELECTRIC_DEMAND_IDX']], color='blue', label='Total')
    ax[1, 1].plot(hrs, 0.001 * data[:, idx_e['HVAC_DEMAND_IDX']], color='red', label='HVAC')
    ax[1, 1].set_ylabel('kW')
    ax[1, 1].set_title('Building Electrical Demand')
    ax[1, 1].legend(loc='best')

    #    ax[2,1].plot(hrs, data[:,idx_e['COOLING_DELTA_IDX']], color='blue', label='Cooling')
    #    ax[2,1].plot(hrs, data[:,idx_e['HEATING_DELTA_IDX']], color='red', label='Heating')
    #    ax[2,1].set_ylabel(idx_e['HEATING_STATE_UNITS'])
    ax[2, 1].plot(hrs, 0.001 * data[:, idx_e['COOLING_POWER_IDX']], color='blue', label='Cooling')
    ax[2, 1].plot(hrs, 0.001 * data[:, idx_e['HEATING_POWER_IDX']], color='red', label='Heating')
    ax[2, 1].plot(hrs, 0.001 * data[:, idx_e['HVAC_DEMAND_IDX']], color='green', label='HVAC')
    ax[2, 1].set_ylabel('kW')
    ax[2, 1].set_title('DX/Electrical Coil Demand')
    ax[2, 1].legend(loc='best')

    ax[0, 2].plot(hrs, data[:, idx_e['OCCUPANTS_IDX']], color='blue')
    ax[0, 2].set_ylabel(idx_e['OCCUPANTS_UNITS'])
    ax[0, 2].set_title('Occupants')

    ax[1, 2].plot(hrs, data[:, idx_e['ASHRAE_HOURS_IDX']], color='blue')
    ax[1, 2].set_ylabel(idx_e['ASHRAE_HOURS_UNITS'])
    ax[1, 2].set_title('Uncomfortable Hours')

    ax[2, 2].plot(hrs, 0.001 * data[:, idx_e['HEATING_VOLUME_IDX']] + 0.001 * data[:, idx_e['COOLING_VOLUME_IDX']],
                  color='magenta', label='Total')
    ax[2, 2].plot(hrs, 0.001 * data[:, idx_e['COOLING_VOLUME_IDX']], color='blue', label='Cooling')
    ax[2, 2].plot(hrs, 0.001 * data[:, idx_e['HEATING_VOLUME_IDX']], color='red', label='Heating')
    ax[2, 2].set_ylabel('thousand m^3')
    ax[2, 2].set_title('Sensible Zone Volumes')
    ax[2, 2].legend(loc='best')

    if bConsensus:
        ax[0, 3].set_title('Consensus Price')
        ax[0, 3].plot(hrs, data[:, idx_e['OFFER_CLEARED_PRICE_IDX']])
        ax[0, 3].set_ylabel(idx_e['OFFER_CLEARED_PRICE_UNITS'])

        ax[1, 3].set_title('Consensus Loads')
        ax[1, 3].plot(hrs, data[:, idx_e['OFFER_KW_IDX']], color='red', label='Supply Offer')
        ax[1, 3].plot(hrs, np.abs(data[:, idx_e['OFFER_CLEARED_KW_IDX']]), color='blue', label='Local Cleared')
        ax[1, 3].set_ylabel(idx_e['OFFER_KW_UNITS'])
        ax[1, 3].legend(loc='best')

        ax[2, 3].set_title('Consensus Thermostat')
        ax[2, 3].plot(hrs, data[:, idx_e['OFFER_CLEARED_DEGF_IDX']])
        ax[2, 3].set_ylabel(idx_e['OFFER_CLEARED_DEGF_UNITS'])

    for i in range(ncols):
        ax[2, i].set_xlabel('Hours')

    if save_file is not None:
        plt.savefig(save_file)
    if not save_only:
        plt.show()


def process_eplus(name_root, title=None, save_file=None, save_only=False):
    """ Plots the min and max line-neutral voltages for every billing meter

    This function reads *eplus_[name_root]_metrics.json* for both metadata and data.
    This must exist in the current working directory.
    One graph is generated with 3 subplots:

    1. Cooling system setpoint, actual temperature and the difference between them.
    2. Heating system setpoint, actual temperature and the difference between them.
    3. Price that the building controller responded to.

    Args:
        name_root (str): name of the TESP case, not necessarily the same as the EnergyPlus case, without the extension
        title (str): supertitle for the page of plots.
        save_file (str): name of a file to save plot, should include the *png* or *pdf* extension to determine type.
        save_only (Boolean): set True with *save_file* to skip the display of the plot. Otherwise, script waits for user keypress.
    """
    path = os.getcwd()
    diction = read_eplus_metrics(path, name_root)
    plot_eplus(diction, title, save_file, save_only)
