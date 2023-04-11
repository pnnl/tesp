# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: DSOT_map_results.py
import os
import warnings
from datetime import datetime
from os.path import isdir

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import matplotlib
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from .DSOT_plots import load_json, load_ames_data, load_gen_data


def bulk_system_map_plot(dataPath, configPath, shapePath, case_config_path, case_config_name, day_range, hour,
                         contour_index, ercot200, realtime, showplot=False, plotdata=True, dispatchgenonly=True):
    """Creates a comparison of change in energy consumption and anemities for all customers:
        case_data (str): path location for reference case with annual energy and amenity data
        comp_data (str): path location for comparison case with annual energy and amenity data
        case_path (str): path location for reference case with simulation metadata for agents/GLD etc.
        comp_path (str): path location for comparison case with simulation metadata for agents/GLD etc.
        dso_num (str): dso to be plotted
        month (str): month of annual analysis to be plotted.  set to 'sum' to plot aggregate of all data.
        slice (str): sub set of data to be plotted (e.g. 'residential', 'office', 'HVAC'
    Returns:
        saves plot to file.
        """

    contoursubjects = ['Wholesale LMP', 'Generation Utilization', 'Generation Load', 'Generation Capacity',
                       'Generation Capacity Fraction', 'Load', 'Net Load', 'Load Fraction', 'Renewable Capacity',
                       'Renewable Generation']
    contourlabels = ['LMP ($/MW-hr', 'Generation Fraction (-)', 'Gen Load (MW)', 'Gen Capacity (MW)',
                     'Gen Capacity (-)',
                     'Load (MW)', 'Net Load (MW)', 'Load Fraction (-)', 'Renew Capacity (MW)', 'Renew Gen (MW)']
    contoursubject = contoursubjects[contour_index]
    contourlabel = contourlabels[contour_index]

    if realtime:
        time_index = 12 * hour
        bid_mode = 'Real Time'
    else:
        time_index = hour
        bid_mode = 'Day Ahead'

    # Check if there is a plots folder - create if not.
    check_folder = isdir(dataPath + '/plots')
    if not check_folder:
        os.makedirs(dataPath + '/plots')

    # case_config_file = case_config_path + '\\' + case_config_name

    # Load and Apply Map Features:
    featureScale = '50m'  # 10, 50 0r 110
    urbanColor = 'seagreen'
    #  Data from https://viewer.nationalmap.gov/basic/
    #  https://www.sciencebase.gov/catalog/item/59fa9f63e4b0531197affb6b

    rdr1 = shpreader.Reader(shapePath + 'GU_CountyOrEquivalent.shp')
    counties = list(rdr1.geometries())
    COUNTIES = cfeature.ShapelyFeature(counties, ccrs.PlateCarree())

    plt.figure(figsize=(10, 10))

    ax = plt.axes(projection=ccrs.PlateCarree())
    # ax.add_feature(cfeature.LAND.with_scale(featureScale))
    # ax.add_feature(COUNTIES, facecolor='none', edgecolor='whitesmoke')
    ax.add_feature(cfeature.BORDERS.with_scale(featureScale), edgecolor='lightgray', linewidth=5)
    ax.add_feature(cfeature.STATES.with_scale(featureScale), edgecolor='lightgray', linewidth=2.5)
    ax.add_feature(cfeature.OCEAN.with_scale(featureScale), edgecolor='lightgray', facecolor='lightgray')
    # ax.add_feature(cfeature.RIVERS.with_scale(featureScale), zorder=2)
    # ax.add_feature(cfeature.LAKES.with_scale(featureScale), zorder=2)
    # ax.coastlines(featureScale)

    ax.set_extent([-107.0, -93.0, 25.0, 37.0])

    # Load Results Data
    case_config_data = load_json(case_config_path, case_config_name)
    if plotdata:
        if realtime:
            line_data_df = load_gen_data(dataPath, 'rt_line', day_range)
            lmp_data_df = load_ames_data(dataPath, day_range)
            q_data_df = load_gen_data(dataPath, 'rt_q', day_range)
        else:
            line_data_df = load_gen_data(dataPath, 'da_line', day_range)
            q_data_df = load_gen_data(dataPath, 'da_q', day_range)

            lmp_data_df = load_gen_data(dataPath, 'da_lmp', day_range)
            lmp_data_df = lmp_data_df.unstack(level=1)
            lmp_data_df.columns = lmp_data_df.columns.droplevel()
            lmp_data_df.columns = [col.replace('da_lmp', ' LMP') for col in lmp_data_df.columns]

        # gen_data_df = load_gen_data(dataPath, 'gen', day_range)
        line_data_df = line_data_df.unstack(level=1)
        line_data_df.columns = line_data_df.columns.droplevel()

        q_data_df = q_data_df.unstack(level=1)
        q_data_df.columns = q_data_df.columns.droplevel()

        time = lmp_data_df.index[time_index]

        cmap = matplotlib.cm.get_cmap('Oranges')
        # Ensure red is maximum color of color map (for maxed out lines)
        newcmap = cmap.from_list('newcmap', list(map(cmap, range(250))) + [(1, 0, 0, 1)], N=251)

    if not ercot200:
        # name,bus1,bus2,kV,length[miles],#parallel,r1[Ohms/mile],x1[Ohms/mile],b1[MVAR/mile],ampacity,capacity[MW]
        dlines = np.genfromtxt(configPath + 'Lines8.csv', dtype=str, skip_header=1,
                               delimiter=',')  # ['U',int,int,float,float,int,float,float,float,float,float], skip_header=1, delimiter=',')
        # bus,lon,lat,load,gen,diff,caps
        dbuses = np.genfromtxt(configPath + 'Buses8.csv', dtype=[int, float, float, float, float, float, float],
                               skip_header=1, delimiter=',')
        # idx,bus,mvabase,pmin,qmin,qmax,c2,c1,c0
        dunits = np.genfromtxt(configPath + 'Units8.csv',
                               dtype=[int, int, float, float, float, float, float, float, float], skip_header=1,
                               delimiter=',')

        lbl345 = {}
        e345 = set()
        n345 = set()
        lst345 = []
        w345 = []
        c345 = []
        graph = nx.Graph()
        for e in dlines:
            if '//' not in e[0]:
                n1 = int(e[1])
                n2 = int(e[2])
                npar = int(e[5])
                graph.add_edge(n1, n2)
                n345.add(n1)
                n345.add(n2)
                lbl345[(n1, n2)] = e[0]
                e345.add((n1, n2))
                lst345.append((n1, n2))
                w345.append(1.5 * npar)
                # TODO: Need to check that I have the branch ordering correct?
                if plotdata:
                    if realtime:
                        line_utl = line_data_df.loc[time, 'rt_line' + e[0].replace('ehv', '')]
                    else:
                        line_utl = line_data_df.loc[time, 'da_line' + e[0].replace('ehv', '')]
                    rgba = newcmap(abs(line_utl))
                    c345.append(rgba)
                else:
                    c345 = 'saddlebrown'

        xy = {}
        for b in dbuses:
            xy[b[0]] = [b[1], b[2]]

    # gnodes345 = nx.draw_networkx_nodes(graph, xy, nodelist=list(n345), node_color='orange', node_size=60) # , alpha=0.3)
    # glines345 = nx.draw_networkx_edges(graph, xy, edgelist=lst345, edge_color='r', width=w345) # , alpha=0.8)
    #
    # gnodes345.set_zorder(20)
    # glines345.set_zorder(18)

    else:
        # name,bus1,bus2,kV,length[miles],#parallel,r1[Ohms/mile],x1[Ohms/mile],b1[MVAR/mile],ampacity,capacity[MW]
        dlines = np.genfromtxt(configPath + 'RetainedLines.csv', dtype=str, skip_header=1,
                               delimiter=',')  # ['U',int,int,float,float,int,float,float,float,float,float], skip_header=1, delimiter=',')
        # bus,lon,lat,load,gen,diff,caps
        dbuses = np.genfromtxt(configPath + 'RetainedBuses.csv', dtype=[int, float, float, float, float, float, float],
                               skip_header=1, delimiter=',')
        # idx,bus,mvabase,pmin,qmin,qmax,c2,c1,c0
        dunits = np.genfromtxt(configPath + 'Units.csv',
                               dtype=[int, int, float, float, float, float, float, float, float], skip_header=1,
                               delimiter=',')
        # hvbus,mvaxf,rpu,xpu,tap
        # dxfmrs = np.genfromtxt('RetainedTransformers.csv', dtype=[int, float, float, float,float], skip_header=1, delimiter=',')

        lbl345 = {}
        lbl138 = {}
        e345 = set()
        e138 = set()
        n345 = set()
        n138 = set()
        lst345 = []
        lst138 = []
        w345 = []
        w138 = []
        c345 = []
        c138 = []
        graph = nx.Graph()
        for e in dlines:
            if '//' not in e[0]:
                n1 = int(e[1])
                n2 = int(e[2])
                npar = int(e[5])
                graph.add_edge(n1, n2)
                # TODO: Need to find DSO+T branch number based on matching node values.
                i = 1
                branch_id = 'nan'
                for branch in case_config_data['branch']:
                    if branch[0] > 200:
                        # Since there is not a simple mapping from EHV to HV buses need to use branches to find connection.
                        for branch2 in case_config_data['branch']:
                            if branch2[0] == branch[0] and branch2[1] < 201:
                                node1 = branch2[1]
                                break
                            if branch2[1] == branch[0] and branch2[0] < 201:
                                node1 = branch2[0]
                                break
                    else:
                        node1 = branch[0]
                    if branch[1] > 200:
                        # Since there is not a simple mapping from EHV to HV buses need to use branches to find connection.
                        for branch2 in case_config_data['branch']:
                            if branch2[0] == branch[1] and branch2[1] < 201:
                                node2 = branch2[1]
                                break
                            if branch2[1] == branch[1] and branch2[0] < 201:
                                node2 = branch2[0]
                                break
                    else:
                        node2 = branch[1]
                    if node1 == n1 + 1 and node2 == n2 + 1:  # Need +1 as TESP ercot bus index starts at zero.
                        branch_id = i
                        break
                    i += 1

                if float(e[3]) > 200.0:
                    n138.discard(n1)
                    n138.discard(n2)
                    n345.add(n1)
                    n345.add(n2)
                    lbl345[(n1, n2)] = e[0]
                    e345.add((n1, n2))
                    lst345.append((n1, n2))
                    w345.append(1.5 * npar)
                    if plotdata:
                        if realtime:
                            line_utl = line_data_df.loc[time, 'rt_line' + str(branch_id)]
                        else:
                            line_utl = line_data_df.loc[time, 'da_line' + str(branch_id)]
                        rgba = newcmap(abs(line_utl))
                        c345.append(rgba)
                    else:
                        c345 = 'saddlebrown'
                else:
                    lbl138[(n1, n2)] = e[0]
                    n138.add(n1)
                    n138.add(n2)
                    e138.add((n1, n2))
                    lst138.append((n1, n2))
                    w138.append(1.0 * npar)
                    if plotdata:
                        if realtime:
                            line_utl = line_data_df.loc[time, 'rt_line' + str(branch_id)]
                        else:
                            line_utl = line_data_df.loc[time, 'da_line' + str(branch_id)]
                        rgba = newcmap(abs(line_utl))
                        c138.append(rgba)
                    else:
                        c138 = 'orange'
        xy = {}
        lblbus345 = {}
        lblbus138 = {}
        for b in dbuses:
            xy[b[0]] = [b[1], b[2]]
            if b[0] in n345:
                lblbus345[b[0]] = str(b[0]) + ':' + str(int(b[5]))
            else:
                lblbus138[b[0]] = str(b[0]) + ':' + str(int(b[5]))

    if not plotdata:
        c345 = 'saddlebrown'
        c138 = 'orange'

    glines345 = nx.draw_networkx_edges(graph, xy, edgelist=lst345, edge_color=c345, width=w345)  # , alpha=0.8)
    if ercot200:
        glines138 = nx.draw_networkx_edges(graph, xy, edgelist=lst138, edge_color=c138,
                                           width=w138)  # , arrowsize=100, arrowstyle='fancy'
    if not plotdata:
        gnodes345 = nx.draw_networkx_nodes(graph, xy, nodelist=list(n345), node_color='saddlebrown', node_size=60)
    if not ercot200:
        gnodes345 = nx.draw_networkx_nodes(graph, xy, nodelist=list(n345), node_color='saddlebrown', node_size=60)
    if ercot200:
        gnodes138 = nx.draw_networkx_nodes(graph, xy, nodelist=list(n138), node_color='orange', node_size=20,
                                           linewidths=1)  # , alpha=0.3)
        gnodes138.set_edgecolor('orange')

    # gnodes345 = nx.draw_networkx_nodes (graph, xy, nodelist=list(n345), node_color='k', node_size=60) # , alpha=0.3)
    # gnodes138 = nx.draw_networkx_nodes (graph, xy, nodelist=list(n138), node_color='b', node_size=20) # , alpha=0.3)
    # glines345 = nx.draw_networkx_edges (graph, xy, edgelist=lst345, edge_color='r', width=w345) # , alpha=0.8)
    # nx.draw_networkx_edges (graph, xy, edgelist=lst345, edge_color='r', width=1, alpha=0.3)
    # glines138 = nx.draw_networkx_edges (graph, xy, edgelist=lst138, edge_color='b', width=w138) # , alpha=0.8)
    # nx.draw_networkx_labels (graph, xy, lblbus345, font_size=12, font_color='g')
    # nx.draw_networkx_labels (graph, xy, lblbus138, font_size=12, font_color='g')
    # nx.draw_networkx_edge_labels (graph, xy, edge_labels=lbl345, label_pos=0.5, font_color='m', font_size=6)
    # nx.draw_networkx_edge_labels (graph, xy, edge_labels=lbl138, label_pos=0.5, font_color='k', font_size=6)

    if not plotdata:
        gnodes345.set_zorder(20)
    if ercot200:
        gnodes138.set_zorder(19)
    glines345.set_zorder(18)
    if ercot200:
        glines138.set_zorder(17)

    if plotdata:
        lons = []
        lats = []
        bus_lmp = []
        bus_load = np.zeros(len(xy))
        bus_qmax = np.zeros(len(xy))
        for node in xy:
            lons.append(xy[node][0])
            lats.append(xy[node][1])
            # TODO - check that node ordering is correct.
            if ercot200:
                node_str = str(node + 1)
                node_idx = node
            else:
                node_str = str(node)
                node_idx = node - 1
            bus_lmp.append(lmp_data_df.loc[time, ' LMP' + node_str])
            if realtime:
                bus_load[node_idx] = (q_data_df.loc[time, 'rt_q' + node_str])
            else:
                bus_load[node_idx] = (q_data_df.loc[time, 'da_q' + node_str])
        # sst.append(np.random.uniform(0, 1))
        # lons[node] = node[0]
        # lats[node] = node[1]
        # TODO: this seems to crash when all sst values are identical

        # Load generator operation and rates per bus
        if realtime:
            fuel_key = {'nuc': 'Nuclear',
                        'coal': 'Coal',
                        'wind': 'Wind',
                        'gas': 'Gas',
                        'solar': 'Photovoltaic'}
            gen_cap = np.zeros(len(xy))
            gen_load = np.zeros(len(xy))
            renew_cap = np.zeros(len(xy))
            renew_gen = np.zeros(len(xy))
            i = 0
            for gen in case_config_data['gen']:
                gen_type = case_config_data['genfuel'][i][1]
                for key in fuel_key:
                    if fuel_key[key] in gen_type:
                        gen_fuel = key
                gen_id = ' ' + gen_fuel + str(case_config_data['genfuel'][i][2])
                if gen[0] > 200:
                    gen_bus = gen[0] - 200
                else:
                    gen_bus = gen[0]
                # Include mode that only counts dispatchable generation.
                if dispatchgenonly:
                    if gen_fuel not in ['wind', 'solar']:
                        gen_cap[gen_bus - 1] += gen[8]
                        gen_load[gen_bus - 1] += lmp_data_df.loc[time, gen_id]
                else:
                    gen_cap[gen_bus - 1] += gen[8]
                    gen_load[gen_bus - 1] += lmp_data_df.loc[time, gen_id]
                if gen_fuel in ['wind', 'solar']:
                    renew_cap[gen_bus - 1] += gen[8]
                    renew_gen[gen_bus - 1] += lmp_data_df.loc[time, gen_id]
                i += 1
            gen_load_ratio = gen_load / gen_cap
            gen_cap_ratio = gen_cap / gen_cap.sum()
            bus_load_ratio = bus_load / bus_load.sum()

        if contoursubject == 'Wholesale LMP':
            sst = bus_lmp
        elif contoursubject == 'Generation Utilization':
            sst = gen_load_ratio
            sst = np.nan_to_num(sst)
        elif contoursubject == 'Generation Load':
            sst = gen_load
        elif contoursubject == 'Generation Capacity':
            sst = gen_cap
        elif contoursubject == 'Generation Capacity Fraction':
            sst = gen_cap_ratio
            sst = np.nan_to_num(sst)
        elif contoursubject == 'Load':
            sst = bus_load
        elif contoursubject == 'Load Fraction':
            sst = bus_load_ratio
        elif contoursubject == 'Net Load':
            sst = bus_load - gen_load
        elif contoursubject == 'Renewable Capacity':
            sst = renew_cap
        elif contoursubject == 'Renewable Generation':
            sst = renew_gen

        if max(sst) != min(sst):
            tcf = plt.tricontourf(lons, lats, sst, 30, transform=ccrs.PlateCarree())

            plt.tricontourf(lons, lats, sst, 30, transform=ccrs.PlateCarree())
            cbar = plt.colorbar(tcf, ax=ax, shrink=0.5, label=contourlabel)
        else:
            warnings.warn(contoursubject + " values are identical for all nodes.  Contour will not be plotted")

        # plt.legend()

        # cbar.ax.set_label('LMP ($/MW-hr)')
        norm = matplotlib.colors.Normalize(vmin=0, vmax=1)

        plt.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=newcmap), ax=ax, shrink=0.5,
                     label='Line Capacity (-)')

        # plt.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=newcmap), ax=ax, orientation='horizontal', label='Capacity (-)')
        plt.title(bid_mode + ' Transmission Congestion and ' + contoursubject + ': ' + str(time) + ';')

        # Save the plot by calling plt.savefig() BEFORE plt.show()
        plot_filename = datetime.now().strftime(
            '%Y%m%d') + '_Transmission_map_results_' + lmp_data_df.index[time_index].strftime('%m-%d-%H') + \
                        bid_mode + contoursubject + '.png'
    else:
        plot_filename = 'ERCOT MAP.png'

    plt.savefig(dataPath + '/plots/' + plot_filename, bbox_inches='tight')

    # plt.title ('Retained Buses and Lines')
    # plt.xlabel ('Longitude [deg]')
    # plt.ylabel ('Latitude [deg N]')
    # plt.grid(linestyle='dotted')
    if showplot:
        plt.show()


