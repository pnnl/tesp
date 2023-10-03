# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 07:01:52 2021

The purpose of this module is to provide some
miscellaneous funtionality for data pre-processing.
This will help the analysis efforts of power
distribution system models.

This module provides the ability to parse JSON, .dss,
.txt files for reformatting the power distribution
models data. These files should have feeder and meter
information, along with the meters' locations.

The functions below turn the data into a pandas dataframe.
A pandas dataframe is similar in structure and format
to an Excel spreadsheet. This allows for easy data
and statistical analysis for evaluating and comparing
models of power distribution systems.

This module can be expanded to include other
data processing functions should the need arise.


@author: barn553
"""

import os
import pandas as pd
import json


def parse_json_file(json_file, out_path, out_file_name):
    """
    This function turns a JSON file representation of
    GLD power distribution system model into a dataframe
    of the billing meter names and positions.

    Args:
        json_file (JSON file) - JSON file of the GLD power
        distribution system model.

        out_path (path) - Path to send the dataframe. Saves
        the dataframe as a csv.

        out_file_name (str) - Name of the output file.

    Returns:
        (null)
    """
    # Reading in the JSON file:
    with open(json_file, 'r') as file:
        # We use json.load NOT .loads because we're looking at
        # a JSON file, NOT a JSON object.
        data = json.load(file)
    # There are other types of meters. For our analysis, we
    # only care about the billing meters. So, we go through all
    # the (key, value) pairs in the JSON and grab the billing meters
    # only.
    names = [n['id'] for n in data['nodes'] if n['nclass'] == 'billing_meter']
    # For our analysis, we care about how far away meters are from
    # each other. So, we go through the (key, value) pairs of
    # the JSON and grab the positional information for each of
    # the billing meters.
    pos_x = [n['ndata']['x'] for n in data['nodes']
             if n['nclass'] == 'billing_meter']
    pos_y = [n['ndata']['y'] for n in data['nodes']
             if n['nclass'] == 'billing_meter']
    # The path/folder names provide model and feeder information.
    # We need this information for making comparisons across
    # feeders and different power distribution models. So, we grab
    # parts of the path to save that information in our dataframe.
    head1, tail1 = os.path.split(json_file)
    feeder = tail1[:-5]
    head2, tail2 = os.path.split(head1)
    model_name = tail2
    # Creating the dataframe after collecting all the necessary
    # data:
    #   NOTE: For this to work, every list/array has to be the same
    #   length; otherwise there will be an error.
    df = pd.DataFrame(
        {'model_name': [model_name] * len(names),
         'feeder': [feeder] * len(names),
         'name': names,
         'pos_x': pos_x,
         'pos_y': pos_y},
        index=range(len(names)))
    # Saving the reformatted data as a .csv file.
    # This function can be expanded to have the option
    # of saving in different file types.
    df.to_csv(r'{}/{}.csv'.format(out_path, out_file_name))


def parse_dss_file(load_file, coord_file, out_path, out_file_name):
    """
    This function parses the lines of a file
    and saves them as a csv file.

    Args:
        load_file (str) - Name of the load file. This dss file has
        bus and load data, among other data. We use this to pair
        its data with the correct coordinates.

        coord_file (str) - Name of the coordinate file. This
        contains the coordinates for the bus(es).

        out_path (path) - Path to send the reformatted data file(s)

        out_file_name (str) - Name to give the data file(s).

    Returns:
        (null)
    """
    # Reading in the Load file:
    #   NOTE: This can be parsed/treated like a .txt file.
    with open(load_file, 'r') as load:
        # In the .dss files, there is one line of data per
        # bus. So, we read in line of the file as one
        # unique string object.
        load_data = load.readlines()
    load_name = []
    # Grabbing th bus information:
    for i, line in enumerate(load_data):
        line_list = line.split(' ')
        # There are multiple pieces of information in each
        # line of the .dss file. We only care about the bus
        # information. So, we read through each line as a
        # single string object and grab the bus information.
        for ll in line_list:
            if 'bus' in ll:
                # The name of the bus, which is what we care about,
                # precedes the '.2.3' or '.2'. So, we grab the part
                # of the string before those numbers and dots.
                if '.2.3' in ll:
                    load_name.append(ll[5:-6])
                else:
                    load_name.append(ll[5:-4])
    # Creating a dataframe of the load names:
    #   NOTE: The names from the load file are what we care
    #   about. The coordinate file has more names than what
    #   we care about. So, we create a dataframe of the names
    #   to merge the load file with the coordinate file.
    load_df = pd.DataFrame(
        load_name, columns=['name'], index=range(len(load_name)))
    # Reading in the Coordinate file:
    with open(coord_file, 'r') as coord:
        # Each line represents a unique load, so we read
        # them in as an individual string.
        coord_data = coord.readlines()
    names = []
    lons = []
    lats = []
    # Grabbing the name, longitude, and latitude data:
    for j, lne in enumerate(coord_data):
        # Each line in the file has three pieces of information
        # separated by a space. The order of these pieces is as
        # follows: name of the load, longitude, and latitude. We
        # grab each of these and add them to our lists.
        lne_list = lne.split(' ')
        names.append(lne_list[0])
        lons.append(lne_list[1])
        lats.append(lne_list[2][0:-1])
    # The path/folder names provide model and feeder information.
    # We need this information for making comparisons across
    # feeders and different power distribution models. So, we grab
    # parts of the path to save that information in our dataframe.
    head, tail = os.path.split(out_path)
    model_name = tail
    feeder = out_file_name
    # Creating a dataframe of the location data:
    #   NOTE: The names from the load file are contained in the
    #   coordinate file, but there are more names than what we care
    #   about. So, we create a dataframe of the coordinate data.
    #   Then, we get the intersection of the load data and coordinate
    #   data to get the final set of data we need for analysis in
    #   one dataframe.
    loc_df = pd.DataFrame(
        {'model_name': [model_name] * len(names),
         'feeder': [feeder] * len(names),
         'name': names,
         'lat': lats,
         'lon': lons}, index=range(len(names)))
    # Merging the two dataframes into one to get the final set
    # of data:
    final_df = pd.merge(load_df, loc_df, on='name', how='inner')
    final_df = final_df.drop_duplicates().set_index(
        ['model_name', 'feeder']).reset_index()
    # Saving the reformatted data as a .csv file.
    # This function can be expanded to have the option
    # of saving in different file types.
    final_df.to_csv(r'{}/{}.csv'.format(
        os.path.join(out_path, 'csvs'), out_file_name))


if __name__ == '__main__':
    # The purpose of this '__main__' stuff is to test
    # the above functions.
    head, tail = os.path.split(os.getcwd())
    data_path = os.path.join(head, 'results')
    # Uncomment the following lines if we need to run this
    # script again for each of the models.
    for root, dirs, files in os.walk(os.path.join(data_path, 'grb')):
        print('root:', root)
        root_head, root_tail = os.path.split(root)
        print(root_head)
        print(root_tail)
        for file in files:
            print('\tfile:', file)
            if 'Loads' in file or 'Long' in file:
                tamu_data_path = os.path.join(root_head, root_tail)
                load_file = os.path.join(
                    tamu_data_path, 'Loads.dss')
                coord_file = os.path.join(
                    tamu_data_path, 'Long_lat_buscoords.txt')
                parse_dss_file(
                    load_file, coord_file, root_head, root_tail)
        print('')
    # for root, dirs, files in os.walk(os.path.join(data_path, 'tamu')):
    #     print('root:', root)
    #     root_head, root_tail = os.path.split(root)
    #     print(root_head)
    #     print(root_tail)
    #     for file in files:
    #         print('\tfile:', file)
    #         if 'Loads' in file or 'Long' in file:
    #             tamu_data_path = os.path.join(root_head, root_tail)
    #             load_file = os.path.join(
    #                 tamu_data_path, 'Loads.dss')
    #             coord_file = os.path.join(
    #                 tamu_data_path, 'Long_lat_buscoords.txt')
    #             parse_dss_file(
    #                 load_file, coord_file, root_head, root_tail)
    #     print('')
    # for root, dirs, files in os.walk(os.path.join(data_path, 'santa_fe')):
    #     print('root:', root)
    #     root_head, root_tail = os.path.split(root)
    #     print(root_head)
    #     print(root_tail)
    #     for file in files:
    #         print('\tfile:', file)
    #         if 'Loads' in file or 'Long' in file:
    #             santa_fe = os.path.join(root_head, root_tail)
    #             load_file = os.path.join(
    #                 santa_fe, 'Loads.dss')
    #             coord_file = os.path.join(
    #                 santa_fe, 'Long_lat_buscoords.txt')
    #             parse_dss_file(
    #                 load_file, coord_file, root_head, root_tail)
    #     print('')
    # for root, dirs, files in os.walk(os.path.join(head, 'results', 'gld')):
    #     # print('root:', root)
    #     for file in files:
    #         h, t = os.path.split(file)
    #         if '.json' in t:
    #             json_file = os.path.join(root, file)
    #             # print(json_file)
    #             parse_json_file(
    #                 json_file, os.path.join(root), t[0:-5])
    #         else:
    #             pass
    #     print('')
