# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: dso_helper_functions.py
"""
@author: yint392
"""

import itertools
import math
import pandas as pd

# get rid of the burn-in days

# filenames the list of filenames of h5 files that you want, for example
# filenames = [f for f in os.listdir(dso_path) if f.endswith('.hdf5') and f.startswith('battery_agent') and '300' in f and '38' not in f]
# filenames[0]

# old functions
'''
def get_correct_days(dso_path, filenames):
    sub_filenames = []
    temp_df = pd.read_hdf(os.path.join(dso_path, filenames[0]), key='/metrics_df0', mode='r')
    correct_month = temp_df.index.values[0,][0].month + 1

    for i in range(len(filenames)):
        temp_df = pd.read_hdf(os.path.join(dso_path, filenames[i]), key='/metrics_df0', mode='r')
        if temp_df.index.values[0,][0].month == correct_month:
           sub_filenames.append(filenames[i])
    return sub_filenames



def get_incorrect_days_tables(Substation_path, filename):
    h5filename = [f for f in os.listdir(Substation_path) if f.endswith(filename + '.h5')]
    temp_df = pd.read_hdf(os.path.join(Substation_path, h5filename[0]), key='/Metadata', mode='r')

    datetime_object = datetime.strptime(temp_df.loc[temp_df["name"] == "StartTime", "value"][0], '%Y-%m-%d %H:%M:%S EST')
    number_days = monthrange(datetime_object.year, datetime_object.month)[1] - datetime_object.day + 1
    keys_delete = []
    for i in range(number_days):
        keys_delete.append('/index' + str(i+1))
    return keys_delete

Substation_path = Substation_paths[0]

def get_DSOPeakLoad_Total_MWh(Substation_path, dso_name):

    h5filename_sub = [f for f in os.listdir(Substation_path) if f.endswith('substation.h5')][0]
    store_sub = pd.HDFStore(os.path.join(Substation_path, h5filename_sub), 'r')

    # need to exclude the burn-in days
    # keys_delete_sub = get_incorrect_days_tables(Substation_path, 'substation')
    keys_delete_sub = [] # for the simulated data now only has 7 days

    Total_real_energy = 0
    DSOPeakLoad = 0
    DSOLossQuantity = 0

    for i in [i for i in list(store_sub.keys()) if i.startswith('/index') and i not in keys_delete_sub]: # i not in burn-in days
        test_df = pd.read_hdf(os.path.join(Substation_path, h5filename_sub), key=i, mode='r')
        Total_real_energy += test_df["real_energy"].sum()

        if DSOPeakLoad < test_df["real_power_max"].max():
            DSOPeakLoad = test_df["real_power_max"].max()

        DSOLossQuantity += test_df["real_power_losses_avg"].sum()

    metadata_te_base_sub = pd.read_hdf(os.path.join(Substation_path, h5filename_sub), key='/Metadata', mode='r')

    real_energy_unit_sub = metadata_te_base_sub.loc[metadata_te_base_sub["name"] == "real_energy"]["value"].values[0]

    if  real_energy_unit_sub.upper() == 'WH':
        Total_MWh = Total_real_energy/1000000
    elif real_energy_unit_sub.upper() == 'KWH':
        Total_MWh = Total_real_energy/1000
    elif real_energy_unit_sub.upper() == 'MWH':
        Total_MWh = Total_real_energy

    return DSOPeakLoad, Total_MWh



def dict_add(dict_list):

    base_dict = dict_list[0].copy()

    for k, v in base_dict.items():
        if isinstance(v, dict):
            base_dict[k] = dict_add([dict_list[i][k] for i in range(len(dict_list))])
        elif isinstance(v, str):
            pass
        elif isinstance(v, float) or isinstance(v, int):
            for i in range(1, len(dict_list)):
                base_dict[k] += dict_list[i][k]

    return base_dict


def get_number_levels(d):
    return max(get_number_levels(v) if isinstance(v, dict) else 0 for v in d.values()) + 1
'''


###################################################

def returnDictSum(temp_dict):
    temp_sum = 0
    for k, v in temp_dict.items():
        if isinstance(v, dict):
            temp_sum += returnDictSum(v)
        elif isinstance(v, str):
            pass
        else:
            temp_sum += temp_dict[k]

    return temp_sum


def TEAM(FteLev1=100.0, SalaryEsc1=1.3):
    Fte = [0.0] * 6
    Fte[0] = FteLev1

    MaxDirect = [0.0] * 6
    MinDirect = [0.0] * 6
    MaxDirect[1:5] = [10, 8, 8, 8, 6]
    MinDirect[1:5] = [5, 5, 5, 5, 5]

    for N in range(1, 6):
        if Fte[N - 1] < MinDirect[N]:
            Fte[N] = 0
        else:
            Fte[N] = float(math.ceil(Fte[N - 1] / MaxDirect[N]))
    FteTeam = sum(Fte)

    Esc = [0] * 6
    for N in range(0, 6):
        Esc[N] = SalaryEsc1 ** N

    Salary = [0.0] * 6
    Salary[0] = 1.0
    Cost = 0
    for N in range(1, 6):
        Salary[N] = Salary[N - 1] * Esc[N]

    LeaderLevel = 0
    LeaderRatio = 1
    for N in range(6):
        Cost = Cost + Salary[N] * Fte[N]
        if Fte[N] > 0:
            LeaderRatio = Salary[N]
            LeaderLevel = N + 1

    CostRatio = Cost / (Fte[0] * Salary[0])

    return FteTeam, CostRatio, LeaderRatio, LeaderLevel


