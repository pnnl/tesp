import operator

import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout

from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib import cm
import matplotlib.patches as mpatches
import matplotlib.colors as colors
import numpy as np

from ..utils import make_interpolater
from ..case.utils import calculate_segments

cdict = {'red':   ((0.0,  0.0, 0.0),   # From 0 to 0.25, we fade the red and green channels
                   (0.25, 0.5, 0.5),   # up a little, to make the blue a bit more grey

                   (0.25, 0.0, 0.0),   # From 0.25 to 0.75, we fade red from 0.5 to 1
                   (0.75, 1.0, 1.0),   # to fade from green to yellow

                   (1.0,  0.5, 0.5)),  # From 0.75 to 1.0, we bring the red down from 1
                                       # to 0.5, to go from bright to dark red

         'green': ((0.0,  0.0, 0.0),   # From 0 to 0.25, we fade the red and green channels
                   (0.25, 0.6, 0.6),   # up a little, to make the blue a bit more grey

                   (0.25, 1.0, 1.0),   # Green is 1 from 0.25 to 0.75 (we add red
                   (0.75, 1.0, 1.0),   # to turn it from green to yellow)

                   (0.75, 0.0, 0.0),   # No green needed in the red upper quarter
                   (1.0,  0.0, 0.0)),

         'blue':  ((0.0,  0.9, 0.9),   # Keep blue at 0.9 from 0 to 0.25, and adjust its
                   (0.25, 0.9, 0.9),   # tone using the green and red channels

                   (0.25, 0.0, 0.0),   # No blue needed above 0.25
                   (1.0,  0.0, 0.0))

             }

cmap = colors.LinearSegmentedColormap('BuGnYlRd',cdict)




def plot_network_with_results(psstc, model, time=0):
    G = create_network(psstc)

    fig, axs = plt.subplots(1, 1, figsize=(12, 9))
    ax = axs

    line_color_dict = dict()
    hour = 0
    for i, b in branch_df.iterrows():
        if model.ThermalLimit[i] != 0:
            line_color_dict[(b['F_BUS'], b['T_BUS'])] = round(abs(model.LinePower[i, hour].value / model.ThermalLimit[i]), 2)
        else:
            line_color_dict[(b['F_BUS'], b['T_BUS'])] = 0

    gen_color_dict = dict()
    hour = 0
    for i, g in generator_df.iterrows():
        gen_color_dict[(i, g['GEN_BUS'])] = round(abs(model.PowerGenerated[i, hour].value / model.MaximumPowerOutput[i]), 2)

    color_dict = line_color_dict.copy()
    color_dict.update(gen_color_dict)

    edge_color = list()

    for e in G.edges():
        try:
            edge_color.append( color_dict[(e[0], e[1])] )
        except KeyError:
            edge_color.append( color_dict[(e[1], e[0])] )

    ax.axis('off')
    pos = graphviz_layout(G, prog='sfdp')
    nx.draw_networkx_nodes(G, pos, list(generator_df.index),)
    nx.draw_networkx_nodes(G, pos, list(bus_df.index), node_color='black',)
    edges = nx.draw_networkx_edges(G, pos, edge_color=edge_color, edge_cmap=cmap, width=3)
    nx.draw_networkx_edge_labels(G, pos, edge_labels=color_dict)

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("left", size="5%", pad=0.05)
    cb = plt.colorbar(edges, cax=cax)
    cax.yaxis.set_label_position('left')
    cax.yaxis.set_ticks_position('left')
    # cb.set_label('Voltage (V)')


def plot_stacked_power_generation(results, ax=None, kind='bar', legend=False):
    if ax is None:
        fig, axs = plt.subplots(1, 1, figsize=(16, 10))
        ax = axs

    df = results.power_generated
    cols = (df - results.unit_commitment*results.maximum_power_output).std().sort_values().index
    df = df[[c for c in cols]]

    df.plot(kind=kind, stacked=True, ax=ax, colormap=cm.jet, alpha=0.5, legend=legend)

    df = results.unit_commitment * results.maximum_power_output

    df = df[[c for c in cols]]

    df.plot.area(stacked=True, ax=ax, alpha=0.125/2,  colormap=cm.jet, legend=None)

    ax.set_ylabel('Dispatch and Committed Capacity (MW)')
    ax.set_xlabel('Time (h)')
    return ax


def plot_costs(case, number_of_segments=1, ax=None, legend=True):
    if ax is None:
        fig, axs = plt.subplots(1, 1, figsize=(16, 10))
        ax = axs

    color_scale = make_interpolater(0, len(case.gen_name), 0, 1)

    color = {g: plt.cm.jet(color_scale(i)) for i, g in enumerate(case.gen_name)}

    for s in calculate_segments(case, number_of_segments=number_of_segments):
        pmin, pmax = s['segment']
        x = np.linspace(pmin, pmax)
        y = x * s['slope']
        ax.plot(x, y, color=color[s['name']])

    ax = ax.twinx()
    for s in calculate_segments(case, number_of_segments=number_of_segments):
        pmin, pmax = s['segment']
        x = np.linspace(pmin, pmax)
        y = [s['slope'] for _ in x]
        ax.plot(x, y, color=color[s['name']])

    ax.set_ylim(0, 1.2*y[-1])

    if legend:
        lines = list()
        for g in case.gen_name:
            lines.append(mlines.Line2D([], [], color=color[g], label=g))
            ax.legend(handles=lines, loc='upper left')

    return ax


