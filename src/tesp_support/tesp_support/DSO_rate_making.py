# -*- coding: utf-8 -*-

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: DSO_rate_making.py
"""
@author: reev057
"""
import json
import os
import sys
from os.path import dirname, abspath

import pandas as pd

sys.path.insert(0, dirname(abspath(__file__)))

from .DSOT_plots import load_da_retail_price, customer_meta_data, load_json, load_agent_data, \
    load_system_data, get_date, tic, toc, load_retail_data, load_ames_data, load_gen_data, load_indust_data


def read_meters(metadata, dir_path, folder_prefix, dso_num, day_range, SF, dso_data_path):
    """Determines the total energy consumed and max power consumption for all meters within a DSO for a series of days.
    Also collects information on day ahead and real time quantities consumed by transactive customers.
    Creates summation of these statistics by customer class.
    Arguments:
        metadata (dict): metadata structure for the DSO to be analyzed
        dir_path (str): directory path for the case to be analyzed
        folder_prefix (str): prefix of GLD folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
        day_range (list): range of days to be summed (for example a month).
        SF (float): Scaling factor to scale GLD results to TSO scale (e.g. 1743)
    Returns:
        meter_df: dataframe of energy consumption and max 15 minute power consumption for each month and total
        energysum_df: dataframe of energy consumption summations by customer class (residential, commercial, and industial)
        saves the two dataframe above to an h5 file in the dir_path
        """
    # Load in bulk industrial loads
    case_config = load_json(dir_path, 'generate_case_config.json')
    industrial_file = os.path.join(dso_data_path, case_config['indLoad'][5].split('/')[-1])
    indust_df = load_indust_data(industrial_file, day_range)

    # Create empty dataframe structure for all meters.
    meter = []
    variable = []
    month = []

    for each in metadata['billingmeters']:
        meter.append(each)
        variable.append('kw-hr')
        month.append(0)
        meter.append(each)
        variable.append('max_kw')
        month.append(0)
        meter.append(each)
        variable.append('avg_load')
        month.append(0)
        meter.append(each)
        variable.append('load_factor')
        month.append(0)

    meter_df = pd.DataFrame(month,
                            index=[meter, variable],
                            columns=['sum'])

    # Create dataframe for transactive customer data.
    trans = []
    variable = []
    month = []

    for each in metadata['billingmeters']:
        if metadata['billingmeters'][each]['cust_participating']:
            trans.append(each)
            variable.append('DA_Q')
            month.append(0)
            trans.append(each)
            variable.append('DA_cost')
            month.append(0)
            trans.append(each)
            variable.append('RT_Q')
            month.append(0)
            trans.append(each)
            variable.append('RT_cost')
            month.append(0)
            trans.append(each)
            variable.append('Congestion_Q')
            month.append(0)
            trans.append(each)
            variable.append('Congestion_cost')
            month.append(0)

    trans_df = pd.DataFrame(month,
                            index=[trans, variable],
                            columns=['sum'])

    # Create empty dataframe structure for total energy summation
    month = []
    variable = []
    loads = []
    loadtype = ['residential', 'commercial', 'industrial', 'total']

    for each in loadtype:
        loads.append(each)
        variable.append('kw-hr')
        month.append(0)
        loads.append(each)
        variable.append('demand_quantity')
        month.append(0)
        loads.append(each)
        variable.append('da_q')
        month.append(0)
        loads.append(each)
        variable.append('rt_q')
        month.append(0)
        loads.append(each)
        variable.append('congest_$')
        month.append(0)
        loads.append(each)
        variable.append('congest_q')
        month.append(0)
        if each == 'total':
            loads.append(each)
            variable.append('dist_loss_$')
            month.append(0)
            loads.append(each)
            variable.append('dist_loss_q')
            month.append(0)

    energysum_df = pd.DataFrame(month,
                                index=[loads, variable],
                                columns=['sum'])

    # load meter data for each day
    for day in day_range:
        # Label columns of data frame by actual calendar date (not simulation day)
        date = get_date(dir_path, dso_num, str(day))
        day_name = date.strftime("%m-%d")
        meter_df[day_name] = [0] * len(meter_df)
        trans_df[day_name] = [0] * len(trans_df)
        energysum_df[day_name] = [0] * len(energysum_df)

        # Load in transactive customer Q data, real-time price data, and DA cleared price
        filename = dir_path + '/DSO_' + dso_num + '/Retail_Quantities.h5'
        cust_trans_df = pd.read_hdf(filename, key='/index' + str(day), mode='r')
        # DSO agent retail values are used for congestion and AMES price LMPs used for quantity billing.
        RT_price_df = load_ames_data(dir_path, range(int(day), int(day) + 1))
        RT_retail_df, RT_bid_df = load_agent_data(dir_path, '/DSO_', dso_num, str(day), 'retail_market')
        RT_retail_df = RT_retail_df.droplevel(level=1)
        DA_price_df = load_gen_data(dir_path, 'da_lmp', range(int(day), int(day) + 1))
        DA_price_df = DA_price_df.unstack(level=1)
        DA_price_df.columns = DA_price_df.columns.droplevel()
        DA_retail_df = load_da_retail_price(dir_path, '/DSO_', dso_num, str(day))
        # Load meter data
        substation_meta_df, substation_data_df = load_system_data(dir_path, folder_prefix, dso_num, str(day),
                                                                  'substation')
        substation_data_df = substation_data_df.set_index(['time'])
        meter_meta_df, meter_data_df = load_system_data(dir_path, folder_prefix, dso_num, str(day), 'billing_meter')
        meter_data_df['date'] = pd.to_datetime(meter_data_df['date'], infer_datetime_format=True)
        # meter_data_df['date'] = meter_data_df['date'].apply(pd.to_datetime(infer_datetime_format=True))
        meter_data_df = meter_data_df.set_index(['time', 'name'])
        for each in metadata['billingmeters']:
            # Calculate standard customer energy consumption metrics used for all customers (including baseline)
            # temp = meter_data_df[meter_data_df['name'].str.contains(each)]
            temp = meter_data_df.xs(each, level=1)[['real_power_avg', 'date']]
            meter_df.loc[(each, 'kw-hr'), day_name] = temp.loc[:, 'real_power_avg'].sum() / 1000 / 12
            meter_df.loc[(each, 'avg_load'), day_name] = temp.loc[:, 'real_power_avg'].mean() / 1000
            # TODO: changed from fixed window to moving window.  Need to check if this is OK.
            # find average max power over a 15 minute moving window (=3 * 5 minute intervals).
            windowsize = 3
            max_kw = temp['real_power_avg'].rolling(window=windowsize).mean().max() / 1000
            meter_df.loc[(each, 'max_kw'), day_name] = max(meter_df.loc[(each, 'max_kw'), day_name], max_kw)
            if meter_df.loc[(each, 'max_kw'), day_name] != 0:
                meter_df.loc[(each, 'load_factor'), day_name] = meter_df.loc[(each, 'avg_load'), day_name] / \
                                                                meter_df.loc[(each, 'max_kw'), day_name]
            else:
                meter_df.loc[(each, 'load_factor'), day_name] = 0
            # Calculate transactive customer energy consumption metrics
            if metadata['billingmeters'][each]['cust_participating']:
                temp2 = cust_trans_df[cust_trans_df.meter == each]
                trans_df.loc[(each, 'DA_Q'), day_name] = temp2.loc[:, 'total_cleared_quantity'].sum()
                trans_df.loc[(each, 'RT_Q'), day_name] = meter_df.loc[(each, 'kw-hr'), day_name] - \
                                                         trans_df.loc[(each, 'DA_Q'), day_name]
                # TODO:  Need to interpolate day ahead Q to make RT summation every
                #  5 minutes rather than one hour average
                RTonehour = temp.set_index('date').resample('H').mean() / 1000
                RThourprice = RT_price_df[' LMP' + dso_num].resample('H').mean() / 1000
                RThourcongestionprice = RT_retail_df['congestion_surcharge_RT'].resample('H').mean() / 1000
                RThourcleartype = RT_retail_df['clear_type_rt'].resample('H').mean() / 1000
                # test = temp2.resample('5min').ffill()
                trans_df.loc[(each, 'DA_cost'), day_name] = (temp2['total_cleared_quantity'] *
                                                             DA_price_df['da_lmp' + dso_num] / 1000).sum()
                Real_time_purchase = (RTonehour['real_power_avg'] - temp2['total_cleared_quantity']) * RThourprice
                trans_df.loc[(each, 'RT_cost'), day_name] = Real_time_purchase.sum()
                #  Calculate Congestion Quantities and costs for each customer
                trans_df.loc[(each, 'Congestion_cost'), day_name] = (temp2['total_cleared_quantity'] *
                                                                     DA_retail_df['congestion_surcharge_DA']).sum() + \
                                                                    ((RTonehour['real_power_avg'] - temp2[
                                                                        'total_cleared_quantity']) * RThourcongestionprice).sum()
                # TODO: Need to check or verify that clear_type is never 2 or 3 (inefficient or failure)...
                trans_df.loc[(each, 'Congestion_Q'), day_name] = (temp2['total_cleared_quantity'] *
                                                                  DA_retail_df['clear_type_da']).sum() + \
                                                                 ((RTonehour['real_power_avg'] - temp2[
                                                                     'total_cleared_quantity']) * RThourcleartype).sum()

        # Calculate total energy consumption for each customer class (aka load type)
        for each in metadata['billingmeters']:
            for load in loadtype:
                if metadata['billingmeters'][each]['tariff_class'] == load:
                    energysum_df.loc[(load, 'kw-hr'), day_name] += meter_df.loc[(each, 'kw-hr'), day_name] * SF
                    if metadata['billingmeters'][each]['cust_participating']:
                        energysum_df.loc[(load, 'da_q'), day_name] += trans_df.loc[(each, 'DA_Q'), day_name] * SF
                        energysum_df.loc[(load, 'rt_q'), day_name] += trans_df.loc[(each, 'RT_Q'), day_name] * SF
                        energysum_df.loc[(load, 'congest_$'), day_name] += trans_df.loc[
                                                                               (each, 'Congestion_Q'), day_name] * SF
                        energysum_df.loc[(load, 'congest_q'), day_name] += trans_df.loc[
                                                                               (each, 'Congestion_cost'), day_name] * SF
                    else:
                        energysum_df.loc[(load, 'demand_quantity'), day_name] += meter_df.loc[
                                                                                     (each, 'max_kw'), day_name] * SF
        # Break the street lights out into a separate catagory for reporting and verification purposes
        # energysum_df.loc[('street_lights', 'kw-hr'), :] = energysum_df.loc[('industrial', 'kw-hr'), :]
        # energysum_df.loc[('street_lights', 'max_kw'), :] = energysum_df.loc[('industrial', 'max_kw'), :]

        # Load in bulk industrial load for day in question:
        start_time = (day - 1) * 300 * 288
        end_time = start_time + 300 * 287
        # TODO: Need to verify MW-kW conversion?
        energysum_df.loc[('industrial', 'kw-hr'), day_name] += \
            indust_df.loc[start_time:end_time, 'Bus' + dso_num].sum() / 12 * 1000
        energysum_df.loc[('industrial', 'demand_quantity'), day_name] += \
            indust_df.loc[start_time:end_time, 'Bus' + dso_num].rolling(window=windowsize).mean().max() * 1000
        dso_losses = (substation_data_df['real_power_avg'] - meter_data_df['real_power_avg'].
                      groupby(level=0).sum()) / 1000 / 12 * SF
        energysum_df.loc[('total', 'dist_loss_$'), day_name] += (
                    dso_losses * RT_price_df[' LMP' + dso_num].values / 1000).sum()
        energysum_df.loc[('total', 'dist_loss_q'), day_name] += dso_losses.sum()

    # Create totals for energy metrics
    for item in ['kw-hr', 'demand_quantity', 'da_q', 'rt_q', 'congest_$', 'congest_q']:
        for load in ['residential', 'commercial', 'industrial']:
            energysum_df.loc[('total', item), :] += energysum_df.loc[(load, item), :]

    # Sum the total power consumption for all days
    meter_df.loc[(slice(None), 'kw-hr'), ['sum']] = \
        meter_df.loc[(slice(None), 'kw-hr'), meter_df.columns[not meter_df.columns.str.contains('sum')]].sum(axis=1)
    meter_df.loc[(slice(None), 'max_kw'), ['sum']] = \
        meter_df.loc[(slice(None), 'max_kw'), meter_df.columns[not meter_df.columns.str.contains('sum')]].max(axis=1)
    meter_df.loc[(slice(None), 'avg_load'), ['sum']] = \
        meter_df.loc[(slice(None), 'avg_load'), meter_df.columns[not meter_df.columns.str.contains('sum')]].mean(axis=1)

    for each in metadata['billingmeters']:
        if meter_df.loc[(each, 'max_kw'), 'sum'] != 0:
            meter_df.loc[(each, 'load_factor'), 'sum'] = meter_df.loc[(each, 'avg_load'), 'sum'] / \
                                                         meter_df.loc[(each, 'max_kw'), 'sum']
        else:
            meter_df.loc[(each, 'load_factor'), 'sum'] = 0

    trans_df.loc[:, ['sum']] = \
        trans_df.loc[:, trans_df.columns[not trans_df.columns.str.contains('sum')]].sum(axis=1)

    # Sum all days to create total for the month.
    energysum_df['sum'] = \
        energysum_df.loc[:, meter_df.columns[not meter_df.columns.str.contains('sum')]].sum(axis=1)
    # Need to correct demand quantity to be the max for the month and not the sum of each day of the month.
    energysum_df.loc[(slice(None), 'demand_quantity'), ['sum']] = \
        energysum_df.loc[(slice(None), 'demand_quantity'),
                         energysum_df.columns[not energysum_df.columns.str.contains('sum')]].max(axis=1)
    # Save summary data to h5 file in folder where meter data came from (dir_path)
    # os.chdir(dir_path + folder_prefix + dso_num)
    save_path = dir_path + folder_prefix + dso_num
    meter_df.to_hdf(save_path + '/energy_metrics_data.h5', key='energy_data')
    energysum_df.to_hdf(save_path + '/energy_metrics_data.h5', key='energy_sums')
    trans_df.to_hdf(save_path + '/transactive_metrics_data.h5', key='trans_data')

    return meter_df, energysum_df