# ----------------------   MAIN  ------------------------

if __name__ == '__main__':

    # --- PLOTTING INPUTS  -----------
    ercot_200 = False
    plot_data = True
    real_time = False
    dispatch_gen_only = False
    dayrange = range(32, 33)
    hr = 12  # Select hour from start of first day in day range (keeping to integer hours allows RT and DA to be compared at same time)

    data_path = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\Simdata\DER2\\v1.1-1557-gc2432db4\\2016_08_pv'
    config_path = 'C:\\Users\\reev057\\PycharmProjects\\TESP\\src\\ercot\\bulk_system\\'
    shape_path = 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Texas_County_Boundaries\\GOVTUNIT_Texas_State_Shape\\Shape\\'
    case_config_path = 'C:\\Users\\reev057\\PycharmProjects\\TESP\\src\\examples\\dsot_v3'

    case_config_name = '8_hi_system_case_config.json'
    # case_config_name = '200_system_case_config.json'

    contour_idx = 0
    ''' Contour Index = Title , Units
    0 = 'Wholesale LMP', 'LMP ($/MW-hr)'
    1 = 'Generation Utilization', 'Generation Fraction (-)' (Fraction of generation capacity dispatched at each bus)
    2 = 'Generation Load', 'Gen Load (MW)'  (Generator capacity dispatched at each bus)
    3 = 'Generation Capacity', 'Gen Capacity (MW)' (Generator capacity available at each bus)
    4 = 'Generation Capacity Fraction', 'Gen Capacity (-)'  (Fraction of total system gen capacity that resides at each bus)
    5 = 'Load', 'Load (MW)'  (Total load forecast or realtime at each bus)
    6 = 'Net Load', 'Net Load (MW)' (Net load at each bus [Load - gen] indicating what transmission must provide)
    7 = 'Load Fraction', 'Load Fraction (-)' (fraction of total system load that resides at each bus)
    8 = 'Renewable Capacity', 'Renew Capacity (MW)' Total renewable capacity installed at each bus
    9 = 'Renewable Generation', 'Renew Gen (MW)' Total renewable generation produced at each bus
    '''

    index_range = range(0, 1)
    for contour_idx in index_range:
        bulk_system_map_plot(data_path, config_path, shape_path, case_config_path, case_config_name, dayrange, hr,
                             contour_idx, ercot_200, real_time)

    # contour_idx = 0
    # hr_range = range(0, 24)
    # for hr in hr_range:
    # 	real_time = True
    # 	bulk_system_map_plot(data_path, config_path, shape_path, case_config_path, case_config_name, dayrange, hr,
    # 					 contour_idx, ercot_200, real_time)
    # 	real_time = False
    # 	bulk_system_map_plot(data_path, config_path, shape_path, case_config_path, case_config_name, dayrange, hr,
    # 					 contour_idx, ercot_200, real_time)

    # real_time = False
    # contour_idx = 0
    # # hr = 16
    # bulk_system_map_plot(data_path, config_path, shape_path, case_config_path, case_config_name, dayrange, hr,
    # 				 contour_idx, ercot_200, real_time, True, plot_data, dispatch_gen_only)

# Additional features:
# Need to add node load (gross and net of generation) as well.
# Need to add node labels of contour values.
# Add arrows to edges to show direction of transmission flow
# Make node size based on substation capacity.
# Make node color based on fraction of QMAX
# add retail lmps
# get DA generation values
# Enable animation for an entire day.
# Have option to color nodes by utility type?
