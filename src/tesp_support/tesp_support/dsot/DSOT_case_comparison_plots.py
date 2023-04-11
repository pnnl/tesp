# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: DSOT_case_comparison_plots.py
import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .DSOT_plots import load_json


def plot_lmp_stats(cases, data_paths, output_path, dso_num, variable):
    """Will plot LMPS by month, duration, and versus netloads loads (for select month), and save to file.
    Arguments:
        data_path (str): location of the data files to be used.
        output_path (str): path of the location where output (plots, csv) should be saved
        dso_num (str): bus number for LMP data to be plotted
    Returns:
        saves dso lmps plots to file
        """
    label_size = 17
    num_size = 14
    stats = True

    if variable == 'DA LMP':
        old_variable = 'da_lmp'
        title_name = 'Day Ahead LMP'
        file_name = 'DA_LMP'
        upper_limit = 100
        lower_limit = 0
        units = '$/MW-hr'
        Log = True
    elif variable == 'RT LMP':
        variable = 'RT LMP'
        old_variable = ' LMP'
        title_name = 'Real-Time LMP'
        file_name = 'RT_LMP'
        upper_limit = 100
        lower_limit = 0
        units = '$/MW-hr'
        Log = True
    elif variable == 'Total Load':
        old_variable = 'Total Load'
        title_name = 'Total System Load'
        file_name = 'Total_Load'
        upper_limit = 70000
        lower_limit = 0
        units = 'MW'
        Log = False

    for i in range(len(cases)):
        case = cases[i]
        data_path = data_paths[i]
        if variable == 'DA LMP':
            var_df = pd.read_csv(data_path + '/Annual_DA_LMP_Load_data.csv', index_col=[0])
        elif variable == 'RT LMP':
            var_df = pd.read_csv(data_path + '/Annual_RT_LMP_Load_data.csv', index_col=[0])
        elif variable == 'Total Load':
            var_df = pd.read_csv(data_path + '/DSO_Total_Loads.csv', index_col='time', parse_dates=True)

        var_df = var_df.set_index(pd.to_datetime(var_df.index))
        var_df['Month'] = var_df.index.month
        if variable in ['DA LMP', 'RT LMP']:
            var_df = var_df[[old_variable + dso_num, 'Month']]
            var_df.rename(columns={old_variable + dso_num: variable}, inplace=True)
        else:
            var_df = var_df[[old_variable, 'Month']]
            var_df.rename(columns={old_variable: variable}, inplace=True)
        var_df['Case'] = case

        var_daily_df = pd.Series.to_frame(var_df[variable].groupby(pd.Grouper(freq='D')).max()
                                          - var_df[variable].groupby(pd.Grouper(freq='D')).min())
        var_daily_df[variable + ' STD'] = var_df[variable].groupby(pd.Grouper(freq='D')).std()
        var_daily_df['Month'] = var_daily_df.index.month
        var_daily_df.dropna(subset=[variable], inplace=True)
        var_daily_df['Case'] = case

        if i == 0:
            var_comparison_df = var_df
            var_daily_comparison_df = var_daily_df
        else:
            var_comparison_df = pd.concat([var_comparison_df, var_df])
            var_daily_comparison_df = pd.concat([var_daily_comparison_df, var_daily_df])

    # ==============  Plot box and whiskers ==========================
    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    pal = ['violet'] + ['lightgreen'] + ["gold"] + ['skyblue']

    sns.boxplot(data=var_comparison_df, x='Month', y=variable, hue='Case', ax=axes[0], palette=pal)
    axes[0].set_ylabel(units)
    axes[0].set_title('Variation in ' + title_name + ' over the Year')
    axes[0].set_xlabel('')
    axes[0].set_ylim(top=upper_limit, bottom=lower_limit)
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles=handles, labels=labels, framealpha=1)

    sns.boxplot(data=var_daily_comparison_df, x='Month', y=variable, hue='Case', ax=axes[1], palette=pal)
    axes[1].set_ylabel(units)
    axes[1].set_title('Variation in Daily Change in ' + title_name + ' over the Year')
    axes[1].set_xlabel('Month')
    axes[1].set_ylim(top=upper_limit, bottom=lower_limit)
    handles, labels = axes[1].get_legend_handles_labels()
    axes[1].legend(handles=handles, labels=labels, framealpha=1)

    sns.boxplot(data=var_daily_comparison_df, x='Month', y=variable + ' STD', hue='Case', ax=axes[2], palette=pal)
    axes[2].set_ylabel(units)
    axes[2].set_title('Standard Deviation of Daily ' + title_name + ' over the Year')
    axes[2].set_xlabel('Month')
    axes[2].set_ylim(top=upper_limit / 3, bottom=lower_limit)
    handles, labels = axes[2].get_legend_handles_labels()
    axes[2].legend(handles=handles, labels=labels, framealpha=1)

    plot_filename = datetime.now().strftime(
        '%Y%m%d') + 'Case_Compare_' + file_name + ' _Annual_Box_Plots-focused-SBS.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    # ============================

    pal = ['violet'] + ['lightgreen']
    plt.clf()
    sns.ecdfplot(data=var_comparison_df, y=variable, hue="Case", palette=pal)
    plt.ylabel(units)
    plt.title('Duration vs. ' + title_name)
    plt.xlabel('Duration (%)')
    if Log:
        plt.yscale('log')
    plt.grid(b=True, which='both', color='k', linestyle=':')
    plt.minorticks_on()
    ax = plt.gca()
    # axes[0].tick_params(axis='both', which='major', labelsize=17)

    if stats:
        text = "               Mean    Median \n"
        for case in cases:
            case_df = var_comparison_df.loc[var_comparison_df['Case'] == case]
            case_data = np.array(case_df[variable].values.tolist())
            mean = np.mean(case_data[~np.isnan(case_data)])
            median = np.median(case_data[~np.isnan(case_data)])
            text = text + case + " = " + str(round(mean)) + "     " + str(round(median)) + "\n"
        plt.text(0.4, 0.1, text, size=10, horizontalalignment='left',
                 verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

    plot_filename = datetime.now().strftime('%Y%m%d') + 'Case_Comparison_' + file_name + '_Duration_Curve.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    # ----- DAily Variation Curve
    plt.clf()
    sns.ecdfplot(data=var_daily_comparison_df, y=variable, hue="Case", palette=pal)
    plt.ylabel(units)
    plt.title('Duration vs. Daily Variation in ' + title_name)
    plt.xlabel('Duration (%)')
    if Log:
        plt.yscale('log')
    plt.grid(b=True, which='both', color='k', linestyle=':')
    plt.minorticks_on()
    ax = plt.gca()
    # axes[0].tick_params(axis='both', which='major', labelsize=17)

    if stats:
        text = "               Mean    Median \n"
        for case in cases:
            case_df = var_daily_comparison_df.loc[var_daily_comparison_df['Case'] == case]
            case_data = np.array(case_df[variable].values.tolist())
            mean = np.mean(case_data[~np.isnan(case_data)])
            median = np.median(case_data[~np.isnan(case_data)])
            text = text + case + " = " + str(round(mean)) + "     " + str(round(median)) + "\n"
        plt.text(0.4, 0.1, text, size=10, horizontalalignment='left',
                 verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

    plot_filename = datetime.now().strftime(
        '%Y%m%d') + 'Case_Comparison_Daily_Variation_' + file_name + '_Duration_Curve.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


# -------------------  Plot Variable  Versus Duration Curve  --------------------
#     pal = ['violet'] + ['lightgreen']
#
#     fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharex=True)
#     sns.ecdfplot(data=var_comparison_df, x="DA LMP", hue="Case", palette=pal, ax=axes[0])
#     axes[0].set_xlabel('$/MW-hr')
#     axes[0].set_title('Duration vs. DA LMP')
#     axes[0].set_ylabel('Duration (%)')
#     axes[0].set_xscale('log')
#     axes[0].grid(b=True, which='both', color='k', linestyle=':')
#     axes[0].minorticks_on()
#     # axes[0].tick_params(axis='both', which='major', labelsize=17)
#
#     # if stats:
#     #     text = "               Mean    Median \n"
#     #     for case in cases:
#     #         case_df = var_daily_comparison_df.loc[var_comparison_df['Case'] == case]
#     #         case_data = np.array(case_df['DA LMP'].values.tolist())
#     #         mean = np.mean(case_data[~np.isnan(case_data)])
#     #         median = np.median(case_data[~np.isnan(case_data)])
#     #         text = text + case + " = " + str(round(mean)) + "     " + str(round(median)) + "\n"
#     #     axes[0].text(0.5, 0.2, text, size=10, horizontalalignment='left',
#     #              verticalalignment='center', transform=axes[0].transAxes, bbox=dict(fc="white"))
#
#     sns.ecdfplot(data=var_daily_comparison_df, x="DA LMP", hue="Case", palette=pal, ax=axes[1])
#     axes[1].set_xlabel('$/MW-hr')
#     axes[1].set_title('Duration vs. Daily Variation in DA LMP')
#     axes[1].set_ylabel('Duration (%)')
#     # axes[1].set_xscale('log')
#     axes[1].set_xlim(right=150)
#     axes[1].grid(b=True, which='both', color='k', linestyle=':')
#     axes[1].minorticks_on()
#     # axes[1].tick_params(axis='both', which='major', labelsize=17)
#
#     if stats:
#         text = "               Mean    Median \n"
#         for case in cases:
#             case_df = var_daily_comparison_df.loc[var_daily_comparison_df['Case'] == case]
#             case_data = np.array(case_df['DA LMP'].values.tolist())
#             mean = np.mean(case_data[~np.isnan(case_data)])
#             median = np.median(case_data[~np.isnan(case_data)])
#             text = text + case + " = " + str(round(mean)) + "     " + str(round(median)) + "\n"
#         axes[1].text(0.5, 0.2, text, size=10, horizontalalignment='left',
#                  verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))


if __name__ == '__main__':
    pd.set_option('display.max_columns', 50)

    # ------------ Selection of DSO and Day  ---------------------------------
    DSO_num = '2'  # Needs to be non-zero integer
    day_num = '9'  # Needs to be non-zero integer
    # Set day range of interest (1 = day 1)
    day_range = range(2, 3)  # 1 = Day 1. Starting at day two as agent data is missing first hour of run.
    dso_range = range(1, 9)  # 1 = DSO 1 (end range should be last DSO +1)

    #  ------------ Select folder locations for different cases ---------

    data_path = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2\\V1.1-1317-gfbf326a2\MR-Batt\lean_8_bt'
    # data_path = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2'
    metadata_path = 'C:\\Users\\reev057\\PycharmProjects\TESP\src\examples\analysis\dsot\data'
    ercot_path = 'C:\\Users\\reev057\\PycharmProjects\TESP\src\examples\analysis\dsot\data'
    base_case = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2\\v1.1-1545-ga2893bd8'
    batt_case = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2\\v1.1-1567-g8cb140e1'
    Output_path = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2\\v1.1-1567-g8cb140e1'
    trans_case = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2\\V1.1-1317-gfbf326a2\MR-Flex\lean_8_fl'
    config_path = 'C:\\Users\\reev057\PycharmProjects\TESP\src\examples\dsot_v3'
    case_config_name = '200_system_case_config.json'

    case_config_file = config_path + '\\' + case_config_name
    agent_prefix = '/DSO_'
    GLD_prefix = '/Substation_'
    case_config = load_json(config_path, case_config_name)
    metadata_file = case_config['dsoPopulationFile']
    dso_meta_file = metadata_path + '\\' + metadata_file

    # Check if there is a plots folder - create if not.
    check_folder = os.path.isdir(data_path + '\\plots')
    if not check_folder:
        os.makedirs(data_path + '\\plots')

    # ---------- Flags to turn on and off plot types etc
    LoadExData = True  # load example data frames of GLD and agent data

    Cases = ['MR BAU', 'MR Batt']
    Data_paths = [base_case, batt_case]
    Variables = ['DA LMP', 'RT LMP', 'Total Load']

    for Variable in Variables:
        plot_lmp_stats(Cases, Data_paths, Output_path, DSO_num, Variable)