def annual_energy(month_list, folder_prefix, dso_num, metadata):
    """Creates a dataframe of monthly energy consumption values and annual sum based on monthly h5 files.
    Arguments:
        month_list (list): list of lists.  Each sub list has month name (str), directory path (str)
        folder_prefix (str): prefix of GLD folder name (e.g. '/TE_base_s')
        dso_num (str): number of the DSO folder to be opened
        metadata (dict): metadata of GridLAB-D model entities
    Returns:
        year_meter_df: dataframe of energy consumption and max 15 minute power consumption for each month and total
        year_energysum_df: dataframe of energy consumption summations by customer class (res., commercial, and indust)
        """

    for i in range(len(month_list)):
        filename = (month_list[i][1] + folder_prefix + dso_num + '/energy_metrics_data.h5')
        trans_file = (month_list[i][1] + folder_prefix + dso_num + '/transactive_metrics_data.h5')
        meter_df = pd.read_hdf(filename, key='energy_data', mode='r')
        energysum_df = pd.read_hdf(filename, key='energy_sums', mode='r')
        trans_df = pd.read_hdf(trans_file, key='trans_data', mode='r')

        if i == 0:
            year_meter_df = meter_df[['sum']]
            year_meter_df = year_meter_df.rename(columns={'sum': month_list[i][0]})
            year_energysum_df = energysum_df[['sum']]
            year_energysum_df = year_energysum_df.rename(columns={'sum': month_list[i][0]})
            year_trans_sum_df = trans_df[['sum']]
            year_trans_sum_df = year_trans_sum_df.rename(columns={'sum': month_list[i][0]})
        else:
            year_meter_df[month_list[i][0]] = meter_df[['sum']]
            year_energysum_df[month_list[i][0]] = energysum_df[['sum']]
            year_trans_sum_df[month_list[i][0]] = trans_df[['sum']]

    year_meter_df['sum'] = year_meter_df.sum(axis=1)
    year_energysum_df['sum'] = year_energysum_df.sum(axis=1)
    year_trans_sum_df['sum'] = year_trans_sum_df.sum(axis=1)

    year_meter_df.loc[(slice(None), 'max_kw'), ['sum']] = \
        year_meter_df.loc[(slice(None), 'max_kw'),
                          year_meter_df.columns[not year_meter_df.columns.str.contains('sum')]].max(axis=1)
    year_meter_df.loc[(slice(None), 'avg_load'), ['sum']] = \
        year_meter_df.loc[(slice(None), 'avg_load'),
                          year_meter_df.columns[not year_meter_df.columns.str.contains('sum')]].mean(axis=1)
    for each in metadata['billingmeters']:
        if year_meter_df.loc[(each, 'max_kw'), 'sum'] != 0:
            year_meter_df.loc[(each, 'load_factor'), 'sum'] = \
                year_meter_df.loc[(each, 'avg_load'), 'sum'] / year_meter_df.loc[(each, 'max_kw'), 'sum']
        else:
            year_meter_df.loc[(each, 'load_factor'), 'sum'] = 0

    return year_meter_df, year_energysum_df, year_trans_sum_df


