# -*- coding: utf-8 -*-
"""
Created on Fri Jan 29 07:34:28 2021

@author: barn553
"""
import os
import random
from system import MeterNetwork
from metrics import EvaluateSystem, Results, Compare
import pandas as pd
import logging
import logging.config
# import numpy as np
import json
import itertools

if __name__ == '__main__':
    pd.options.mode.chained_assignment = None  # default='warn'
    head, tail = os.path.split(os.getcwd())
    # data_path = os.path.join(head, 'results', 'tamu', 'tamu_test1_csvs')
    data_path = os.path.join(
        head, 'results', 'gld')
    # MN = MeterNetwork()
    # MN.from_csv(
    #     os.path.join(data_path, 'R1-12.47-1_ns3.csv'),
    #     ['name', 'pos_x', 'pos_y'])
    # df = MN.make_dataframe()
    # # print(df.head())
    # ES = EvaluateSystem(df, MN.meter_nodes, 'pos_x', 'pos_y', 'feet')
    # # print(len(MN.meter_nodes))
    # dd = ES.get_distances()
    # isl = ES.island_count(100.0)
    # print(isl)
    # print(len(dd))
    # print(dd['distance'].max())
    # # print(dd.head())
    # # print(MN.meter_nodes)
    # combos = list(itertools.product(
    #     *[MN.meter_nodes, [100.0, 200.0, 300.0, 400.0,
    #                        500.0, 1000.0, 1500.0]]))
    # densities = [ES.meter_density(c[0], c[1]) for c in combos]
    # meters = [c[0] for c in combos]
    # radii = [c[1] for c in combos]
    # # for c in combos:
    # #     dens = ES.meter_density(c[0], c[1])
    # #     densities.append(dens)
    # #     meters.append(c[0])
    # #     radii.append(c[1])
    # test_dens_df = pd.DataFrame({'meter': meters,
    #                              'count': densities,
    #                              'radius': radii})
    # print(test_dens_df.sort_values(['meter', 'radius']))
    # dens = ES.meter_density(MN.meter_nodes[0], 200.0)
    # print(dens)
    # full_dens = ES.all_densities(
    #     [100.0, 200.0, 300.0, 400.0, 500.0, 1000.0, 1500.0])
    # print(ES.dens_df.sort_values(['meter', 'radius']))
    # densities = ES.all_densities([100.0, 200.0, 300.0, 400.0,
    #                               500.0, 1000.0, 1500.0])
    # ranges = ES.all_ranges()
    # isos = ES.all_isolates([100.0, 200.0, 300.0, 400.0,
    #                         500.0, 1000.0, 1500.0])
    # conts = ES.all_continuous([100.0, 200.0, 300.0, 400.0,
    #                            500.0, 1000.0, 1500.0])
    # shc = ES.all_single_hops([100.0, 200.0, 300.0, 400.0,
    #                           500.0, 1000.0, 1500.0])
    # islands = ES.all_islands([100.0, 200.0, 300.0, 400.0,
    #                           500.0, 1000.0, 1500.0])
    # score = ES.evaluate_system([100.0, 200.0, 300.0, 400.0,
    #                             500.0, 1000.0, 1500.0])
    # print(score)
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
    # config_file = os.path.join(
    #     head, 'results', 'tamu', 'config.json')
    # with open(config_file, 'r') as file:
    #     config = json.load(file)
    #     logging.config.dictConfig(config)
    # logger = logging.getLogger(__name__)
    # from timeit import default_timer as timer
    # logger.info('Starting the calculations for the TAMU models...')
    # print('Starting the calculations for the TAMU models...')
    # # # counter = 0
    # # # while counter < 10:
    # start = timer()
    # RS = Results()
    # for root, dirs, files in os.walk(data_path):
    #     # print('root:', root)
    #     # rand_files = random.sample(os.listdir(data_path), 20)
    #     for file in files:  # rand_files:
    #         # print('file:', file)
    #         h, t = os.path.split(file)
    #         if '.csv' in t:
    #             MN = MeterNetwork()
    #             graph = MN.from_csv(
    #                 os.path.join(data_path, file),
    #                 ['name', 'lon', 'lat'])
    #             df = MN.make_dataframe()
    #             ES = EvaluateSystem(
    #                 df, MN.meter_nodes, 'pos_x', 'pos_y', 'geo')
    #             dd = ES.get_distances()
    #             shc = ES.all_single_hops(
    #                 [30.0, 60.0, 100.0, 200.0, 300.0,
    #                  400.0, 500.0, 1000.0, 1500.0])
    #             ranges = ES.all_ranges()
    #             densities = ES.all_densities(
    #                 [30.0, 60.0, 100.0, 200.0, 300.0,
    #                  400.0, 500.0, 1000.0, 1500.0])
    #             isolates = ES.all_isolates(
    #                 [30.0, 60.0, 100.0, 200.0, 300.0,
    #                  400.0, 500.0, 1000.0, 1500.0])
    #             continuous = ES.all_continuous(
    #                 [30.0, 60.0, 100.0, 200.0, 300.0,
    #                  400.0, 500.0, 1000.0, 1500.0])
    #             island = ES.all_islands(
    #                 [30.0, 60.0, 100.0, 200.0, 300.0,
    #                  400.0, 500.0, 1000.0, 1500.0])
    #             score = ES.evaluate_system(
    #                 [30.0, 60.0, 100.0, 200.0, 300.0,
    #                  400.0, 500.0, 1000.0, 1500.0])
    #             RS.add(ES)
    # RS.save(
    #     os.path.join(head, 'results', 'tamu'),
    #     'tamu_test1_results.h5'.format())
    # #     counter += 1
    # print('Finished the calculations for the TAMU models.')
    # logger.info('Finished the calculations for the TAMU models.')
    # end = timer()
    # print('total time:', end - start)
    # -----Testing the Compare class -----
    # gld use case: R5-12.47-4_ns3 (929 total meters)
    # tamu use case: p1uhs1_1247--p1udt138 (944 total meters)
    # start = timer()
    # full_tamu_dens = pd.read_hdf(
    #     os.path.join(head, 'results', 'tamu', 'tamu_results1.h5'),
    #     key='density')
    # full_tamu_range = pd.read_hdf(
    #     os.path.join(head, 'results', 'tamu', 'tamu_results1.h5'),
    #     key='range')
    # full_tamu_isos = pd.read_hdf(
    #     os.path.join(head, 'results', 'tamu', 'tamu_results1.h5'),
    #     key='isolated')
    # full_tamu_isl = pd.read_hdf(
    #     os.path.join(head, 'results', 'tamu', 'tamu_results1.h5'),
    #     key='island')
    # full_tamu_cont = pd.read_hdf(
    #     os.path.join(head, 'results', 'tamu', 'tamu_results1.h5'),
    #     key='continuous')
    # full_tamu_shc = pd.read_hdf(
    #     os.path.join(head, 'results', 'tamu', 'tamu_results1.h5'),
    #     key='single_hop')
    # feeder_list = list(full_tamu_shc.feeder.unique())
    # # print(feeder_list)
    # test_df = full_tamu_shc[
    #     full_tamu_shc['feeder'] == feeder_list[0]]
    # # print(test_df.head())
    C = Compare()
    C.load_data()
    dens = pd.read_hdf(
        os.path.join(head, 'results', 'gld', 'gld_results2.h5'),
        key='density')
    rnge = pd.read_hdf(
        os.path.join(head, 'results', 'gld', 'gld_results2.h5'),
        key='range')
    isos = pd.read_hdf(
        os.path.join(head, 'results', 'gld', 'gld_results2.h5'),
        key='isolated')
    cont = pd.read_hdf(
        os.path.join(head, 'results', 'gld', 'gld_results2.h5'),
        key='continuous')
    shc = pd.read_hdf(
        os.path.join(head, 'results', 'gld', 'gld_results2.h5'),
        key='single_hop')
    isl = pd.read_hdf(
        os.path.join(head, 'results', 'gld', 'gld_results2.h5'),
        key='island')
    dens_reduced = dens[dens['feeder'] == 'R1-12.47-1_ns3']
    rnge_reduced = rnge[rnge['feeder'] == 'R1-12.47-1_ns3']
    isos_reduced = isos[isos['feeder'] == 'R1-12.47-1_ns3']
    cont_reduced = cont[cont['feeder'] == 'R1-12.47-1_ns3']
    shc_reduced = shc[shc['feeder'] == 'R1-12.47-1_ns3']
    isl_reduced = isl[isl['feeder'] == 'R1-12.47-1_ns3']
    stats_df = C.compare_island_count(
        [isl_reduced], 'agg',
        [100.0, 200.0, 300.0])
    print(stats_df)
    # stats_df = C.compare_single_hop_count(
    #     [test_df], 'agg',
    #     [100.0, 200.0, 300.0, 400.0, 500.0, 1000.0, 1500.0])
    # print(stats_df)
    # print(stats_df['mse'].mean())
    # gld_df = pd.read_hdf(
    #     os.path.join(head, 'results', 'gld', 'gld_results.h5'),
    #     key='density')
    # models = list(gld_df['feeder'].unique())[0:20]
    # print(len(models))
    # keys = ['density', 'range', 'isolated',
    #         'continuous', 'island', 'single_hop']
    # print('Starting the comparison...')
    # # Try this for 30 and 60 feet
    # for key in keys:
    #     if key == 'density':
    #         tamu_df = pd.read_hdf(
    #             os.path.join(head, 'results',
    #                          'tamu', 'tamu_results1.h5'),
    #             key='density')
    #         models = list(tamu_df.feeder.unique())
    #         model_dfs = [tamu_df[tamu_df['feeder'] == m] for m in models]
    #         gld_df = pd.read_hdf(
    #             os.path.join(head, 'results', 'gld', 'gld_results.h5'),
    #             key='density')
    #         glds = list(gld_df.feeder.unique())[0:20]
    #         gld_dfs = [gld_df[gld_df['feeder'] == g] for g in glds]
    #         C = Compare()
    #         C.load_data()
    #         # df = C.real_density
    #         tamu_dens = C.compare_meter_density(
    #             model_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #         gld_dens = C.compare_meter_density(
    #             gld_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #     elif key == 'range':
    #         tamu_df = pd.read_hdf(
    #             os.path.join(head, 'results',
    #                          'tamu', 'tamu_results1.h5'),
    #             key='range')
    #         models = list(tamu_df.feeder.unique())
    #         model_dfs = [tamu_df[tamu_df['feeder'] == m] for m in models]
    #         gld_df = pd.read_hdf(
    #             os.path.join(head, 'results', 'gld', 'gld_results.h5'),
    #             key='range')
    #         glds = list(gld_df.feeder.unique())[0:20]
    #         gld_dfs = [gld_df[gld_df['feeder'] == g] for g in glds]
    #         C = Compare()
    #         C.load_data()
    #         # df = C.real_range
    #         tamu_range = C.compare_meter_range(
    #             model_dfs, 'single')
    #         gld_range = C.compare_meter_range(
    #             gld_dfs, 'single')
    #     elif key == 'isolated':
    #         tamu_df = pd.read_hdf(
    #             os.path.join(head, 'results',
    #                          'tamu', 'tamu_results1.h5'),
    #             key='isolated')
    #         models = list(tamu_df.feeder.unique())
    #         model_dfs = [tamu_df[tamu_df['feeder'] == m] for m in models]
    #         gld_df = pd.read_hdf(
    #             os.path.join(head, 'results', 'gld', 'gld_results.h5'),
    #             key='isolated')
    #         glds = list(gld_df.feeder.unique())[0:20]
    #         gld_dfs = [gld_df[gld_df['feeder'] == g] for g in glds]
    #         C = Compare()
    #         C.load_data()
    #         # df = C.real_isolated
    #         tamu_isos = C.compare_isolated_meters(
    #             model_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #         gld_isos = C.compare_isolated_meters(
    #             gld_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #     elif key == 'continuous':
    #         tamu_df = pd.read_hdf(
    #             os.path.join(head, 'results',
    #                          'tamu', 'tamu_results1.h5'),
    #             key='continuous')
    #         models = list(tamu_df.feeder.unique())
    #         model_dfs = [tamu_df[tamu_df['feeder'] == m] for m in models]
    #         gld_df = pd.read_hdf(
    #             os.path.join(head, 'results', 'gld', 'gld_results.h5'),
    #             key='continuous')
    #         glds = list(gld_df.feeder.unique())[0:20]
    #         gld_dfs = [gld_df[gld_df['feeder'] == g] for g in glds]
    #         C = Compare()
    #         C.load_data()
    #         # df = C.real_continuous
    #         tamu_cont = C.compare_meter_continuity(
    #             model_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #         gld_cont = C.compare_meter_continuity(
    #             gld_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #     elif key == 'island':
    #         tamu_df = pd.read_hdf(
    #             os.path.join(head, 'results',
    #                          'tamu', 'tamu_results1.h5'),
    #             key='island')
    #         models = list(tamu_df.feeder.unique())
    #         model_dfs = [tamu_df[tamu_df['feeder'] == m] for m in models]
    #         gld_df = pd.read_hdf(
    #             os.path.join(head, 'results', 'gld', 'gld_results.h5'),
    #             key='island')
    #         glds = list(gld_df.feeder.unique())[0:20]
    #         gld_dfs = [gld_df[gld_df['feeder'] == g] for g in glds]
    #         C = Compare()
    #         C.load_data()
    #         # df = C.real_island
    #         tamu_isl = C.compare_island_count(
    #             model_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #         gld_isl = C.compare_island_count(
    #             gld_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #     elif key == 'single_hop':
    #         tamu_df = pd.read_hdf(
    #             os.path.join(head, 'results',
    #                          'tamu', 'tamu_results1.h5'),
    #             key='single_hop')
    #         models = list(tamu_df.feeder.unique())
    #         model_dfs = [tamu_df[tamu_df['feeder'] == m] for m in models]
    #         gld_df = pd.read_hdf(
    #             os.path.join(head, 'results', 'gld', 'gld_results.h5'),
    #             key='single_hop')
    #         glds = list(gld_df.feeder.unique())[0:20]
    #         gld_dfs = [gld_df[gld_df['feeder'] == g] for g in glds]
    #         C = Compare()
    #         C.load_data()
    #         # df = C.real_single_hop
    #         tamu_shc = C.compare_single_hop_count(
    #             model_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #         gld_shc = C.compare_single_hop_count(
    #             gld_dfs, 'agg',
    #             [100.0, 200.0, 300.0,
    #              400.0, 500.0, 1000.0, 1500.0])
    #     else:
    #         pass
    # with pd.ExcelWriter('tamu_stats.xlsx') as writer:
    #     tamu_dens.to_excel(writer, sheet_name='density')
    #     tamu_range.to_excel(writer, sheet_name='range')
    #     tamu_isos.to_excel(writer, sheet_name='isolated')
    #     tamu_cont.to_excel(writer, sheet_name='continuous')
    #     tamu_isl.to_excel(writer, sheet_name='island')
    #     tamu_shc.to_excel(writer, sheet_name='single_hop')
    # with pd.ExcelWriter('gld_stats.xlsx') as writer:
    #     gld_dens.to_excel(writer, sheet_name='density')
    #     gld_range.to_excel(writer, sheet_name='range')
    #     gld_isos.to_excel(writer, sheet_name='isolated')
    #     gld_cont.to_excel(writer, sheet_name='continuous')
    #     gld_isl.to_excel(writer, sheet_name='island')
    #     gld_shc.to_excel(writer, sheet_name='single_hop')
    # end = timer()
    # print('Finished the comparison')
    # print('total time:', end - start)
