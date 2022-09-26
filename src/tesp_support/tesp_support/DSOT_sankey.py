# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: DSOT_sankey

from os.path import expandvars
import matplotlib
import pandas as pd
import plotly.graph_objects as go

import tesp_support.DSOT_plots


# Example from: https://plotly.com/python/sankey-diagram/

# url = 'https://raw.githubusercontent.com/plotly/plotly.js/master/test/image/mocks/sankey_energy.json'
# https://community.plotly.com/t/sankey-diagram-with-percentages/28884

# Universal Color Scheme:
# Loads:
# Plug/Unresponsive Loads: 'darkseagreen'
# HVAC: 'wheat'
# WH: 'cornflowerblue'
# EV: 'yellowgreen'
# Battery: '
#
# Customers:
# Industrial: 'grey'
# Residential: 'yellowgreen' ****
# Commercial: 'cornflowerblue'  ****
#
# Generation:
# Nuclear: 'silver'
# Coal: 'black'
# Natural Gas: 'darkorange'
# Wind: 'blue'
# Solar: 'yellow'
# DSO: Plum
#
#   "Transmission System Operator","khaki",
#    "Ancillary Services","skyblue",
#    "Energy Purchases","dodgerblue",
#    "Capacity Payments","orange",
#    "ISO","pink",
#    "Generation","firebrick",
#    "Space","brown",
#     "Capital IT","darkviolet",
#     "Capital Hardware","tan",
#     "Labor/Operations","c",
#     "Fuel/O&M","saddlebrown",
#     "Startup Costs""y"


def rec_diff(d1, d2):
    diff = dict()
    for k, v1 in d1.items():
        if isinstance(v1, dict):
            diff[k] = rec_diff(v1, d2[k])
        else:
            diff[k] = v1 - d2[k]
    return diff


def label_nodes(data, total_value):
    """ Adds max quantity of node value to node label"""
    for node in range(0, len(data['data'][0]['node']['label'])):
        source_value = 0
        target_value = 0
        for link in range(0, len(data['data'][0]['link']['value'])):
            if data['data'][0]['link']['target'][link] == node:
                target_value += data['data'][0]['link']['value'][link]
            if data['data'][0]['link']['source'][link] == node:
                source_value += data['data'][0]['link']['value'][link]
        node_value = round(max(source_value, target_value), 2)
        node_percent = round(100 * node_value / total_value)

        data['data'][0]['node']['label'][node] = \
            data['data'][0]['node']['label'][node] + ' (' + str(node_value) + ' ' + \
            data['data'][0]['valuesuffix'] + ', ' + str(node_percent) + '%)'
    return data