def calc_cust_bill(metadata, meter_df, trans_df, energy_sum_df, tariff, dso_num, SF, ind_cust):
    """Calculate the customer bill using summary meter data and fixed tariff structure.
    Arguments:
        metadata (dict): metadata structure for the DSO to be analyzed
        meter_df (dataframe): monthly and total energy consumption and peak power by house (meter)
        trans_df:
        energy_sum_df:
        tariff (dict): dictionary of fixed tariff structure
        dso_num:
        SF (float): Scaling factor to scale GLD results to TSO scale (e.g. 1743)
        ind_cust (int): number of industrial customers
    Returns:
        bill_df : dataframe of monthly and total bill for each house broken out by each element (energy, demand,
        connection, and total bill)
        """

    # Create empty dataframe structure for all bills for first month.
    meter = []
    variable = []
    month = []

    for each in metadata['billingmeters']:
        meter.append(each)
        variable.append('fix_energy')
        month.append(0)
        meter.append(each)
        variable.append('demand')
        month.append(0)
        meter.append(each)
        variable.append('fix_connect')
        month.append(0)
        meter.append(each)
        variable.append('fix_total')
        month.append(0)
        meter.append(each)
        variable.append('DA_energy')
        month.append(0)
        meter.append(each)
        variable.append('RT_energy')
        month.append(0)
        meter.append(each)
        variable.append('trans_connect')
        month.append(0)
        meter.append(each)
        variable.append('distribution')
        month.append(0)
        meter.append(each)
        variable.append('trans_total')
        month.append(0)
        meter.append(each)
        variable.append('quantity_purchased')
        month.append(0)
        meter.append(each)
        variable.append('blended_rate')
        month.append(0)

    bill_df = pd.DataFrame(month,
                           index=[meter, variable],
                           columns=['sum'])

    month = []
    variable = []
    loads = []
    loadtype = ['residential', 'commercial', 'industrial', 'total']

    for each in loadtype:
        loads.append(each)
        variable.append('fix_energy')
        month.append(0)
        loads.append(each)
        variable.append('demand')
        month.append(0)
        loads.append(each)
        variable.append('fix_connect')
        month.append(0)
        loads.append(each)
        variable.append('fix_total')
        month.append(0)
        loads.append(each)
        variable.append('fix_blended_rate')
        month.append(0)
        loads.append(each)
        variable.append('DA_energy')
        month.append(0)
        loads.append(each)
        variable.append('RT_energy')
        month.append(0)
        loads.append(each)
        variable.append('trans_connect')
        month.append(0)
        loads.append(each)
        variable.append('distribution')
        month.append(0)
        loads.append(each)
        variable.append('trans_total')
        month.append(0)
        loads.append(each)
        variable.append('trans_blended_rate')
        month.append(0)
        loads.append(each)
        variable.append('da_blended_rate')
        month.append(0)
        loads.append(each)
        variable.append('rt_blended_rate')
        month.append(0)

    billsum_df = pd.DataFrame(month,
                              index=[loads, variable],
                              columns=['sum'])

    # Set up dynamic (transactive) tariff structure
    flat = tariff['DSO_' + dso_num]['flat_rate']
    connection = tariff['DSO_' + dso_num]['base_connection_charge']
    trans_dist_rate = tariff['DSO_' + dso_num]['transactive_dist_rate']
    trans_connection = tariff['DSO_' + dso_num]['transactive_connection_charge']
    trans_retail_scale = tariff['DSO_' + dso_num]['transactive_LMP_multiplier']

    # Cycle through each month for which there is energy data and calculate customer bill
    months = list(meter_df.columns[not meter_df.columns.str.contains('sum')])

    for m in months:
        bill_df[m] = [0] * len(bill_df)
        billsum_df[m] = [0] * len(billsum_df)
        if energy_sum_df.loc[('total', 'da_q'), m] + energy_sum_df.loc[('total', 'rt_q'), m] == 0:
            congestion_rebate = 0
        else:
            congestion_rebate = energy_sum_df.loc[('total', 'congest_$'), m] / (
                    energy_sum_df.loc[('total', 'da_q'), m] + energy_sum_df.loc[('total', 'rt_q'), m])

        for each in metadata['billingmeters']:
            kw_hrs = meter_df.loc[(each, 'kw-hr'), m]
            max_kw = meter_df.loc[(each, 'max_kw'), m]

            if metadata['billingmeters'][each]['cust_participating']:
                # Calculate bill for transactive customer
                bill_df.loc[(each, 'DA_energy'), m] = trans_df.loc[(each, 'DA_cost'), m] * trans_retail_scale
                bill_df.loc[(each, 'RT_energy'), m] = trans_df.loc[(each, 'RT_cost'), m] * trans_retail_scale
                bill_df.loc[(each, 'trans_connect'), m] = trans_connection
                bill_df.loc[(each, 'distribution'), m] = \
                    meter_df.loc[(each, 'kw-hr'), m] * trans_dist_rate - congestion_rebate
                bill_df.loc[(each, 'trans_total'), m] = \
                    bill_df.loc[(each, 'DA_energy'), m] + bill_df.loc[(each, 'RT_energy'), m] + \
                    bill_df.loc[(each, 'trans_connect'), m] + bill_df.loc[(each, 'distribution'), m]
            else:
                # Calculate bill for baseline (non-participating) customer on fixed tariff structure
                tier2 = 0
                tier3 = 0
                tariff_class = metadata['billingmeters'][each]['tariff_class']
                T1P = tariff['DSO_' + dso_num][tariff_class]['tier_1']['price']
                T1Q = tariff['DSO_' + dso_num][tariff_class]['tier_1']['max_quantity']
                T2P = tariff['DSO_' + dso_num][tariff_class]['tier_2']['price']
                T2Q = tariff['DSO_' + dso_num][tariff_class]['tier_2']['max_quantity']
                demand = tariff['DSO_' + dso_num][tariff_class]['demand_charge']

                if kw_hrs >= T1Q:
                    tier2 = 1
                if kw_hrs >= T2Q:
                    tier3 = 1
                bill_df.loc[(each, 'fix_energy'), m] = \
                    flat * kw_hrs + T1P * tier2 * (kw_hrs - T1Q) + T2P * tier3 * (kw_hrs - T2Q)
                bill_df.loc[(each, 'demand'), m] = demand * max_kw
                # TODO: Need to fix connection charge for street lights (gets too expensive given how many there are).
                bill_df.loc[(each, 'fix_connect'), m] = connection
                bill_df.loc[(each, 'fix_total'), m] = \
                    bill_df.loc[(each, 'fix_energy'), m] + \
                    bill_df.loc[(each, 'demand'), m] + \
                    bill_df.loc[(each, 'fix_connect'), m]

            #  Calculated average electricity price (blended rate) for each customer
            if kw_hrs == 0:
                bill_df.loc[(each, 'blended_rate'), m] = 0
            else:
                bill_df.loc[(each, 'blended_rate'), m] = (bill_df.loc[(each, 'fix_total'), m] +
                                                          bill_df.loc[(each, 'trans_total'), m]) / kw_hrs

            bill_df.loc[(each, 'quantity_purchased'), m] = kw_hrs

            # Calculate total revenue for each customer class (aka load type)
        for each in metadata['billingmeters']:
            for load in loadtype:
                if metadata['billingmeters'][each]['tariff_class'] == load:
                    # Sum transactive values
                    billsum_df.loc[(load, 'DA_energy'), m] += bill_df.loc[(each, 'DA_energy'), m] * SF
                    billsum_df.loc[(load, 'RT_energy'), m] += bill_df.loc[(each, 'RT_energy'), m] * SF
                    billsum_df.loc[(load, 'trans_connect'), m] += bill_df.loc[(each, 'trans_connect'), m] * SF
                    billsum_df.loc[(load, 'distribution'), m] += bill_df.loc[(each, 'distribution'), m] * SF
                    billsum_df.loc[(load, 'trans_total'), m] += bill_df.loc[(each, 'trans_total'), m] * SF
                    # Sum non-partipating / base-case values
                    billsum_df.loc[(load, 'fix_energy'), m] += bill_df.loc[(each, 'fix_energy'), m] * SF
                    billsum_df.loc[(load, 'demand'), m] += bill_df.loc[(each, 'demand'), m] * SF
                    billsum_df.loc[(load, 'fix_connect'), m] += bill_df.loc[(each, 'fix_connect'), m] * SF
                    billsum_df.loc[(load, 'fix_total'), m] += bill_df.loc[(each, 'fix_total'), m] * SF

    # Calculate industrial load bill.  This lumps all industrial loads as one entity and surplants the any individual
    # industrial load bills calculated for individual GLD meters above.  This is OK as those meters are small zip loads
    # representing street lights.
    for m in months:
        # Calculate bill for baseline (non-participating) customer on fixed tariff structure
        tier2 = 0
        tier3 = 0
        tariff_class = 'industrial'
        T1P = tariff['DSO_' + dso_num][tariff_class]['tier_1']['price']
        T1Q = tariff['DSO_' + dso_num][tariff_class]['tier_1']['max_quantity']
        T2P = tariff['DSO_' + dso_num][tariff_class]['tier_2']['price']
        T2Q = tariff['DSO_' + dso_num][tariff_class]['tier_2']['max_quantity']
        demand = tariff['DSO_' + dso_num][tariff_class]['demand_charge']

        kw_hrs = energy_sum_df.loc[('industrial', 'kw-hr'), m]
        max_kw = energy_sum_df.loc[('industrial', 'demand_quantity'), m]
        if kw_hrs >= T1Q:
            tier2 = 1
        if kw_hrs >= T2Q:
            tier3 = 1
        billsum_df.loc[('industrial', 'fix_energy'), m] = \
            flat * kw_hrs + T1P * tier2 * (kw_hrs - T1Q) + T2P * tier3 * (kw_hrs - T2Q)
        billsum_df.loc[('industrial', 'demand'), m] = demand * max_kw
        billsum_df.loc[('industrial', 'fix_connect'), m] = connection * ind_cust
        billsum_df.loc[('industrial', 'fix_total'), m] = \
            billsum_df.loc[('industrial', 'fix_energy'), m] + \
            billsum_df.loc[('industrial', 'demand'), m] + \
            billsum_df.loc[('industrial', 'fix_connect'), m]

    # Calculate total values across all customer classes.
    for item in ['DA_energy', 'RT_energy', 'trans_connect', 'distribution', 'trans_total', 'fix_energy', 'demand',
                 'fix_connect', 'fix_total']:
        for load in ['residential', 'commercial', 'industrial']:
            billsum_df.loc[('total', item), :] += billsum_df.loc[(load, item), :]

    # Calculate the annual sum.
    bill_df['sum'] = bill_df.loc[:, bill_df.columns[not bill_df.columns.str.contains('sum')]].sum(axis=1)
    for each in metadata['billingmeters']:
        bill_df.loc[(each, 'blended_rate'), 'sum'] = (bill_df.loc[(each, 'fix_total'), 'sum'] +
                                                      bill_df.loc[(each, 'trans_total'), 'sum']) / bill_df.loc[
                                                         (each, 'quantity_purchased'), 'sum']
    billsum_df['sum'] = billsum_df.loc[:, billsum_df.columns[not billsum_df.columns.str.contains('sum')]].sum(
        axis=1)

    #  Calculated average electricity price (blended rate) for each customer class and purchase type
    for load in ['residential', 'commercial', 'industrial', 'total']:
        fixed_energy_q = energy_sum_df.loc[(load, 'kw-hr')] - energy_sum_df.loc[(load, 'da_q')] \
                         - energy_sum_df.loc[(load, 'rt_q')]
        billsum_df.loc[(load, 'fix_blended_rate')] = billsum_df.loc[(load, 'fix_total')] / fixed_energy_q
        # Find fraction of day ahead energy to proportion distribution and connection costs.
        da_fraction = energy_sum_df.loc[(load, 'da_q')] / (
                    energy_sum_df.loc[(load, 'da_q')] + energy_sum_df.loc[(load, 'rt_q')])
        billsum_df.loc[(load, 'da_blended_rate')] = (billsum_df.loc[(load, 'DA_energy')] + da_fraction *
                                                     (billsum_df.loc[(load, 'trans_connect')] +
                                                      billsum_df.loc[(load, 'distribution')])) / energy_sum_df.loc[
                                                        (load, 'da_q')]
        billsum_df.loc[(load, 'rt_blended_rate')] = (billsum_df.loc[(load, 'RT_energy')] + (1 - da_fraction) *
                                                     (billsum_df.loc[(load, 'trans_connect')] +
                                                      billsum_df.loc[(load, 'distribution')])) / energy_sum_df.loc[
                                                        (load, 'rt_q')]
        billsum_df.loc[(load, 'trans_blended_rate')] = billsum_df.loc[(load, 'trans_total')] / \
                                                       (energy_sum_df.loc[(load, 'da_q')] + energy_sum_df.loc[
                                                           (load, 'rt_q')])

    return bill_df, billsum_df