# TEAM(100, 1.3)

# group = 'operator'

def labor(group, metadata_general, metadata_dso, utility_type, NoSubstations):
    labor_Lev1Fte = (metadata_general['labor'][group][group + '_labor_ratios']['constant'] +
                     metadata_general['labor'][group][group + '_labor_ratios']['per_customer'] * metadata_dso[
                         'number_of_customers'] / 1000 +
                     (metadata_general['labor'][group][group + '_labor_ratios']['per_customer^1/2'] * (
                             metadata_dso['number_of_customers'] / 1000) ** (1 / 2)) +
                     metadata_general['labor'][group][group + '_labor_ratios']['per_substation'] * NoSubstations)

    FteTeam, CostRatio, LeaderRatio, LeaderLevel = TEAM(labor_Lev1Fte,
                                                        metadata_general['labor']['team_salary_escalation_1'])

    Lev1_labor_cost = metadata_general['labor'][group][group + '_hourly_rate'][utility_type] * \
                      metadata_general['hours_per_year'] / metadata_general['labor'][
                          'salary_to_total_compensation_ratio']

    labor_cost = CostRatio * labor_Lev1Fte * Lev1_labor_cost / 1000

    return labor_Lev1Fte, FteTeam, Lev1_labor_cost, LeaderRatio, labor_cost, LeaderLevel


def labor_transactive(group, metadata_general, metadata_dso, utility_type, NoSubstations, TransactiveCaseFlag):
    labor_Lev1Fte = (metadata_general['labor'][group][group + '_labor_ratios']['constant'] +
                     metadata_general['labor'][group][group + '_labor_ratios']['per_customer'] * metadata_dso[
                         'number_of_customers'] / 1000 +
                     (metadata_general['labor'][group][group + '_labor_ratios']['per_customer^1/2'] * (
                             metadata_dso['number_of_customers'] / 1000) ** (1 / 2)) +
                     metadata_general['labor'][group][group + '_labor_ratios'][
                         'per_substation'] * NoSubstations) * TransactiveCaseFlag

    FteTeam, CostRatio, LeaderRatio, LeaderLevel = TEAM(labor_Lev1Fte,
                                                        metadata_general['labor']['team_salary_escalation_1'])
    FteTeam = FteTeam * TransactiveCaseFlag

    Lev1_labor_cost = metadata_general['labor'][group][group + '_hourly_rate'][utility_type] * \
                      metadata_general['hours_per_year'] / metadata_general['labor'][
                          'salary_to_total_compensation_ratio'] * TransactiveCaseFlag

    labor_cost = CostRatio * labor_Lev1Fte * Lev1_labor_cost / 1000

    return labor_Lev1Fte, FteTeam, Lev1_labor_cost, LeaderRatio, labor_cost, LeaderLevel


def labor_increase(group, metadata_general, metadata_dso, utility_type, NoSubstations, TransactiveCaseFlag):
    labor_Lev1Fte = metadata_general['labor'][group][group + '_labor_ratios']['constant'] + \
                    metadata_general['labor'][group][group + '_labor_ratios']['per_customer'] * metadata_dso[
                        'number_of_customers'] / 1000 + \
                    (metadata_general['labor'][group][group + '_labor_ratios']['per_customer^1/2'] * (
                            metadata_dso['number_of_customers'] / 1000) ** (1 / 2)) + \
                    metadata_general['labor'][group][group + '_labor_ratios']['per_substation'] * NoSubstations * \
                    (1 + metadata_general['labor'][group][group + '_labor_ratios'][
                        'transactive_increase'] * TransactiveCaseFlag)

    FteTeam, CostRatio, LeaderRatio, LeaderLevel = TEAM(labor_Lev1Fte,
                                                        metadata_general['labor']['team_salary_escalation_1'])

    labor_Fte = FteTeam * (1 + metadata_general['labor'][group][group + '_labor_ratios'][
        'transactive_increase'] * TransactiveCaseFlag)

    Lev1_labor_cost = metadata_general['labor'][group][group + '_hourly_rate'][utility_type] * \
                      metadata_general['hours_per_year'] / metadata_general['labor'][
                          'salary_to_total_compensation_ratio'] * \
                      (1 + metadata_general['labor'][group][group + '_labor_ratios'][
                          'transactive_increase'] * TransactiveCaseFlag)

    labor_cost = CostRatio * labor_Lev1Fte * Lev1_labor_cost / 1000

    return labor_Lev1Fte, labor_Fte, Lev1_labor_cost, LeaderRatio, labor_cost, LeaderLevel


