# Copyright (C) 2021-2024 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: case_comparison_plots.py
import os
from datetime import datetime

import waterfall_chart
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import tesp_support.dsot.plots as pt


def rec_diff(d1, d2):
    diff = dict()
    for k,v1 in d1.items():
        if isinstance(v1, dict):
            diff[k] = rec_diff(v1, d2[k])
        else:
            diff[k] = v1 - d2[k]
    return diff


def plot_annual_stats(cases, data_paths, output_path, dso_num, variable):
    """ Will plot LMPS by month, duration, and versus netloads loads (for select month), and save to file.
    Args:
        cases (List[str]): names of the cases
        data_paths (str): location of the data files to be used.
        output_path (str): path of the location where output (plots, csv) should be saved
        dso_num (str): bus number for LMP data to be plotted
        variable (str):
    Returns:
        saves dso lmps plots to file
        """

    large_font = True
    if large_font:
        label_size = 17
        title_size = 17
        num_size = 14
        legend_font = 15
    else:
        label_size = 17
        num_size = 14
        legend_font = 17

    stats = True
    include_stdev = False
    box_plot = True

    if variable == 'DA LMP':
        old_variable = 'da_lmp'
        title_name = 'Day Ahead LMP'
        file_name = 'DA_LMP'
        upper_limit = 60
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
    elif variable in ['Total Load', 'Hybrid']:
        old_variable = 'Total Load'
        title_name = 'Total System Load'
        file_name = 'Total_Load'
        upper_limit = 80000
        lower_limit = 0
        units = 'MW'
        Log = False
    elif variable == 'Renewable Percent':
        old_variable = 'Renewable Percent'
        title_name = 'System Renewable Generation (%)'
        file_name = 'Renew_Pct'
        upper_limit = 100
        lower_limit = 0
        units = '%'
        Log = False
    elif variable == 'Curtailment Percent':
        old_variable = 'Curtailment Percent'
        title_name = 'Renewable Curtailment (% System Load)'
        file_name = 'Curtail_Pct'
        upper_limit = 100
        lower_limit = 0
        units = '%'
        Log = False

    for i in range(len(cases)):
        case = cases[i]
        data_path = data_paths[i]
        if variable == 'DA LMP':
            var_df = pd.read_csv(data_path + '/Annual_DA_LMP_Load_data.csv', index_col=[0])
        elif variable == 'RT LMP':
            var_df = pd.read_csv(data_path + '/Annual_RT_LMP_Load_data.csv', index_col=[0])
        elif variable in ['Total Load', 'Hybrid']:
            var_df = pd.read_csv(data_path + '/DSO_Total_Loads.csv', index_col='time', parse_dates=True)
        elif variable in ['Renewable Percent', 'Curtailment Percent']:
            var_df = pd.read_csv(data_path + '/DSO_Total_Loads.csv', index_col='time', parse_dates=True)
            gen_df = pt.load_ames_data(data_path, range(1, 365))
            path = "../../../examples/dsot_data"
            name = os.path.join(path + '/high_renew.csv')
            renew_tape = pd.read_csv(name, index_col='time')
            renew_tape['Total_Renew_Tape'] = renew_tape.sum(axis=1)
            var_df = pd.merge(var_df, renew_tape['Total_Renew_Tape'], left_index=True, right_index=True)
            var_df['Thermal Gen'] = gen_df.loc[:, gen_df.columns[gen_df.columns.str.contains('coal|gas|nuc')]].sum(axis=1)
            var_df['Total Gen'] = gen_df[' TotalGen'] + var_df['PV']
            var_df['Renewable Percent'] = 100*(1 - (var_df['Thermal Gen'] / (var_df['Total Gen'])))
            var_df['Curtailment Percent'] = 100*(var_df['Total_Renew_Tape'] - (var_df['Total Gen'] - var_df['Thermal Gen'])) / (var_df['Total Gen'])
            curtailment = (var_df['Total_Renew_Tape'] - (var_df['Total Gen'] - var_df['Thermal Gen'])).sum()
            curtailment_pct = curtailment / var_df['Total Gen'].sum()

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
    if variable == 'Hybrid':
        for i in range(len(cases)):
            case = cases[i]
            data_path = data_paths[i]
            var2_df = pd.read_csv(data_path + '/Annual_DA_LMP_Load_data.csv', index_col=[0])
            var2_df = var2_df.set_index(pd.to_datetime(var2_df.index))
            var2_df['Month'] = var2_df.index.month
            var2_df = var2_df[['da_lmp' + dso_num, 'Month']]
            var2_df.rename(columns={'da_lmp' + dso_num: 'DA LMP'}, inplace=True)
            var2_df['Case'] = case
            if i == 0:
                var2_comparison_df = var2_df
            else:
                var2_comparison_df = pd.concat([var2_comparison_df, var2_df])


        fig, axes = plt.subplots(2, 1, figsize=(11, 10), sharex=True)
        pal = ['violet'] + ['lightgreen'] + ["gold"] + ['skyblue']
        pal = pal[0:len(cases)]

        sns.boxplot(data=var_comparison_df, x='Month', y=variable, hue='Case', ax=axes[0], palette=pal)
        axes[0].set_ylabel(units, fontsize=label_size)
        axes[0].set_title('Variation in ' + title_name + ' over the Year', fontsize=title_size)
        axes[0].set_xlabel('', fontsize=label_size)
        axes[0].tick_params(axis='both', which='major', labelsize=num_size)
        # axes[0].set_ylim(top=upper_limit, bottom=lower_limit)
        handles, labels = axes[0].get_legend_handles_labels()
        axes[0].legend(handles=handles, labels=labels, framealpha=1, fontsize=legend_font)

        sns.boxplot(data=var2_comparison_df, x='Month', y='DA LMP', hue='Case', ax=axes[1], palette=pal)
        axes[1].set_ylabel('$/MW-hr', fontsize=label_size)
        axes[1].set_title('Variation in DA LMP over the Year', fontsize=title_size)
        axes[1].set_xlabel('Month', fontsize=label_size)
        axes[1].tick_params(axis='both', which='major', labelsize=num_size)

        handles, labels = axes[1].get_legend_handles_labels()
        axes[1].legend(handles=handles, labels=labels, framealpha=1, fontsize=legend_font)

        plot_filename = datetime.now().strftime(
            '%Y%m%d') + 'Case_Compare_Hybrid_Annual_Box_Plots-focused-SBS.png'
        file_path_fig = os.path.join(output_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

    else:
        if include_stdev:
            fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
        else:
            fig, axes = plt.subplots(2, 1, figsize=(11, 10), sharex=True)
        pal = ['violet'] + ['lightgreen'] + ["gold"] + ['skyblue']
        # pal = sns.color_palette("Paired")
        pal = pal[0:len(cases)]

        if box_plot:
            sns.boxplot(data=var_comparison_df, x='Month', y=variable, hue='Case', ax=axes[0], palette=pal)
        else:
            sns.violinplot(data=var_comparison_df, x='Month', y=variable, hue='Case', ax=axes[0], palette=pal)
        axes[0].set_ylabel(units)
        axes[0].set_title('Variation in ' + title_name + ' over the Year')
        axes[0].set_xlabel('')
        axes[0].set_ylim(top=upper_limit, bottom=lower_limit)
        handles, labels = axes[0].get_legend_handles_labels()
        axes[0].legend(handles=handles, labels=labels, framealpha=1)

        if box_plot:
            sns.boxplot(data=var_daily_comparison_df, x='Month', y=variable, hue='Case', ax=axes[1], palette=pal)
        else:
            sns.violinplot(data=var_daily_comparison_df, x='Month', y=variable, hue='Case', ax=axes[1], palette=pal)
        axes[1].set_ylabel(units)
        axes[1].set_title('Variation in Daily Change in ' + title_name + ' over the Year')
        axes[1].set_xlabel('Month')
        if variable == 'Renewable Percent':
            axes[1].set_ylim(top=upper_limit, bottom=lower_limit)
        else:
            axes[1].set_ylim(top=upper_limit / 1.8, bottom=lower_limit)
        handles, labels = axes[1].get_legend_handles_labels()
        axes[1].legend(handles=handles, labels=labels, framealpha=1)

        if include_stdev:
            if box_plot:
                sns.boxplot(data=var_daily_comparison_df, x='Month', y=variable + ' STD', hue='Case', ax=axes[2], palette=pal)
            else:
                sns.violinplot(data=var_daily_comparison_df, x='Month', y=variable + ' STD', hue='Case', ax=axes[2],
                            palette=pal)
            axes[2].set_ylabel(units)
            axes[2].set_title('Standard Deviation of Daily ' + title_name + ' over the Year')
            axes[2].set_xlabel('Month')
            axes[2].set_ylim(top=upper_limit/3, bottom=lower_limit)
            handles, labels = axes[2].get_legend_handles_labels()
            axes[2].legend(handles=handles, labels=labels, framealpha=1)

        plot_filename = datetime.now().strftime(
            '%Y%m%d') + 'Case_Compare_' + file_name + ' _Annual_Box_Plots-focused-SBS.png'
        file_path_fig = os.path.join(output_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

    # ============================

        # pal = ['violet'] + ['lightgreen'] + ['khaki']
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
                text = text + case + " = " + str(round(mean, 1)) + "     " + str(round(median, 1)) + "\n"
            plt.text(0.4, 0.1, text, size=10, horizontalalignment='left',
                     verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

        plot_filename = datetime.now().strftime('%Y%m%d') + 'Case_Comparison_' + file_name + '_Duration_Curve.png'
        file_path_fig = os.path.join(output_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        # ----- Daily Variation Curve
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
                text = text + case + " = " + str(round(mean,1)) + "     " + str(round(median,1)) + "\n"
            plt.text(0.4, 0.1, text, size=10, horizontalalignment='left',
                     verticalalignment='center', transform=ax.transAxes, bbox=dict(fc="white"))

        plot_filename = datetime.now().strftime('%Y%m%d') + 'Case_Comparison_Daily_Variation_' + file_name + '_Duration_Curve.png'
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


def reduction_by_class(cases, data_paths, output_path,  variable):
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
    include_stdev = False
    box_plot = False

    if variable == 'Load':
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

    # for i in range(len(cases)):
    #     case = cases[i]
    #     data_path = data_paths[i]
    #     if variable == 'Load':
    var_df = pd.read_csv(data_paths[0] + '/DSO_load_stats.csv', index_col=[0])

    comp_df = pd.read_csv(data_paths[1] + '/DSO_load_stats.csv', index_col=[0])

    var_df.loc['Max', :] = var_df.loc['Max', :].apply(pd.to_numeric, errors='ignore')
    comp_df.loc['Max', :] = comp_df.loc['Max', :].apply(pd.to_numeric, errors='ignore')

    delta_df = var_df.loc['Max', :].subtract(comp_df.loc['Max', :]) #.divide(var_df.loc['Max', :])
        # elif variable == 'RT LMP':
        #     var_df = pd.read_csv(data_path + '/Annual_RT_LMP_Load_data.csv', index_col=[0])
        # elif variable == 'Total Load':
        #     var_df = pd.read_csv(data_path + '/DSO_Total_Loads.csv', index_col='time', parse_dates=True)


def dso_cfs_delta(cases_list, data_paths_list, dso_range, metadata_file):
    """Will plot LMPS by month, duration, and versus netloads loads (for select month), and save to file.
    Arguments:
        cases
        data_paths (list): location of the data files to be used.
        output_path (str): path of the location where output (plots, csv) should be saved
        dso_num (str): bus number for LMP data to be plotted
    Returns:
        saves dso lmps plots to file
        """
    assumptions = []
    cases = []
    benefits = []

    for i in range(len(cases_list)):
        results_path = data_paths_list[i][1]
        comp_path = data_paths_list[i][0]

        path = "../../../examples/dsot_data"

        # data = pt.load_json(path, 'sankey_delta_cost_structure.json')

        customer_costs = pd.read_csv(results_path + '/Customer_CFS_Summary.csv', index_col=[0])
        customer_costs_comp = pd.read_csv(comp_path + '/Customer_CFS_Summary.csv', index_col=[0])
        customer_costs_delta = customer_costs.subtract(customer_costs_comp)
        # dso_cfs = pd.read_csv(results_path + '/DSO_CFS_Summary.csv')
        # dso_cfs = dso_cfs.set_index(dso_cfs.columns[0])
        # dso_cfs_comp = pd.read_csv(comp_path + '/DSO_CFS_Summary.csv', index_col=False)
        # dso_cfs_comp.set_index(pd.Index(dso_cfs_comp.iloc[:,0].tolist()), inplace=True)
        # dso_cfs_comp.iloc[:,0].tolist()
        metadata = pt.load_json(path, metadata_file)

        Dist_Hardware = 0
        Software = 0
        Labor = 0
        WorkSpace = 0
        transmission = 0
        ancilliary_services = 0
        energy_purchases = 0
        capacity_payments = 0
        der_investment = 0

        # cfs_elements = ['Dist_Hardware', 'Software', 'Labor', 'WorkSpace', 'Transmission', 'ancilliary_services',
        #     'energy_purchases', 'capacity_payments', 'der_investment']
        cfs_elements = ['NetBenefits', 'NetBenefitsPct', 'DSO Type', 'PeakLoadReductionPct', 'Number of Customers']
        dso_cfs_df = pd.DataFrame(index=[str(dso_range[0])],
                                    columns=cfs_elements)

        # Compile data for all DSOs:
        for dso in dso_range:
            revenue = pt.load_json(results_path, 'DSO' + str(dso)+'_Revenues_and_Energy_Sales.json')
            expenses = pt.load_json(results_path, 'DSO' + str(dso)+'_Expenses.json')
            capital_costs = pt.load_json(results_path, 'DSO' + str(dso) + '_Capital_Costs.json')
            wholesale = pt.load_json(results_path, 'DSO' + str(dso) + '_Market_Purchases.json')

            revenue_comp = pt.load_json(comp_path, 'DSO' + str(dso)+'_Revenues_and_Energy_Sales.json')
            expenses_comp = pt.load_json(comp_path, 'DSO' + str(dso)+'_Expenses.json')
            capital_costs_comp = pt.load_json(comp_path, 'DSO' + str(dso) + '_Capital_Costs.json')
            wholesale_comp = pt.load_json(comp_path, 'DSO' + str(dso) + '_Market_Purchases.json')

            revenue_delta = rec_diff(revenue, revenue_comp)
            expenses_delta = rec_diff(expenses, expenses_comp)
            capital_costs_delta = rec_diff(capital_costs, capital_costs_comp)
            wholesale_delta = rec_diff(wholesale, wholesale_comp)

            # DSO Items
            Dist_Hardware += sum(capital_costs_delta['DistPlant'].values())
            dso_software = sum(capital_costs_delta['InfoTech']['MktSoftHdw'].values()) + \
                sum(capital_costs_delta['InfoTech']['AMIDERNetwork'].values()) + capital_costs_delta['InfoTech']['DaNetwork'] + \
                capital_costs_delta['InfoTech']['DmsSoft'] + capital_costs_delta['InfoTech']['OmsSoft'] + \
                capital_costs_delta['InfoTech']['CisSoft'] + capital_costs_delta['InfoTech']['BillingSoft']
            Software += dso_software

            dso_labor = expenses_delta['O&mMaterials'] +sum(expenses_delta['O&mLabor'].values()) + expenses_delta['Admin'] +  \
                sum(expenses_delta['RetailOps'].values()) + sum(expenses_delta['AmiCustOps']['AmiOps'].values()) + \
                sum(expenses_delta['AmiCustOps']['CustOps'].values()) + sum(expenses_delta['AmiCustOps']['DmsOps'].values())
            Labor += dso_labor
            WorkSpace += expenses_delta['Space']

            # Wholesale items
            transmission += expenses_delta['TransCharges']
            ancilliary_services += expenses_delta['OtherWholesale']['WhReserves']
            energy_purchases += sum(expenses_delta['WhEnergyPurchases'].values())
            capacity_payments += expenses_delta['PeakCapacity']

            # Customer items
            # Customer Costs and Savings
            num_of_cust = metadata['DSO_' + str(dso)]['number_of_customers']
            der_investment += customer_costs_delta.loc['Investment', str(dso)] * num_of_cust / 1000

            dso_cfs_df.loc[str(dso), 'NetBenefits'] = -expenses_delta['PeakCapacity']-sum(expenses_delta['WhEnergyPurchases'].values())\
                                                      -expenses_delta['TransCharges']-expenses_delta['OtherWholesale']['WhReserves']\
                                                      -sum(capital_costs_delta['DistPlant'].values())-dso_labor-dso_software-expenses_delta['Space']
            dso_cfs_df.loc[str(dso), 'NetBenefitsPct'] = 100 * dso_cfs_df.loc[str(dso), 'NetBenefits'] / revenue_comp['RequiredRevenue']
            dso_cfs_df.loc[str(dso), 'PeakLoadReductionPct'] = -100*wholesale_delta['WhEnergyPurchases']['WholesalePeakLoadRate'] / wholesale_comp['WhEnergyPurchases']['WholesalePeakLoadRate']
            dso_cfs_df.loc[str(dso), 'EnergyCostReductionPct'] = -100*sum(expenses_delta['WhEnergyPurchases'].values()) / sum(expenses_comp['WhEnergyPurchases'].values())
            dso_cfs_df.loc[str(dso), 'DSO Type'] = metadata['DSO_'+str(dso)]['utility_type']
            dso_cfs_df.loc[str(dso), 'Number of Customers'] = metadata['DSO_'+str(dso)]['number_of_customers']

    # https://plotly.com/python/waterfall-charts/
    # https://www.machinelearningplus.com/waterfall-plot-in-python/

        labels = ['Capacity Payments',
                  'Energy Purchases',
                  'Transmission Costs',
                  'Ancillary Services',
                  'Distribution Hardware',
                  'O&M/Labor',
                  'IT/Software',
                  'Workspace',
                  'Asset Investments']

        values = [-capacity_payments,
                  -energy_purchases,
                  -transmission,
                  -ancilliary_services,
                  -Dist_Hardware,
                  -Labor,
                  -Software,
                  -WorkSpace,
                  -der_investment]

        values_low = [-capacity_payments/2,
                  -energy_purchases,
                  -transmission,
                  -ancilliary_services,
                  -Dist_Hardware,
                  -Labor,
                  -Software,
                  -WorkSpace,
                  -der_investment]

        values_high = [-capacity_payments*91/75,
                  -energy_purchases,
                  -transmission,
                  -ancilliary_services,
                  -Dist_Hardware,
                  -Labor,
                  -Software,
                  -WorkSpace,
                  -der_investment]

        values = [value / 1e3 for value in values]
        values_low = [value / 1e3 for value in values_low]
        values_high = [value / 1e3 for value in values_high]
        net_benefit = sum(values)
        net_benefit_low = sum(values_low)
        net_benefit_high = sum(values_high)

        waterfall_chart.plot(labels, values, sorted_value=True, rotation_value=90, net_label='Net Benefit', y_lab='Annual Impact ($M)')
        plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_CFS_Waterfall_ranked.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        waterfall_chart.plot(labels, values, rotation_value=90, net_label='Net Benefit', y_lab='Annual Impact ($M)')
        plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_CFS_Waterfall.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        waterfall_chart.plot(labels, values_low, rotation_value=90, net_label='Net Benefit (Low)', y_lab='Annual Impact ($M)')
        plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_CFS_Waterfall_low.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        plt.figure(figsize=(6, 4))
        sns.scatterplot(
            data=dso_cfs_df,
            x="PeakLoadReductionPct", y="NetBenefitsPct", hue="DSO Type"
            # ci="sd", palette="dark", alpha=.6, height=4
        )

        m, b = np.polyfit(dso_cfs_df['PeakLoadReductionPct'].astype('float'), dso_cfs_df['NetBenefitsPct'].astype('float'), 1)
        x = pd.Series(np.linspace(dso_cfs_df['PeakLoadReductionPct'].min(), dso_cfs_df['PeakLoadReductionPct'].max(), 10))
        plt.plot(x, m*x + b, color='grey', linestyle='dotted')

        plt.xlabel("Coincident Peak Load Reduction (%)", size=12)
        plt.ylabel("Annual DSO Savings (%)", size=12)
        # plt.xlim(0, 11)
        # plt.ylim(0, 11)
        plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_CFS_Benefits_Load_Scatter.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        plt.figure(figsize=(6, 4))
        sns.scatterplot(
            data=dso_cfs_df,
            x="Number of Customers", y="NetBenefitsPct", hue="DSO Type"
        )

        m, b = np.polyfit(dso_cfs_df['Number of Customers'].astype('float'), dso_cfs_df['NetBenefitsPct'].astype('float'), 1)
        x = pd.Series(np.linspace(dso_cfs_df['Number of Customers'].min(), dso_cfs_df['Number of Customers'].max(), 10))
        plt.plot(x, m*x + b, color='grey', linestyle='dotted')

        plt.xlabel("Number of Customers", size=12)
        plt.ylabel("Annual DSO Savings (%)", size=12)
        # plt.xlim(0, 11)
        # plt.ylim(0, 11)
        plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_CFS_Benefits_Cust_Scatter.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        plt.figure(figsize=(6, 4))
        sns.scatterplot(
            data=dso_cfs_df,
            x="EnergyCostReductionPct", y="NetBenefitsPct", hue="DSO Type"
        )

        m, b = np.polyfit(dso_cfs_df['EnergyCostReductionPct'].astype('float'),
                          dso_cfs_df['NetBenefitsPct'].astype('float'), 1)
        x = pd.Series(np.linspace(dso_cfs_df['EnergyCostReductionPct'].min(), dso_cfs_df['EnergyCostReductionPct'].max(), 10))
        plt.plot(x, m * x + b, color='grey', linestyle='dotted')

        plt.xlabel("Wholesale Energy Cost Reduction (%)", size=12)
        plt.ylabel("Annual DSO Savings (%)", size=12)
        # plt.xlim(0, 11)
        # plt.ylim(0, 11)
        plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_CFS_Benefits_Energy_Scatter.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

        assumptions.extend(['High', 'Nominal', 'Low'])
        cases.extend([cases_list[i][1], cases_list[i][1], cases_list[i][1]])
        benefits.extend([net_benefit_high, net_benefit, net_benefit_low])

    # Add data to dataframe for summary plot
    benefits_sum = {'Assumption': assumptions,
                'Case': cases,
                'Annual Net Benefit ($M)': benefits}

    summary_benefits_df = pd.DataFrame(benefits_sum, columns = ['Assumption', 'Case', 'Annual Net Benefit ($M)'])

    plt.figure(figsize=(20, 10))
    sns.catplot(
        data=summary_benefits_df, kind="bar",
        x="Case", y="Annual Net Benefit ($M)", hue="Assumption",
        ci="sd", palette="dark", alpha=.6, height=4
    )
    plt.xlabel("Case", size=12)
    plt.ylabel("Annual Net Benefit ($M)", size=12)
    plot_filename = datetime.now().strftime('%Y%m%d') + 'DSO_CFS_Benefits_Summary.png'
    file_path_fig = os.path.join(results_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')
    # plt.despine(left=True)
    # plt.set_axis_labels("", "Body mass (g)")


def customer_cfs_delta(cases, data_paths, output_path, metadata_file):
    """Will plot customer population CFS savings comparisons.
    Arguments:
        data_paths (str): location of the data files to be used.
        output_path (str): path of the location where output (plots, csv) should be saved
    Returns:
        saves dso lmps plots to file
        """

    '''
    commercial versus residential savings
    multi-family versus single vs manufactured home
    HR: solar versus no solar
    HR: ev versus battery versus both.
    Rural, Urban, Suburban
    '''
    # dso
    # building_type
    # tariff_class
    # sqft
    # battery_capacity
    # pv_capacity
    # cust_participating
    # slider_setting
    # cooling
    # heating
    # wh_gallons
    # Bills
    # Capital Investment
    # NetEnergyCost
    # EnergyPurchased
    # BlendedRate
    # EffectiveCostEnergy

    path = "../../../examples/dsot_data"
    metadata = pt.load_json(path, metadata_file)

    # Load customer CFS dataframes:
    cust_cfs_file = data_paths[1] + '/Master_Customer_Dataframe.h5'
    customer_cfs_df = pd.read_hdf(cust_cfs_file, key='customer_data', mode='r')

    cust_comp_cfs_file = data_paths[0] + '/Master_Customer_Dataframe.h5'
    customer_comp_cfs_df = pd.read_hdf(cust_comp_cfs_file, key='customer_data', mode='r')

    # Calculate savings (gross and net of DER investments
    customer_cfs_df['bill_savings_abs'] = customer_comp_cfs_df['Bills'].subtract(customer_cfs_df['Bills'])
    customer_cfs_df['bill_savings_pct'] = 100*customer_comp_cfs_df['Bills'].subtract(customer_cfs_df['Bills']).divide(customer_comp_cfs_df['Bills'])
    # base case PV can result in annual bills close to $0.  This can make percent bill savings go asymtotic on a small number of customers.
    customer_cfs_df['bill_savings_pct'] = np.clip(customer_cfs_df['bill_savings_pct'], a_max=100, a_min=-100)

    customer_cfs_df['net_energy_cost_savings'] = customer_comp_cfs_df['NetEnergyCost'].subtract(customer_cfs_df['NetEnergyCost'])
    customer_cfs_df['net_energy_cost_savings_pct'] = 100*customer_comp_cfs_df['NetEnergyCost'].subtract(customer_cfs_df['NetEnergyCost']).divide(customer_comp_cfs_df['NetEnergyCost'])

    customer_cfs_df['base_energy_purchased'] = customer_comp_cfs_df['EnergyPurchased']
    customer_cfs_df['base_peak_load'] = customer_comp_cfs_df['PeakLoad']
    customer_cfs_df['base_bills'] = customer_comp_cfs_df['Bills']
    customer_cfs_df['base_net_energy_expense'] = customer_comp_cfs_df['NetEnergyCost']
    customer_cfs_df['net_energy_purchased'] = customer_comp_cfs_df['EnergyPurchased'].subtract(customer_cfs_df['EnergyPurchased'])
    customer_cfs_df['net_energy_purchased_pct'] = 100*customer_comp_cfs_df['EnergyPurchased'].subtract(customer_cfs_df['EnergyPurchased']).divide(customer_comp_cfs_df['EnergyPurchased'])
    customer_cfs_df['net_energy_purchased_pct'] = np.clip(customer_cfs_df['net_energy_purchased_pct'], a_max=100, a_min=-100)

    customer_cfs_df['peak_load_reduction'] = customer_comp_cfs_df['PeakLoad'].subtract(customer_cfs_df['PeakLoad'])
    customer_cfs_df['peak_load_reduction_pct'] = 100*customer_comp_cfs_df['PeakLoad'].subtract(customer_cfs_df['PeakLoad']).divide(customer_comp_cfs_df['PeakLoad'])

    cust_pop_stats = pd.DataFrame(index=['Annual Energy Consumption (kW-hrs)', 'Peak Load (kW)', 'Annual Utility Bill ($)', 'Net Energy Expenses ($)'],
                            columns=['comm part '+cases[0], 'comm nonpart '+cases[0], 'comm part '+cases[1], 'comm nonpart '+cases[1],
                                     'res part '+cases[0], 'res nonpart '+cases[0], 'res part '+cases[1], 'res nonpart '+cases[1]])

    list1 = [['residential','res'], ['commercial','comm']]
    list2 = [[False,' nonpart '], [True,' part ']]

    for type in list1:
        for part in list2:
            case = customer_cfs_df[customer_cfs_df['tariff_class'] == type[0]]
            case = case[case['cust_participating'] == part[0]]

            cust_pop_stats.loc['Annual Energy Consumption (kW-hrs)', type[1]+ part[1] +cases[0]] = case['base_energy_purchased'].mean()
            cust_pop_stats.loc['Annual Energy Consumption (kW-hrs)', type[1]+ part[1] +cases[1]] = case['EnergyPurchased'].mean()
            cust_pop_stats.loc['Peak Load (kW)', type[1]+ part[1] +cases[0]] = case['base_peak_load'].mean()
            cust_pop_stats.loc['Peak Load (kW)', type[1]+ part[1] +cases[1]] = case['PeakLoad'].mean()
            cust_pop_stats.loc['Annual Utility Bill ($)', type[1]+ part[1] +cases[0]] = case['base_bills'].mean()
            cust_pop_stats.loc['Annual Utility Bill ($)', type[1]+ part[1] +cases[1]] = case['Bills'].mean()
            cust_pop_stats.loc['Net Energy Expenses ($)', type[1]+ part[1] +cases[0]] = case['base_net_energy_expense'].mean()
            cust_pop_stats.loc['Net Energy Expenses ($)', type[1]+ part[1] +cases[1]] = case['NetEnergyCost'].mean()

    cust_pop_stats.to_csv(path_or_buf=data_paths[1] + '/Customer_pop_stats.csv')

    # Define parameters and variables to be analyzed.
    subpopulation = 'Residential'
    # subpopulation = None

    customer_cfs_df['building_type'].replace({'SINGLE_FAMILY': 'Single-family', 'MOBILE_HOME': 'Manufactured home', 'MULTI_FAMILY': 'Multi-family'}, inplace=True)
    customer_comp_cfs_df['building_type'].replace(
        {'SINGLE_FAMILY': 'Single-family', 'MOBILE_HOME': 'Manufactured home', 'MULTI_FAMILY': 'Multi-family'},
        inplace=True)
    customer_cfs_df['heating'].replace(
        {'GAS': 'Gas', 'RESISTANCE': 'Resistance', 'HEAT_PUMP': 'Heat pump'},
        inplace=True)
    customer_comp_cfs_df['heating'].replace(
        {'GAS': 'Gas', 'RESISTANCE': 'Resistance', 'HEAT_PUMP': 'Heat pump'},
        inplace=True)
    customer_cfs_df['tariff_class'].replace(
        {'residential': 'Residential', 'commercial': 'Commercial'},
        inplace=True)
    customer_comp_cfs_df['tariff_class'].replace(
        {'residential': 'Residential', 'commercial': 'Commercial'},
        inplace=True)

    customer_cfs_df.rename(columns={"building_type": "Building Type"}, inplace=True)
    customer_comp_cfs_df.rename(columns={"building_type": "Building Type"}, inplace=True)


    customer_class = ['Residential', 'Commercial']
    building_type = ['Single-family', 'Manufactured home', 'Multi-family', "office", "warehouse_storage", "big_box",
                     "strip_mall", "education", "food_service", "food_sales", "lodging", "healthcare_inpatient", "low_occupancy"]
    # solar_type = [True, False]
    dsos = [1, 2, 3, 4, 5, 6, 7, 8]
    dsos = [1, 2, 3, 4, 5, 7, 8, 15, 16, 23, 26, 43, 48, 51, 52, 54, 55, 59, 69, 76, 77, 78, 79, 80, 83, 86, 89, 98, 100,
            104, 110, 115, 117, 123, 125, 127, 140, 161, 166, 197]

    heating = ['Gas', 'Resistance', 'Heat pump']
    der_participation = [' None', ' EV', ' Battery', ' EV, Battery', ' HVAC', ' WH', ' HVAC, WH', ' HVAC, EV', ' WH, EV', ' HVAC, WH, EV']
    participation = [True, False]
    hr_bau_participation = ['None', ' EV', ' PV', ' EV, PV']

    dso_type = {'Urban': [],
                'Suburban': [],
                'Rural': []}

    for DSO in metadata.keys():
        if 'DSO' in DSO:
            if DSOmetadata[DSO]['used']:
                dso_type[DSOmetadata[DSO]['utility_type']].append(int(DSO.split('_')[-1]))

    # Determine participating DER mix for each customer:

    #None, WH, HVAC, WH+HVAC, WH+HVAC+EV, EV only, EV+Battery,

    customer_cfs_df.set_index('Customer ID', inplace = True)

    for customer in customer_cfs_df.index.values:
        DER_list = ''
        if not customer_cfs_df.loc[customer, 'cust_participating']:
            customer_cfs_df.loc[customer, 'DER_participating'] = ' None'
        else:
            if customer_cfs_df.loc[customer, 'hvac_participating']:
                DER_list = DER_list + ' HVAC,'
            if customer_cfs_df.loc[customer, 'wh_participating']:
                DER_list = DER_list + ' WH,'
            if customer_cfs_df.loc[customer, 'ev_participating']:
                DER_list = DER_list + ' EV,'
            if customer_cfs_df.loc[customer, 'batt_participating']:
                DER_list = DER_list + ' Battery,'
            customer_cfs_df.loc[customer, 'DER_participating'] = DER_list[:-1]

    customer_comp_cfs_df.set_index('Customer ID', inplace = True)

    for customer in customer_cfs_df.index.values:
        DER_list = ''
        if customer_cfs_df.loc[customer, 'ev_participating']:
            DER_list = DER_list + ' EV,'
        if customer_cfs_df.loc[customer, 'pv_participating']:
            DER_list = DER_list + ' PV,'
        if DER_list == '':
            DER_list = 'None '
        customer_comp_cfs_df.loc[customer, 'DER_participating'] = DER_list[:-1]

    if subpopulation != None:
        pop_subset = customer_cfs_df[customer_cfs_df['tariff_class'] == subpopulation]
        pop_comp_subset = customer_comp_cfs_df[customer_comp_cfs_df['tariff_class'] == subpopulation]
    else:
        pop_subset = customer_cfs_df
        pop_comp_subset = customer_comp_cfs_df

    # Bill and energy data for the BAU case
    plot_customer_pdf('tariff_class', customer_class, 'Bills', customer_comp_cfs_df, cases[0], data_paths[0])
    # plot_customer_pdf('tariff_class', customer_class, 'EnergyPurchased', customer_comp_cfs_df, cases[0], data_paths[0])

    plt.clf()
    for cust in customer_class:
        subset = customer_comp_cfs_df[customer_comp_cfs_df['tariff_class'] == cust]

        sns.distplot(subset['EnergyPurchased'], hist=True, kde=False,
                     norm_hist=True,
                     bins=200,
                     kde_kws={'shade': True, 'linewidth': 3}, label=str(cust))

    plt.legend(prop={'size': 10}, title='Customer Class', loc='upper left')
    plt.title(cases[0] + ': Energy purchases by customer class')
    plt.xlabel('Energy Purchased (kw-hrs/year)')
    plt.ylabel('Density')
    plt.xlim(0, 0.2e6)
    plot_filename = datetime.now().strftime('%Y%m%d') + 'Customer_PDF_tariff_class_EnergyPurchased.png'
    file_path_fig = os.path.join(data_paths[0], 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


    plot_customer_pdf('heating', heating, 'Bills', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('heating', heating, 'EnergyPurchased', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('heating', heating, 'PeakLoad', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('Building Type', building_type, 'Bills', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('Building Type', building_type, 'Bills', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('Building Type', building_type, 'EnergyPurchased', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('Building Type', building_type, 'PeakLoad', pop_comp_subset, cases[0], data_paths[0])

    plot_customer_pdf('DER_participating', hr_bau_participation, 'Bills', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('DER_participating', hr_bau_participation, 'EnergyPurchased', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('DER_participating', hr_bau_participation, 'PeakLoad', pop_comp_subset, cases[0], data_paths[0])

    plot_customer_pdf('pv_participating', participation, 'Bills', pop_subset, cases[0], data_paths[0])
    plot_customer_pdf('pv_participating', participation, 'EnergyPurchased', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('pv_participating', participation, 'PeakLoad', pop_comp_subset, cases[0], data_paths[0])

    # 'pv_participating': 'Rooftop Solar',
    # 'DER_participating'

    plt.figure(figsize=(6, 4))
    sns.scatterplot(
        data=pop_subset,
        x="sqft", y="EnergyPurchased", hue="Building Type"
        # ci="sd", palette="dark", alpha=.6, height=4
    )
    m, b = np.polyfit(pop_subset['sqft'].astype('float'), pop_subset['EnergyPurchased'].astype('float'), 1)
    x = pd.Series(np.linspace(pop_subset['sqft'].min(), pop_subset['sqft'].max(), 10))
    plt.plot(x, m * x + b, color='black', linestyle='dashed')

    plt.xlabel("House Size (SqFt)", size=12)
    plt.ylabel("Energy Purchased (kw-hrs/year)", size=12)
    plt.xlim(100, 6500)
    # plt.ylim(0, 11)
    plot_filename = datetime.now().strftime('%Y%m%d') + 'House_sqft_energy_Scatter.png'
    file_path_fig = os.path.join(data_paths[0], 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    pop_subset = customer_cfs_df[customer_cfs_df['cust_participating'] == True]

    # Plot participating customer savings by customer class:
    plot_customer_pdf('tariff_class', customer_class, 'bill_savings_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('tariff_class', customer_class, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('tariff_class', customer_class, 'net_energy_purchased_pct', pop_subset, cases[1], data_paths[1])

    # Plot participating customer savings by building type:
    plot_customer_pdf('Building Type', building_type, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])

    if subpopulation != None:
        pop_subset = customer_cfs_df[customer_cfs_df['tariff_class'] == subpopulation]
        pop_comp_subset = customer_comp_cfs_df[customer_comp_cfs_df['tariff_class'] == subpopulation]
    else:
        pop_subset = customer_cfs_df
        pop_comp_subset = customer_comp_cfs_df

    # Plot residential customer bills by participation
    plot_customer_pdf('cust_participating', participation, 'Bills', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('cust_participating', participation, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('cust_participating', participation, 'net_energy_purchased_pct', pop_subset, cases[1], data_paths[1])

    plot_customer_pdf('cust_participating', participation, 'peak_load_reduction_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('cust_participating', participation, 'bill_savings_pct', pop_subset, cases[1],
                      data_paths[1])

    # Plot annual bills by heating type
    plot_customer_pdf('heating', heating, 'Bills', pop_subset, cases[1], data_paths[1])

    # Plot annual % savings for residential participating customers by DSO #
    pop_subset = pop_subset[pop_subset['dso'] == 1]
    plot_customer_pdf('cust_participating', participation, 'bill_savings_pct', pop_subset, cases[1],
                      data_paths[1])
    pop_subset = pop_subset[pop_subset['cust_participating'] == True]
    # plot_customer_pdf('dso', dsos, 'net_bill_savings_pct', pop_subset, cases[1], data_paths[1])

    # Plot residential customer bills by solar

    plot_customer_pdf('heating', heating, 'bill_savings_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('Building Type', building_type, 'bill_savings_pct', pop_subset, cases[1], data_paths[1])

    # Plot participating customer savings by DSO type
    plot_customer_pdf('dso', dso_type, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])
    # plot_customer_pdf('dso', dsos, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])

    # Plot residential customer bills by solar
    plot_customer_pdf('DER_participating', der_participation, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])

    pop_subset = pop_subset[pop_subset['tariff_class'] == 'Residential']

    plot_customer_pdf('pv_participating', participation, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('pv_participating', participation, 'bill_savings_pct', pop_subset, cases[1], data_paths[1])


    pop_subset = customer_cfs_df[customer_cfs_df['dso'] == 1]
    pop_subset = pop_subset[pop_subset['tariff_class'] == 'Residential']
    # plot_customer_pdf('cust_participating', participation, 'bill_savings_pct', pop_subset, cases[1],
    #                   data_paths[1])
    pop_subset = pop_subset[pop_subset['cust_participating'] == True]


    plt.figure(figsize=(6, 4))
    sns.scatterplot(
        data=pop_subset,
        x="slider_setting", y="bill_savings_pct", hue="Building Type"
        # ci="sd", palette="dark", alpha=.6, height=4
    )
    m, b = np.polyfit(pop_subset['slider_setting'].astype('float'), pop_subset['bill_savings_pct'].astype('float'), 1)
    x = pd.Series(np.linspace(pop_subset['slider_setting'].min(), pop_subset['slider_setting'].max(), 10))
    plt.plot(x, m * x + b, color='black', linestyle='dashed')

    plt.xlabel("Slider Setting", size=12)
    plt.ylabel("Annual Bill Savings (%)", size=12)
    plt.ylim(10, 30)
    # plt.ylim(0, 11)
    plot_filename = datetime.now().strftime('%Y%m%d') + 'Customer_Slider_Scatter.png'
    file_path_fig = os.path.join(data_paths[1], 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    # plt.clf()
    # plt.scatter(customer_cfs_df['slider_setting'], customer_cfs_df['net_energy_cost_savings_pct'])
    # plt.scatter(customer_cfs_df['EnergyPurchased'], customer_cfs_df['net_energy_cost_savings_pct'])
    # plt.scatter(customer_cfs_df['sqft'], customer_cfs_df['net_energy_cost_savings_pct'])
    # fig = customer_cfs_df.plot.scatter(x='slider_setting', y='net_energy_cost_savings_pct')
    # plt.show()
    # plot_filename = datetime.now().strftime('%Y%m%d') + 'Customer_PDF_scatter.png'
    # file_path_fig = os.path.join(data_paths[0], 'plots', plot_filename)
    # plt.savefig(file_path_fig, bbox_inches='tight')


def plot_customer_pdf(attribute, variables, metric, pop_df, case, output_path):
    """Will plot customer population savings comparisons.
    Arguments:
        attribute (str): customer attribute to be studied (e.g. tariff class)
        variables (list): list of variables possible for each attribute (e.g. ['residential', 'commercial'])
        metric (str): metric of interest to be plotted (e.g. 'net_bill_savings_pct')
        data_paths (str): location of the data files to be used.
        output_path (str): path of the location where output (plots, csv) should be saved
    Returns:
        saves customer pdf plots to file
        """

    xlabel_dict = {'bill_savings_pct': 'Annual Utility Bill Savings (%)',
                   'net_energy_cost_savings_pct': 'Annual Energy Costs Savings (%)',
                   'net_energy_purchased': 'Annual Energy Consumption (kW-hrs)',
                   'net_energy_purchased_pct': 'Annual Energy Savings (%)',
                   'peak_load_reduction': 'Annual Peak Load (kW)',
                   'peak_load_reduction_pct': 'Annual Peak Load Reduction (%)',
                   'Bills': 'Annual Electricity Bill ($)',
                   'PeakLoad': 'Annual Peak Load (kW)',
                   'EnergyPurchased': 'Energy Purchased (kw-hrs/year)'}

    legend_dict = {'tariff_class': 'Customer Class',
                   'cust_participating': 'Customer Participation',
                   'dso': 'DSO',
                   'dso_type': 'DSO Type',
                   'heating': 'Heating Type',
                   'Building Type': 'Building Type',
                   'pv_participating': 'Rooftop Solar',
                   'DER_participating': 'DER Participation'}

    if metric in ['bill_savings_pct', 'net_energy_cost_savings_pct']:
        x_low = -10
        x_high = 60
        # x_low = -0
        # x_high = 30
    elif metric in ['net_energy_purchased_pct']:
        x_low = -10
        x_high = 10
    elif metric in ['peak_load_reduction_pct']:
        x_low = -25
        x_high = 25
    elif metric in ['Bills']:
        x_low = 0
        x_high = 5000
    elif metric in ['EnergyPurchased']:
        x_low = 0
        x_high = 50000
    elif metric in ['PeakLoad']:
        x_low = 0
        x_high = 50
    else:
        x_low = -50
        x_high = 50

    plt.clf()
    for var in variables:
        if var in ['Rural', 'Suburban', 'Urban']:
            subset = pop_df[pop_df[attribute].isin(variables[var])]
        else:
            subset = pop_df[pop_df[attribute] == var]

    # TODO Address distplot deprecation
    # sns.displot(data=pop_df, x=metric, kind='kde', hue = attribute)

        sns.distplot(subset[metric], hist=False, kde=True,
                     norm_hist=True,
                     kde_kws={'shade': True, 'linewidth': 3}, label=str(var))

    plt.legend(prop={'size': 10}, title=legend_dict[attribute])
    plt.title(case + ': ' + xlabel_dict[metric] + ' by ' + legend_dict[attribute])
    plt.xlabel(xlabel_dict[metric])
    plt.xlim(x_low, x_high)
    plt.ylabel('Population Fraction (-)')
    plot_filename = datetime.now().strftime('%Y%m%d') + 'Customer_PDF_' + attribute + '_' + metric + '.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    plt.clf()
    for var in variables:
        if var in ['Rural', 'Suburban', 'Urban']:
            subset = pop_df[pop_df[attribute].isin(variables[var])]
        else:
            subset = pop_df[pop_df[attribute] == var]

    # TODO Address distplot deprecation
        sns.distplot(subset[metric], hist=True, kde=False,
                     norm_hist=True, bins = 200,
                     kde_kws={'shade': True, 'linewidth': 3}, label=str(var))

    plt.legend(prop={'size': 10}, title=legend_dict[attribute])
    plt.title(case + ': ' + xlabel_dict[metric] + ' by ' + legend_dict[attribute])
    plt.xlabel(xlabel_dict[metric])
    plt.xlim(x_low, x_high)
    plt.ylabel('Population Fraction (-)')
    plot_filename = datetime.now().strftime('%Y%m%d') + 'Customer_PDF_' + attribute + '_' + metric + 'dist.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')


if __name__ == '__main__':
    pd.set_option('display.max_columns', 50)

    # ------------ Selection of DSO and Day  ---------------------------------
    DSO_num = '2'  # Needs to be non-zero integer
    day_num = '9'  # Needs to be non-zero integer
    # Set day range of interest (1 = day 1)
    day_range = range(2, 3)  # 1 = Day 1. Starting at day two as agent data is missing first hour of run.
    dso_range = range(1, 9)  # 1 = DSO 1 (end range should be last DSO +1)

    #  ------------ Select folder locations for different cases ---------

    data_path = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2/V1.1-1317-gfbf326a2/MR-Batt/lean_8_bt'
    # data_path = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2'
    metadata_path = 'C:/Users/reev057/PycharmProjects/TESP/src/examples/analysis/Dsot/Data'
    ercot_path = 'C:/Users/reev057/PycharmProjects/TESP/src/examples/analysis/Dsot/Data'
    base_case = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2/v1.1-1545-ga2893bd8'
    batt_case = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2/v1.1-1567-g8cb140e1'
    Output_path = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2/v1.1-1567-g8cb140e1'
    trans_case = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2/V1.1-1317-gfbf326a2/MR-Flex/lean_8_fl'
    config_path = 'C:/Users/reev057/PycharmProjects/TESP/src/examples/Dsot_v3'
    case_config_name = '200_system_case_config.json'


    # system_case = '8_system_case_config.json'
    # system_case = '8_hi_system_case_config.json'
    system_case = '200_system_case_config.json'
    # system_case = '200_hi_system_case_config.json'

    config_path = 'C:/Users/reev057/PycharmProjects/examples/dsot_v3'
    case_config = pt.load_json(config_path, system_case)
    metadata_path = 'C:/Users/reev057/PycharmProjects/examples/dsot_data'
    dso_metadata_file = case_config['dsoPopulationFile']
    DSOmetadata = pt.load_json(metadata_path, dso_metadata_file)

    # DSO range for 8 node case.  (for 200 node case we will need to determine active DSOs from metadata file).
    # dso_range = range(1, 2)
    dso_range = []
    for DSO in DSOmetadata.keys():
        if 'DSO' in DSO:
            if DSOmetadata[DSO]['used']:
                dso_range.append(int(DSO.split('_')[-1]))

    agent_prefix = '/DSO_'
    GLD_prefix = '/Substation_'
    case_config = pt.load_json(config_path, case_config_name)
    metadata_file = case_config['dsoPopulationFile']
    dso_meta_file = metadata_path + '/' + metadata_file

    # ---------- Flags to turn on and off plot types etc
    DER_load_Curves = False # plot load curve comparisons
    Annual_whiskers = False  # plot annual box and whisker and quantity-duration curves
    dso_valuation_waterfall = False
    Customer_PDFs = True

    compare_MR_cases = False
    compare_HR_cases = True
    compare_All_cases = False
    compare_MR_vs_HR_BAU = False
    compare_200_vs_8_BAU = False

    if compare_MR_cases:
        # Cases = ['MR BAU', 'MR Batt', 'MR Flex']
        # Data_paths = [mr_bau_path, mr_batt_path, mr_flex_path]
        Data_paths = [mr_200_bau_path, mr_200_batt_path, mr_200_flex_path]
        # Cases = ['MR BAU', 'MR Batt']
        # Data_paths = [mr_bau_path, mr_batt_path]
        Cases = ['MR BAU', 'MR Flex']
        # Data_paths = [mr_bau_path, mr_flex_path]
        # Data_paths = [mr_200_bau_path, mr_200_flex_path]
        Variables = ['DA LMP', 'Total Load', 'Hybrid']

    if compare_MR_vs_HR_BAU:
        Cases = ['MR BAU', 'HR BAU']
        Data_paths = [mr_200_bau_path, hr_200_bau_path]
        # Variables = ['Curtailment Percent', 'Renewable Percent', 'DA LMP', 'RT LMP', 'Total Load']
        Variables = ['DA LMP', 'RT LMP', 'Total Load']

    if compare_HR_cases:
        # Cases = ['HR BAU', 'HR Batt', 'HR Flex']
        # Data_paths = [hr_200_bau_path, hr_200_batt_path, hr_200_flex_path]
        Cases = ['HR BAU', 'HR Flex']
        Data_paths = [hr_200_bau_path, hr_200_flex_path]
        # Cases = ['HR BAU', 'HR Batt']
        # Data_paths = [hr_bau_path, hr_batt_path]
        # Data_paths = [hr_bau_path, hr_flex_path]
        Variables = ['DA LMP', 'Total Load', 'Hybrid']

    if compare_All_cases:
        Cases = ['MR Batt', 'MR BAU', 'HR BAU', 'HR Batt']
        Data_paths = [mr_batt_path, mr_bau_path, hr_bau_path, hr_batt_path]
        Variables = ['Renewable Percent', 'DA LMP', 'Total Load']

    if compare_200_vs_8_BAU:
        Cases = ['MR BAU-200', 'MR BAU-8']
        Data_paths = [mr_200_bau_path, mr_bau_path]
        Variables = ['DA LMP', 'Total Load']

        Cases = ['MR BAU-200', 'MR BAU-8', 'HR BAU-200', 'HR BAU-8', 'HR Batt-200', 'HR Batt-8']
        Data_paths = [mr_200_bau_path, mr_bau_path, hr_200_bau_path, hr_bau_path, hr_200_batt_path, hr_batt_path]
        Variables = ['DA LMP', 'Total Load']

    Cases_list = [['MR BAU', 'MR Batt'], ['MR BAU', 'MR Flex'], ['HR BAU', 'HR Batt']]
    Data_paths_list = [[mr_bau_path, mr_batt_path], [mr_bau_path, mr_flex_path], [hr_bau_path, hr_batt_path]]
    Cases_list = [['MR BAU', 'MR Batt'], ['MR BAU', 'MR Flex'], ['HR BAU', 'HR Batt'], ['HR BAU', 'HR Flex']]
    Data_paths_list = [[mr_200_bau_path, mr_200_batt_path], [mr_200_bau_path, mr_200_flex_path], [hr_200_bau_path, hr_200_batt_path], [hr_200_bau_path, hr_200_flex_path]]

    Output_path = Data_paths[0]

    # DSO Market Plot
    # base_lean = "C:/Users/reev057/DSOT-DATA/w_lean_aug_8"
    # case_lean = "C:/Users/reev057/DSOT-DATA/w_lean_aug_8_bt"
    # pt.dso_market_plot(dso_range, "6", base_lean, dso_metadata_file, metadata_path, case_lean)

    # Check if there is a plots folder - create if not.
    check_folder = os.path.isdir(data_path + '/plots')
    if not check_folder:
        os.makedirs(data_path + '/plots')

    if DER_load_Curves:
        # Cycle through months and days for interest for load profiles
        Months = ['01', '03', '08']
        # Months = ['08']
        # Day_Ranges = [range(21, 24), range(4, 11), range(4, 33)]
        Day_Ranges = [range(21, 24), range(25, 28), range(13, 16)]
        # Day_Ranges = [range(11, 18)]
        for i in range(len(Months)):
            day_range = Day_Ranges[i]
            if compare_MR_cases:
                # case_path = Data_paths[1] + "/8_2016_" + Months[i] + "_fl"
                # comp_path = Data_paths[0] + "/8_2016_" + Months[i]
                case_path = Data_paths[2] + "/200_2016_" + Months[i] + "_fl"
                case2_path = Data_paths[1] + "/200_2016_" + Months[i] + "_bt"
                comp_path = Data_paths[0] + "/200_2016_" + Months[i]
            if compare_HR_cases:
                # case_path = Data_paths[1] + "/8_2016_" + Months[i] + "_pv_bt_ev"
                # comp_path = Data_paths[0] + "/8_2016_" + Months[i] + "_pv"
                case2_path = Data_paths[2] + "/200_2016_" + Months[i] + "_pv_fl_ev"
                case_path = Data_paths[1] + "/200_2016_" + Months[i] + "_pv_bt_ev"
                comp_path = Data_paths[0] + "/200_2016_" + Months[i] + "_pv"
            # pt.der_stack_plot(dso_range, day_range, metadata_path, case_path, comp_path)
            # pt.der_stack_plot(dso_range, day_range, metadata_path, comp_path)
            # pt.bldg_stack_plot(dso_range, day_range, comp_path, metadata_path)
            pt.generation_load_profiles(comp_path, metadata_path, comp_path, day_range,
                                                             False, comp_path)
            pt.generation_load_profiles(case_path, metadata_path, case_path, day_range,
                                                             False, comp_path)
            pt.generation_load_profiles(case2_path, metadata_path, case2_path, day_range,
                                                             False, comp_path)
            # pt.generation_load_profiles(comp_path, metadata_path, comp_path, day_range,
            #                                                  True)

    if Annual_whiskers:
        for Variable in Variables:
            plot_annual_stats(Cases, Data_paths, Output_path, DSO_num, Variable)

    if Customer_PDFs:
        customer_cfs_delta(Cases, Data_paths, Output_path, metadata_file)

    # reduction_by_class(Cases, Data_paths, Output_path, 'Load')
    if dso_valuation_waterfall:
        dso_cfs_delta(Cases_list, Data_paths_list, dso_range, metadata_file)