# def calc_te_bill(metadata, meter_df, tariff):
    # """Calculate the customer bill using realtime meter and agent bid data and transactive tariff structure.
    # Arguments:
    #     metadata (dict): metadata structure for the DSO to be analyzed
    #     meter_df (dataframe): monthly and total energy consumption and peak power by house (meter)
    #     tariff (dict): dictionary of fixed tariff structure
    # Returns:
    #     bill_df : dataframe of monthly and total bill for each house broken out by each element (energy, demand,
    #     connection, and total bill)
    #     """
    # Customer participation:
    # Need to determine if a customer is participating in transactive program or not
    # If not then their bill is calculated using the baseline equations and tariffs (I assume that is not safe to assume
    # that I can just pull the baseline values.  Better to recalculate)
    # Need to recalculate change in flat tariff for fixed customers similiar to baseline case.

    # Need to calculate the DA and Realtime price structure
    # DA price structure is:
    # DAP = A_da + LMP_da / 1000 + DMP_da + D + Delta_D
    # A_da = day ahead multiplier from tariff dictionary
    # LMP_da is the cleared price determined at 10 am as found in the dso_market 86400 file?
    # DMP_da = Retail_rate_da - LMP_da
    # D comes from tariff (needs to be assumed and then calculated to true up revenue).
    # Delta_D = to be determined peanut buttering of DMP_da charges as rebate.  Over year sum of DMP and Delta_D
    # should offset.  Offset should only go to folks on the feeder/substation affected.

    # RT price structure is:
    # RTP = A_rt + LMP_rt / 1000 + DMP_rt + D + Delta_D +Risk
    # A_rt = day ahead multiplier from tariff dictionary
    # LMP_rt is the realtime price as found in the dso_market 300 file?
    # DMP_rt = Retail_rate_da - LMP_da
    # Retail_rate_rt comes from price in the retail_market 300 file??
    # D comes from tariff (needs to be assumed and then calculated to true up revenue).
    # Delta_D = to be determined peanut buttering of DMP_rt charges as rebate to transactive customers.
    #           Over year sum of DMP and Delta_D
    # should offset
    # Risk = ????? average flat risk premium [$/kWh] for customers not making binding bids in day-ahead market.
    #   Will be set in tariff dictionary.  Since it is flat it will not affect agent behavior.

    # Calculation of DA and RT energy consumption at each 5 minute interval:
    # Q_da = sum of each agents day ahead commitment at 10 am.  Where does this come from ???????????
    # ###^^^^^ are these values hourly or 5 minute?
    # Q_rt = Meter_rt - Q_da

    # Calculation of energy bill:
    # for each day (then summing each day per month)
    # RTC =  RTP * Q_rt (product sum for the day)
    # DAC = DAP * Q_da (product sum for the day)
    # Flat_Charge = Q_total * D
    # Connection charge
    # Flat rebate = rebate to all on substation of congestion charge (do rebate retroactively monthly)
    # bill = RTC + DAC + Flat_C + Connection - Rebate
    # bill_2 = bill corrected with new flat rate for all rate payers on DSO to square up revenue with expenses.

    # data structure:
    # Energy:
    # energy bought DA
    # energy bought RT
    # peak power consumption (15 minute) for comparison to baseline
    # bill:
    # DA energy cost
    # DA congestion charge
    # RT energy cost
    # RT congestion charge
    # rebate charge
    # Flat energy charge
    # Connection Charge


