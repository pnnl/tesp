# Copyright (C) 2021-2024 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
# file: case_comparison_plots.py
"""Build comparison plots and summary files from TESP DSOT simulation results.

The helpers load existing CSV, JSON, and HDF5 results, compare cases, and save
figures and (for selected workflows) CSV summaries. ``rates_plots`` is the
example-configured workflow; ``DSOT_plots`` is a legacy workflow with
hard-coded paths and optional analysis stages controlled by flags. Neither
driver runs a simulation or creates its input result files.
"""

import calendar
import os
from datetime import datetime

import waterfall_chart #distribution name: waterfallcharts
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from datetime import datetime, date, timedelta

import tesp_support.dsot.plots as pt

# Thermal integrity levels per building type, from DSO+T report Tables 25-27.
# Each entry: (level index, description, population fraction, properties).
# Properties use the metadata key names so houses can be compared directly.
THERMAL_INTEGRITY_BY_CLASS = {
    'SINGLE_FAMILY': [
        (0, 'old, uninsulated', 0.05,
         {'Rroof': 11, 'Rwall': 4, 'Rfloor': 4, 'Rdoors': 3,
          'glazing_layers': 1, 'glass_type': 1, 'glazing_treatment': 1, 'window_frame': 1,
          'airchange_per_hour': 1.5}),
        (1, 'old, insulated', 0.20,
         {'Rroof': 19, 'Rwall': 11, 'Rfloor': 4, 'Rdoors': 3,
          'glazing_layers': 2, 'glass_type': 1, 'glazing_treatment': 1, 'window_frame': 1,
          'airchange_per_hour': 1.5}),
        (2, 'old, weatherized', 0.20,
         {'Rroof': 19, 'Rwall': 11, 'Rfloor': 15, 'Rdoors': 3,
          'glazing_layers': 2, 'glass_type': 1, 'glazing_treatment': 1, 'window_frame': 1,
          'airchange_per_hour': 1.0}),
        (3, 'old, retrofit upgraded', 0.40,
         {'Rroof': 30, 'Rwall': 11, 'Rfloor': 15, 'Rdoors': 3,
          'glazing_layers': 2, 'glass_type': 1, 'glazing_treatment': 1, 'window_frame': 2,
          'airchange_per_hour': 1.0}),
        (4, '2003 IECC code', 0.10,
         {'Rroof': 38, 'Rwall': 16, 'Rfloor': 22, 'Rdoors': 5,
          'glazing_layers': 2, 'glass_type': 2, 'glazing_treatment': 1, 'window_frame': 2,
          'airchange_per_hour': 0.5}),
        (5, '2009 IECC code', 0.05,
         {'Rroof': 48, 'Rwall': 22, 'Rfloor': 30, 'Rdoors': 11,
          'glazing_layers': 3, 'glass_type': 2, 'glazing_treatment': 2, 'window_frame': 4,
          'airchange_per_hour': 0.5}),
    ],
    'APARTMENT': [
        (0, 'old, uninsulated', 0.05,
         {'Rroof': 11, 'Rwall': 4, 'Rfloor': 4, 'Rdoors': 3,
          'glazing_layers': 1, 'glass_type': 1, 'glazing_treatment': 1, 'window_frame': 1,
          'airchange_per_hour': 1.5}),
        (1, 'old, insulated', 0.20,
         {'Rroof': 19, 'Rwall': 11, 'Rfloor': 4, 'Rdoors': 3,
          'glazing_layers': 2, 'glass_type': 1, 'glazing_treatment': 1, 'window_frame': 1,
          'airchange_per_hour': 1.5}),
        (2, 'old, weatherized', 0.25,
         {'Rroof': 19, 'Rwall': 11, 'Rfloor': 15, 'Rdoors': 3,
          'glazing_layers': 2, 'glass_type': 1, 'glazing_treatment': 1, 'window_frame': 1,
          'airchange_per_hour': 1.0}),
        (3, 'old, retrofit upgraded', 0.40,
         {'Rroof': 30, 'Rwall': 11, 'Rfloor': 15, 'Rdoors': 3,
          'glazing_layers': 2, 'glass_type': 1, 'glazing_treatment': 1, 'window_frame': 2,
          'airchange_per_hour': 1.0}),
        (4, '2003 IECC code', 0.10,
         {'Rroof': 38, 'Rwall': 16, 'Rfloor': 22, 'Rdoors': 5,
          'glazing_layers': 2, 'glass_type': 2, 'glazing_treatment': 1, 'window_frame': 2,
          'airchange_per_hour': 0.5}),
    ],
    'MOBILE': [
        (0, 'old (1976-1994) HUD code', 0.49,
         {'Rroof': 13.4, 'Rwall': 9.2, 'Rfloor': 11.7, 'Rdoors': 2.2,
          'glazing_layers': 1, 'glass_type': 1, 'glazing_treatment': 1, 'window_frame': 1,
          'airchange_per_hour': 1.5}),
        (1, 'new (1994-present) HUD code', 0.51,
         {'Rroof': 24.1, 'Rwall': 11.7, 'Rfloor': 18.1, 'Rdoors': 2.2,
          'glazing_layers': 2, 'glass_type': 2, 'glazing_treatment': 1, 'window_frame': 2,
          'airchange_per_hour': 0.4}),
    ],
}

# GridLAB-D house_class values map onto the three report building types.
HOUSE_CLASS_TO_BUILDING_TYPE = {
    'SINGLE_FAMILY': 'SINGLE_FAMILY',
    'MOBILE': 'MOBILE',
    'MANUFACTURED': 'MOBILE',
    'APARTMENT': 'APARTMENT',
    'MULTI_FAMILY': 'APARTMENT',
}

# Doors and door area per report section 6.3.1: single family and manufactured
# homes have four solid doors of 19.5 sq-ft; apartments have one, plus a
# sliding glass door counted as window area.
DOORS_BY_BUILDING_TYPE = {'SINGLE_FAMILY': 4, 'MOBILE': 4, 'APARTMENT': 1}

# Approximate window R-values (hr·ft²·°F/Btu) used by
# :func:`envelope_conductance_index`. GridLAB-D derives window U-values from
# the glazing enumerations (GridLAB-D 2017, Tables 1 and 2); these are a
# coarse additive stand-in for that lookup, adequate because windows are a
# modest share of total UA and only the resulting ranking is used.
#
# Base R by number of glazing layers (glazing_layers: 1 single, 2 double,
# 3 triple). Roughly 1/1.04, 1/0.55, and 1/0.37 Btu/(hr·ft²·°F).
WINDOW_R_BY_LAYERS = {1: 0.96, 2: 1.80, 3: 2.70}

# Added R for low-e coating (glass_type: 1 GLASS, 2 LOW_E_GLASS).
WINDOW_R_LOW_E_BONUS = 0.60

# Added R by frame material (window_frame: 0 NONE, 1 ALUMINUM,
# 2 THERMAL_BREAK, 3 WOOD, 4 INSULATED).
WINDOW_R_FRAME_BONUS = {0: 0.0, 1: 0.0, 2: 0.20, 3: 0.30, 4: 0.40}

# Added R for an absorptive or reflective treatment
# (glazing_treatment: 1 CLEAR, 2+ ABSORPTIVE/REFLECTIVE/LOW_S).
WINDOW_R_TREATMENT_BONUS = 0.10

# Report building types, ordered for consistent legend grouping.
BUILDING_TYPE_ORDER = ['SINGLE_FAMILY', 'APARTMENT', 'MOBILE']

# Grouping dimensions available from Master_Customer_Dataframe.h5.
# from_comparison_case: read from a non-baseline case, since the flat baseline
#   enables no transactive or DER participation.
CFS_DIMENSIONS = {
    'tariff_class': {
        'title': 'Customer Class', 'field': 'tariff_class',
        'remap': {'residential': 'Residential', 'commercial': 'Commercial',
                  'industrial': 'Industrial'},
        'order': ['Residential', 'Commercial', 'Industrial']},
    'building_type': {
        'title': 'Building Type', 'field': 'building_type',
        'remap': {'SINGLE_FAMILY': 'Single-family', 'MOBILE_HOME': 'Manufactured home',
                  'MULTI_FAMILY': 'Multi-family'},
        'order': ['Single-family', 'Multi-family', 'Manufactured home']},
    'heating': {
        'title': 'Heating Type', 'field': 'heating',
        'remap': {'GAS': 'Gas', 'RESISTANCE': 'Resistance', 'HEAT_PUMP': 'Heat pump',
                  'ELECTRIC': 'Electric', 'NONE': 'None'},
        'order': ['Heat pump', 'Resistance', 'Electric', 'Gas', 'None']},
    'cooling': {
        'title': 'Cooling Type', 'field': 'cooling',
        'remap': {'ELECTRIC': 'Electric', 'NONE': 'None'},
        'order': ['Electric', 'None']},
    'income_level': {
        'title': 'Income Level', 'field': 'income_level',
        'order': ['Low', 'Middle', 'Upper']},
    'cust_participating': {
        'title': 'Participation', 'field': 'cust_participating',
        'remap': {True: 'Participating', False: 'Non-participating'},
        'order': ['Participating', 'Non-participating'],
        'from_comparison_case': True},
    'pv_participating': {
        'title': 'Rooftop Solar', 'field': 'pv_participating',
        'remap': {True: 'PV', False: 'No PV'}, 'order': ['PV', 'No PV'],
        'from_comparison_case': True},
    'ev_participating': {
        'title': 'EV Ownership', 'field': 'ev_participating',
        'remap': {True: 'EV', False: 'No EV'}, 'order': ['EV', 'No EV'],
        'from_comparison_case': True},
    'DER_participating': {
        'title': 'DER Participation', 'field': 'DER_participating',
        'order': ['None', 'HVAC', 'WH', 'EV', 'Battery', 'HVAC, WH', 'HVAC, EV',
                  'WH, EV', 'HVAC, WH, EV', 'HVAC, WH, EV, Battery'],
        'from_comparison_case': True},
    'wh_participating': {
        'title': 'WH Participation', 'field': 'wh_participating',
        'remap': {True: 'WH', False: 'No WH'}, 'order': ['WH', 'No WH'],
        'from_comparison_case': True},
    'batt_participating': {
        'title': 'BESS Participation', 'field': 'batt_participating',
        'remap': {True: 'BESS', False: 'No BESS'}, 'order': ['BESS', 'No BESS'],
        'from_comparison_case': True},
    'hvac': {
        'title': 'Heating / Cooling', 'fields': ['heating', 'cooling'],
        'combine': lambda values: f'{values[0]} heat / {values[1]} cool'},
    'dso_type': {
        'title': 'DSO Type', 'field': 'dso_type',
        'order': ['Urban', 'Suburban', 'Rural']},
    'insulation': {
        'title': 'Insulation Level', 'field': 'Insulation Level', 'requires_metadata': True},
}

# Metrics plottable from the CFS dataframe. 'bin' sets the density-axis
# denominator for levels, 'change_bin' for paired changes, which are typically
# an order of magnitude smaller than the levels themselves.
CFS_METRICS = {
    'Bills': {'label': 'Annual Electricity Bill ($)', 'unit': '$',
              'bin': 100, 'change_bin': 25, 'short': 'Bill'},
    'EnergyPurchased': {'label': 'Energy Purchased (kW-hr/year)', 'unit': 'kW-hr',
                        'bin': 1000, 'change_bin': 250, 'short': 'Energy'},
    'PeakLoad': {'label': 'Annual Peak Load (kW)', 'unit': 'kW',
                 'bin': 1, 'change_bin': 0.5, 'short': 'Peak Load'},
    'NetEnergyCost': {'label': 'Net Energy Expenses ($)', 'unit': '$',
                      'bin': 100, 'change_bin': 25, 'short': 'Net Energy Cost'},
}

def rec_diff(d1, d2):
    """Recursively subtract corresponding numeric values in nested mappings.

    Args:
        d1: Mapping containing the minuend values.
        d2: Mapping with the same keys and nesting as ``d1``.

    Returns:
        A new nested dictionary containing ``d1 - d2`` at each leaf. Inputs
        must have matching structures and numeric leaf values.
    """
    diff = dict()
    for k,v1 in d1.items():
        if isinstance(v1, dict):
            diff[k] = rec_diff(v1, d2[k])
        else:
            diff[k] = v1 - d2[k]
    return diff

