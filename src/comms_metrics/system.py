# -*- coding: utf-8 -*-
"""
Created on Fri Jan 15 08:40:05 2021

This module turns a model of a power distribtuion
system into a graph that can be evaluated.

It has the ability to read in different file formats,
such as Excel spreadsheets, .csvs, and JSON files. The
types of files to read in can be expanded to handle
any type of file format.

For creating a graph, we use NetworkX, which is a
Python library for graph theory analysis.

In addition, we turn the graph of the model into
a pandas dataframe for analysis. This allows for
easy computations.

This module has the capability of creating a plot
of the model and saving it as a .png. It is possible
to expand upon different plots to make, but we are
leaving it as is for now.

@author: barn553
"""

import pandas as pd
import os
import json
import networkx as nx
import holoviews as hv
import hvplot.networkx as hvnx
from itertools import combinations
import logging
import logging.config

# Creating a custom logger
head, tail = os.path.split(os.getcwd())
config_file = os.path.join(
    head, 'results', 'santa_fe', 'config.json')
with open(config_file, 'r') as file:
    config = json.load(file)
    logging.config.dictConfig(config)
logger = logging.getLogger(__name__)


class MeterNetwork:
    """
    This class creates a NetworkX representation of the
    system of power distribution system meters.

    This class has the ability to read in information about
    the system, create a NetworkX graph, and generate plots
    of the system.

    This class grabs all the meta data about the model
    that we care about for analysis purposes. This data
    includes meter names and their locations. We also
    care about the name of the model for comparing
    results across multiple models.
    """

    def __init__(self):
        """
    This initializes the class."""
        logger.info(
            '++++++++++ A MeterNetwork object has been created ++++++++++')

    @classmethod
    def from_excel(self, excel_file, sheet, columns):
        """
    This function turns an Excel file into a NetworkX
        representation of the meter system.

        Args:
            excel_file (file) - Excel file of the system that
            contains meter locations, connections between
            meters, among other information.

            sheet (str) - The sheet of the Excel file with
            meters' (aka nodes') information in it.

            columns (list) - List of node columns to call for
            reading in the data, e.g. 'name' or 'id', 'latitude',
            'longitude', etc. The format assumes the name of the
            node is first and the location data is second. We only
            care about the names of the meters and their locations
            for our analysis; all other information is unnecessary.

        Returns:
            G (NetworkX graph) - NetworkX graph representation
            of the meter system.
        """
        # Checking to make sure this is a valid file:
        assert os.path.isfile(excel_file),\
            'Oops! %r is not a valid Excel file' % excel_file
        logger.info('Reading in the data from the excel spredsheet')
        # Reading in the spreadsheet:
        nodes = pd.read_excel(excel_file, sheet_name=sheet)
        # Checking if model name and feeder information is
        # available in the data:
        if ('model_name' in nodes.columns.unique()
                and 'feeder' in nodes.columns.unique()):
            model_name = nodes['model_name'].unique()[0]
            feeder = nodes['feeder'].unique()[0]
        else:
            head1, tail1 = os.path.split(excel_file)
            feeder = tail1
            head2, tail2 = os.path.split(head1)
            model_name = tail2
        # Grabbing the metadata we care about:
        #   NOTE: This function assumes that the order of the
        #   columns is as follows:
        #       ['name', 'x-value', 'y-value']
        #   It is VERY important that the x-value comes before
        #   the y-value, especially with geospatial data. There
        #   will be errors or incorrect results, otherwise.
        nodes = nodes[columns]
        logger.info('Creating a NetworkX representation of the data')
        # Creating a NetworkX representation of the data:
        G = nx.Graph()
        G.add_nodes_from(
            [(n, {'pos': (a, b)}) for n, a, b, in zip(
                nodes[columns[0]], nodes[columns[1]], nodes[columns[2]])]
            )
        edges = list(combinations(nodes[columns[0]], 2))
        G.add_edges_from(edges)
        logger.info('Reformatting the meter position info for plotting')
        # Grabbing the positional data for plotting:
        positions = {
            n: (a, b) for n, a, b in zip(
                nodes[columns[0]], nodes[columns[1]], nodes[columns[2]])}
        logger.info('Saving the metadata as attributes of the object')
        self.meter_nodes = list(G.nodes())
        self.meter_edges = list(G.edges())
        self.meter_positions = positions
        self.model_name = model_name
        self.feeder = feeder
        self.graph = G
        return G

    @classmethod
    def from_csv(self, csv_file, columns):
        """
    This function turns a CSV file into a NetworkX
        representation of the meter system.

        Args:
            csv_file (file) - CSV file of the system that
            contains meter location, meter names, and other
            information.

            columns (list) - List of node columns to call for
            reading in the data, e.g. 'name' or 'id', 'latitude',
            'longitude', etc. The format assumes the name of the
            node is first and the location data is second.

        Returns:
            G (NetworkX graph) - NetworkX graph representation
            of the meter system.
        """
        assert os.path.isfile(csv_file),\
            'Oops! %r is not a valid CSV file.' % csv_file
        logger.info('Reading in the data from the csv file')
        # Reading in the .csv file:
        nodes = pd.read_csv(csv_file)
        # Checking if model name and feeder information is
        # available in the data:
        if ('model_name' in nodes.columns.unique()
                and 'feeder' in nodes.columns.unique()):
            model_name = nodes['model_name'].unique()[0]
            feeder = nodes['feeder'].unique()[0]
        else:
            head1, tail1 = os.path.split(csv_file)
            feeder = tail1
            head2, tail2 = os.path.split(head1)
            model_name = tail2
        # Grabbing the metadata we care about:
        #   NOTE: This function assumes that the order of the
        #   columns is as follows:
        #       ['name', 'x-value', 'y-value']
        #   It is VERY important that the x-value comes before
        #   the y-value, especially with geospatial data. There
        #   will be errors or incorrect results, otherwise.
        nodes = nodes[columns]
        logger.info('Creating a NetworkX representation of! the data')
        # Creating a NetorkX representation of the data:
        G = nx.Graph()
        edges = list(combinations(nodes[columns[0]], 2))
        G.add_edges_from(edges)
        G.add_nodes_from(
            [(n, {'pos': (a, b)}) for n, a, b, in zip(
                nodes[columns[0]], nodes[columns[1]], nodes[columns[2]])]
            )
        logger.info('Reformatting the meter position info for plotting')
        # Grabbing the positional data for plotting:
        positions = {
            n: (a, b) for n, a, b in zip(
                nodes[columns[0]], nodes[columns[1]], nodes[columns[2]])}
        logger.info('Saving the metadata as attributes of the object')
        self.meter_nodes = list(G.nodes())
        self.meter_edges = list(G.edges())
        self.meter_positions = positions
        self.model_name = model_name
        self.feeder = feeder
        self.graph = G
        return G

    @classmethod
    def from_json(self, json_file, key_list, position_labels):
        """
    This function turns a JSON file into a NetworkX
        representation of the meter system.

        Args:
            json_file (file) - JSON file of the system that
            contains meter locations, connections between
            meters, and other information.

            key_list (list) - List of the keys from the JSON file.
            They should be something like 'name', 'id', etc.
            This function assumes the first key listed is the key
            that has the names/ids of the meters.

            position_labels (list) - List of the meter position keys
            in the JSON, e.g. 'lat' and 'lon', 'latitude' and 'longitude',
            'x' and 'y', etc. This function assumes the first element
            is the 'longitude' element.

        Returns:
            G (NetworkX graph) - NetworkX graph reprsentation
            of the meter system.
        """
        assert os.path.isfile(json_file),\
            'Oops! %r is not a valid JSON' % json_file
        logger.info('Reading in the data from the JSON file')
        # Reading in the JSON file:
        with open(json_file, 'r') as file:
            data = json.load(file)
        # Checking to see if model name and feeder are in
        # the data:
        if ('model_name' in data.keys() and 'feeder' in data.keys()):
            model_name = data['model_name']
            feeder = data['feeder']
        else:
            head1, tail1 = os.path.split(json_file)
            feeder = tail1[0:-5]
            head2, tail2 = os.path.split(head1)
            model_name = tail2
        # Grabbing the data we care about:
        #   NOTE: This function assumes the first
        #   key is the key that contains all the meters.
        nodes = data[key_list[0]]
        logger.info('Creating a NetworkX representation of the data')
        # Creating a NetworkX representation of the data:
        G = nx.Graph()
        edges = list(combinations(list(nodes.keys()), 2))
        G.add_edges_from(edges)
        G.add_nodes_from(
            [(n, {'pos': (
                nodes[n][position_labels[0]], nodes[n][position_labels[1]])})
                for n in list(nodes.keys())])
        logger.info('Reformatting the meter position info for plotting')
        # Grabbing the positional data for plotting:
        positions = {
            n: (nodes[n][position_labels[0]],
                nodes[n][position_labels[1]]) for n in list(nodes.keys())}
        # logger.info('Saving the metadata as attributes of the object')
        self.meter_nodes = list(nodes.keys())
        self.meter_edges = list(G.edges())
        self.meter_positions = positions
        self.model_name = model_name
        self.feeder = feeder
        self.graph = G
        return G

    @classmethod
    def make_dataframe(self):
        """
    This function turns the meter graph into a pandas
        dataframe. This allows for ease and the ability to
        perform metrics calculations and validation of the
        system as a whole.

        Args:
            (null)

        Returns:
            dataframe (pandas dataframe) - Pandas datafrane
            representation of the meter names, locations, and
            other information.
        """
        logger.info(
            'Grabbing the meter names and positions from the network')
        # Grabbing the meter names and positional information:
        name = [n for n in self.graph.nodes()]
        pos = nx.get_node_attributes(self.graph, 'pos')
        pos_x = [pos[n][0] for n in self.graph.nodes()]
        pos_y = [pos[n][1] for n in self.graph.nodes()]
        logger.info(
            'Creating a dataframe of the meter network')
        # Creating a dataframe:
        dataframe = pd.DataFrame(
            {'model_name': [self.model_name] * len(name),
             'feeder': [self.feeder] * len(name),
             'name': name,
             'pos_x': pos_x,
             'pos_y': pos_y},
            index=range(0, len(self.graph.nodes())))
        logger.info(
            'Finished creating a dataframe for {};'.format(
                self.feeder))
        logger.info(
            'it has feeder info, meters, and meter positions.')
        logger.info(
            'Now, we evaluate {}'.format(self.feeder))
        return dataframe

    @classmethod
    def plot_graph(self, nodes, node_args, edges, edge_args, plot_positions,
                   opts_dict, output_dir, save_plot=True):
        """
    This function creates a visual representation
        of the meter system using Holoviews NetworkX
        drawing capabilities.

        Args:
            nodes (list) - List of the nodes in the NetworkX representation
            of the meter system.

            node_args (dict) - Dictionary of data of how to draw the
            graph. Things to consider include node color, node size, node
            labels, etc. Visit
            http://holoviews.org/user_guide/Network_Graphs.html for more
            examples and suggestions.

            edges (list) - List of the edges that connect the meters.

            edge_args (dict) - Dictionary of the meter connections
            within the graph. Things to consider include edge color,
            edge size, etc. See the above link for more information.

            plot_positions (dict) - Dictionary of the meter
            positions within the graph. If they are not provided or
            updated, the plot_positions will be the default positions
            after instantiation of the MeterNetwork object.

            opts_dict (dict) - Dictionary of how the final plot
            should look. Things to consider include title, font size,
            the height and width of the plot, etc.

            output_dir (directory) - Directory to send the final
            plot of the graph.

            save_plot (bool) - Boolean of whether or not to save the
            plot generated. Default is 'True'.

        Returns:
            (null)
        """
        logger.info(
            'Creating a NetworkX representation of the meter network.')
        # Creating a NetworkX representation of the meter network:
        G = nx.Graph()
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)
        logger.info('Adding node (aka meter) positions.')
        # "Drawing" it:
        nodes = hvnx.draw_networkx_nodes(
            G, pos=plot_positions, **node_args)
        logger.info(
            'Adding edges (abstract connections between nodes')
        edges = hvnx.draw_networkx_edges(
            G, pos=plot_positions, **edge_args)
        plot = (nodes * edges).opts(**opts_dict)
        # Saving it:
        if save_plot is True:
            hv.save(plot, '{}.png'.format(output_dir), fmt='png')
            logger.info('Saving the graph as a picture.')