def DSO_rate_making(case, dso_num, metadata, dso_expenses, tariff_path, dso_scaling_factor, num_indust_cust):
    """Main function to call for calculating the customer energy consumption, monthly bills, and tariff adjustments to
    ensure revenue matches expenses.  Saves meter and bill dataframes to an hdf5 file.
    Arguments:
        case (str): directory path for the case to be analyzed
        dso_num (str): number of the DSO folder to be opened
        metadata:
        dso_expenses (TBD): dso expenses that need to be matched by customer revenue
        tariff_path:
        dso_scaling factor (float): multiplier on customer bills to reflect the total number of customers in the DSO
        num_indust_cust (int): number of industrial customers
    Returns:
        meter_df : dataframe of energy consumption and max 15 minute power consumption for each month and total
        bill_df : dataframe of monthly and total bill for each house broken out by each element (energy, demand,
        connection, and total bill)
        tariff: Updated dictionary of tariff structure with rates adjusted to ensure revenue meets expenses
        surplus: dollar value difference between dso revenue and expenses.  When converged should be tiny (e.g 1e-12)
        """

    # Load Tariff structure:
    file_name = 'rate_case_inputs.json'
    tariff = load_json(tariff_path, file_name)
    # Load in transactive A values from simulation settings to ensure consistency
    default_config = load_json(tariff_path, 'default_case_config.json')
    for DSO in tariff:
        tariff[DSO]['transactive_LMP_multiplier'] = default_config['MarketPrep']['DSO']['dso_retail_scaling']

    energy_file = case + '/energy_dso_' + str(dso_num) + '_data.h5'
    trans_file = case + '/transactive_dso_' + str(dso_num) + '_data.h5'
    year_meter_df = pd.read_hdf(energy_file, key='energy_data', mode='r')
    year_energysum_df = pd.read_hdf(energy_file, key='energy_sums', mode='r')
    year_trans_df = pd.read_hdf(trans_file, key='trans_data', mode='r')

    #  Calculate data frame of month customer bills
    tic()
    cust_bill_df, billsum_df = calc_cust_bill(metadata, year_meter_df, year_trans_df, year_energysum_df, tariff,
                                              str(dso_num), dso_scaling_factor, num_indust_cust)
    toc()

    surplus = (billsum_df.loc[('total', 'fix_total'), 'sum'] + billsum_df.loc[
        ('total', 'trans_total'), 'sum']) - dso_expenses
    rebate = surplus / year_energysum_df.loc[('total', 'kw-hr'), 'sum']
    # TODO: Clean up implementation of iterate flag.
    iterate = True
    if iterate:
        tariff['DSO_' + str(dso_num)]['flat_rate'] = tariff['DSO_' + str(dso_num)]['flat_rate'] - rebate

        cust_bill_df, billsum_df = calc_cust_bill(metadata, year_meter_df, year_trans_df, year_energysum_df, tariff,
                                                  str(dso_num), dso_scaling_factor, num_indust_cust)

        surplus = (billsum_df.loc[('total', 'fix_total'), 'sum'] + billsum_df.loc[
            ('total', 'trans_total'), 'sum']) - dso_expenses
        rebate = surplus / year_energysum_df.loc[('total', 'kw-hr'), 'sum']

    # Need to save files to hdf5 format.
    os.chdir(case)
    cust_bill_df.to_hdf('bill_dso_' + str(dso_num) + '_data.h5', key='cust_bill_data')
    billsum_df.to_hdf('bill_dso_' + str(dso_num) + '_data.h5', key='bill_sum_data')
    cust_bill_df.to_csv(path_or_buf=case + '/cust_bill_dso_' + str(dso_num) + '_data.csv')
    billsum_df.to_csv(path_or_buf=case + '/billsum_dso_' + str(dso_num) + '_data.csv')

    with open(os.path.join(tariff_path, 'rate_case_outputs.json'), 'w') as out_file:
        json.dump(tariff, out_file)

    # Calculate congestion averages and catch for zero values
    if year_energysum_df.loc[('residential', 'congest_q'), 'sum'] == 0:
        TransactiveCongestAvgPriceRes = 0
    else:
        TransactiveCongestAvgPriceRes = (year_energysum_df.loc[('residential', 'congest_$'), 'sum'] /
                                         year_energysum_df.loc[('residential', 'congest_q'), 'sum'])  # $/kW-hr
    if year_energysum_df.loc[('commercial', 'congest_q'), 'sum'] == 0:
        TransactiveCongestAvgPriceComm = 0
    else:
        TransactiveCongestAvgPriceComm = (
                    year_energysum_df.loc[('commercial', 'congest_$'), 'sum'] / year_energysum_df.loc[
                ('commercial', 'congest_q'), 'sum'])  # $/kW-hr
    if year_energysum_df.loc[('industrial', 'congest_q'), 'sum'] == 0:
        TransactiveCongestAvgPriceInd = 0
    else:
        TransactiveCongestAvgPriceInd = (
                    year_energysum_df.loc[('industrial', 'congest_$'), 'sum'] / year_energysum_df.loc[
                ('industrial', 'congest_q'), 'sum'])  # $/kW-hr

    DSO_Revenues_and_Energy_Sales = {
        'RetailSales': {
            'FixedSales': {
                'ConnChargesFix': {
                    'ConnChargesFixRes': billsum_df.loc[('residential', 'fix_connect'), 'sum'] / 1000,  # $k
                    'ConnChargesFixComm': billsum_df.loc[('commercial', 'fix_connect'), 'sum'] / 1000,  # $k
                    'ConnChargesFixInd': billsum_df.loc[('industrial', 'fix_connect'), 'sum'] / 1000  # $k
                },
                'SalesFixRes': {
                    'EnergyFixPriceRes': year_energysum_df.loc[('residential', 'kw-hr'), 'sum'] / 1000,  # MW-hr/year
                    'EnergyFixRes': billsum_df.loc[('residential', 'fix_energy'), 'sum'] / 1000,  # $k
                    'DemandQuantityRes': year_energysum_df.loc[('residential', 'demand_quantity'), 'sum'] / 1000,  # MW
                    'DemandChargesRes': billsum_df.loc[('residential', 'demand'), 'sum'] / 1000,  # $k
                    'AvgPriceFixRes': billsum_df.loc[('residential', 'fix_blended_rate'), 'sum']  # $/kW-hr
                },
                'SalesFixComm': {
                    'EnergyFixPriceComm': year_energysum_df.loc[('commercial', 'kw-hr'), 'sum'] / 1000,  # MW-hr/year
                    'EnergyFixComm': billsum_df.loc[('commercial', 'fix_energy'), 'sum'] / 1000,  # $k
                    'DemandQuantityComm': year_energysum_df.loc[('commercial', 'demand_quantity'), 'sum'] / 1000,  # MW
                    'DemandChargesComm': billsum_df.loc[('commercial', 'demand'), 'sum'] / 1000,  # $k
                    'AvgPriceFixComm': billsum_df.loc[('commercial', 'fix_blended_rate'), 'sum']  # $/kW-hr
                },
                'SalesFixInd': {
                    'EnergyFixPriceInd': year_energysum_df.loc[('industrial', 'kw-hr'), 'sum'] / 1000,  # MW-hr/year
                    'EnergyFixInd': billsum_df.loc[('industrial', 'fix_energy'), 'sum'] / 1000,  # $k
                    'DemandQuantityInd': year_energysum_df.loc[('industrial', 'demand_quantity'), 'sum'] / 1000,  # MW
                    'DemandChargesInd': billsum_df.loc[('industrial', 'demand'), 'sum'] / 1000,  # $k
                    'AvgPriceFixInd': billsum_df.loc[('industrial', 'fix_blended_rate'), 'sum']  # $/kW-hr
                }
            },
            'TransactiveSales': {
                'ConnChargesDyn': {
                    'ConnChargesDynRes': billsum_df.loc[('residential', 'trans_connect'), 'sum'] / 1000,  # $k
                    'ConnChargesDynComm': billsum_df.loc[('commercial', 'trans_connect'), 'sum'] / 1000,  # $k
                    'ConnChargesDynInd': billsum_df.loc[('industrial', 'trans_connect'), 'sum'] / 1000  # $k
                },
                'DistCharges': {
                    'DistChargesRes': billsum_df.loc[('residential', 'distribution'), 'sum'] / 1000,  # $k
                    'DistChargesComm': billsum_df.loc[('commercial', 'distribution'), 'sum'] / 1000,  # $k
                    'DistChargesInd': billsum_df.loc[('industrial', 'distribution'), 'sum'] / 1000  # $k
                },
                'RetailDASales': {
                    'RetailDASalesRes': billsum_df.loc[('residential', 'DA_energy'), 'sum'] / 1000,  # $k
                    'RetailDASalesComm': billsum_df.loc[('commercial', 'DA_energy'), 'sum'] / 1000,  # $k
                    'RetailDASalesInd': billsum_df.loc[('industrial', 'DA_energy'), 'sum'] / 1000  # $k
                },
                'RetailDAEnergy': {
                    'RetailDAEnergyRes': year_energysum_df.loc[('residential', 'da_q'), 'sum'] / 1000,  # MW-hrs
                    'RetailDAEnergyComm': year_energysum_df.loc[('commercial', 'da_q'), 'sum'] / 1000,  # MW-hrs
                    'RetailDAEnergyInd': year_energysum_df.loc[('industrial', 'da_q'), 'sum'] / 1000  # MW-hrs
                },
                'RetailDAAvgPrice': {
                    'RetailDAAvgPriceRes': billsum_df.loc[('residential', 'da_blended_rate'), 'sum'],  # $/kW-hr
                    'RetailDAAvgPriceComm': billsum_df.loc[('commercial', 'da_blended_rate'), 'sum'],  # $/kW-hr
                    'RetailDAAvgPriceInd': billsum_df.loc[('industrial', 'da_blended_rate'), 'sum']  # $/kW-hr
                },
                'RetailRTSales': {
                    'RetailRTSalesRes': billsum_df.loc[('residential', 'RT_energy'), 'sum'] / 1000,  # $k
                    'RetailRTSalesComm': billsum_df.loc[('commercial', 'RT_energy'), 'sum'] / 1000,  # $k
                    'RetailRTSalesInd': billsum_df.loc[('industrial', 'RT_energy'), 'sum'] / 1000  # $k
                },
                'RetailRTEnergy': {
                    'RetailRTEnergyRes': year_energysum_df.loc[('residential', 'rt_q'), 'sum'] / 1000,  # MW-hrs
                    'RetailRTEnergyComm': year_energysum_df.loc[('commercial', 'rt_q'), 'sum'] / 1000,  # MW-hrs
                    'RetailRTEnergyInd': year_energysum_df.loc[('industrial', 'rt_q'), 'sum'] / 1000  # MW-hrs
                },
                'RetailRTAvgPrice': {
                    'RetailRTAvgPriceRes': billsum_df.loc[('residential', 'rt_blended_rate'), 'sum'],  # $/kW-hr
                    'RetailRTAvgPriceComm': billsum_df.loc[('commercial', 'rt_blended_rate'), 'sum'],  # $/kW-hr
                    'RetailRTAvgPriceInd': billsum_df.loc[('industrial', 'rt_blended_rate'), 'sum']  # $/kW-hr
                },
                'TransactiveAvgPrice': {
                    'TransactiveAvgPriceRes': billsum_df.loc[('residential', 'trans_blended_rate'), 'sum'],  # $/kW-hr
                    'TransactiveAvgPriceComm': billsum_df.loc[('commercial', 'trans_blended_rate'), 'sum'],  # $/kW-hr
                    'TransactiveAvgPriceInd': billsum_df.loc[('industrial', 'trans_blended_rate'), 'sum']  # $/kW-hr
                },
                'TransactiveCongestionEnergy': {
                    'TransactiveCongestEnergyRes': year_energysum_df.loc[('residential', 'congest_q'), 'sum'] / 1000,   # MW-hrs
                    'TransactiveCongestEnergyComm': year_energysum_df.loc[('commercial', 'congest_q'), 'sum'] / 1000,   # MW-hrs
                    'TransactiveCongestEnergyInd': year_energysum_df.loc[('industrial', 'congest_q'), 'sum'] / 1000   # MW-hrs
                },
                'TransactiveCongestionSales': {
                    'TransactiveCongestSalesRes': year_energysum_df.loc[('residential', 'congest_$'), 'sum'] / 1000,  # $k
                    'TransactiveCongestSalesComm': year_energysum_df.loc[('commercial', 'congest_$'), 'sum'] / 1000,  # $k
                    'TransactiveCongestSalesInd': year_energysum_df.loc[('industrial', 'congest_$'), 'sum'] / 1000  # $k
                },
                'TransactiveCongestionAvgPrice': {
                    'TransactiveCongestAvgPriceRes': TransactiveCongestAvgPriceRes,  # $/kW-hr
                    'TransactiveCongestAvgPriceComm': TransactiveCongestAvgPriceComm,  # $/kW-hr
                    'TransactiveCongestAvgPriceInd': TransactiveCongestAvgPriceInd  # $/kW-hr
                }
            }
        },
        'EnergySold': year_energysum_df.loc[('total', 'kw-hr'), 'sum'] / 1000,  # Energy Sold in MW-hr
        'RequiredRevenue': (billsum_df.loc[('total', 'fix_total'), 'sum'] + billsum_df.loc[
            ('total', 'trans_total'), 'sum']) / 1000,  # Energy Charges in $k
        'EffectiveCostRetailEnergy': (billsum_df.loc[('total', 'fix_total'), 'sum'] +
                                      billsum_df.loc[('total', 'trans_total'), 'sum']) \
                                     / year_energysum_df.loc[('total', 'kw-hr'), 'sum'],  # $/kW-hr
        'DistLosses': {
            'DistLossesCost': year_energysum_df.loc[('total', 'dist_loss_$'), 'sum'] / 1000,  # DSO Losses in $k
            'DistLossesEnergy': year_energysum_df.loc[('total', 'dist_loss_q'), 'sum'] / 1000,  # DSO Losses in MW-hrs
        }
    }

    DSO_Cash_Flows = {
        'Revenues': {
            'RetailSales': {
                'FixedSales': {
                    'FixedEnergyCharges': billsum_df.loc[('total', 'fix_energy'), 'sum'] / 1000,  # Energy Charges in $k
                    'DemandCharges': billsum_df.loc[('total', 'demand'), 'sum'] / 1000,  # Demand Charges in $k
                    'ConnectChargesFix': billsum_df.loc[('total', 'fix_connect'), 'sum'] / 1000
                    # Connection Charges in $k
                },
                'TransactiveSales': {
                    'RetailDACharges': billsum_df.loc[('total', 'DA_energy'), 'sum'] / 1000,  # DA Energy Charges in $k
                    'RetailRTCharges': billsum_df.loc[('total', 'RT_energy'), 'sum'] / 1000,  # RT Energy Charges in $k
                    'DistCharges': billsum_df.loc[('total', 'distribution'), 'sum'] / 1000,  # Distribution Charges in $k
                    'ConnectChargesDyn': billsum_df.loc[('total', 'trans_connect'), 'sum'] / 1000  # Connection Charges in $k
                }
            },
        },
    }

    return DSO_Cash_Flows, DSO_Revenues_and_Energy_Sales, tariff, surplus