def customer_bill_component_comparison(cases, data_paths, output_path, dso_num, customer_class='commercial'):
    """Compare average residential bill components across cases.

    Reads each case's DSO bill summary and customer-scaling data, converts the
    selected tariff components to a per-customer basis, and plots stacked
    totals for April, August, December, and the annual average.

    Args:
        cases (list[str]): Case labels, such as ``Flat``, ``TOU``, ``DE``,
            ``DE+C``, or ``B&S``.
        data_paths (list[str]): Result directory for each corresponding case.
        output_path (str): Output root; its ``plots`` subdirectory must exist.
        dso_num (str | int): DSO identifier used to select bill data.
        customer_class (str): Customer class, either 'residential' or 'commercial'. Defaults to 'commercial'.

    Returns:
        None. Saves a PNG in ``output_path/plots``.
    """

    Customer_class = customer_class
    Cost_components = ['Fixed Charge', 'Volumetric Energy Charge', 'Volumetric Charge (Peak)',
                         'Volumetric Charge (Off-Peak)', 'Demand Charge', 'Dynamic (DA) Charge', 'Dynamic (RT) Charge', 'Dynamic Swing Charge']

    title_name = 'Average Customer Bills ($)'
    upper_limit = 600
    lower_limit = 0
    units = '$'

    # months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Average']
    months = [ 'Apr', 'Aug', 'Dec', 'Average']

    case_list = []
    costs = []
    month_list = []
    for month in months:
        for case in cases:
            case_list.append(case)
            month_list.append(month)

    df = pd.DataFrame(
        index=[month_list, case_list],
        columns=Cost_components)

    for cost in Cost_components:
        # df[cost] = np.random.rand(len(df))
        df[cost] = 0.0

    for i in range(len(cases)):
        case = cases[i]
        data_path = data_paths[i]
        var_df = pd.read_csv(data_path + '/billsum_dso_' + str(dso_num) + '_data.csv', index_col=[0, 1])
        # Average out sum value
        var_df['Average'] = var_df['sum']/12

        rci_df = pd.read_csv(data_path + '/RCI_check.csv', index_col=[0])
        # Calculate scaling factor to per customer basis TODO: find actual participating values:
        if case == 'Flat':
            cust_sf = rci_df.loc[int(dso_num), 'Scaling Factor'] *893
        else:
            cust_sf = rci_df.loc[int(dso_num), 'Scaling Factor'] *699

        for month in months:
            # Cost_components = ['Fixed Charge', 'Volumetric Energy Charge', 'Volumetric Charge (Peak)',
            #                    'Volumetric Energy Charge (Off-Peak)', 'Dynamic (DA) Charge', 'Dynamic (RT) Charge']

            if case == 'Flat':
                df.loc[(month, case), 'Fixed Charge'] = var_df.loc[(Customer_class, 'flat_fixed_charge'), month] / cust_sf
                df.loc[(month, case), 'Volumetric Energy Charge'] = var_df.loc[(Customer_class, 'flat_energy_charge'), month] / cust_sf
                df.loc[(month, case), 'Demand Charge'] = var_df.loc[(Customer_class, 'flat_demand_charge'), month] / cust_sf

            elif case == 'TOU':
                df.loc[(month, case), 'Fixed Charge'] = var_df.loc[(Customer_class, 'tou_fixed_charge'), month] / cust_sf
                df.loc[(month, case), 'Volumetric Charge (Peak)'] = var_df.loc[(Customer_class, 'tou_peak_energy_charge'), month] / cust_sf
                df.loc[(month, case), 'Volumetric Charge (Off-Peak)'] = var_df.loc[(Customer_class, 'tou_off-peak_energy_charge'), month] / cust_sf
                df.loc[(month, case), 'Demand Charge'] = var_df.loc[(Customer_class, 'tou_demand_charge'), month] / cust_sf

            elif case == 'DE':
                df.loc[(month, case), 'Fixed Charge'] = var_df.loc[(Customer_class, 'dsot_fixed_charge'), month] / cust_sf
                df.loc[(month, case), 'Volumetric Energy Charge'] = var_df.loc[(Customer_class, 'dsot_volumetric_charge'), month] / cust_sf
                df.loc[(month, case), 'Dynamic (DA) Charge'] = var_df.loc[(Customer_class, 'dsot_DA_energy_charge'), month] / cust_sf
                df.loc[(month, case), 'Dynamic (RT) Charge'] = var_df.loc[(Customer_class, 'dsot_RT_energy_charge'), month] / cust_sf

            elif case == 'DE+C':
                df.loc[(month, case), 'Fixed Charge'] = var_df.loc[(Customer_class, 'transactive_fixed_charge'), month] / cust_sf
                df.loc[(month, case), 'Volumetric Energy Charge'] = var_df.loc[(Customer_class, 'transactive_volumetric_charge'), month] / cust_sf
                df.loc[(month, case), 'Dynamic (DA) Charge'] = var_df.loc[(Customer_class, 'transactive_DA_energy_charge'), month] / cust_sf
                df.loc[(month, case), 'Dynamic (RT) Charge'] = var_df.loc[(Customer_class, 'transactive_RT_energy_charge'), month] / cust_sf

            elif case == 'B&S':
                df.loc[(month, case), 'Fixed Charge'] = var_df.loc[(Customer_class, 'subscription_fixed_charge'), month] / cust_sf
                df.loc[(month, case), 'Volumetric Energy Charge'] = var_df.loc[(Customer_class, 'subscription_energy_charge'), month] / cust_sf
                df.loc[(month, case), 'Dynamic Swing Charge'] = var_df.loc[(Customer_class, 'subscription_net_deviation_charge'), month] / cust_sf

    matplotlib.style.use('seaborn-v0_8') # Only 6 distinct colors natively
    component_colors = sns.color_palette("Set2", n_colors=len(Cost_components))

    fig, axes = plt.subplots(nrows=1, ncols=len(months), figsize=(max(11,3*len(months)), 10))

    ax_position = 0
    for month in months:
        idx = pd.IndexSlice
        subset = df.loc[idx[[month], :],
                        Cost_components]

        # ax = subset.plot(kind="bar", stacked=True, colormap="Blues",
        #                  ax=axes[ax_position])
        ax = subset.plot(kind="bar", stacked=True, color=component_colors,
                         ax=axes[ax_position])
        ax.set_title(month, fontsize=14, alpha=1.0)
        ax.set_ylabel(title_name, fontsize=14),
        ax.set_xlabel(month, fontsize=12, alpha=0.0),
        ax.set_ylim(-5, 200)  # Need to use this otherwise each subplot will rescale and not match final Y-axis scale
        # ax.set_yticks(range(0, 9000, 1000))
        # ax.set_yticklabels(labels=range(0, 9000, 1000), rotation=0,
        #                    minor=False, fontsize=28)
        ax.set_xticklabels(labels=cases, rotation=90,
                           minor=False, fontsize=10)
        handles, labels = ax.get_legend_handles_labels()
        # ax.legend(Cost_components,
        #           loc='upper right', fontsize=28)
        ax_position += 1


    # look "one plot"
    # plt.tight_layout(pad=0., w_pad=-16.5, h_pad=0.0)

    for n in range(len(months)):
        if n != 0:
            axes[n].set_ylabel("")
            axes[n].set_yticklabels("")
        if n == range(len(months))[-1]:
            axes[n].legend(Cost_components,
                   loc='upper right', fontsize=10)
        else:
            axes[n].legend().set_visible(False)

    plot_filename = 'Case_Compare_Bill_Components_DSO_' + str(dso_num) + '_' + str(Customer_class) + '.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

def indoor_air_amenity_comparison(cases, data_paths, output_path, dso_range):
    """Compare residential HVAC discomfort for matched households across tariffs.

    Runs the flat rate as baseline case. Compares flat rate to participating
    residential households across other tariff designs. Reads annual amenity 
    HDF5 files and annual customer metadata JSONs. Multiple house zones on a 
    billing meter are averaged to give each household equal weight.

    Args:
        cases (list[str]): Unique tariff labels, baseline first.
        data_paths (list[str]): Corresponding annual result directories.
        output_path (str): Root for the plot and household-score CSV.
        dso_range (iterable[int]): DSOs to include, matched independently.

    Returns:
        pandas.DataFrame: Monthly and annual household HVAC scores and paired
        changes from baseline. Positive changes mean greater discomfort.

    Existing scores cannot distinguish skipped data or missing schedules from
    genuine zero discomfort. Check simulation coverage before interpreting them.
    """
    if len(cases) < 2 or len(cases) != len(data_paths) or len(set(cases)) != len(cases):
        raise ValueError('Provide at least two unique case labels and matching result paths.')

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    periods = months + ['Annual']
    frames = []
    for dso in dso_range:
        scores_by_case = []
        eligible_by_case = []
        for case, data_path in zip(cases, data_paths):
            metadata = pt.load_json(data_path, 'DSO' + str(dso) + '_Customer_Metadata.json')
            amenity_path = os.path.join(data_path, 'amenity_dso_' + str(dso) + '_data.h5')
            amenity = pd.read_hdf(amenity_path, key='amenity_data', mode='r')
            scores = amenity.xs('HVAC_deg-hrs', level=1).copy()
            month_columns = {str(column)[:3]: column for column in scores.columns
                             if str(column)[:3] in months}
            if len(month_columns) != 12 or 'sum' not in scores.columns:
                raise ValueError(f'{amenity_path} must contain twelve monthly HVAC scores and an annual sum.')
            scores = scores[[month_columns[month] for month in months] + ['sum']]
            scores.columns = periods
            scores = scores.apply(pd.to_numeric, errors='coerce').replace([np.inf, -np.inf], np.nan)
            house_to_meter = {house: details['billingmeter_id']
                              for house, details in metadata['houses'].items()}
            scores['meter ID'] = scores.index.map(house_to_meter)
            invalid_meters = set(scores.loc[scores[periods].isna().any(axis=1), 'meter ID'].dropna())
            missing_houses = set(house_to_meter) - set(scores.index)
            invalid_meters.update(house_to_meter[house] for house in missing_houses)
            household_scores = scores.groupby('meter ID')[periods].mean()
            household_scores = household_scores.drop(index=list(invalid_meters), errors='ignore')
            eligible = {meter for meter, details in metadata['billingmeters'].items()
                        if details.get('tariff_class') == 'residential'
                        and (case == cases[0] or (details.get('cust_participating', False)
                                                 and details.get('hvac_participating', False)))}
            eligible_by_case.append(eligible & set(household_scores.index))
            scores_by_case.append(household_scores)

        matched = sorted(set.intersection(*eligible_by_case))
        print(f'Indoor-air amenity: DSO {dso}, {len(matched)} matched HVAC-participating households; '
              f'eligible counts by tariff: {dict(zip(cases, map(len, eligible_by_case)))}')
        if not matched:
            continue
        baseline = scores_by_case[0].loc[matched, periods]
        for case, scores in zip(cases, scores_by_case):
            values = scores.loc[matched, periods]
            values.index.name = 'meter ID'
            changes = values.subtract(baseline)
            long_values = values.reset_index().melt(
                id_vars='meter ID', var_name='Period', value_name='HVAC Discomfort (F-hr)')
            long_changes = changes.reset_index().melt(
                id_vars='meter ID', var_name='Period', value_name='Change from Baseline (F-hr)')
            frame = long_values.merge(long_changes, on=['meter ID', 'Period'], validate='one_to_one')
            frame['DSO'] = dso
            frame['Case'] = case
            frames.append(frame)

    if not frames:
        raise ValueError('No matched residential HVAC-participating households have complete amenity scores.')
    results = pd.concat(frames, ignore_index=True)
    annual = results[results['Period'] == 'Annual']
    colors = sns.color_palette('colorblind', n_colors=len(cases))
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    try:
        for case, color in zip(cases, colors):
            monthly = results[(results['Case'] == case) & (results['Period'] != 'Annual')]
            means = monthly.groupby('Period')[['HVAC Discomfort (F-hr)', 'Change from Baseline (F-hr)']].mean().reindex(months)
            axes[0, 0].plot(range(12), means['HVAC Discomfort (F-hr)'], label=case, color=color, marker='o')
            axes[1, 0].plot(range(12), means['Change from Baseline (F-hr)'], label=case, color=color, marker='o')
        for axis in axes[:, 0]:
            axis.set_xticks(range(12), months)
            axis.set_xlabel('Month')
            axis.legend(title='Tariff')
        sns.boxplot(data=annual, x='Case', y='HVAC Discomfort (F-hr)', hue='Case',
                    order=cases, hue_order=cases, palette=colors, legend=False, ax=axes[0, 1])
        sns.boxplot(data=annual, x='Case', y='Change from Baseline (F-hr)', hue='Case',
                    order=cases, hue_order=cases, palette=colors, legend=False, ax=axes[1, 1])
        axes[0, 0].set_title('Mean Monthly HVAC Discomfort')
        axes[0, 1].set_title('Annual Household HVAC Discomfort')
        axes[1, 0].set_title('Mean Monthly Change from ' + cases[0])
        axes[1, 1].set_title('Annual Household Change from ' + cases[0])
        for axis in axes[0, :]:
            axis.set_ylabel('HVAC Discomfort (F-hr per Household)')
        for axis in axes[1, :]:
            axis.set_ylabel('Change from Baseline (F-hr per Household)')
            axis.axhline(0, color='grey', linestyle='--', linewidth=1)
        fig.tight_layout()
        plot_path = os.path.join(output_path, 'plots')
        data_path = os.path.join(output_path, 'data')
        os.makedirs(plot_path, exist_ok=True)
        os.makedirs(data_path, exist_ok=True)
        fig.savefig(os.path.join(plot_path, 'Case_Compare_Indoor_Air_Amenity.png'), bbox_inches='tight')
        results.to_csv(os.path.join(data_path, 'Case_Compare_Indoor_Air_Amenity.csv'), index=False)
    finally:
        plt.close(fig)
    return results

def customer_monthly_stats(cases, data_paths, output_path, dso_num, cust_class=None):
    """Compare monthly customer bills and changes from a baseline case.

    Loads bill data for each case and optionally filters customers by tariff
    class using the first case's customer-data HDF5 file. The first case is the
    baseline for the monthly percent-change distribution.

    Args:
        cases (list[str]): Case labels, with the first case as the baseline.
        data_paths (list[str]): Result directory for each corresponding case.
        output_path (str): Output root; its ``plots`` subdirectory must exist.
        dso_num (str | int): DSO identifier used to select monthly bill data.
        cust_class (str | None): Optional tariff-class filter.

    Returns:
        None. Saves a dated PNG in ``output_path/plots``.
    """

    title_name = 'Customer Monthly Bills ($)'
    upper_limit = 600
    lower_limit = 0
    units = '$'
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    for i in range(len(cases)):
        case = cases[i]
        data_path = data_paths[i]
        var_df = pd.read_csv(data_path + '/cust_bill_dso_' + str(dso_num) + '_data.csv', index_col=[0])

        var_df = var_df[var_df[var_df.columns[0]].str.contains('total')]

        if case == cases[0]:
            customers = sorted(var_df.index.unique().tolist())

            if cust_class is not None:
                cust_cfs_file = data_path + '/Master_Customer_Dataframe.h5'
                customer_cfs_df = pd.read_hdf(cust_cfs_file, key='customer_data', mode='r')
                customer_cfs_df = customer_cfs_df[customer_cfs_df['Customer ID'].str.contains(
                    'DSO' + str(dso_num) + r'(?!\d)', case=False, na=False)]
                missing_meters = set(customers) - set(customer_cfs_df['meter ID'])
                if missing_meters:
                    print(f'CFS is missing {len(missing_meters)} billing meters for DSO {dso_num}; '
                          f'excluding them from the {cust_class} filter.')
                class_meters = set(customer_cfs_df.loc[
                    customer_cfs_df['tariff_class'] == cust_class, 'meter ID'])
                customers = [meter for meter in customers if meter in class_meters]

            # Create empty DataFrame for all consumer bills
            meters = []
            case_list = []
            month_list = []
            for meter in customers:
                for case2 in cases:
                    for month in months:
                        meters.append(meter)
                        case_list.append(case2)
                        month_list.append(month)

            results_df = pd.DataFrame(
                index=[meters, case_list, month_list],
                columns=['total bill', 'month', 'case', 'change']).sort_index()
            results_df['total bill'] = np.nan
            results_df['change'] = np.nan

        monthly_bills = var_df[months].groupby(level=0).sum()
        for customer in customers:
            for month in months:
                results_df.at[(customer, case, month), 'total bill'] = monthly_bills.at[customer, month]
                results_df.at[(customer, case, month), 'month'] = month
                results_df.at[(customer, case, month), 'case'] = case
                baseline_bill = results_df.at[(customer, cases[0], month), 'total bill']
                results_df.at[(customer, case, month), 'change'] = (
                    100 * (monthly_bills.at[customer, month] - baseline_bill) / baseline_bill
                    if baseline_bill != 0 else np.nan)

    fig, axes = plt.subplots(2, 1, figsize=(11, 10), sharex=True)
    # pal = ['violet'] + ['lightgreen'] + ["gold"] + ['skyblue']
    pal = ['#e0813e'] + ['#062c49'] + ['#84baa9'] + ['#965c79'] + ["gold"]
    # pal = sns.color_palette("Paired")
    pal = pal[0:len(cases)]

    sns.boxplot(data=results_df, x='month', y='total bill', hue='case', ax=axes[0], palette=pal,
                order=months, hue_order=cases)

    axes[0].set_ylabel(units)
    axes[0].set_title('Variation in ' + title_name + ' over the Year')
    axes[0].set_xlabel('')
    axes[0].set_ylim(top=upper_limit, bottom=lower_limit)
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles=handles, labels=labels, framealpha=1)

    sns.boxplot(data=results_df, x='month', y='change', hue='case', ax=axes[1], palette=pal,
                order=months, hue_order=cases)
    axes[1].set_ylabel('Percent Change (%)')
    axes[1].set_title('Change in ' + title_name + ' compared to ' + cases[0] + ' case')
    axes[1].set_xlabel('Month')
    axes[1].set_ylim(top=upper_limit / 6, bottom=-upper_limit / 6)
    handles, labels = axes[1].get_legend_handles_labels()
    axes[1].legend(handles=handles, labels=labels, framealpha=1)

    plot_filename =  'Case_Compare_Customer_Monthly_Bills.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    fig.savefig(file_path_fig, bbox_inches='tight')
    plt.close(fig)

