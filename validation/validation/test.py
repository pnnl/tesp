# -*- coding: utf-8 -*-
"""
Created on Fri Jan 29 07:34:28 2021

@author: barn553
"""
import os
from system import MeterNetwork
from metrics import EvaluateSystem, Results
# import pandas as pd
import logging
import logging.config
# import numpy as np
import json


if __name__ == '__main__':
    head, tail = os.path.split(os.getcwd())
    # data_path = os.path.join(head, 'results', 'santa_fe', 'csvs')
    data_path = os.path.join(
        head, 'results', 'gld')
    # MN = MeterNetwork()
    # MN.from_csv(
    #     os.path.join(data_path, 'R1-12.47-3_ns3.csv'),
    #     ['name', 'pos_x', 'pos_y'])
    # df = MN.make_dataframe()
    # ES = EvaluateSystem(df, MN.meter_nodes, 'pos_x', 'pos_y', 'feet')
    # dd = ES.get_distances()
    # dens = ES.all_densities([100.0, 200.0, 300.0])
    # ranges = ES.all_ranges()
    # isos = ES.all_isolates([100.0, 200.0, 300.0])
    # conts = ES.all_continuous([100.0, 200.0, 300.0])
    # shc = ES.all_single_hops([100.0, 200.0, 300.0])
    # score = ES.evaluate_system([100.0, 200.0, 300.0])
    # # reduced_dd = dd[dd.distance > 100.0]
    # print(np.round(score, 1))
    # n_labels = {
    #     m: 'meter{}'.format(i) for i, m in enumerate(df.name.unique())}
    # n_args = {'node_color': 'tan',
    #           'node_size': 3500,
    #           'labels': n_labels,
    #           'alpha': 0.5}
    # e_args = {'edge_color': 'grey',
    #           'edge_size': 1,
    #           'style': 'dotted',
    #           'alpha': 0.65}
    # opts = {'width': 1600,
    #           'height': 1000,
    #           'title': 'My Meter Network:',
    #           'fontsize': {'title': 30}}
    # MN.plot_graph(
    #     MN.meter_nodes, n_args, MN.meter_edges, e_args,
    #     MN.meter_positions, opts, os.path.join(data_path, 'my_model'), True)
    # Creating a custom logger
    config_file = os.path.join(
        head, 'results', 'gld', 'config.json')
    with open(config_file, 'r') as file:
        config = json.load(file)
        logging.config.dictConfig(config)
    logger = logging.getLogger(__name__)
    from timeit import default_timer as timer
    logger.info('Starting the calculations for the GLD models...')
    print('Starting the calculations for the GLD models...')
    start = timer()
    RS = Results()
    for root, dirs, files in os.walk(data_path):
        # print('root:', root)
        for file in files:
            # print('file:', file)
            h, t = os.path.split(file)
            if '.csv' in t:
                MN = MeterNetwork()
                graph = MN.from_csv(
                    os.path.join(data_path, file),
                    ['name', 'pos_x', 'pos_y'])
                df = MN.make_dataframe()
                ES = EvaluateSystem(
                    df, MN.meter_nodes, 'pos_x', 'pos_y', 'feet')
                dd = ES.get_distances()
                shc = ES.all_single_hops(
                    [100.0, 200.0, 300.0, 400.0, 500.0, 1000.0, 1500.0])
                ranges = ES.all_ranges()
                densities = ES.all_densities(
                    [100.0, 200.0, 300.0, 400.0, 500.0, 1000.0, 1500.0])
                isolates = ES.all_isolates(
                    [100.0, 200.0, 300.0, 400.0, 500.0, 1000.0, 1500.0])
                continuous = ES.all_continuous(
                    [100.0, 200.0, 300.0, 400.0, 500.0, 1000.0, 1500.0])
                score = ES.evaluate_system(
                    [100.0, 200.0, 300.0, 400.0, 500.0, 1000.0, 1500.0])
                RS.add(ES)
    RS.save(
        os.path.join(head, 'results', 'gld'), 'gld_results.h5')
    print('Finished the calculations for the GLD models.')
    logger.info('Finished the calculations for the GLD models.')
    end = timer()
    print('total time:', end - start)