def labor_network_admin(group, hourly_rate, metadata_general, metadata_dso, utility_type, NoSubstations):
    labor_Lev1Fte = (metadata_general['labor']['network_admin'][group]['constant'] +
                     metadata_general['labor']['network_admin'][group]['per_customer'] * metadata_dso[
                         'number_of_customers'] / 1000 +
                     (metadata_general['labor']['network_admin'][group]['per_customer^1/2'] * (
                             metadata_dso['number_of_customers'] / 1000) ** (1 / 2)) +
                     metadata_general['labor']['network_admin'][group]['per_substation'] * NoSubstations)

    FteTeam, CostRatio, LeaderRatio, LeaderLevel = TEAM(labor_Lev1Fte,
                                                        metadata_general['labor']['team_salary_escalation_1'])

    Lev1_labor_cost = metadata_general['labor']['network_admin'][hourly_rate][utility_type] * \
                      metadata_general['hours_per_year'] / metadata_general['labor'][
                          'salary_to_total_compensation_ratio']

    labor_cost = CostRatio * labor_Lev1Fte * Lev1_labor_cost / 1000

    return labor_Lev1Fte, FteTeam, Lev1_labor_cost, LeaderRatio, labor_cost, LeaderLevel


def labor_network_admin_transactive(group, hourly_rate, metadata_general, metadata_dso, utility_type, NoSubstations,
                                    TransactiveCaseFlag):
    labor_Lev1Fte = (metadata_general['labor']['network_admin'][group]['constant'] +
                     metadata_general['labor']['network_admin'][group]['per_customer'] * metadata_dso[
                         'number_of_customers'] / 1000 +
                     (metadata_general['labor']['network_admin'][group]['per_customer^1/2'] * (
                             metadata_dso['number_of_customers'] / 1000) ** (1 / 2)) +
                     metadata_general['labor']['network_admin'][group][
                         'per_substation'] * NoSubstations) * TransactiveCaseFlag

    FteTeam, CostRatio, LeaderRatio, LeaderLevel = TEAM(labor_Lev1Fte,
                                                        metadata_general['labor']['team_salary_escalation_1'])
    FteTeam = FteTeam * TransactiveCaseFlag

    Lev1_labor_cost = metadata_general['labor']['network_admin'][hourly_rate][utility_type] * \
                      metadata_general['hours_per_year'] / metadata_general['labor'][
                          'salary_to_total_compensation_ratio'] * \
                      TransactiveCaseFlag

    labor_cost = CostRatio * labor_Lev1Fte * Lev1_labor_cost / 1000

    return labor_Lev1Fte, FteTeam, Lev1_labor_cost, LeaderRatio, labor_cost, LeaderLevel


def labor_network_admin_increase(group, hourly_rate, metadata_general, metadata_dso, utility_type, NoSubstations,
                                 TransactiveCaseFlag):
    labor_Lev1Fte = (metadata_general['labor']['network_admin'][group]['constant'] +
                     metadata_general['labor']['network_admin'][group]['per_customer'] * metadata_dso[
                         'number_of_customers'] / 1000 +
                     (metadata_general['labor']['network_admin'][group]['per_customer^1/2'] * (
                             metadata_dso['number_of_customers'] / 1000) ** (1 / 2)) +
                     metadata_general['labor']['network_admin'][group]['per_substation'] * NoSubstations)

    FteTeam, CostRatio, LeaderRatio, LeaderLevel = TEAM(labor_Lev1Fte,
                                                        metadata_general['labor']['team_salary_escalation_1'])

    labor_Fte = FteTeam * \
                (1 + metadata_general['labor']['network_admin'][group]['transactive_increase'] * TransactiveCaseFlag)

    Lev1_labor_cost = metadata_general['labor']['network_admin'][hourly_rate][utility_type] * \
                      metadata_general['hours_per_year'] / metadata_general['labor'][
                          'salary_to_total_compensation_ratio'] * \
                      (1 + metadata_general['labor']['network_admin'][group][
                          'transactive_increase'] * TransactiveCaseFlag)

    labor_cost = CostRatio * labor_Lev1Fte * Lev1_labor_cost / 1000

    return labor_Lev1Fte, labor_Fte, Lev1_labor_cost, LeaderRatio, labor_cost, LeaderLevel


def get_mean_for_diff_groups(df, main_variables, variables_combs, cfs_start_position=24):
    customer_mean_df = pd.DataFrame([])
    customer_mean_df['all'] = df.iloc[:, cfs_start_position:].mean()
    for main_variable in main_variables:
        temp_list = df[main_variable].unique()
        for value in temp_list:
            df_temp = df.copy()
            df_temp = df_temp[df_temp[main_variable] == value]
            temp_col = df_temp.iloc[:, cfs_start_position:].mean()
            customer_mean_df[str(value)] = temp_col

    for variables_comb in variables_combs:
        temp_list = []
        for variable in variables_comb:
            temp_list.append(df[variable].unique())
        comb_list = list(itertools.product(*temp_list))

        for comb in comb_list:
            df_temp = df.copy()
            for i in range(len(variables_comb)):
                df_temp = df_temp[df_temp[variables_comb[i]] == comb[i]]
            temp_col = df_temp.iloc[:, cfs_start_position:].mean()
            customer_mean_df[comb] = temp_col

    return customer_mean_df