def load_customer_cfs_population(cases, data_paths, cust_class='residential',
                                 attribute_case=1, insulation_options=None,
                                 metadata_paths=None):
    """Load per-customer annual metrics and attributes for every rate case.

    Reads each case's ``Master_Customer_Dataframe.h5`` and stacks them into one
    long frame keyed on ``Customer ID``, which already encodes the DSO and so is
    unique across the system. Customer attributes are taken from a single
    comparison case and broadcast to all cases, because attributes describe the
    customer rather than the rate and the flat baseline flags no transactive or
    DER participation.

    A ``DER_participating`` label is derived from the individual device flags,
    following the convention in :func:`customer_cfs_delta`. Insulation level is
    joined from the customer metadata JSONs only when requested, since it is
    not carried in the CFS dataframe.

    Args:
        cases (list[str]): Rate labels with the baseline first.
        data_paths (list[str]): Result directory for each corresponding case,
            each containing ``Master_Customer_Dataframe.h5``.
        cust_class (str | None): Tariff class filter, or None for all classes.
        attribute_case (int): Index of the case supplying customer attributes.
            Defaults to 1, the first comparison case.
        insulation_options (dict | None): When given, join an insulation level
            using ``method``, ``bins``, and ``dso_range`` keys.
        metadata_paths (list[str] | None): Directories holding the customer
            metadata JSONs, defaulting to ``data_paths``.

    Returns:
        pandas.DataFrame: One row per customer and case, with ``Rate``,
        ``Customer ID``, ``dso``, the attribute columns, and the CFS metrics.
    """
    if len(cases) != len(data_paths):
        raise ValueError('Provide one result path per case label.')
    if not 0 <= attribute_case < len(cases):
        raise ValueError('attribute_case must index into cases.')

    device_flags = [('hvac_participating', 'HVAC'), ('wh_participating', 'WH'),
                    ('ev_participating', 'EV'), ('batt_participating', 'Battery')]
    attribute_columns = ['tariff_class', 'building_type', 'heating', 'cooling',
                         'income_level', 'sqft', 'slider_setting', 'dso',
                         'cust_participating', 'pv_participating', 'meter ID']
    # Device flags are kept as their own dimensions as well as feeding the
    # combined DER_participating label.
    attribute_columns += [column for column, _name in device_flags]

    frames = {}
    for case, data_path in zip(cases, data_paths):
        cfs_file = os.path.join(data_path, 'Master_Customer_Dataframe.h5')
        if not os.path.isfile(cfs_file):
            raise FileNotFoundError(f'{cfs_file} is missing for the {case} case.')
        frame = pd.read_hdf(cfs_file, key='customer_data', mode='r')
        if 'Customer ID' in frame.columns:
            frame = frame.set_index('Customer ID')
        frame.index.name = 'Customer ID'
        if frame.index.duplicated().any():
            raise ValueError(f'Duplicate Customer IDs in the {case} CFS dataframe.')
        frames[case] = frame

    source = frames[cases[attribute_case]]
    print(f'Customer attributes taken from the {cases[attribute_case]} case.')

    attributes = source[[column for column in attribute_columns
                         if column in source.columns]].copy()

    # DER mix label, matching the customer_cfs_delta convention.
    present_flags = [(column, name) for column, name in device_flags
                     if column in source.columns]
    if present_flags and 'cust_participating' in source.columns:
        def der_label(row):
            if not row['cust_participating']:
                return 'None'
            devices = [name for column, name in present_flags if row[column]]
            return ', '.join(devices) if devices else 'None'
        attributes['DER_participating'] = source.apply(der_label, axis=1)

    # for key, spec in CFS_DIMENSIONS.items():
    #     field = spec.get('field')
    #     if field in attributes.columns and spec.get('remap'):
    #         attributes[field] = attributes[field].replace(spec['remap'])

    if insulation_options:
        options = dict(insulation_options)
        dso_range = options.pop('dso_range')
        meter_levels, _order = meter_insulation_levels(
            metadata_paths[0] if metadata_paths else data_paths[0], dso_range,
            cust_class, options.get('method', 'conductance'), options.get('bins', 3),
            options.get('group_description', True))
        if 'meter ID' not in attributes.columns:
            raise ValueError('The CFS dataframe has no "meter ID" column to join '
                             'insulation levels on.')
        by_meter = {}
        for (dso, meter), label in meter_levels.items():
            by_meter.setdefault(meter, {})[int(dso)] = label
        attributes['Insulation Level'] = [
            by_meter.get(meter, {}).get(int(dso))
            for meter, dso in zip(attributes['meter ID'], attributes['dso'])]

        matched = attributes['Insulation Level'].notna().sum()
        print(f'Joined insulation levels onto {matched} of {len(attributes)} customers.')

    metric_columns = [column for column in CFS_METRICS if column in source.columns]
    if not metric_columns:
        raise ValueError(f'None of {sorted(CFS_METRICS)} are in the CFS dataframe.')

    stacked = []
    for case in cases:
        frame = frames[case]
        shared = attributes.index.intersection(frame.index)
        if len(shared) < len(attributes):
            print(f'{len(attributes) - len(shared)} customers are missing from the '
                  f'{case} case and are excluded.')
        combined = attributes.loc[shared].join(frame.loc[shared, metric_columns],
                                               how='inner', rsuffix='_metric')
        combined['Rate'] = case
        stacked.append(combined.reset_index())

    population = pd.concat(stacked, ignore_index=True)

    if cust_class is not None:
        remap = CFS_DIMENSIONS['tariff_class']['remap']
        wanted = {cust_class, remap.get(cust_class, cust_class)}
        matches = population['tariff_class'].isin(wanted)
        if not matches.any():
            available = sorted(population['tariff_class'].dropna().unique())
            raise ValueError(f"No customers with tariff_class '{cust_class}'. "
                            f'Available: {available}.')
        population = population[matches]

    for column in metric_columns:
        population[column] = pd.to_numeric(population[column], errors='coerce')

    # Paired changes from the baseline, per customer.
    baseline = (population[population['Rate'] == cases[0]]
                .set_index('Customer ID')[metric_columns])
    if baseline.index.duplicated().any():
        raise ValueError(f'Duplicate Customer IDs in the {cases[0]} baseline.')
    for column in metric_columns:
        base_values = population['Customer ID'].map(baseline[column])
        population[column + ' base'] = base_values
        population[column + ' change'] = population[column] - base_values
        population[column + ' change pct'] = np.where(
            base_values > 0, 100 * (population[column] - base_values) / base_values, np.nan)
        # Near-zero baselines (rooftop PV) make percent changes asymptotic.
        population[column + ' change pct'] = np.clip(
            population[column + ' change pct'], -100, 100)

    print(f'Loaded {population["Customer ID"].nunique()} customers across '
          f'{len(cases)} cases ({len(population)} rows), DSOs '
          f'{sorted(population["dso"].dropna().unique())}.')
    return population

def resolve_cfs_groups(population, dimension, include_counts=False):
    """Resolve a grouping dimension into a labeled column and ordered labels.

    Args:
        population (pandas.DataFrame): Output of
            :func:`load_customer_cfs_population`.
        dimension (str): Key in ``CFS_DIMENSIONS``.
        include_counts (bool): Append distinct customer counts to the labels.

    Returns:
        tuple[pandas.DataFrame, list, str]: ``(frame with a 'Group' column,
        label order, dimension title)``.
    """
    if dimension not in CFS_DIMENSIONS:
        raise ValueError(f"Unknown dimension '{dimension}'. Available: "
                         f'{sorted(CFS_DIMENSIONS)}.')
    spec = CFS_DIMENSIONS[dimension]
    frame = population.copy()

    fields = spec.get('fields') or [spec['field']]
    missing = [field for field in fields if field not in frame.columns]
    if missing:
        raise ValueError(f"Dimension '{dimension}' needs column(s) {missing}, which are "
                         f'not in the loaded population. Available: '
                         f'{sorted(frame.columns)}.')

    if spec.get('combine'):
        frame['Group'] = [spec['combine']([str(value) for value in values])
                          for values in zip(*(frame[field] for field in fields))]
    else:
        frame['Group'] = frame[fields[0]].map(
            lambda value: spec.get('remap', {}).get(value, value))
    frame['Group'] = frame['Group'].astype(str).replace({'nan': np.nan, 'None': 'None'})
    frame = frame.dropna(subset=['Group'])
    if frame.empty:
        raise ValueError(f"Dimension '{dimension}' produced no labeled customers.")

    counts = frame.drop_duplicates('Customer ID')['Group'].value_counts()
    preferred = spec.get('order', [])
    order = ([label for label in preferred if label in counts.index]
             + sorted(label for label in counts.index if label not in preferred))

    if include_counts:
        renamed = {label: f'{label} (n={int(counts[label]):,})' for label in order}
        frame['Group'] = frame['Group'].map(renamed)
        order = [renamed[label] for label in order]

    print(f'{spec["title"]} groups: '
          + ', '.join(f'{label}={int(counts[label])}' for label in
                      ([entry for entry in preferred if entry in counts.index] or counts.index))
          + f' | {int(counts.sum())} customers')
    if len(order) == 1:
        print(f"Warning: dimension '{dimension}' produced a single group.")
    return frame, order, spec['title']

def customer_cfs_pdf_by_group(cases, data_paths, output_path, dimension='building_type',
                              metric='Bills', cust_class='residential', mode='level',
                              split_by='cust_participating', options=None,
                              include_counts=True, x_limits=None, palette_name='viridis',
                              population=None):
    """Plot customer metric distributions by rate and a chosen customer attribute.

    Draws one density panel per rate, with a column per split group and the
    chosen customer dimension encoded by color. Levels, paired changes from the
    baseline, and paired percent changes are all available, so the same call
    pattern covers both bill distributions and bill variation.

    Data comes from each case's ``Master_Customer_Dataframe.h5`` via
    :func:`load_customer_cfs_population`, which keys on ``Customer ID`` and
    takes customer attributes from a comparison case. In ``change`` modes the
    baseline rate is omitted, since its change is zero by construction.

    Args:
        cases (list[str]): Rate labels with the baseline first.
        data_paths (list[str]): Result directory for each corresponding case.
        output_path (str): Output root; ``plots`` and ``data`` subdirectories
            are created if missing.
        dimension (str): Grouping dimension key in ``CFS_DIMENSIONS``.
        metric (str): Metric key in ``CFS_METRICS``.
        cust_class (str | None): Tariff class filter, or None for all classes.
        mode (str): ``level`` plots the metric, ``change`` plots the paired
            change from the baseline, and ``change_pct`` the percent change.
        split_by (str | None): Dimension used for figure columns, or None for a
            single column.
        options (dict | None): Loader settings, including ``attribute_case``
            and ``insulation_options``.
        include_counts (bool): Append customer counts to legend labels.
        x_limits (tuple[float, float] | None): Axis limits. Derived from
            percentiles when None, symmetric about zero in change modes.
        palette_name (str): Seaborn palette for the group colors.
        population (pandas.DataFrame | None): Pre-loaded population, to avoid
            re-reading the HDF5 files across repeated calls.

    Returns:
        pandas.DataFrame: The plotted rows, with ``Rate``, ``Group``,
        ``Split``, and the plotted value column.
    """
    if mode not in ('level', 'change', 'change_pct'):
        raise ValueError("mode must be 'level', 'change', or 'change_pct'.")
    if metric not in CFS_METRICS:
        raise ValueError(f'Unknown metric {metric}. Available: {sorted(CFS_METRICS)}.')
    options = options or {}

    if population is None:
        population = load_customer_cfs_population(
            cases, data_paths, cust_class,
            options.get('attribute_case', 1), options.get('insulation_options'),
            options.get('metadata_paths'))

    column = {'level': metric, 'change': metric + ' change',
              'change_pct': metric + ' change pct'}[mode]
    if column not in population.columns:
        raise ValueError(f'Column "{column}" is not in the loaded population.')

    frame, group_order, group_title = resolve_cfs_groups(population, dimension, include_counts)

    if split_by:
        frame, split_order, split_title = resolve_cfs_groups(frame, split_by)
        frame = frame.rename(columns={'Group': 'Split'})
        frame, group_order, group_title = resolve_cfs_groups(frame, dimension, include_counts)
    else:
        frame['Split'] = 'Participating customers'
        split_order, split_title = ['Participating customers'], ''

    rows = list(cases) if mode == 'level' else list(cases[1:])
    frame = frame[frame['Rate'].isin(rows)].dropna(subset=[column])
    if frame.empty:
        raise ValueError(f'No rows remain for metric {metric} in mode {mode}.')

    group_order = [label for label in group_order if label in set(frame['Group'])]
    split_order = [label for label in split_order if label in set(frame['Split'])]

    spec = CFS_METRICS[metric]
    if mode == 'change_pct':
        axis_label = f'Change in {spec["label"]} from {cases[0]} (%)'
        bin_width, unit_suffix = 5, '%'
        share_y = False
    elif mode == 'change':
        axis_label = f'Change in {spec["label"]} from {cases[0]}'
        bin_width, unit_suffix = spec.get('change_bin', spec['bin']), spec['unit']
        share_y = True
    else:
        axis_label = spec['label']
        bin_width, unit_suffix = spec['bin'], spec['unit']
        share_y = True

    if x_limits is None:
        low = float(frame[column].quantile(0.01))
        high = float(frame[column].quantile(0.99))
        if mode != 'level':
            reach = max(abs(low), abs(high))
            x_limits = (-reach, reach)
        else:
            x_limits = (low, high)

    palette = sns.color_palette(palette_name, n_colors=max(len(group_order), 1))
    colors = {label: palette[index] for index, label in enumerate(group_order)}

    plot_path = os.path.join(output_path, 'plots')
    csv_path = os.path.join(output_path, 'data')
    os.makedirs(plot_path, exist_ok=True)
    os.makedirs(csv_path, exist_ok=True)
    stem = ('Case_Compare_CFS_' + metric + '_'
            + mode + '_by_' + dimension + '_' + str(cust_class)
            + ('_by_' + split_by if split_by else ''))

    fig, axes = plt.subplots(len(rows), len(split_order),
                             figsize=(5.6 * len(split_order), 3.2 * len(rows)),
                             sharex=True, sharey=share_y, squeeze=False)
    try:
        drawn = []
        for row, case in enumerate(rows):
            for col, split in enumerate(split_order):
                axis = axes[row][col]
                subset = frame[(frame['Rate'] == case) & (frame['Split'] == split)]
                for label in group_order:
                    values = subset.loc[subset['Group'] == label, column].dropna()
                    if len(values) < 2 or values.nunique() < 2:
                        continue
                    sns.kdeplot(x=values, color=colors[label], fill=True, alpha=0.20,
                                linewidth=2.5, warn_singular=False, ax=axis)
                    axis.axvline(values.median(), color=colors[label],
                                 linestyle=':', linewidth=1.5)
                    if label not in drawn:
                        drawn.append(label)

                if mode != 'level':
                    axis.axvline(0, color='dimgrey', linestyle='--', linewidth=1.5)
                heading = case if mode == 'level' else f'{case} vs {cases[0]}'
                title = heading if not split_by else f'{heading} — {split} (n={len(subset):,})'
                axis.set_title(title, fontsize=12, loc='left')
                axis.set_xlabel('')
                axis.set_xlim(*x_limits)
                if col == 0:
                    scale = 100 * bin_width
                    axis.yaxis.set_major_formatter(FuncFormatter(
                        lambda value, _position: f'{value * scale:g}'))
                    axis.set_ylabel(f'Share of Customers\n(% per {bin_width:g} '
                                    f'{unit_suffix})', size=10)
                else:
                    axis.set_ylabel('')

        for axis in axes[-1]:
            axis.set_xlabel(axis_label, size=12)
        handles = [Line2D([], [], color=colors[label], linewidth=2.5, label=str(label))
                   for label in group_order if label in drawn]
        handles.append(Line2D([], [], color='dimgrey', linestyle=':', linewidth=1.5,
                              label='Group median'))
        if mode != 'level':
            handles.append(Line2D([], [], color='dimgrey', linestyle='--', linewidth=1.5,
                                  label='No change'))
        axes[0][-1].legend(handles=handles, title=group_title, loc='best',
                           fontsize=9, title_fontsize=10, framealpha=1)
        fig.suptitle(f'{str(cust_class).capitalize()} {axis_label} by Rate'
                     + (f' and {split_title}' if split_by else '')
                     + f', grouped by {group_title}', y=1.0)
        fig.tight_layout()
        fig.savefig(os.path.join(plot_path, stem + '.png'), bbox_inches='tight')
    finally:
        plt.close(fig)

    aggregations = {'customers': (column, 'count'), 'mean': (column, 'mean'),
                    'median': (column, 'median'), 'std': (column, 'std'),
                    'p10': (column, lambda values: values.quantile(0.10)),
                    'p90': (column, lambda values: values.quantile(0.90))}
    if mode != 'level':
        aggregations['share_worse_off'] = (column, lambda values: 100 * (values > 0).mean())
    summary = (frame.groupby(['Rate', 'Split', 'Group']).agg(**aggregations)
               .reindex(pd.MultiIndex.from_product([rows, split_order, group_order],
                                                   names=['Rate', 'Split', group_title]))
               .dropna(how='all'))
    summary['p90-p10 spread'] = summary['p90'] - summary['p10']
    summary.to_csv(os.path.join(csv_path, stem + '_summary.csv'))
    frame.to_csv(os.path.join(csv_path, stem + '.csv'), index=False)
    print(summary.round(2).to_string())

    return frame