def load_CFS_data(results_path, dso_range, update_data, scale, labelvals):
    """Initiates and updates Sankey diagram data structure for Cash Flow Sheet data.
    Arguments:
        results_path (str): directory path for the case to be analyzed.  Should be run after annual post-processing
        dso_range (range): range of DSOs to be included in data analysis
        update_data (bool): If True pulls in analysis data. If False plots Sankey with default data to show structure
        scale (bool): If True scales data to $B from standard $K CFS units
        labelvals (bool): If True adds quantitative values to node labels
    Returns:
        data (dict): Sankey data structure for Plotly Sankey diagram plotting
"""

    path = expandvars("$TESPDIR$/examples/analysis/dsot/data")

    data = tesp_support.DSOT_plots.load_json(path, 'sankey_cost_structure.json')

    if update_data:
        # Set default values to zero
        data['data'][0]['link']['value'] = [0] * len(data['data'][0]['link']['value'])

        # Compile data for all DSOs:
        for dso in dso_range:
            revenue = tesp_support.DSOT_plots.load_json(results_path,
                                                        'DSO' + str(dso) + '_Revenues_and_Energy_Sales.json')
            expenses = tesp_support.DSOT_plots.load_json(results_path, 'DSO' + str(dso) + '_Expenses.json')
            capital_costs = tesp_support.DSOT_plots.load_json(results_path, 'DSO' + str(dso) + '_Capital_Costs.json')

            Hardware = sum(capital_costs['DistPlant'].values())
            Software = \
                sum(capital_costs['InfoTech']['MktSoftHdw'].values()) + \
                sum(capital_costs['InfoTech']['AMIDERNetwork'].values()) + \
                capital_costs['InfoTech']['DaNetwork'] + \
                capital_costs['InfoTech']['DmsSoft'] + capital_costs['InfoTech']['OmsSoft'] + \
                capital_costs['InfoTech']['CisSoft'] + capital_costs['InfoTech']['BillingSoft']

            Distribution = \
                Hardware + Software + expenses['O&mMaterials'] + \
                sum(expenses['O&mLabor'].values()) + expenses['Admin'] + expenses['Space'] + \
                sum(expenses['RetailOps'].values()) + sum(expenses['AmiCustOps']['AmiOps'].values()) + \
                sum(expenses['AmiCustOps']['CustOps'].values()) + sum(expenses['AmiCustOps']['DmsOps'].values())

            data['data'][0]['link']['value'][0] += \
                revenue['RetailSales']['FixedSales']['SalesFixInd']['EnergyFixInd']
            data['data'][0]['link']['value'][1] += \
                revenue['RetailSales']['FixedSales']['SalesFixInd']['DemandChargesInd']
            data['data'][0]['link']['value'][2] += \
                revenue['RetailSales']['FixedSales']['ConnChargesFix']['ConnChargesFixInd']
            data['data'][0]['link']['value'][3] += \
                revenue['RetailSales']['FixedSales']['SalesFixComm']['EnergyFixComm']
            data['data'][0]['link']['value'][4] += \
                revenue['RetailSales']['FixedSales']['SalesFixComm']['DemandChargesComm']
            data['data'][0]['link']['value'][5] += \
                revenue['RetailSales']['FixedSales']['ConnChargesFix']['ConnChargesFixComm']
            data['data'][0]['link']['value'][6] += \
                revenue['RetailSales']['FixedSales']['SalesFixRes']['EnergyFixRes']
            data['data'][0]['link']['value'][7] += \
                revenue['RetailSales']['FixedSales']['SalesFixRes']['DemandChargesRes']
            data['data'][0]['link']['value'][8] += \
                revenue['RetailSales']['FixedSales']['ConnChargesFix']['ConnChargesFixRes']
            data['data'][0]['link']['value'][9] = \
                data['data'][0]['link']['value'][0] + \
                data['data'][0]['link']['value'][3] + \
                data['data'][0]['link']['value'][6]
            data['data'][0]['link']['value'][10] = \
                data['data'][0]['link']['value'][1] + \
                data['data'][0]['link']['value'][4] + \
                data['data'][0]['link']['value'][7]
            data['data'][0]['link']['value'][11] = \
                data['data'][0]['link']['value'][2] + \
                data['data'][0]['link']['value'][5] + \
                data['data'][0]['link']['value'][8]
            data['data'][0]['link']['value'][12] += Distribution
            data['data'][0]['link']['value'][13] += expenses['TransCharges']
            data['data'][0]['link']['value'][14] += expenses['OtherWholesale']['WhReserves']
            data['data'][0]['link']['value'][15] += sum(expenses['WhEnergyPurchases'].values())
            data['data'][0]['link']['value'][16] += expenses['PeakCapacity']
            data['data'][0]['link']['value'][17] += expenses['OtherWholesale']['WhISO']
            data['data'][0]['link']['value'][18] = data['data'][0]['link']['value'][14]
            data['data'][0]['link']['value'][19] = data['data'][0]['link']['value'][15]
            data['data'][0]['link']['value'][20] = data['data'][0]['link']['value'][16]
            data['data'][0]['link']['value'][21] += expenses['Space']
            data['data'][0]['link']['value'][22] += Software
            data['data'][0]['link']['value'][23] += Hardware
            data['data'][0]['link']['value'][24] += Distribution - expenses['Space'] - Software - Hardware

        # Load and assign generator data:
        gendata_df = pd.read_csv(results_path + "/generator_statistics_AMES.csv", index_col=[0], dtype=object)
        gendata_df.loc['Total revenue ($k)', :] = \
            gendata_df.loc['Total revenue ($k)', :].apply(pd.to_numeric, errors='ignore')
        gendata_df.loc['Capacity (MW)', :] = \
            gendata_df.loc['Capacity (MW)', :].apply(pd.to_numeric, errors='ignore')
        gendata_df.loc['Fuel cost ($k)', :] = \
            gendata_df.loc['Fuel cost ($k)', :].apply(pd.to_numeric, errors='ignore')
        gendata_df.loc['Startup costs ($k)', :] = \
            gendata_df.loc['Startup costs ($k)', :].apply(pd.to_numeric, errors='ignore')

        CapacityPayments = data['data'][0]['link']['value'][16]
        TotalCapacity = 0
        for fuel in ['nuc', 'coal', 'gas', 'wind', 'solar']:
            TotalCapacity += gendata_df.loc['Capacity (MW)', fuel]

        # Create dictionary of fuel keys and number of first link number
        fuel_key = {'nuc': 25,
                    'coal': 30,
                    'gas': 35,
                    'wind': 40,
                    'solar': 45}

        total_gen_revenue = 0
        for fuel in ['nuc', 'coal', 'gas', 'wind', 'solar']:
            link_id = fuel_key[fuel]
            data['data'][0]['link']['value'][link_id] = \
                gendata_df.loc['Total revenue ($k)', fuel] + CapacityPayments * \
                gendata_df.loc['Capacity (MW)', fuel] / TotalCapacity
            total_gen_revenue += data['data'][0]['link']['value'][link_id]
            data['data'][0]['link']['value'][link_id + 1] = gendata_df.loc['Capacity (MW)', fuel] * 0.8 * 0.0825 * 1000
            data['data'][0]['link']['value'][link_id + 3] = gendata_df.loc['Fuel cost ($k)', fuel]
            data['data'][0]['link']['value'][link_id + 4] = gendata_df.loc['Startup costs ($k)', fuel]
            data['data'][0]['link']['value'][link_id + 2] = \
                data['data'][0]['link']['value'][link_id] - data['data'][0]['link']['value'][link_id + 1] - \
                data['data'][0]['link']['value'][link_id + 3] - data['data'][0]['link']['value'][link_id + 4]

        # Calibration step to balance generator revenues whose splits that are only estimates:
        calibrate = True
        if calibrate:
            corrected_total_gen_revenue = 0
            correction_factor = (data['data'][0]['link']['value'][14] + data['data'][0]['link']['value'][15] +
                                 data['data'][0]['link']['value'][16]) / total_gen_revenue
            for fuel in ['nuc', 'coal', 'gas', 'wind', 'solar']:
                link_id = fuel_key[fuel]
                data['data'][0]['link']['value'][link_id] = \
                    data['data'][0]['link']['value'][link_id] * correction_factor
                corrected_total_gen_revenue += data['data'][0]['link']['value'][link_id]
                data['data'][0]['link']['value'][link_id + 2] = \
                    data['data'][0]['link']['value'][link_id] - data['data'][0]['link']['value'][link_id + 1] - \
                    data['data'][0]['link']['value'][link_id + 3] - data['data'][0]['link']['value'][link_id + 4]

            correction_factor = (data['data'][0]['link']['value'][15] + data['data'][0]['link']['value'][16] +
                                 data['data'][0]['link']['value'][17]) / corrected_total_gen_revenue
        # Load and assign transmission data:
        loads_df = pd.read_csv(results_path + "\\DSO_load_stats.csv", index_col=[0], dtype=object)
        peak_sys_load = float((loads_df.loc['Max', 'Substation'])) + float((loads_df.loc['Max', 'Industrial Loads']))

        Transmission_Capital = 169 * peak_sys_load * 0.0825
        Transmission_Operation = data['data'][0]['link']['value'][13] - Transmission_Capital
        data['data'][0]['link']['value'][50] = Transmission_Capital
        data['data'][0]['link']['value'][51] = Transmission_Operation

        # ISO link
        data['data'][0]['link']['value'][52] = data['data'][0]['link']['value'][17]

        # Scale to billions of dollars
        if scale:
            data['data'][0]['link']['value'] = [value / 1e6 for value in data['data'][0]['link']['value']]
            data['data'][0]['valuesuffix'] = "$B"

        # Find the total max value for each node and add it to the label
        # todo - find this value
        total_costs = 40
        if labelvals:
            data = label_nodes(data, total_costs)

    return data