def get_cust_bill(cust, bill_df, bill_metadata):
    """ Populates dictionary of individual customer's annual bill.
    Arguments:
        cust (str): customer name (meter name from GLD dictionary)
        bill_df (dataframe): dataframe of annual and monthly customer bills
        bill_metadata (dict): dictionary of GLD metadata including tarrif and building type for each meter
    Returns:
        customer_annual_bill (dict): dictionary of customers annual energy bill
        """

    customer_annual_bill = {
        'BillsFix': {
            'PurchasesFix': {
                'EnergyFix': bill_df.loc[(cust, 'fix_energy'), 'sum'],
                'DemandCharges': bill_df.loc[(cust, 'demand'), 'sum']
            },
            'ConnChargesFix': bill_df.loc[(cust, 'fix_connect'), 'sum'],
            'TotalFix': bill_df.loc[(cust, 'fix_total'), 'sum']
        },
        'BillsTransactive': {
            'PurchasesDyn': {
                'DAEnergy': bill_df.loc[(cust, 'DA_energy'), 'sum'],
                'RTEnergy': bill_df.loc[(cust, 'RT_energy'), 'sum']
            },
            'DistCharges': bill_df.loc[(cust, 'distribution'), 'sum'],
            'ConnChargesDyn': bill_df.loc[(cust, 'trans_connect'), 'sum'],
            'TotalDyn': bill_df.loc[(cust, 'trans_total'), 'sum'],
        },
        'EnergyQuantity': bill_df.loc[(cust, 'quantity_purchased'), 'sum'],
        'BlendedRate': bill_df.loc[(cust, 'blended_rate'), 'sum'],
        'CustomerType': {
            'BuildingType': bill_metadata['billingmeters'][cust]['building_type'],
            'TariffClass': bill_metadata['billingmeters'][cust]['tariff_class']
        }
    }

    return customer_annual_bill

    # ----------------------   MAIN  ------------------------