def load_temperature_incidence(data_path, dso_range, hvac_mode='cooling'):
    """Load one case's annual indoor-air deviation histograms by customer.

    Reads ``temperature_incidence_dso_<N>_data.h5`` written by
    :func:`tesp_support.dsot.plots.annual_temperature_incidence`, keeps one HVAC
    mode, and sums the readings of houses sharing a billing meter, so each
    customer counts by its hours of data.

    Args:
        data_path (str): Annual result directory for the case.
        dso_range (iterable[int]): DSOs to load.
        hvac_mode (str): ``cooling`` or ``heating``.

    Returns:
        pandas.DataFrame: Reading counts indexed by ``Customer ID``, with the
        columns of :func:`tesp_support.dsot.plots.temperature_incidence_columns`.
    """
    frames = []
    for dso in dso_range:
        print(f'reading {data_path} - temperature_incidence_dso_{dso}_data.h5')
        incidence_file = os.path.join(data_path, f'temperature_incidence_dso_{dso}_data.h5')
        if not os.path.isfile(incidence_file):
            raise FileNotFoundError(f'{incidence_file} is missing; run the temperature-incidence '
                                    'post-processing first.')
        incidence = pd.read_hdf(incidence_file, key='temperature_incidence', mode='r')
        try:
            meters = incidence.xs(hvac_mode, level='mode').groupby('meter ID').sum()
        except KeyError:
            print(f'Cannot find {meters.index}')
        meters.index = 'DSO' + str(dso) + '_' + meters.index.astype(str)
        frames.append(meters)
    customers = pd.concat(frames)
    customers.index.name = 'Customer ID'
    return customers