def load_CFS_delta_data(results_path, comp_path, dso_range, update_data, scale, labelvals, metadata_file):
    """Initiates and updates Sankey diagram data structure for Cash Flow Sheet data.
    Arguments:
        results_path (str): directory path for the case to be analyzed.  Should be run after annual post-processing
        comp_path (str): directory path for the baseline (business-as-usual) case.
        dso_range (range): range of DSOs to be included in data analysis
        update_data (bool): If True pulls in analysis data. If False plots Sankey with default data to show structure
        scale (bool): If True scales data to $B from standard $K CFS units
        labelvals (bool): If True adds quantitative values to node labels
        metadata_file:
    Returns:
        data (dict): Sankey data structure for Plotly Sankey diagram plotting
"""

    path = expandvars("$TESPDIR$/examples/analysis/dsot/data")

    data = tesp_support.DSOT_plots.load_json(path, 'sankey_delta_cost_structure.json')

    if update_data:
        # Set default values to zero
        data['data'][0]['link']['value'] = [0] * len(data['data'][0]['link']['value'])
        customer_bills = 0
        customer_costs = pd.read_csv(results_path + '/Customer_CFS_Summary.csv', index_col=[0])
        customer_costs_comp = pd.read_csv(comp_path + '/Customer_CFS_Summary.csv', index_col=[0])
        customer_costs_delta = customer_costs.subtract(customer_costs_comp)
        metadata = tesp_support.DSOT_plots.load_json(path, metadata_file)

        # Compile data for all DSOs:
        for dso in dso_range:
            revenue = tesp_support.DSOT_plots.load_json(results_path,
                                                        'DSO' + str(dso) + '_Revenues_and_Energy_Sales.json')
            expenses = tesp_support.DSOT_plots.load_json(results_path, 'DSO' + str(dso) + '_Expenses.json')
            capital_costs = tesp_support.DSOT_plots.load_json(results_path, 'DSO' + str(dso) + '_Capital_Costs.json')

            revenue_comp = tesp_support.DSOT_plots.load_json(comp_path,
                                                             'DSO' + str(dso) + '_Revenues_and_Energy_Sales.json')
            expenses_comp = tesp_support.DSOT_plots.load_json(comp_path, 'DSO' + str(dso) + '_Expenses.json')
            capital_costs_comp = tesp_support.DSOT_plots.load_json(comp_path, 'DSO' + str(dso) + '_Capital_Costs.json')

            revenue_delta = rec_diff(revenue, revenue_comp)
            expenses_delta = rec_diff(expenses, expenses_comp)
            capital_costs_delta = rec_diff(capital_costs, capital_costs_comp)

            Dist_Hardware = sum(capital_costs_delta['DistPlant'].values())
            Software = \
                sum(capital_costs_delta['InfoTech']['MktSoftHdw'].values()) + \
                sum(capital_costs_delta['InfoTech']['AMIDERNetwork'].values()) + \
                capital_costs_delta['InfoTech']['DaNetwork'] + \
                capital_costs_delta['InfoTech']['DmsSoft'] + capital_costs_delta['InfoTech']['OmsSoft'] + \
                capital_costs_delta['InfoTech']['CisSoft'] + capital_costs_delta['InfoTech']['BillingSoft']

            Labor = \
                expenses_delta['O&mMaterials'] + sum(expenses_delta['O&mLabor'].values()) + \
                expenses_delta['Admin'] + sum(expenses_delta['RetailOps'].values()) + \
                sum(expenses_delta['AmiCustOps']['AmiOps'].values()) + \
                sum(expenses_delta['AmiCustOps']['CustOps'].values()) + \
                sum(expenses_delta['AmiCustOps']['DmsOps'].values())

            # Benefits (minus sign used to match Sankey convention).
            data['data'][0]['link']['value'][0] += -Dist_Hardware
            data['data'][0]['link']['value'][1] += -expenses_delta['TransCharges']
            data['data'][0]['link']['value'][2] += -expenses_delta['OtherWholesale']['WhReserves']
            data['data'][0]['link']['value'][3] += -sum(expenses_delta['WhEnergyPurchases'].values())
            data['data'][0]['link']['value'][4] += -expenses_delta['PeakCapacity']

            # Intermediate Links
            data['data'][0]['link']['value'][5] = \
                data['data'][0]['link']['value'][2] + \
                data['data'][0]['link']['value'][3] + \
                data['data'][0]['link']['value'][4]
            total_benefits = \
                data['data'][0]['link']['value'][0] + \
                data['data'][0]['link']['value'][1] + \
                data['data'][0]['link']['value'][5]

            # DSO Expenses
            data['data'][0]['link']['value'][7] += expenses_delta['Space']
            data['data'][0]['link']['value'][8] += Software
            data['data'][0]['link']['value'][9] += Labor
            total_expenses = \
                data['data'][0]['link']['value'][7] + \
                data['data'][0]['link']['value'][8] + \
                data['data'][0]['link']['value'][9]

            # Net Savings
            # data['data'][0]['link']['value'][6] += total_benefits + total_expenses
            data['data'][0]['link']['value'][6] += revenue_delta['RequiredRevenue']

            # Customer Costs and Savings
            num_of_cust = metadata['DSO_' + str(dso)]['number_of_customers']
            data['data'][0]['link']['value'][11] += \
                customer_costs_delta.loc['Investment', str(dso)] * num_of_cust / 1000
            customer_bills += (customer_costs_delta.loc['Bills', str(dso)] * num_of_cust) / 1000
            data['data'][0]['link']['value'][10] = customer_bills - data['data'][0]['link']['value'][11]
    else:
        total_benefits = 3

    # Scale to billions of dollars
    if scale:
        data['data'][0]['link']['value'] = [value / 1e6 for value in data['data'][0]['link']['value']]
        data['data'][0]['valuesuffix'] = "$B"
    # Find the total max value for each node and add it to the label
    if labelvals:
        data = label_nodes(data, total_benefits)

    return data