if __name__ == '__main__':

    '''
    Example of creating energy statistics and bills for each customer (GLD meter) and by customer class.
    '''
    # ------------ Selection of DSO Range  ---------------------------------

    dso_range = range(4, 5)
    # ------------ Select folder locations for different cases ---------

    sys.path.insert(0, dirname(dirname(dirname(abspath(__file__)))))

    data_path = 'C:\\Users\\reev057\PycharmProjects\\DSO+T\\Data\\Simdata\\DER2\\V1.1-1336-gb74f2d99\lean_8'
    base_case = 'C:\\Users\\reev057\PycharmProjects\\DSO+T\\Data\Simdata\DER2\\V1.1-1336-gb74f2d99\lean_8'
    agent_prefix = '/DSO_'
    GLD_prefix = '/Substation_'
    tariff_path = 'C:\\Users\\reev057\\PycharmProjects\\TESP\\src\\examples\\analysis\\dsot\\data'
    metadata_path = 'C:\\Users\\reev057\\PycharmProjects\\TESP\\src\\examples\\analysis\\dsot\\data'

    # ------  For each DSO determine the scaling factor and update the metadata
    for dso_num in dso_range:
        # load DSO metadata
        file_name = 'Substation_' + str(dso_num) + '_glm_dict.json'
        agent_prefix = '/DSO_'
        GLD_prefix = '/Substation_'
        metadata = load_json(base_case + agent_prefix + str(dso_num), file_name)

        DSOmetadata = load_json(metadata_path, '8-metadata-lean.json')
        # TODO: This should be done in meta data and read in.
        dso_scaling_factor = DSOmetadata['DSO_' + str(dso_num)]['number_of_customers'] \
                             * DSOmetadata['DSO_' + str(dso_num)]['RCI customer count mix']['residential'] \
                             / DSOmetadata['DSO_' + str(dso_num)]['number_of_gld_homes']

        # Placeholder code to add whether a customer is participating or not.
        # TODO: this should be done in prepare case and read in as part of GLD meter metadata.
        agent_file_name = 'Substation_' + str(dso_num) + '_agent_dict.json'
        agent_metadata = load_json(base_case + agent_prefix + str(dso_num), agent_file_name)

        metadata = customer_meta_data(metadata, agent_metadata, tariff_path)

        # List of month names, data paths, and day ranges to be used for energy bill creation
        # month_def = [
        #             ['Jan', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\Data\\Slim2\\case_slim_1', 2, 31],
        #             ['Feb', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_2', 2, 30],
        #             ['March', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_3', 2, 31],
        #             ['April', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_4', 2, 31],
        #             ['May', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_5', 2, 31],
        #             ['June', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_6', 2, 30],
        #             ['July', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_7', 2, 31],
        #             ['August', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_8', 2, 7],
        #             ['Sept', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_9', 2, 30],
        #             ['Oct', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_10', 2, 31],
        #             ['Nov', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_11', 2, 30],
        #             ['Dec', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Slim2\\case_slim_12', 2, 7]]
        month_def = [['Jan', 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Simdata\DER2\\V1.1-1336-gb74f2d99\\lean_8', 2, 4]]

        #  -------------- Calculate dataframe of monthly power consumption and peak power demand ---------
        process_meters = True
        if process_meters:

            for i in range(len(month_def)):
                for day_num in range(month_def[i][2], month_def[i][3]):
                    retail_data_df, retail_index_df = load_retail_data(month_def[i][1], agent_prefix, str(dso_num),
                                                                       str(day_num), 'retail_site')
                tic()
                meter_df, energysum_df = read_meters(metadata, month_def[i][1], GLD_prefix, str(dso_num),
                                                     range(month_def[i][2], month_def[i][3]), dso_scaling_factor,
                                                     metadata_path)
                print('Meter reading complete: DSO ' + str(dso_num) + ', Month ' + month_def[i][0])
                toc()

        #  -------------- Create dataframe with all monthly energy metrics and create annual sum ---------

        year_meter_df, year_energysum_df, year_trans_sum_df = annual_energy(month_def, GLD_prefix, str(dso_num),
                                                                            metadata)
        os.chdir(data_path)
        year_meter_df.to_hdf('energy_dso_' + str(dso_num) + '_data.h5', key='energy_data')
        year_energysum_df.to_hdf('energy_dso_' + str(dso_num) + '_data.h5', key='energy_sums')
        year_trans_sum_df.to_hdf('transactive_dso_' + str(dso_num) + '_data.h5', key='trans_data')

        required_revenue = 10000000

        DSO_Cash_Flows, DSO_Revenues_and_Energy_Sales, tariff, surplus = DSO_rate_making(data_path, dso_num, metadata,
                                                                                         required_revenue,
                                                                                         tariff_path,
                                                                                         dso_scaling_factor)

        # Example of getting an annual customer bill in dictionary form:
        customer = list(metadata['billingmeters'].keys())[0]
        cust_bill_file = data_path + '\\bill_dso_' + str(dso_num) + '_data.h5'
        cust_bills = pd.read_hdf(cust_bill_file, key='cust_bill_data', mode='r')
        customer_bill = get_cust_bill(customer, cust_bills, metadata)

        print(DSO_Cash_Flows)
        print(DSO_Revenues_and_Energy_Sales)
        print(customer_bill)
        print(surplus)

#  Need to read-in scaling factors at DSO level to scale to correct number of buildings.
# Need separate function to calculate the aggregate industrial bill.
# function to calculate transactive bill
# Need function to read in cashflow (balance) sheets
# what are unit testing requirements for this code...
# add function to sum up all energy charges by customer class.
# add blended rate by customer class
# Calculate load factor for each building and compare to ORNL data.
# Calculate energy consumption by class and compare it to DSO meta-data file (both customer counts and energy consumption)