def customer_comfort_pdf_by_group(cases, data_paths, output_path, hvac_mode='cooling',
                                  dimension='building_type', cust_class='residential',
                                  split_by=None, options=None, include_counts=True,
                                  normalize='mode', palette_name='viridis', population=None):
    """Plot time spent beyond the original HVAC setpoint by rate and customer attribute.

    Draws one panel per rate and the chosen customer dimension encoded by color, 
    similar to `customer_cfs_pdf_by_group`. Each curve is the pooled histogram of
    5-minute readings for HVAC-participating customers in the group, binned by
    how far indoor temperature was above the original cooling setpoint or below
    the original heating setpoint (separately) at 0.1°F resolution. Each customer 
    counts by its hours of data.

    Readings are assigned to cooling or heating by the house's last active HVAC
    mode, and participation is taken from the attribute case so every rate,
    including the baseline (Flat), covers the same customers.

    How to read these plots: For example, a bar of 2% at 1.5°F means that 2% of 
    that group's cooling-mode hours were spent 1.5°F warmer than the customer's
    original setpoint (before adjusting to participate in the market or rate).

    Args:
        cases (list[str]): Rate labels with the baseline first.
        data_paths (list[str]): Result directory for each corresponding case.
        output_path (str): Output root; ``plots`` and ``data`` subdirectories
            are created if missing.
        hvac_mode (str): ``cooling`` or ``heating``.
        dimension (str): Grouping dimension key in ``CFS_DIMENSIONS``.
        cust_class (str | None): Tariff class filter, or None for all classes.
        split_by (str | None): Dimension used for figure columns, or None for a
            single column.
        options (dict | None): Loader settings, as in
            :func:`customer_cfs_pdf_by_group`.
        include_counts (bool): Append customer counts to legend labels.
        normalize (str): ``mode`` divides by all hours in the HVAC mode, so the
            area under each curve is the share of time beyond the setpoint.
            ``exceedance`` divides by hours beyond the setpoint only.
        palette_name (str): Seaborn palette for the group colors.
        population (pandas.DataFrame | None): Pre-loaded population, to avoid
            re-reading the HDF5 files across repeated calls.

    Returns:
        pandas.DataFrame: The plotted histograms, with ``Rate``, ``Split``,
        ``Group``, ``Deviation start (F)``, and ``Share (%)``. A summary CSV
        also reports shares at or within the setpoint and beyond the plotted
        range, and mean exceedance with readings past the range counted at its
        upper edge.
    """
    if hvac_mode not in ('cooling', 'heating'):
        raise ValueError("hvac_mode must be 'cooling' or 'heating'.")
    if normalize not in ('mode', 'exceedance'):
        raise ValueError("normalize must be 'mode' or 'exceedance'.")
    options = options or {}

    if population is None:
        population = load_customer_cfs_population(
            cases, data_paths, cust_class,
            options.get('attribute_case', 1), options.get('insulation_options'),
            options.get('metadata_paths'))

    flags = ['cust_participating', 'hvac_participating']
    missing = [flag for flag in flags if flag not in population.columns]
    if missing:
        raise ValueError(f'Columns {missing} are not in the loaded population.')
    participants = population[population[flags].eq(True).all(axis=1)]
    #dso_range = sorted({int(dso) for dso in participants['dso'].dropna()})
    dso_range = [1,2,3,4,5,6,7,8]

    frames = []
    for case, data_path in zip(cases, data_paths):
        print(f'Reading data from {case} case for {dso_range} dsos')
        counts = load_temperature_incidence(data_path, dso_range, hvac_mode)
        rows = participants[participants['Rate'] == case]
        matched = rows.join(counts, on='Customer ID', how='inner')
        matched = matched[matched['samples'] > 0]
        print(f'{case}: {len(matched)} of {len(rows)} HVAC-participating customers '
              f'have {hvac_mode}-mode readings.')
        frames.append(matched)
    frame = pd.concat(frames, ignore_index=True)
    if frame.empty:
        raise ValueError(f'No HVAC-participating customers have {hvac_mode}-mode readings.')
    count_columns = list(counts.columns)

    frame, group_order, group_title = resolve_cfs_groups(frame, dimension, include_counts)
    if split_by:
        frame, split_order, split_title = resolve_cfs_groups(frame, split_by)
        frame = frame.rename(columns={'Group': 'Split'})
        frame, group_order, group_title = resolve_cfs_groups(frame, dimension, include_counts)
    else:
        frame['Split'] = 'Participating customers'
        split_order, split_title = ['Participating customers'], ''

    edges, _share, _stats = pt.deviation_histogram(frame[count_columns].sum(), normalize)
    bin_width = edges[1] - edges[0]

    mode_title = hvac_mode.capitalize()
    direction = 'Above' if hvac_mode == 'cooling' else 'Below'
    axis_label = f'Indoor Temperature {direction} Original {mode_title} Setpoint (°F)'
    hours_label = (f'{mode_title}-Mode Hours' if normalize == 'mode'
                   else f'Hours {direction} Setpoint')

    palette = sns.color_palette(palette_name, n_colors=max(len(group_order), 1))
    colors = {label: palette[index] for index, label in enumerate(group_order)}

    plot_path = os.path.join(output_path, 'plots')
    csv_path = os.path.join(output_path, 'data')
    os.makedirs(plot_path, exist_ok=True)
    os.makedirs(csv_path, exist_ok=True)
    stem = ('Case_Compare_Comfort_' + hvac_mode + '_'
            + normalize + '_by_' + dimension + '_' + str(cust_class)
            + ('_by_' + split_by if split_by else ''))

    rows = list(cases)
    panel_axes = {}                      # (case, split) -> axis, in plotting order
    ylabel_axes, xlabel_axes = set(), set()
    # Baseline in its own full-height column with an independent y-axis;
    # comparison rates wrap into a grid that shares one y-axis among themselves.
    compare_cases = list(cases[1:])
    n_cols = max(1, min(2, len(compare_cases)))
    n_rows = -(-len(compare_cases) // n_cols)          # ceiling division
    fig = plt.figure(figsize=(5.6 * (n_cols + 1), 3.2 * n_rows))
    grid = fig.add_gridspec(n_rows, n_cols + 1)
    base_axis = fig.add_subplot(grid[:, 0])
    panel_axes[(cases[0], split_order[0])] = base_axis
    ylabel_axes.add(base_axis)
    xlabel_axes.add(base_axis)

    shared_y = None
    for index, case in enumerate(compare_cases):
        row, col = divmod(index, n_cols)
        axis = fig.add_subplot(grid[row, col + 1], sharex=base_axis, sharey=shared_y)
        shared_y = shared_y or axis
        panel_axes[(case, split_order[0])] = axis
        if col == 0:
            ylabel_axes.add(axis)                      # comparison scale differs from Flat
        else:
            axis.tick_params(labelleft=False)
        if index + n_cols >= len(compare_cases):       # nothing below it in this column
            xlabel_axes.add(axis)
        else:
            axis.tick_params(labelbottom=False)
    legend_axis = panel_axes[(compare_cases[n_cols - 1], split_order[0])]
    histograms, summaries = [], []
    try:
        drawn = []
        for (case, split), axis in panel_axes.items():
            subset = frame[(frame['Rate'] == case) & (frame['Split'] == split)]
            for label in group_order:
                    members = subset[subset['Group'] == label]
                    _edges, share, stats = pt.deviation_histogram(
                        members[count_columns].sum(), normalize)
                    if share is None:
                        continue
                    axis.stairs(share, edges, color=colors[label], fill=True, alpha=0.20)
                    axis.stairs(share, edges, color=colors[label], linewidth=2.5)
                    if label not in drawn:
                        drawn.append(label)

                    histograms.append(pd.DataFrame({
                        'Rate': case, 'Split': split, 'Group': label,
                        'Deviation start (F)': edges[:-1], 'Share (%)': share}))
                    stats[f'{hvac_mode} hours'] = stats.pop('hours')
                    stats['F-hrs per customer'] = stats.pop('F-hrs') / len(members)
                    summaries.append({'Rate': case, 'Split': split, group_title: label,
                                      'customers': len(members), **stats})
            title = case if not split_by else f'{case} — {split} (n={len(subset):,})'
            axis.set_title(title, fontsize=12, loc='left')
            axis.set_xlim(0, edges[-1])
            axis.set_ylabel(f'Share of {hours_label}\n(% per {bin_width:g} °F)'
                            if axis in ylabel_axes else '', size=10)
            axis.set_xlabel(axis_label if axis in xlabel_axes else '', size=12)

        handles = [Line2D([], [], color=colors[label], linewidth=2.5, label=str(label))
                   for label in group_order if label in drawn]
        legend_axis.legend(handles=handles, title=group_title, loc='best',
                           fontsize=9, title_fontsize=10, framealpha=1)
        fig.suptitle(f'Participating {str(cust_class).capitalize()} Customers: Time {direction} '
                     f'Original {mode_title} Setpoint by Rate'
                     + (f' and {split_title}' if split_by else '')
                     + f', grouped by {group_title}', y=1.0)
        fig.tight_layout()
        fig.savefig(os.path.join(plot_path, stem + '.png'), bbox_inches='tight')
    finally:
        plt.close(fig)

    histogram = pd.concat(histograms, ignore_index=True)
    summary = pd.DataFrame(summaries).set_index(['Rate', 'Split', group_title])
    summary.to_csv(os.path.join(csv_path, stem + '_summary.csv'))
    histogram.to_csv(os.path.join(csv_path, stem + '.csv'), index=False)
    print(summary.round(2).to_string())

    return histogram

def classify_thermal_integrity(house, jitter=(0.8, 1.2), tables=None):
    """Assign a thermal integrity level using the building type's own table.

    Thermal integrity levels are defined per building type, with six levels for
    single family homes, five for apartments, and two HUD-code levels for
    manufactured homes, so candidates are restricted to the table matching the
    house class. The population generator writes the window enumerations
    unjittered and applies multiplicative jitter to the R-values and
    infiltration rate, so windows filter candidates exactly and the continuous
    attributes are ranked by mean absolute log ratio.

    Args:
        house (dict): House entry from ``DSO<N>_Customer_Metadata.json``.
        jitter (tuple[float, float]): Generator jitter bounds.
        tables (dict | None): Override for ``THERMAL_INTEGRITY_BY_CLASS``.

    Returns:
        tuple[str, int, str] | None: ``(building type, level index,
        description)``, or None when the house class is unrecognized or the
        envelope attributes are unusable.
    """
    tables = tables if tables is not None else THERMAL_INTEGRITY_BY_CLASS
    house_class = str(house.get('house_class', '')).upper()
    building_type = HOUSE_CLASS_TO_BUILDING_TYPE.get(house_class)
    if building_type is None or building_type not in tables:
        return None
    table = tables[building_type]

    stated = str(house.get('thermal_integrity', 'UNKNOWN')).upper()
    if stated.isdigit():
        for index, description, _fraction, _reference in table:
            if int(stated) == index:
                return building_type, index, description

    continuous = ['Rroof', 'Rwall', 'Rfloor', 'airchange_per_hour']
    values = {}
    for attribute in continuous:
        value = pd.to_numeric(house.get(attribute), errors='coerce')
        if pd.isna(value) or value <= 0:
            return None
        values[attribute] = float(value)

    # Window enumerations are unjittered, so use them as an exact filter.
    window_keys = ['glazing_layers', 'glass_type', 'glazing_treatment', 'window_frame']
    observed_windows = {}
    for key in window_keys:
        value = pd.to_numeric(house.get(key), errors='coerce')
        if not pd.isna(value):
            observed_windows[key] = int(value)

    candidates = [entry for entry in table
                  if all(entry[3].get(key) == value for key, value in observed_windows.items())]
    if not candidates and 'glazing_layers' in observed_windows:
        candidates = [entry for entry in table
                      if entry[3].get('glazing_layers') == observed_windows['glazing_layers']]
    if not candidates:
        candidates = table

    low, high = jitter
    tolerance = 1.02
    scored, feasible = [], []
    for index, description, _fraction, reference in candidates:
        ratios = [values[attribute] / reference[attribute] for attribute in continuous]
        distance = float(np.mean([abs(np.log(ratio)) for ratio in ratios]))
        scored.append((distance, index, description))
        if all(low / tolerance <= ratio <= high * tolerance for ratio in ratios):
            feasible.append((distance, index, description))

    pool = feasible or scored
    best = min(pool)
    return building_type, best[1], best[2]

def meter_insulation_levels(data_path, dso_range, cust_class='residential',
                            method='conductance', bins=3, group_description=True):
    """Map billing meters across DSOs to an insulation-level label.

    Two bucketing methods are available. ``conductance`` computes the
    :func:`envelope_conductance_index` for each house, aggregates it to the
    meter as a floor-area-weighted mean, then cuts the pooled population into
    equal-count groups. ``table`` matches each house to its building type's
    thermal integrity table via :func:`classify_thermal_integrity` and labels
    the meter with its largest house, since level indices mean different things
    across building types and cannot be averaged.

    ``conductance`` is the default because it is insensitive to the
    multiplicative jitter the population generator applies to R-values and does
    not assume the generator sampled the published tables. Equal-count binning
    also guarantees comparable sample sizes per group. Bin edges and labels are
    derived from the baseline case metadata, so groups are identical across
    rate cases.

    Args:
        data_path (str): Directory holding the customer metadata JSONs.
        dso_range (iterable[int] | int | str): DSOs to pool.
        cust_class (str | None): Tariff class filter, or None for all meters.
        method (str): ``conductance`` or ``table``.
        bins (int | list[float]): Group count for equal-count binning, or
            explicit UA-per-sqft edges. Ignored when ``method='table'``.
        group_description (bool): Append UA ranges or level descriptions to
            the group labels.

    Returns:
        tuple[dict, list]: ``((dso, meter ID) -> label, labels ordered from
        least to best insulated)``.
    """
    if isinstance(dso_range, (int, str)):
        dso_range = [dso_range]
    dso_range = [int(dso) for dso in dso_range]
    if method not in ('conductance', 'table'):
        raise ValueError("method must be 'conductance' or 'table'.")

    rows = []
    skipped = 0
    for dso in dso_range:
        metadata = pt.load_json(data_path, 'DSO' + str(dso) + '_Customer_Metadata.json')
        class_meters = {meter for meter, details in metadata['billingmeters'].items()
                        if cust_class is None or details.get('tariff_class') == cust_class}
        for house, details in metadata['houses'].items():
            meter = details.get('billingmeter_id')
            if meter not in class_meters:
                continue
            sqft = pd.to_numeric(details.get('sqft'), errors='coerce')
            weight = 1.0 if pd.isna(sqft) or sqft <= 0 else float(sqft)
            row = {'dso': dso, 'meter ID': meter, 'weight': weight}

            if method == 'conductance':
                score = envelope_conductance_index(details)
                if score is None:
                    skipped += 1
                    continue
                row['score'] = score
            else:
                level = classify_thermal_integrity(details)
                if level is None:
                    skipped += 1
                    continue
                building_type, index, description = level
                row['building_type'] = building_type
                row['level'] = index
                row['description'] = description
            rows.append(row)

    if not rows:
        raise ValueError(f'No {cust_class} houses in DSOs {dso_range} have usable envelope properties.')
    if skipped:
        print(f'Insulation bucketing skipped {skipped} houses with unusable or '
              f'unrecognized envelope data.')

    house_df = pd.DataFrame(rows)

    if method == 'table':
        if group_description:
            house_df['label'] = (house_df['building_type'] + ' L'
                                 + house_df['level'].astype(str) + ': '
                                 + house_df['description'])
        else:
            house_df['label'] = (house_df['building_type'] + ' L'
                                 + house_df['level'].astype(str))

        # Level indices are type-specific, so label each meter with its largest
        # house rather than averaging across houses.
        mixed = house_df.groupby(['dso', 'meter ID'])['label'].nunique()
        if int((mixed > 1).sum()):
            print(f'{int((mixed > 1).sum())} meters host houses at differing integrity '
                  f'levels; each is labeled by its largest house.')
        dominant = (house_df.sort_values('weight', ascending=False)
                    .drop_duplicates(subset=['dso', 'meter ID']))

        meter_to_label = {(row['dso'], row['meter ID']): row['label']
                          for _index, row in dominant.iterrows()}
        groups = (dominant.drop_duplicates(subset=['label'])[['label', 'building_type', 'level']]
                  .assign(type_rank=lambda frame: frame['building_type'].map(
                      lambda value: BUILDING_TYPE_ORDER.index(value)
                      if value in BUILDING_TYPE_ORDER else len(BUILDING_TYPE_ORDER)))
                  .sort_values(['type_rank', 'level']))
        order = groups['label'].tolist()
        counts = dominant['label'].value_counts()
        detail = ', '.join(f'{label.split(":")[0]}={int(counts[label])}' for label in order)
    else:
        house_df['weighted'] = house_df['score'] * house_df['weight']
        meters = house_df.groupby(['dso', 'meter ID'])[['weighted', 'weight']].sum()
        meters['score'] = meters['weighted'] / meters['weight']

        if isinstance(bins, int):
            edges = meters['score'].quantile(np.linspace(0, 1, bins + 1)).to_numpy()
            edges[0], edges[-1] = -np.inf, np.inf
        else:
            edges = np.concatenate(([-np.inf], np.asarray(bins, dtype=float), [np.inf]))
        edges = np.unique(edges)
        count = len(edges) - 1

        # Low UA per sqft means better insulation, so bin 0 is the best insulated
        # and names are reversed to run least-to-best in the returned order.
        name_sets = {2: ['Best', 'Least'],
                     3: ['Best', 'Moderate', 'Least'],
                     4: ['Best', 'Above median', 'Below median', 'Least']}
        names = name_sets.get(count, [f'Group {index + 1}' for index in range(count)])

        meters['level'] = pd.cut(meters['score'], bins=edges,
                                 labels=False, include_lowest=True).astype(int)
        band = meters.groupby('level')['score'].agg(['min', 'max', 'size'])

        labels = {}
        for index in range(count):
            label = names[index]
            if group_description and index in band.index:
                label = (f'{label} ({band.loc[index, "min"]:.1f} UA/ft²'
                         f'-{band.loc[index, "max"]:.1f})')
            labels[index] = label

        meter_to_label = {key: labels[row['level']] for key, row in meters.iterrows()}
        present = sorted(set(meters['level']), reverse=True)  # least insulated first
        order = [labels[index] for index in present]
        detail = ', '.join(f'{labels[index].split(" (")[0]}={int(band.loc[index, "size"])}'
                           for index in present)

    return meter_to_label, order

def envelope_conductance_index(house, window_wall_ratio=0.15, area_per_door=19.5):
    """Estimate whole-house heat-loss coefficient per floor area.

    Builds a simple UA from the metadata envelope description: conduction
    through ceiling, net wall, floor, doors, and windows, plus infiltration.
    Dividing by floor area gives a size-independent index in Btu/(hr·°F·ft²)
    where lower values mean better-insulated buildings.

    Door counts follow the report's building assumptions rather than the
    metadata ``doors`` field: four solid 19.5 sq-ft doors for single family and
    manufactured homes, and one for apartments with a sliding glass door
    counted as window area. Window area itself is a fixed fraction of gross
    wall area because the metadata does not record it, and window R-values are
    approximated from the glazing enumerations. Both are coarse, but windows
    are a modest share of total UA and the resulting ranking is stable.

    Args:
        house (dict): House entry from ``DSO<N>_Customer_Metadata.json``.
        window_wall_ratio (float): Fraction of gross wall area that is glazing.
        area_per_door (float): Area of a single solid door in square feet.

    Returns:
        float | None: UA per square foot, or None if inputs are unusable.
    """
    def number(key, default=None):
        value = pd.to_numeric(house.get(key, default), errors='coerce')
        return None if pd.isna(value) else float(value)

    sqft = number('sqft')
    r_roof, r_wall, r_floor = number('Rroof'), number('Rwall'), number('Rfloor')
    r_door, air_changes = number('Rdoors'), number('airchange_per_hour')
    if None in (sqft, r_roof, r_wall, r_floor, r_door, air_changes) or sqft <= 0:
        return None
    if min(r_roof, r_wall, r_floor, r_door) <= 0:
        return None

    house_class = str(house.get('house_class', '')).upper()
    building_type = HOUSE_CLASS_TO_BUILDING_TYPE.get(house_class, 'SINGLE_FAMILY')
    door_count = DOORS_BY_BUILDING_TYPE.get(building_type, 4)

    stories = max(int(round(number('stories', 1) or 1)), 1)
    height = number('ceiling_height', 8) or 8
    aspect = number('aspect_ratio', 1.0) or 1.0
    floor_area = sqft / stories
    width = np.sqrt(floor_area / aspect) if aspect > 0 else np.sqrt(floor_area)
    perimeter = 2 * (width + aspect * width)

    wall_fraction = number('exterior_wall_fraction', 1.0) or 1.0
    ceiling_fraction = number('exterior_ceiling_fraction', 1.0) or 1.0
    floor_fraction = number('exterior_floor_fraction', 1.0) or 1.0

    gross_wall = perimeter * height * stories * wall_fraction
    window_area = gross_wall * window_wall_ratio
    door_area = door_count * area_per_door
    if building_type == 'APARTMENT':
        # Second egress is a sliding glass door, counted as window area.
        window_area += area_per_door
    net_wall = max(gross_wall - window_area - door_area, 0.0)

    layers = int(number('glazing_layers', 2) or 2)
    r_window = WINDOW_R_BY_LAYERS.get(layers, 1.8)
    if int(number('glass_type', 1) or 1) == 2:
        r_window += 0.6
    r_window += WINDOW_R_FRAME_BONUS.get(int(number('window_frame', 1) or 1), 0.0)
    if int(number('glazing_treatment', 1) or 1) >= 2:
        r_window += 0.1

    volume = floor_area * height * stories
    ua = (floor_area * ceiling_fraction / r_roof
          + net_wall / r_wall
          + floor_area * floor_fraction / r_floor
          + door_area / r_door
          + window_area / r_window
          + 0.018 * air_changes * volume)
    return ua / sqft

def customer_peak_load_pdf_by_group(cases, data_paths, output_path, dimension='insulation',
                                    cust_class='residential', mode='level',
                                    split_by='cust_participating', dso_range=None,
                                    population=None, **kwargs):
    """Plot annual customer peak-load distributions by rate and a chosen attribute.

    Peak load is each customer's maximum metered demand over the year, so these
    are non-coincident peaks and do not sum to the system peak.

    Args:
        cases (list[str]): Rate labels with the baseline first.
        data_paths (list[str]): Result directory for each corresponding case.
        output_path (str): Output root for plots and summary CSVs.
        dimension (str): Grouping dimension key in ``CFS_DIMENSIONS``.
        cust_class (str | None): Tariff class filter.
        mode (str): ``level``, ``change``, or ``change_pct``.
        split_by (str | None): Dimension used for figure columns.
        dso_range (iterable[int] | None): Required when ``dimension`` is
            ``insulation`` and no population is supplied.
        population (pandas.DataFrame | None): Pre-loaded population.
        **kwargs: Forwarded to :func:`customer_cfs_pdf_by_group`.

    Returns:
        pandas.DataFrame: The plotted rows.
    """
    options = kwargs.pop('options', None)
    if options is None and dimension == 'insulation' and population is None:
        options = {'insulation_options': {'dso_range': dso_range}}
    return customer_cfs_pdf_by_group(
        cases, data_paths, output_path, dimension=dimension, metric='PeakLoad',
        cust_class=cust_class, mode=mode, split_by=split_by, options=options,
        population=population, **kwargs)

def customer_energy_pdf_by_group(cases, data_paths, output_path, dimension='insulation',
                                 cust_class='residential', mode='level',
                                 split_by='cust_participating', dso_range=None,
                                 population=None, **kwargs):
    """Plot annual customer energy-purchase distributions by rate and a chosen attribute.

    Energy purchased is net of any on-site generation, so rooftop-PV customers
    can show very low or negative annual totals.

    Args:
        cases (list[str]): Rate labels with the baseline first.
        data_paths (list[str]): Result directory for each corresponding case.
        output_path (str): Output root for plots and summary CSVs.
        dimension (str): Grouping dimension key in ``CFS_DIMENSIONS``.
        cust_class (str | None): Tariff class filter.
        mode (str): ``level``, ``change``, or ``change_pct``.
        split_by (str | None): Dimension used for figure columns.
        dso_range (iterable[int] | None): Required when ``dimension`` is
            ``insulation`` and no population is supplied.
        population (pandas.DataFrame | None): Pre-loaded population.
        **kwargs: Forwarded to :func:`customer_cfs_pdf_by_group`.

    Returns:
        pandas.DataFrame: The plotted rows.
    """
    options = kwargs.pop('options', None)
    if options is None and dimension == 'insulation' and population is None:
        options = {'insulation_options': {'dso_range': dso_range}}
    return customer_cfs_pdf_by_group(
        cases, data_paths, output_path, dimension=dimension, metric='EnergyPurchased',
        cust_class=cust_class, mode=mode, split_by=split_by, options=options,
        population=population, **kwargs)

def load_comparison_plot(day_range, metadata_path, cases, data_paths, output_path):
    """Compare total system load over a selected day range.

    Uses the first case's ``generate_case_config.json`` to derive timestamps,
    then sums substation and industrial load for each case. ``metadata_path``
    is retained for compatibility but is not currently read.

    Args:
        day_range (range): Day numbers defining the selected time window.
        metadata_path (str): Unused compatibility parameter.
        cases (list[str]): Case identifiers recognized by the display-name map.
        data_paths (list[str]): Result directory for each corresponding case.
        output_path (str): Output root containing existing ``plots`` and
            ``data`` subdirectories.

    Returns:
        None. Saves a load-comparison PNG and a time-series CSV.
    """

    line_colors = ['#e0813e', '#062c49', '#84baa9', '#965c79']

    # Create a mapping between case and desired name
    Case_name_dict = {
        'Flat': 'Flat',
        'TOU': 'TOU',
        'DSOT': 'DE',
        'RND': 'DE+C',
        'TOU-20': 'TOU-20%',
        'TOU-40': 'TOU-40%',
        'TOU-60': 'TOU-60%',
        'TOU-80': 'TOU-80%'
    }

    for i in range(len(cases)):
        case = cases[i]
        case_name = Case_name_dict[case]
        data_path = data_paths[i]

        if case == cases[0]:
            case_config = pt.load_json(data_path, 'generate_case_config.json')
            # Load ERCOT load profile data
            # metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
            sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
            # ercot_df = pt.load_ercot_data(metadata_file, sim_start, day_range)
            # ames_rt_df = pt.load_ames_data(case, day_range)

            start_time = sim_start + timedelta(days=day_range[0] - 1)
            stop_time = sim_start + timedelta(days=day_range[-1]) - timedelta(minutes=5)

        loads_df = pd.read_csv(data_path + '/der_stack_data_allDSOs.csv', index_col='time', parse_dates=True)
        loads_df = loads_df.loc[start_time:stop_time, :]

        if loads_df.index[-1] < stop_time:
            raise Exception('DER stack plot data not available for case' + case + ' at ' + str(stop_time) + ".")

        if i == 0:
            # Plot load plot
            plt.figure(figsize=(15, 10))

            output_df = loads_df[['Substation']].copy()
            output_df['Substation'] += loads_df['Industrial Loads']
            output_df = output_df.rename(columns={'Substation': case_name})
        else:
            output_df[case_name] = loads_df['Substation'] + loads_df['Industrial Loads']

        plt.plot(loads_df.index, loads_df['Substation'] + loads_df['Industrial Loads'], label=case_name,
                 color=line_colors[i], linewidth=3)

        # if plot_ref:
        #     bus_cols = [col for col in ercot_df.columns if 'Bus' in col]
        #     plt.plot(ercot_df.index, ercot_df[bus_cols].sum(axis=1), label='ERCOT Load', color='grey', linestyle='--', linewidth=3)

    large_font = True
    if large_font:
        tick_font = 18
        label_font = 24
        legend_font = 24
    else:
        tick_font = 17
        label_font = 25
        legend_font = 17

    plt.legend(loc='lower left', prop={'size': legend_font})
    # plt.legend(loc='lower left', prop={'size': legend_font}, ncol=2)
    plt.xlabel('Time', size=label_font)
    plt.ylabel('Load (MW)', size=label_font)
    plt.ylim(top=80000, bottom=0)
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=tick_font)
    # plt.title('DSO load profile by end-load type (ALL DSOs)', size=20)
    plot_filename = 'Case_Compare_Load_Plots_' + loads_df.index[0].strftime('%m-%d') + '.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    output_df.to_csv(path_or_buf=output_path + '/data/Case_Compare_System_Load_' + output_df.index[0].strftime('%m-%d') + '.csv')