def load_energy_data(results_path, dso_range, update_data, scale, labelvals):
    """Initiates and updates Sankey diagram data structure for simulation energy data.
    Arguments:
        results_path (str): directory path for the case to be analyzed.  Should be run after annual post-processing
        dso_range (range): range of DSOs to be included in data analysis
        update_data (bool): If True pulls in analysis data. If False plots Sankey with default data to show structure
        scale (bool): If True scales data to GW from standard MW CFS units
        labelvals (bool): If True adds quantitative values to node labels
    Returns:
        data (dict): Sankey data structure for Plotly Sankey diagram plotting
"""

    path = expandvars("$TESPDIR/examples/analysis/dsot/data")
    data = tesp_support.DSOT_plots.load_json(path, 'sankey_energy_structure.json')

    if update_data:
        # Set default values to zero
        data['data'][0]['link']['value'] = [0] * len(data['data'][0]['link']['value'])

        # Load and assign generator data:
        gendata_df = pd.read_csv(results_path + "/generator_statistics_AMES.csv", index_col=[0], dtype=object)
        gendata_df.loc['Capacity (MW)', :] = \
            gendata_df.loc['Capacity (MW)', :].apply(pd.to_numeric, errors='ignore')
        gendata_df.loc['Capacity Factor (-)', :] = \
            gendata_df.loc['Capacity Factor (-)', :].apply(pd.to_numeric, errors='ignore')

        #  Create dictionary of fuel keys and number of first link number
        fuel_key = {'nuc': 4,
                    'coal': 6,
                    'gas': 5,
                    'wind': 3,
                    'solar': 2}

        for fuel in ['nuc', 'coal', 'gas', 'wind', 'solar']:
            link_id = fuel_key[fuel]
            if gendata_df.loc['Capacity (MW)', fuel] != 0:
                data['data'][0]['link']['value'][link_id] = gendata_df.loc['Capacity (MW)', fuel] * \
                                                            gendata_df.loc['Capacity Factor (-)', fuel]

        # Load Building and DER load totals:
        loaddata_df = pd.read_csv(results_path + "/DSO_load_stats.csv", index_col=[0], dtype=object)
        loaddata_df.loc['Average', :] = loaddata_df.loc['Average', :].apply(pd.to_numeric, errors='ignore')
        total_load = loaddata_df.loc['Average', 'Total Load'] + loaddata_df.loc['Average', 'PV']
        RC_ratio = loaddata_df.loc['Average', 'total_res'] / (
                    loaddata_df.loc['Average', 'total_comm'] + loaddata_df.loc['Average', 'total_res'])

        #  Create dictionary of fuel keys and number of first link number
        load_key = {'total_res': 8,
                    'total_comm': 9,
                    'Industrial Loads': 10,
                    'HVAC Loads': 11,
                    'Plug Loads': 12,
                    'WH Loads': 13,
                    'EV': 14,
                    'Battery': 15}

        for load in load_key.keys():
            link_id = load_key[load]
            if load in ['Plug Loads', 'HVAC Loads', 'Battery']:
                data['data'][0]['link']['value'][link_id] = loaddata_df.loc['Average', load] * RC_ratio
                data['data'][0]['link']['value'][link_id + 5] = loaddata_df.loc['Average', load] * (1 - RC_ratio)
            else:
                data['data'][0]['link']['value'][link_id] = loaddata_df.loc['Average', load]

        # Add Industrial Loads to Unrepsonsive Loads
        data['data'][0]['link']['value'][21] = data['data'][0]['link']['value'][10]

        # Distribution losses equal substation less commercial and residential buildings
        data['data'][0]['link']['value'][7] = \
            loaddata_df.loc['Average', 'Substation'] - \
            loaddata_df.loc['Average', 'total_comm'] - \
            loaddata_df.loc['Average', 'total_res']

        # Add Rooftop Solar
        data['data'][0]['link']['value'][0] = loaddata_df.loc['Average', 'PV'] * RC_ratio
        data['data'][0]['link']['value'][1] = loaddata_df.loc['Average', 'PV'] * (1 - RC_ratio)

        # Calibration step to balance loads whose splits that are only estimates:
        calibrate = True
        if calibrate:
            # Adjust residential solar to meet residential loads
            if loaddata_df.loc['Average', 'PV'] != 0:
                data['data'][0]['link']['value'][0] = data['data'][0]['link']['value'][11] + \
                                                      data['data'][0]['link']['value'][12] + \
                                                      data['data'][0]['link']['value'][13] + \
                                                      data['data'][0]['link']['value'][14] + \
                                                      data['data'][0]['link']['value'][15] \
                                                      - data['data'][0]['link']['value'][8]

                # Update commercial solar:
                data['data'][0]['link']['value'][1] = \
                    loaddata_df.loc['Average', 'PV'] - data['data'][0]['link']['value'][0]

            # Adjust commercial plug loads to match up commercial loads
            data['data'][0]['link']['value'][17] = \
                data['data'][0]['link']['value'][1] + \
                data['data'][0]['link']['value'][9] - \
                data['data'][0]['link']['value'][16]

        # Scale to GW
        if scale:
            data['data'][0]['link']['value'] = [value / 1e3 for value in data['data'][0]['link']['value']]
            data['data'][0]['valuesuffix'] = "GW"
            total_load = total_load / 1000

        # Find the total max value for each node and add it to the label
        if labelvals:
            data = label_nodes(data, total_load)

    return data


