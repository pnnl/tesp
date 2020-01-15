from __future__ import division

from mpl_toolkits.axes_grid1 import make_axes_locatable
import pandas as pd
import matplotlib.pyplot as plt

import logging

from ..network import create_network
from ..utils import make_interpolater
from ..case import PSSTCase

logger = logging.getLogger(__name__)


def plot(case, ax=None):

    network.draw_buses(ax=ax)
    network.draw_loads(ax=ax)
    network.draw_generators(ax=ax)
    network.draw_branches(ax=ax)
    network.draw_connections('gen_to_bus', ax=ax)
    network.draw_connections('load_to_bus', ax=ax)

    if ax is not None:
        ax.axis('off')


def plot_line_power(obj, results, hour, ax=None):
    '''
    obj: case or network
    '''

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(16, 10))
        ax.axis('off')

    case, network = _return_case_network(obj)

    network.draw_buses(ax=ax)
    network.draw_loads(ax=ax)
    network.draw_generators(ax=ax)
    network.draw_connections('gen_to_bus', ax=ax)
    network.draw_connections('load_to_bus', ax=ax)

    edgelist, edge_color, edge_width, edge_labels = _generate_edges(results, case, hour)
    branches = network.draw_branches(ax=ax, edgelist=edgelist, edge_color=edge_color, width=edge_width, edge_labels=edge_labels)

    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='5%', pad=0.05)
    cb = plt.colorbar(branches, cax=cax, orientation='vertical')
    cax.yaxis.set_label_position('left')
    cax.yaxis.set_ticks_position('left')
    cb.set_label('Loading Factor')

    return ax


def plot_angles(obj, results, hour, ax=None, colorbar=True, angle_limits=5, **kwargs):
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(16, 10))

    case, network = _return_case_network(obj)
    a = results.angles.loc[hour] * 360 / 2 / pd.np.pi
    y_values = a.astype(object).to_dict()
    network.create_profile_graph(y_values)

    buses = network.draw_buses(ax=ax, node_color=y_values, vmin=-angle_limits, vmax=angle_limits, **kwargs)
    ax.set_ylim(-angle_limits, angle_limits)
    ax.axhline(0, linestyle='--', color='black')
    ax.yaxis.tick_right()
    ax.tick_params(
        axis='both',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        bottom='off',      # ticks along the bottom edge are off
        top='off',         # ticks along the top edge are off
        left='off',
        right='off',
        labelbottom='off',
        labeltop='off',
        labelleft='off',
        labelright='off',
        )

    edgelist, edge_color, edge_width, edge_labels = _generate_edges(results, case, hour)
    branches = network.draw_branches(ax=ax, edgelist=edgelist, edge_color=edge_color, width=edge_width, edge_labels=edge_labels, **kwargs)
    logger.debug('branches = ', branches)

    if colorbar is True:
        divider = make_axes_locatable(ax)
        cax = divider.append_axes('right', size='5%', pad=.5)
        cb = plt.colorbar(buses, cax=cax, orientation='vertical')
        cax.yaxis.set_label_position('right')
        cax.yaxis.set_ticks_position('right')
        cb.set_label('Angle (deg)')

        cax = divider.append_axes('left', size='5%', pad=0.5)
        cb = plt.colorbar(branches, cax=cax, orientation='vertical')
        cax.yaxis.set_label_position('left')
        cax.yaxis.set_ticks_position('left')
        cb.set_label('Loading Factor')

    return ax

def _generate_edges(results, case, hour, minimum_line_width=1, maximum_line_width=10):

    line_power = results.line_power.loc[hour].to_dict()
    line_loading = abs(results.line_power / results.maximum_line_power).loc[hour].to_dict()

    scale = make_interpolater(case.branch['RATE_A'].min(), case.branch['RATE_A'].max(), minimum_line_width, maximum_line_width)

    edge_color = list()
    edgelist = list()
    edge_width = list()
    edge_labels = dict()
    for k, v in line_loading.items():
        branch = case.branch.loc[k]
        f, t, limit = (branch['F_BUS'], branch['T_BUS'], branch['RATE_A'])
        if v == pd.np.inf:
            edge_color.append(0)
        else:
            edge_color.append(v)
        limit_label = ' ({:d}%)'.format(int(abs(line_power[k] / limit * 100.0))) if limit !=0 else ''
        edge_labels[(f, t)] = '{}{}'.format(abs(round(line_power[k])), limit_label)
        edgelist.append((f, t))
        edge_width.append(scale(branch['RATE_A']))

    return edgelist, edge_color, edge_width, edge_labels


def _return_case_network(obj):
    if isinstance(obj, PSSTCase):
        case = obj
        network = create_network(case)
    else:
        network = obj
        case = network._case

    return case, network