def retail_price_comparison_plot(dso, day_range, metadata_path, cases, data_paths, rate_scenarios, Month, output_path):
    """Compare retail-price time series for one DSO and day range.

    Loads day-ahead LMP data for each case, applies its flat, TOU, or
    transactive tariff calculation, then plots and exports the retail prices.
    Tariff JSON and, for TOU, case-specific TOU parameters are read as inputs.

    Args:
        dso (str | int): DSO identifier used to select LMP and tariff data.
        day_range (range): Day numbers defining the selected time window.
        metadata_path (str): Directory containing the tariff JSON files.
        cases (list[str]): Case identifiers recognized by the display-name map.
        data_paths (list[str]): Result directory for each corresponding case.
        rate_scenarios (list[str]): Tariff scenario for each case.
        Month (str): Month-specific case subdirectory used for configuration
            and TOU date lookup.
        output_path (str): Output root containing existing ``plots`` and
            ``data`` subdirectories.

    Returns:
        None. Saves a retail-price PNG and a time-series CSV.
    """

    # line_colors = ['green', 'red', 'blue', 'black']
    line_colors = ['#e0813e', '#062c49', '#84baa9', '#965c79']

    # Create a mapping between month number and month abbreviation
    Case_name_dict = {
        'Flat': 'Flat',
        'TOU': 'TOU',
        'DSOT': 'DE',
        'RND': 'DE+C'}

    for i in range(len(cases)):
        case = cases[i]
        case_name = Case_name_dict[case]
        data_path = data_paths[i]
        rate_scenario = rate_scenarios[i]

        if case == cases[0]:
            case_config = pt.load_json(data_path +'/' + Month, 'generate_case_config.json')
            # Load ERCOT load profile data
            # metadata_file = os.path.join(metadata_path, case_config['refLoadMn'][5].split('/')[-1])
            sim_start = datetime.strptime(case_config['StartTime'], '%Y-%m-%d %H:%M:%S')
            # ercot_df = pt.load_ercot_data(metadata_file, sim_start, day_range)
            # ames_rt_df = pt.load_ames_data(case, day_range)

            start_time = sim_start + timedelta(days=day_range[0] - 1)
            stop_time = sim_start + timedelta(days=day_range[-1]) - timedelta(minutes=5)

            # Create a mapping between month number and month abbreviation
            month_num_to_abbrev = {
                1: "Jan",
                2: "Feb",
                3: "Mar",
                4: "Apr",
                5: "May",
                6: "Jun",
                7: "Jul",
                8: "Aug",
                9: "Sep",
                10: "Oct",
                11: "Nov",
                12: "Dec",
            }

            # Identify the month name
            month_name = month_num_to_abbrev[
                pt.get_date(data_path +'/' + Month, dso, day_range[0]).month
            ]

        DA_LMPs_df = pd.read_csv(data_path + '/Annual_DA_LMP_Load_data.csv', index_col=0, parse_dates=True)
        DA_LMPs_df = DA_LMPs_df.loc[start_time:stop_time, :]

        # Load Tariff structure
        file_name = "rate_case_values_" + rate_scenario + ".json"
        tariff = pt.load_json(metadata_path, file_name, False)

        if rate_scenario in ["flat", "Flat"]:
            DA_LMPs_df['Retail'] = tariff['DSO_'+str(dso)]['flat_rate']
        elif rate_scenario == "TOU":
            tou_params = pt.load_json(os.path.join(data_path), "time_of_use_parameters.json", False)
            for ii in DA_LMPs_df.index:
                hour = ii.hour
                for k in tou_params["DSO_" + dso][month_name]["periods"].keys():
                    for t in range(len(tou_params["DSO_" + dso][month_name]["periods"][k]["hour_start"])):
                        if hour >= tou_params["DSO_" + dso][month_name]["periods"][k]["hour_start"][t] \
                                and hour < tou_params["DSO_" + dso][month_name]["periods"][k]["hour_end"][t]:
                            DA_LMPs_df.loc[ii, 'Retail'] = tou_params["DSO_" + dso][month_name]["price"] \
                                * tou_params["DSO_" + dso][month_name]["periods"][k]["ratio"]
        elif rate_scenario in ["DSOT",""]:
            DA_LMPs_df['Retail'] = DA_LMPs_df['da_lmp'+str(dso)]/1000 + tariff['DSO_'+str(dso)]['transactive_dist_rate']
        elif rate_scenario in ["RandD", "EandC"]:
            # DA_LMPs_df['Retail'] = (DA_LMPs_df['da_lmp'+str(dso)])/1000 + tariff['DSO_'+str(dso)]['transactive_dist_rate']
            DA_LMPs_df['Retail'] = (DA_LMPs_df['da_lmp'+str(dso)] + DA_LMPs_df[' Adder'])/1000 + tariff['DSO_'+str(dso)]['transactive_dist_rate']

        if i == 0:
            # Plot load plot
            plt.figure(figsize=(15, 10))

            output_df = DA_LMPs_df[['Retail']]
            output_df = output_df.rename(columns={'Retail': case_name})
        else:
            output_df[case] = DA_LMPs_df[['Retail']]

        plt.plot(DA_LMPs_df.index, DA_LMPs_df['Retail'], label=case_name, color=line_colors[i], linewidth=3)

        # if plot_ref:
        #     bus_cols = [col for col in ercot_df.columns if 'Bus' in col]
        #     plt.plot(ercot_df.index, ercot_df[bus_cols].sum(axis=1), label='ERCOT Load', color='grey', linestyle='--', linewidth=3)

    large_font = True
    if large_font:
        tick_font = 18
        label_font = 24
        legend_font = 24
    else:
        tick_font = 17
        label_font = 25
        legend_font = 17

    plt.legend(loc='lower left', prop={'size': legend_font})
    # plt.legend(loc='lower left', prop={'size': legend_font}, ncol=2)
    plt.xlabel('Time', size=label_font)
    plt.ylabel('Retail Price ($/kW-hr)', size=label_font)
    plt.ylim(bottom=0, top=0.4)
    ax = plt.gca()
    ax.tick_params(axis='both', which='major', labelsize=tick_font)
    # plt.title('DSO load profile by end-load type (ALL DSOs)', size=20)
    plot_filename = 'Case_Compare_Price_Plots_' + DA_LMPs_df.index[0].strftime('%m-%d') + '.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    output_df.to_csv(path_or_buf=output_path + '/data/Case_Compare_Retail_Price_' + output_df.index[0].strftime('%m-%d') + '.csv')

def plot_annual_stats(cases, data_paths, output_path, dso_num, variable):
    """Plot annual and daily distributions for a system metric across cases.

    Loads the relevant annual result files, adds calendar-month and case
    labels, and produces monthly distribution plots. Most metrics also produce
    annual and daily-variation duration curves; ``Hybrid`` instead compares
    total load and day-ahead LMP in monthly plots.

    Args:
        cases (list[str]): Labels assigned to each case's observations.
        data_paths (list[str]): Result directory for each corresponding case.
        output_path (str): Output root; its ``plots`` subdirectory must exist.
        dso_num (str): DSO identifier appended to an LMP column name.
        variable (str): ``DA LMP``, ``RT LMP``, ``Total Load``, ``Hybrid``,
            ``Renewable Percent``, or ``Curtailment Percent``.

    Returns:
        None. Saves one or more dated PNG files in ``output_path/plots``.
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
    # pal = ['violet'] + ['lightgreen'] + ["gold"] + ['skyblue']
    # pal = sns.color_palette("Paired")
    pal = ['#e0813e'] + ['#062c49'] + ['#84baa9'] + ['#965c79']
    pal = pal[0:len(cases)]

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
        plt.grid(visible=True, which='both', color='k', linestyle=':')
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

        plot_filename =  'Case_Comparison_' + file_name + '_Duration_Curve.png'
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
        plt.grid(visible=True, which='both', color='k', linestyle=':')
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

        plot_filename =  'Case_Comparison_Daily_Variation_' + file_name + '_Duration_Curve.png'
        file_path_fig = os.path.join(output_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')

    plt.close(fig)

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
    """Calculate a preliminary difference between two load-statistics files.

    Currently reads ``DSO_load_stats.csv`` from the first two result
    directories and subtracts their ``Max`` rows. This prototype does not yet
    use ``cases``, ``output_path``, or ``variable`` to generate a plot or save
    the calculated difference.

    Args:
        cases (list[str]): Reserved for the planned case comparison.
        data_paths (list[str]): At least two result directories, each
            containing ``DSO_load_stats.csv``.
        output_path (str): Reserved for planned plot output.
        variable (str): Reserved for planned metric selection.

    Returns:
        None. The calculated difference remains local to this function.
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

def _plot_waterfall(labels, values, output_path, net_label, y_label, sorted_value=False):
    label_order = np.argsort(np.abs(np.asarray(values)))[::-1] if sorted_value else np.arange(len(labels))
    waterfall_chart.plot(
        np.arange(len(labels)), values, sorted_value=sorted_value, rotation_value=90,
        net_label=len(labels), y_lab=y_label)
    tick_labels = [labels[index] for index in label_order] + [net_label]
    plt.xticks(range(len(tick_labels)), tick_labels, rotation=90)
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()

def dso_cfs_delta(cases_list, data_paths_list, dso_range, metadata_file, metadata_path):
    """Compare DSO cost-and-benefit components between baseline and result cases.

    For each comparison, loads customer CFS summaries and per-DSO revenue,
    expense, capital-cost, and wholesale-purchase JSON files. It aggregates
    selected cost deltas, creates waterfall and benefit scatter plots, and
    collects net-benefit totals for a final summary chart. Each path pair is
    ordered as ``[baseline_path, result_path]``.

    Args:
        cases_list (list[list[str]]): Baseline/result case-name pairs. Result
            names must be present in the internal display-name map.
        data_paths_list (list[list[str]]): One ``[baseline, result]`` directory
            pair per case comparison.
        dso_range (iterable[int]): DSOs whose result files are included.
        metadata_file (str): Metadata JSON filename containing DSO population
            and utility-type information.
        metadata_path (str | None): Directory containing ``metadata_file``;
            when ``None``, a relative default path is used.

    Returns:
        None. Saves comparison PNGs under each result directory's ``plots``
        folder, which must already exist.
    """
    assumptions = []
    cases = []
    benefits = []

    Case_name_dict = {
        'Flat': 'Flat',
        'TOU': 'TOU',
        'DSOT': 'DE',
        'RND': 'DE+C',
        'Sub': 'B&S'}

    for i in range(len(cases_list)):
        results_path = data_paths_list[i][1]
        comp_path = data_paths_list[i][0]
        case_name = Case_name_dict[cases_list[i][1]]

        if metadata_path == None:
            path = "../../../examples/dsot_data"
        else:
            path = metadata_path

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

            # TODO: Need to overhaul revenue structure so it is consistent for all cases.  It is not used for now.
            # revenue_delta = rec_diff(revenue, revenue_comp)
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

        plot_filename =  'DSO_CFS_Waterfall_ranked.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        _plot_waterfall(labels, values, file_path_fig, 'Net Benefit', 'Annual Impact ($M)', sorted_value=True)

        plot_filename =  'DSO_CFS_Waterfall.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        _plot_waterfall(labels, values, file_path_fig, 'Net Benefit', 'Annual Impact ($M)')

        plot_filename =  'DSO_CFS_Waterfall_low.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        _plot_waterfall(labels, values_low, file_path_fig, 'Net Benefit (Low)', 'Annual Impact ($M)')

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
        plot_filename =  'DSO_CFS_Benefits_Load_Scatter.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')
        plt.close()

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
        plot_filename =  'DSO_CFS_Benefits_Cust_Scatter.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')
        plt.close()

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
        plot_filename =  'DSO_CFS_Benefits_Energy_Scatter.png'
        file_path_fig = os.path.join(results_path, 'plots', plot_filename)
        plt.savefig(file_path_fig, bbox_inches='tight')
        plt.close()

        sensitivity = False
        if sensitivity:
            assumptions.extend(['High', 'Nominal', 'Low'])
            cases.extend([cases_list[i][1], cases_list[i][1], cases_list[i][1]])
            benefits.extend([net_benefit_high, net_benefit, net_benefit_low])
        else:
            assumptions.extend(['Saving'])
            cases.extend([case_name])
            benefits.extend([net_benefit])

    # Add data to dataframe for summary plot
    benefits_sum = {'Assumption': assumptions,
                'Case': cases,
                'Annual Net Benefit ($M)': benefits}

    summary_benefits_df = pd.DataFrame(benefits_sum, columns = ['Assumption', 'Case', 'Annual Net Benefit ($M)'])

    if sensitivity:
        summary_plot = sns.catplot(
            data=summary_benefits_df, kind="bar",
            x="Case", y="Annual Net Benefit ($M)", hue="Assumption",
            errorbar="sd", palette="dark", alpha=.6, height=4
        )
    else:
        line_colors = ['#062c49', '#84baa9', '#965c79', 'red']
        summary_plot = sns.catplot(
            data=summary_benefits_df, kind="bar",
            x="Case", y="Annual Net Benefit ($M)", hue="Case", legend=False,
            errorbar="sd", palette=line_colors[:summary_benefits_df['Case'].nunique()], alpha=.6, height=4
        )
    summary_plot.set_axis_labels("Case", "Annual Net Benefit ($M)")
    plot_filename =  'DSO_CFS_Benefits_Summary.png'
    file_path_fig = os.path.join(results_path, 'plots', plot_filename)
    summary_plot.savefig(file_path_fig, bbox_inches='tight')
    plt.close(summary_plot.figure)
    # plt.despine(left=True)
    # plt.set_axis_labels("", "Body mass (g)")