def sankey_plot():
    # Todo: have mode for system peak.

    # data_path = "C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Simdata\\DER2\\v1.1-1545-ga2893bd8"
    # data_path = 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Simdata\\DER2\\v1.1-1610-g6c778889'
    data_path = 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Simdata\\DER2\\v1.1-1567-g8cb140e1'
    bau_path = 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\Simdata\\DER2\\v1.1-1588-ge941fcf5'
    # data_path = bau_path

    system_case = '8-metadata-lean.json'

    updatedata = False
    scaledata = True
    label_values = True
    dsorange = range(1, 9)

    # data = load_CFS_data(data_path, dsorange, updatedata, scaledata, label_values)
    data = load_CFS_delta_data(data_path, bau_path, dsorange, updatedata, scaledata, label_values, system_case)
    # data = load_energy_data(data_path, dsorange, updatedata, scaledata, label_values)

    # override gray link colors with 'source' colors
    opacity = 0.4
    # round(255*matplotlib.colors.to_rgba(data['data'][0]['node']['color'][4], alpha=0.8))
    # for color in data['data'][0]['node']['color']:
    for color_id in range(0, len(data['data'][0]['node']['color'])):
        new_color = matplotlib.colors.to_rgba(data['data'][0]['node']['color'][color_id], alpha=0.8)
        new_color = [round(255 * value) for value in new_color]
        new_color[3] = 0.8
        data['data'][0]['node']['color'][color_id] = 'rgba' + str(tuple(new_color))

    # data['data'][0]['node']['color'] = ['rgba'+str(matplotlib.colors.to_rgba(color, alpha=0.8))
    #                                     for color in data['data'][0]['node']['color']]
    data['data'][0]['link']['color'] = [data['data'][0]['node']['color'][src].replace("0.8", str(opacity))
                                        for src in data['data'][0]['link']['source']]

    fig = go.Figure(data=[go.Sankey(
        valueformat=".0f",
        valuesuffix=data['data'][0]['valuesuffix'],
        textfont=dict(size=20),
        # Define nodes
        node=dict(
            pad=15,
            thickness=15,
            line=dict(color="black", width=0.5),
            label=data['data'][0]['node']['label'],
            color=data['data'][0]['node']['color']
        ),
        # Add links
        link=dict(
            source=data['data'][0]['link']['source'],
            target=data['data'][0]['link']['target'],
            value=data['data'][0]['link']['value'],
            label=data['data'][0]['link']['label'],
            color=data['data'][0]['link']['color']
        ))])

    fig.update_layout(title_text=data['layout']['title']['text'],
                      font_size=10)
    fig.show()


if __name__ == "__main__":
    sankey_plot()