def customer_cfs_delta(cases, data_paths, metadata_file, metadata_path = None):
    """Compare customer costs, usage, and savings for a baseline/result pair.

    Loads each case's ``Master_Customer_Dataframe.h5``, derives bill,
    energy-cost, energy-use, and peak-load changes, then generates population
    plots grouped by customer attributes. The first case/path is the baseline;
    the second is the comparison case. A population-statistics CSV is written
    to the comparison result directory; plots are saved under the respective
    case directories used by each analysis.

    Args:
        cases (list[str]): Two labels in baseline, comparison order.
        data_paths (list[str]): Two result directories in the same order, each
            containing ``Master_Customer_Dataframe.h5``.
        metadata_file (str): Metadata JSON filename used to group DSOs by type.
        metadata_path (str | None): Metadata directory; defaults to the
            function's relative DSOT data path.

    Returns:
        None. Writes ``Customer_pop_stats.csv`` to the comparison result
        directory and PNGs beneath the case result directories. Their required
        ``plots`` subdirectories must exist.
    """
    if metadata_path == None:
        path = "../../../examples/dsot_data"
    else:
        path = metadata_path

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

    customer_cfs_df['building_type'] = customer_cfs_df['building_type'].replace(
        {'SINGLE_FAMILY': 'Single-family', 'MOBILE_HOME': 'Manufactured home', 'MULTI_FAMILY': 'Multi-family'})
    customer_comp_cfs_df['building_type'] = customer_comp_cfs_df['building_type'].replace(
        {'SINGLE_FAMILY': 'Single-family', 'MOBILE_HOME': 'Manufactured home', 'MULTI_FAMILY': 'Multi-family'},
        )
    customer_cfs_df['heating'] = customer_cfs_df['heating'].replace(
        {'GAS': 'Gas', 'RESISTANCE': 'Resistance', 'HEAT_PUMP': 'Heat pump'},
        )
    customer_comp_cfs_df['heating'] = customer_comp_cfs_df['heating'].replace(
        {'GAS': 'Gas', 'RESISTANCE': 'Resistance', 'HEAT_PUMP': 'Heat pump'},
        )
    customer_cfs_df['tariff_class'] = customer_cfs_df['tariff_class'].replace(
        {'residential': 'Residential', 'commercial': 'Commercial'},
        )
    customer_comp_cfs_df['tariff_class'] = customer_comp_cfs_df['tariff_class'].replace(
        {'residential': 'Residential', 'commercial': 'Commercial'},
        )

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
    der_participation = [' None', ' EV', ' BESS', ' EV, BESS', ' HVAC', ' WH', ' HVAC, WH', ' HVAC, EV', ' WH, EV', ' HVAC, WH, EV']
    participation = [True, False]
    hr_bau_participation = ['None', ' EV', ' PV', ' EV, PV']
    income_level = ['Low', 'Middle', 'Upper']

    dso_type = {'Urban': [],
                'Suburban': [],
                'Rural': []}

    for DSO in metadata.keys():
        if 'DSO' in DSO:
            if metadata[DSO]['used']:
                dso_type[metadata[DSO]['utility_type']].append(int(DSO.split('_')[-1]))

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
        metric_data = pd.to_numeric(subset['EnergyPurchased'], errors='coerce').dropna()
        if metric_data.empty:
            continue

        sns.histplot(x=metric_data, stat='density', bins=200, label=str(cust))

    plt.legend(prop={'size': 10}, title='Customer Class', loc='upper left')
    plt.title(cases[0] + ': Energy purchases by customer class')
    plt.xlabel('Energy Purchased (kw-hrs/year)')
    plt.ylabel('Density')
    plt.xlim(0, 0.2e6)
    plot_filename =  'Customer_PDF_tariff_class_EnergyPurchased.png'
    file_path_fig = os.path.join(data_paths[0], 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    # Plot base case attributes of residential customers.
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

    plot_customer_pdf('pv_participating', participation, 'Bills', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('pv_participating', participation, 'EnergyPurchased', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('pv_participating', participation, 'PeakLoad', pop_comp_subset, cases[0], data_paths[0])

    plot_customer_pdf('income_level', income_level, 'Bills', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('income_level', income_level, 'EnergyPurchased', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('income_level', income_level, 'PeakLoad', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('income_level', income_level, 'sqft', pop_comp_subset, cases[0], data_paths[0])
    plot_customer_pdf('income_level', income_level, 'slider_setting', pop_comp_subset, cases[0], data_paths[0])

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
    plot_filename =  'House_sqft_energy_Scatter.png'
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

    # Plot residential customer savings by income
    plot_customer_pdf('income_level', income_level, 'peak_load_reduction_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('income_level', income_level, 'bill_savings_pct', pop_subset, cases[1], data_paths[1])

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

    plot_customer_pdf('ev_participating', participation, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('ev_participating', participation, 'bill_savings_pct', pop_subset, cases[1], data_paths[1])

    plot_customer_pdf('wh_participating', participation, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('wh_participating', participation, 'bill_savings_pct', pop_subset, cases[1], data_paths[1])

    plot_customer_pdf('batt_participating', participation, 'net_energy_cost_savings_pct', pop_subset, cases[1], data_paths[1])
    plot_customer_pdf('batt_participating', participation, 'bill_savings_pct', pop_subset, cases[1], data_paths[1])

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
    plot_filename =  'Customer_Slider_Scatter.png'
    file_path_fig = os.path.join(data_paths[1], 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    # plt.clf()
    # plt.scatter(customer_cfs_df['slider_setting'], customer_cfs_df['net_energy_cost_savings_pct'])
    # plt.scatter(customer_cfs_df['EnergyPurchased'], customer_cfs_df['net_energy_cost_savings_pct'])
    # plt.scatter(customer_cfs_df['sqft'], customer_cfs_df['net_energy_cost_savings_pct'])
    # fig = customer_cfs_df.plot.scatter(x='slider_setting', y='net_energy_cost_savings_pct')
    # plt.show()
    # plot_filename =  'Customer_PDF_scatter.png'
    # file_path_fig = os.path.join(data_paths[0], 'plots', plot_filename)
    # plt.savefig(file_path_fig, bbox_inches='tight')

def plot_customer_pdf(attribute, variables, metric, pop_df, case, output_path):
    """Plot grouped customer metric distributions as density and histogram PNGs.

    Each value in ``variables`` selects a subset of ``pop_df`` using
    ``attribute``. The helper saves a density plot and a normalized histogram
    for the requested metric.

    Args:
        attribute (str): Customer-data column used to form groups.
        variables (iterable): Group values to plot. For DSO-type groups, these
            are keys whose corresponding DSO lists are in ``pop_df``.
        metric (str): Numeric customer-data column to plot.
        pop_df (pandas.DataFrame): Customer population or comparison data.
        case (str): Case label included in plot titles.
        output_path (str): Result directory containing an existing ``plots``
            subdirectory.

    Returns:
        None. Saves two dated PNG files in ``output_path/plots``.
    """

    xlabel_dict = {'bill_savings_pct': 'Annual Utility Bill Savings (%)',
                   'net_energy_cost_savings_pct': 'Annual Energy Costs Savings (%)',
                   'net_energy_purchased': 'Annual Energy Consumption (kW-hrs)',
                   'net_energy_purchased_pct': 'Annual Energy Savings (%)',
                   'peak_load_reduction': 'Annual Peak Load (kW)',
                   'peak_load_reduction_pct': 'Annual Peak Load Reduction (%)',
                   'sqft': 'Building Size (sq-ft)',
                   'slider_setting': 'Slider Setting (-)',
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
                   'ev_participating': 'EV Ownership',
                   'wh_participating': 'WH Participation',
                   'batt_participating': 'BESS Participation',
                   'income_level': 'Income Level',
                   'DER_participating': 'DER Participation'}

    if metric in ['bill_savings_pct', 'net_energy_cost_savings_pct']:
        x_low = -30
        x_high = 60
        y_low = 0
        y_high = 0.5
    elif metric in ['net_energy_purchased_pct']:
        x_low = -20
        x_high = 20
        y_low = 0
        y_high = 0.5
    elif metric in ['peak_load_reduction_pct']:
        x_low = -25
        x_high = 25
        y_low = 0
        y_high = 0.5
    elif metric in ['Bills']:
        x_low = 0
        x_high = 5000
        y_low = None
        y_high = None
    elif metric in ['EnergyPurchased']:
        x_low = 0
        x_high = 50000
        y_low = None
        y_high = None
    elif metric in ['PeakLoad']:
        x_low = 0
        x_high = 50
        y_low = None
        y_high = None
    elif metric in ['sqft']:
        x_low = 0
        x_high = 5000
        y_low = None
        y_high = None
    elif metric in ['slider_setting']:
        x_low = 0
        x_high = 1
        y_low = None
        y_high = None
    else:
        x_low = -50
        x_high = 50
        y_low = None
        y_high = None

    plt.clf()
    for var in variables:
        if var in ['Rural', 'Suburban', 'Urban']:
            subset = pop_df[pop_df[attribute].isin(variables[var])]
        else:
            subset = pop_df[pop_df[attribute] == var]
        metric_data = pd.to_numeric(subset[metric], errors='coerce').dropna()
        if metric_data.empty:
            continue

        sns.kdeplot(x=metric_data, fill=True, linewidth=3, warn_singular=False, label=str(var))

    plt.legend(prop={'size': 10}, title=legend_dict[attribute])
    plt.title(case + ': ' + xlabel_dict[metric] + ' by ' + legend_dict[attribute])
    plt.xlabel(xlabel_dict[metric])
    plt.xlim(x_low, x_high)
    plt.ylim(y_low, y_high)
    plt.ylabel('Population Fraction (-)')
    plot_filename =  'Customer_PDF_' + attribute + '_' + metric + '.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

    plt.clf()
    for var in variables:
        if var in ['Rural', 'Suburban', 'Urban']:
            subset = pop_df[pop_df[attribute].isin(variables[var])]
        else:
            subset = pop_df[pop_df[attribute] == var]
        metric_data = pd.to_numeric(subset[metric], errors='coerce').dropna()
        if metric_data.empty:
            continue

        sns.histplot(x=metric_data, stat='density', bins=200, label=str(var))

    plt.legend(prop={'size': 10}, title=legend_dict[attribute])
    plt.title(case + ': ' + xlabel_dict[metric] + ' by ' + legend_dict[attribute])
    plt.xlabel(xlabel_dict[metric])
    plt.xlim(x_low, x_high)
    plt.ylim(y_low, y_high)
    plt.ylabel('Population Fraction (-)')
    plot_filename =  'Customer_PDF_' + attribute + '_' + metric + 'dist.png'
    file_path_fig = os.path.join(output_path, 'plots', plot_filename)
    plt.savefig(file_path_fig, bbox_inches='tight')

def DSOT_plots():
    """Run the legacy DSOT analysis workflow configured in this function.

    This driver contains hard-coded simulation and metadata paths, selects
    cases and analysis stages through local flags, and conditionally runs load
    profiles, annual statistics, customer-population analysis, and DSO
    cost-benefit plots. Several legacy case-path variables used by its case
    selections are not defined here, so configure those names before enabling
    a selection that references them.

    Returns:
        None. Enabled helpers write plots and summary data to configured result
        directories.
    """
    pd.set_option('display.max_columns', 50)

    # ------------ Selection of DSO and Day  ---------------------------------
    DSO_num = '2'  # Needs to be non-zero integer
    day_num = '9'  # Needs to be non-zero integer
    # Set day range of interest (1 = day 1)
    day_range = range(2, 3)  # 1 = Day 1. Starting at day two as agent data is missing first hour of run.
    dso_range = range(1, 9)  # 1 = DSO 1 (end range should be last DSO +1)

    #  ------------ Select folder locations for different cases ---------
    hayden = True
    if hayden: 
        dsot_path = 'C:/Users/reev057/PycharmProjects/DSO+T/'
        tesp_path = 'C:/Users/reev057/PycharmProjects/TESP/'
        dsot_path = os.path.join(dsot_path, 'Data/Simdata/DER2/V1.1-1317-gfbf326a2/MR-Batt/lean_8_bt')
        # data_path = 'C:/Users/reev057/PycharmProjects/DSO+T/Data/Simdata/DER2'
        metadata_path = os.path.join(tesp_path, 'src/examples/analysis/Dsot/Data')
        ercot_path = os.path.join(tesp_path, 'src/examples/analysis/Dsot/Data')
        base_case = os.path.join(dsot_path, 'Data/Simdata/DER2/v1.1-1545-ga2893bd8')
        batt_case = os.path.join(dsot_path, 'Data/Simdata/DER2/v1.1-1567-g8cb140e1')
        Output_path = os.path.join(dsot_path, 'Data/Simdata/DER2/v1.1-1567-g8cb140e1')
        trans_case = os.path.join(dsot_path, 'Data/Simdata/DER2/V1.1-1317-gfbf326a2/MR-Flex/lean_8_fl')
        config_path = os.path.join(tesp_path, 'src/examples/Dsot_v3')
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

    # Enable the analysis stages below as needed for this configured run.
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

    # Stage 1: compare DER load profiles for the selected months and days.
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

    # Stage 2: summarize annual metrics for the selected cases.
    if Annual_whiskers:
        for Variable in Variables:
            plot_annual_stats(Cases, Data_paths, Output_path, DSO_num, Variable)

    # Stage 3: compare customer-level costs, usage, and savings.
    if Customer_PDFs:
        customer_cfs_delta(Cases, Data_paths, Output_path, metadata_file)

    # reduction_by_class(Cases, Data_paths, Output_path, 'Load')
    # Stage 4: calculate and plot DSO cost-benefit deltas.
    if dso_valuation_waterfall:
        dso_cfs_delta(Cases_list, Data_paths_list, dso_range, metadata_file)

def rates_plots():
    """Run the example-configured retail-rate comparison workflow.

    Loads the selected Flat case configuration and DSO metadata, assembles the
    case directories, then runs a fixed sequence of load-profile, annual
    statistics, generation-profile, DSO cost-benefit, and customer-population
    analyses. Paths and case names are configured in this function and must
    match the local post-processing data layout.

    Returns:
        None. The called helpers save figures and summary files to the
        configured case and data directories.
    """
    # ------------ Selection of DSO and Day  ---------------------------------
    dso_num = '1'  # Needs to be non-zero integer
    day_num = '4'  # Needs to be non-zero integer
    # Set day range of interest (1 = day 1)
    # 1 = Day 1. Starting at day two as agent data is missing first hour of run.
    day_range = range(3, 5)  
    dso_range = range(1, 9)  # 1 = DSO 1 (end range should be last DSO +1)

    #  ------------ Select folder locations for different cases ---------
    # Load System Case Config
    # Set current working directory to location of case folder.
    case = 'Flat'
    data_path = os.path.expandvars('$TESPDIR/examples/analysis/dsot/data/post_processing')
    config_path = os.path.join(data_path, case)

    # you should always use 'generate_case_config.json' as it is copied when case is created
    system_case = 'generate_case_config.json'
    case_config = pt.load_json(config_path, system_case)
    case_config_file = config_path + '/' + system_case

    agent_prefix = '/DSO_'
    GLD_prefix = '/Substation_'

    metadata_path = os.path.expandvars('$TESPDIR/examples/analysis/dsot/data/')

    metadata_file = case_config["dsoPopulationFile"]
    if "rate" in case_config:
        metadata_file = case_config["dsoRECSPopulationFile"]
    dso_meta_file = os.path.join(metadata_path, metadata_file)

    flat_path = os.path.join(data_path, 'Flat')
    DSOT_path = os.path.join(data_path, 'DSOT')
    TOU_path = os.path.join(data_path, 'TOU')
    RND_path = os.path.join(data_path, 'rob-don')
    sub_path = os.path.join(data_path, 'sub')

    # Check if there is a plots folder - create if not.
    check_folder = os.path.isdir(data_path + '/plots')
    if not check_folder:
        os.makedirs(data_path + '/plots')

    print('Stage 1: compare DER load profiles for the selected August days.')
    # Provides stacked time series plots of end loads.  E.g., Figure 6, 32, 36, 37 in DSO+T Volume 1.

    #Flat case plot
    flat_aug_path = os.path.join(flat_path, '8_2016_08_pv_bt_fl_ev')
    day_range = range(12, 17) # Set day range and case path around August 11 peak - peak load is given in load stats csv.
    pt.der_stack_plot(dso_range, day_range, metadata_path, flat_aug_path, None, False)

    # Compare TOU and DSO+T to Flat (BAU case)
    TOU_aug_path = os.path.join(TOU_path, '8_2016_08_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, TOU_aug_path, flat_aug_path, False)

    DSOT_aug_path = os.path.join(DSOT_path, '8_2016_08_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, DSOT_aug_path, flat_aug_path, False)

    RND_aug_path = os.path.join(RND_path, '8_2016_08_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, RND_aug_path, flat_aug_path, False)

    # Winter Peak as well as system min load (4/4/2016) plots.
    flat_dec_path = os.path.join(flat_path, '8_2016_12_pv_bt_fl_ev')
    day_range = range(18, 23)  # Set day range and case path around Dec 17 peak - peak load is given in load stats csv.
    pt.der_stack_plot(dso_range, day_range, metadata_path, flat_dec_path, None, False)

    TOU_dec_path = os.path.join(TOU_path, '8_2016_12_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, TOU_dec_path, flat_dec_path, False)

    DSOT_dec_path = os.path.join(DSOT_path, '8_2016_12_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, DSOT_dec_path, flat_dec_path, False)

    RND_dec_path = os.path.join(RND_path, '8_2016_12_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, RND_dec_path, flat_dec_path, False)

    # Compare TOU and DSO+T to Flat (BAU case)
    # Fall Min Load
    flat_oct_path = os.path.join(flat_path, '8_2016_10_pv_bt_fl_ev')
    day_range = range(27, 32)  # Set day range and case path around Oct 28 min.
    pt.der_stack_plot(dso_range, day_range, metadata_path, flat_oct_path, None, False)

    TOU_oct_path = os.path.join(TOU_path, '8_2016_10_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, TOU_oct_path, flat_oct_path, False)

    DSOT_oct_path = os.path.join(DSOT_path, '8_2016_10_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, DSOT_oct_path, flat_oct_path, False)

    RND_oct_path = os.path.join(RND_path, '8_2016_10_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, RND_oct_path, flat_oct_path, False)

    # Compare TOU and DSO+T to Flat (BAU case)
    # Fall Min Load
    flat_nov_path = os.path.join(flat_path, '8_2016_11_pv_bt_fl_ev')
    day_range = range(18, 23)  # Set day range and case path around Oct 28 min.
    pt.der_stack_plot(dso_range, day_range, metadata_path, flat_nov_path, None, False)

    TOU_nov_path = os.path.join(TOU_path, '8_2016_11_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, TOU_nov_path, flat_nov_path, False)

    DSOT_nov_path = os.path.join(DSOT_path, '8_2016_11_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, DSOT_nov_path, flat_nov_path, False)

    RND_nov_path = os.path.join(RND_path, '8_2016_11_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, RND_nov_path, flat_nov_path, False)

    # Compare TOU and DSO+T to Flat (BAU case)
    # Fall Min Load
    flat_apr_path = os.path.join(flat_path, '8_2016_04_pv_bt_fl_ev')
    day_range = range(26, 31)  # Set day range and case path around Oct 28 min.
    pt.der_stack_plot(dso_range, day_range, metadata_path, flat_apr_path, None, False)

    TOU_apr_path = os.path.join(TOU_path, '8_2016_04_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, TOU_apr_path, flat_apr_path, False)

    DSOT_apr_path = os.path.join(DSOT_path, '8_2016_04_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, DSOT_apr_path, flat_apr_path, False)

    RND_apr_path = os.path.join(RND_path, '8_2016_04_pv_bt_fl_ev')
    pt.der_stack_plot(dso_range, day_range, metadata_path, RND_apr_path, flat_apr_path, False)

    print('Stage 2: compare annual distributions for selected system metrics')
    # Provides annual box and whisker like Figure 14, 16, 40 in Vol1.
    Cases = ['Flat', 'TOU', 'DE', 'DE+C']
    Data_paths = [flat_path, TOU_path, DSOT_path, RND_path]  # TODO: Add other cases as they are completed.
    Variables = ['DA LMP', 'Total Load', 'Hybrid']
    for Variable in Variables:
        plot_annual_stats(Cases, Data_paths, data_path, dso_num, Variable)

    print('Stage 2a: compare participating-household indoor-air amenity across tariffs.')
    indoor_air_amenity_comparison(
        ['Flat', 'TOU', 'DE', 'DE+C', 'B&S'],
        [flat_path, TOU_path, DSOT_path, RND_path, sub_path], data_path, dso_range)

    # print('Stage 3: plot generation and load profiles for the baseline case')
    # # Provides stacked time series plots of bulk generation.  
    # # E.g., Figure 15 in DSO+T Volume 1.
    # pt.generation_load_profiles(flat_aug_path, metadata_path, flat_aug_path, day_range, False)

    # print('Stage 4: compare DSO cost-benefit components across rate cases.')
    # # Total grid cost water fall: Figure 42 in Vol 1
    # Cases_list = [['Flat', 'TOU'], ['Flat', 'DSOT'], ['Flat', 'RND']] #TODO: Why DSOT and RND vs DE and DE+C?
    # Data_paths_list = [[flat_path, TOU_path], [flat_path, DSOT_path],[flat_path, RND_path]]
    # dso_cfs_delta(Cases_list, Data_paths_list, dso_range, metadata_file, metadata_path)

    # print('Stage 5: compare customer-population distributions and savings.')
    # # Probably density Functions of customer populations: e.g., Figure 45 in Vol 1
    # Cases = ['Flat', 'TOU']
    # Data_paths = [flat_path, TOU_path]
    # customer_cfs_delta(Cases, Data_paths, metadata_file, metadata_path)

    # Cases = ['Flat', 'DE']
    # Data_paths = [flat_path, DSOT_path]
    # customer_cfs_delta(Cases, Data_paths, metadata_file, metadata_path)

    # Cases = ['Flat', 'DE+C']
    # Data_paths = [flat_path, RND_path]
    # customer_cfs_delta(Cases, Data_paths, metadata_file, metadata_path)

    # Cases = ['Flat', 'B&S']
    # Data_paths = [flat_path, sub_path]
    # customer_cfs_delta(Cases, Data_paths, metadata_file, metadata_path)

    # print('Stage 5b: Annual Customer Bill Plotting - Plot gets saved in case_path/plots folder.')
    # # Provides annual box and whisker
    # Cases = ['Flat', 'TOU', 'DE', 'DE+C', 'B&S']
    # Data_paths = [flat_path, TOU_path, DSOT_path, RND_path, sub_path]
    # customer_monthly_stats(Cases, Data_paths, data_path, dso_num)
    # # Plot bill components
    # customer_bill_component_comparison(Cases, Data_paths, data_path, dso_num)

    # print('Stage 6. House/Customer Daily HVAC / Load & Price Comparison Examples.')
    # # Probably density Functions of customer populations: e.g., Figure 45 in Vol 1
    # day_range = range(12, 15)
    # Cases = ['Flat', 'TOU', 'DSOT', 'RND']
    # Month = '8_2016_08_pv_bt_fl_ev'
    # Data_paths = [flat_path +'/' + Month, TOU_path + '/' + Month, DSOT_path+ '/' + Month, RND_path +'/' + Month]
    # load_comparison_plot(day_range, metadata_path, Cases, Data_paths, data_path)

    # # day_range = range(14, 17)
    # Cases = ['Flat', 'TOU', 'DSOT', 'RND']
    # Rate_Scenarios = ["flat", "TOU", "DSOT", "RandD"]
    # Data_paths = [flat_path, TOU_path, DSOT_path, RND_path]
    # retail_price_comparison_plot(dso_num, day_range, metadata_path, Cases, Data_paths, Rate_Scenarios, Month, data_path)

    # Month = '8_2016_12_pv_bt_fl_ev'
    # day_range = range(20, 23)
    # Data_paths = [flat_path +'/' + Month, TOU_path + '/' + Month, DSOT_path+ '/' + Month, RND_path +'/' + Month]
    # load_comparison_plot(day_range, metadata_path, Cases, Data_paths, data_path)
    # Data_paths = [flat_path, TOU_path, DSOT_path, RND_path]
    # retail_price_comparison_plot(dso_num, day_range, metadata_path, Cases, Data_paths, Rate_Scenarios, Month, data_path)

    # Month = '8_2016_04_pv_bt_fl_ev'
    # day_range = range(27, 30)
    # Data_paths = [flat_path +'/' + Month, TOU_path + '/' + Month, DSOT_path+ '/' + Month, RND_path +'/' + Month]
    # load_comparison_plot(day_range, metadata_path, Cases, Data_paths, data_path)
    # Data_paths = [flat_path, TOU_path, DSOT_path, RND_path]
    # retail_price_comparison_plot(dso_num, day_range, metadata_path, Cases, Data_paths, Rate_Scenarios, Month, data_path)

    # print('Stage 7. Population Attribute PDFs.)
    # Probably density Functions of customer populations: e.g., Figure 45 in Vol 1
    Cases = ['Flat', 'TOU', 'DE', 'DE+C', 'B&S']
    Data_paths = [flat_path, TOU_path, DSOT_path, RND_path, sub_path]

    Population = load_customer_cfs_population(
        Cases, Data_paths, cust_class='residential', attribute_case=1,
        insulation_options={'dso_range': dso_range, 'method': 'conductance', 'bins': 3})

    # for Dimension in ['building_type', 'heating', 'cooling', 'income_level', 'pv_participating', 'ev_participating', 'DER_participating', 'wh_participating', 'batt_participating', 'insulation']:

        # # Bill levels, then paired variation from the Flat baseline
        # customer_cfs_pdf_by_group(Cases, Data_paths, data_path, dimension=Dimension,
        #                           metric='Bills', mode='level', population=Population)
        # customer_cfs_pdf_by_group(Cases, Data_paths, data_path, dimension=Dimension,
        #                           metric='Bills', mode='change_pct', population=Population)
        # customer_cfs_pdf_by_group(Cases, Data_paths, data_path, dimension=Dimension,
        #                       metric='PeakLoad', mode='change_pct', population=Population)
        # customer_cfs_pdf_by_group(Cases, Data_paths, data_path, dimension=Dimension,
        #                       metric='EnergyPurchased', mode='level',
        #                       population=Population)
        # customer_comfort_pdf_by_group(Cases, Data_paths, data_path, hvac_mode='cooling',
        #                           dimension=Dimension, cust_class='residential',
        #                           split_by=None, options=None, include_counts=True,
        #                           normalize='mode', palette_name='viridis', population=None)

    for Dimension in ['building_type', 'heating', 'income_level', 'insulation']:
    
        Cases_no_flat = ['TOU', 'DE', 'DE+C', 'B&S']
        Data_paths_no_flat = [TOU_path, DSOT_path, RND_path, sub_path]

        Population_no_flat = load_customer_cfs_population(
            Cases, Data_paths, cust_class='residential', attribute_case=1,
            insulation_options={'dso_range': dso_range, 'method': 'conductance', 'bins': 3})
        
        customer_comfort_pdf_by_group(Cases, Data_paths, data_path, hvac_mode='cooling',
                                            dimension=Dimension, cust_class='residential',
                                            split_by=None, options=None, include_counts=True,
                                            normalize='mode', palette_name='viridis', population=Population_no_flat)

        customer_comfort_pdf_by_group(Cases, Data_paths, data_path, hvac_mode='heating',
                                            dimension=Dimension, cust_class='residential',
                                            split_by=None, options=None, include_counts=True,
                                            normalize='mode', palette_name='viridis', population=Population_no_flat)

    # print('Stage 8. Subscription Plots')
    # flat_aug_path = os.path.join(flat_path, '8_2016_08_pv_bt_fl_ev')
    # sub_aug_path = os.path.join(sub_path, '8_2016_08_pv_bt_fl_ev')
    # day_range = range(14, 17)  # Set day range and case path around August 11 peak - peak load is given in load stats csv.
    # pt.subscription_plot(dso_num, day_range, metadata_path, flat_aug_path, sub_aug_path)
    # day_range = range(25, 28)  # Set day range and case path around August 11 peak - peak load is given in load stats csv.
    # pt.subscription_plot(dso_num, day_range, metadata_path, flat_aug_path, sub_aug_path)

    # print('Stage 9. TOU Participation Summary')
    # day_range = range(12, 15)
    # Cases = ['TOU-80', 'TOU-60', 'TOU-40', 'TOU-20']
    # Month20 = 'Aug-20TOU_pv_bt_fl_ev'
    # Month40 = 'Aug-40TOU_pv_bt_fl_ev'
    # Month60 = 'Aug-60TOU_pv_bt_fl_ev'
    # Month80 = '8_2016_08_pv_bt_fl_ev'
    # Data_paths = [TOU_path +'/' + Month80, TOU_path +'/' + Month60, TOU_path +'/' + Month40, TOU_path +'/' + Month20]
    # load_comparison_plot(day_range, metadata_path, Cases, Data_paths, data_path)

    # # Summer Peak - TOU Participation example
    # day_range = range(9, 14)
    # pt.der_stack_plot(dso_range, day_range, metadata_path, os.path.join(TOU_path, Month20), flat_aug_path, False)
    # pt.der_stack_plot(dso_range, day_range, metadata_path, os.path.join(TOU_path, Month40), flat_aug_path, False)
    # pt.der_stack_plot(dso_range, day_range, metadata_path, os.path.join(TOU_path, Month60), flat_aug_path, False)


if __name__ == '__main__':
    #DSOT_plots() # TODO - update data paths and variable assignments
    rates_plots()