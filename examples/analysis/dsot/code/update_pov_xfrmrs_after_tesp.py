"""
Demo for parsing a glm file and modifying it
"""
from glm import GLMManager
import utils
import json
import os
import pandas as pd
import h5py
import shutil

import glmanip
import networkx as nx
# from networkx.drawing.nx_agraph import graphviz_layout
# import copy
from create_json_for_networkx import createJson
import matplotlib.pyplot as plt
import random



cache_output = {}
cache_df = {}


def delete_open_elements(model, element):
    if element in model:
        element_model = model[element].copy()
        for ele in model[element]:
            for key in model[element][ele]:
                if 'state' in key:
                    if model[element][ele][key] == 'OPEN':
                        del element_model[ele]
                        break
        model[element] = element_model.copy()
        print('{} model has {} objects'.format(element, len(model[element])))

    return model

# def load_json(dir_path, file_name):
#     """Utility to open Json files."""
#     name = os.path.join(dir_path, file_name)
#     try:
#         cache = cache_output[name]
#         return cache
#     except:
#         with open(name) as json_file:
#             cache_output[name] = json.load(json_file)
#     return cache_output[name]

def get_house_info_networkx(basedir):
    com_load_fn = basedir + "com_loads.json"
    with open(com_load_fn, 'r') as file:
        com_loads = json.load(file)
    com_load_name = set(list(com_loads.keys()))

    feeder_name = 'Substation_1'
    substation_node = 'network_node'

    glm_lines = glmanip.read(basedir + feeder_name + '.glm', basedir, buf=[])
    [model, clock, directives, modules, classes] = glmanip.parse(glm_lines)

    ######### delete disconnected elements from the GridLAB-D Model ########
    model = delete_open_elements(model, 'switch')
    model = delete_open_elements(model, 'sectionalizer')
    model = delete_open_elements(model, 'recloser')
    model = delete_open_elements(model, 'fuse')

    feeder_network = createJson(feeder_name, model, clock, directives, modules, classes, basedir)
    G_feeder = nx.readwrite.json_graph.node_link_graph(feeder_network)

    print("Creating the asset maps")
    xfmr_asset_map = {}
    asset_str = '_hse_'  #### change this to hse to track houses ####

    for xfmr_id in model['transformer']:
        xfmr_config = model['transformer'][xfmr_id]['configuration']

        ##### Logic for identifying Residential Transformers ####
        # if 'POLETOP' in xfmr_config:
        # xfmr_asset_map[xfmr_id] = []
        #### Estimating downstream nodes from transformers ####
        to_node = model['transformer'][xfmr_id]['to']
        connected_items = nx.descendants(G_feeder, to_node)
        intersection_item_set = com_load_name.intersection(connected_items)
        if not intersection_item_set:
            xfmr_asset_map[xfmr_id] = []
            for item in connected_items:
                if asset_str in item:  ### Hard coded logic please change
                    xfmr_asset_map[xfmr_id].append(item)

    with open(basedir + 'asset_map_' + feeder_name + asset_str + '.json', 'w') as fp:
        json.dump(xfmr_asset_map, fp)

    return basedir + 'asset_map_' + feeder_name + asset_str + '.json', 'asset_map_' + feeder_name + asset_str + '.json'

def load_json(dir_path, file_name):
    """Utility to open Json files."""
    name = os.path.join(dir_path, file_name)
    try:
        cache = cache_output[name]
        return cache
    except:
        with open(name) as json_file:
            cache_output[name] = json.load(json_file)
    return cache_output[name]


def get_attributes_from_metrics_data(data_base_df, objects, attrib):
    data_att_df = pd.DataFrame(columns=['Datetime'] + objects)

    for obj in objects:
        idx = data_base_df.index[data_base_df['name'] == obj].tolist()
        data_att_df[obj] = data_base_df[attrib][idx].values
    data_att_df['Datetime'] = pd.to_datetime(data_base_df['date'][idx].values, format='%Y-%m-%d %H:%M:%S CDT')

    return data_att_df


def load_system_data(dir_path, folder_prefix, dso_num, day_num, system_name):
    """Utility to open GLD created h5 files for systems' data.
    Arguments:
        dir_path (str): path of parent directory where DSO folders live
        folder_prefix(str): prefix of DSO folder name (e.g. '\TE_base_s')
        dso_num (str): number of the DSO folder to be opened
        system_name (str): name of system data to load (e.g. 'house', 'substation', 'inverter' etc)
    Returns:
        system_meta_df : dataframe of system metadata
        system_df: dataframe of system timeseries data
        """
    daily_index = True
    os.chdir(dir_path + folder_prefix + dso_num)
    hdf5filenames = [f for f in os.listdir('.') if f.endswith('.h5') and system_name in f]
    filename = hdf5filenames[0]
    # reading data as pandas dataframe
    store = h5py.File(filename, "r")
    list(store.keys())
    system_meta_df = pd.read_hdf(filename, key='/Metadata', mode='r')

    # # to check keys in h5 file
    # f = h5py.File(filename, 'r')
    # print([key for key in f.keys()])

    if daily_index:
        system_df = pd.read_hdf(hdf5filenames[0], key='/index' + day_num, mode='r')
    # ----- The code below was used for when there was one index with multiple days
    else:
        system_df = pd.read_hdf(hdf5filenames[0], key='/index1', mode='r')
        start_time = (int(day_num) - 1) * 300 * 288
        end_time = start_time + 300 * (288 - 1)
        system_df = system_df[system_df['time'] >= start_time]
        system_df = system_df[system_df['time'] <= end_time]
        # start = 300
        # system_df = pd.read_hdf(hdf5filenames[0], key='/index1', mode='r', columns='time', where='time=start')
        # sim_start = date
        # start_time = sim_start + timedelta(days=int(day_num) - 1)
        # stop_time = start_time + timedelta(days=1) - timedelta(minutes=5)
        # system_df['date'] = system_df['date'].apply(pd.to_datetime)
        # system_df = system_df.set_index(['date'])
        # system_df = system_df.loc[start_time:stop_time]
    return system_meta_df, system_df

if __name__ == '__main__':





    main_names = ['AZ_Tucson']  # , 'WA_Tacoma', 'AL_Dothan', 'IA_Johnston', 'LA_Alexandria', 'AK_Anchorage', 'MT_Greatfalls']
    sizes = ["Large"]
    custom_suffix = "jul14_runs"  # "jul9_runs"
    folder_count = 17
    for xol in main_names:
        for xoli in sizes:
            half_name = f"{xol}_{xoli}_{custom_suffix}"
            for k_li in range(folder_count):
                folder_name = f"{half_name}_{k_li+1}_fl"
                print(f"------------------------------------------------")
                print(f"------------------------------------------------")
                print(f"------------------------------------------------")
                print(f"Processing ----> {folder_name}")
                print(f"------------------------------------------------")
                print(f"------------------------------------------------")
                print(f"------------------------------------------------")

    # folder_name = 'AZ_Tucson_Large_feb12_runs_1_fl'
                pd.set_option('display.max_columns', 50)
                day_range = range(1, 7)  # 1 = Day 1. Starting at day two as agent data is missing first hour of run.
                dso_range = range(1, 2)  # 1 = DSO 1 (end range should be last DSO +1)
                dso = 1
                agent_prefix = '/DSO_'
                curr_dir = os.getcwd()
                plots_folder_name = f"{folder_name}_plots"
                base_case = f"{curr_dir}/" + folder_name
                basedir = f"{base_case}/Substation_1/"

                # If this file "Substation_1_no_pov_xfrmr_upgrades.glm" already exists in the folder then this file
                # is the original glm file used to conduct gridlabd simulations. So, if this script is run and if
                # this above glm file exists then Substation_1.glm (has pov xfrmr upgrades) need to be replaced with
                # Substation_1_no_pov_xfrmr_upgrades.glm. This is because this script is trying to update pov ratings
                # on top of the original glm file from tesp (Substation_1_no_pov_xfrmr_upgrades.glm). However,
                # if "Substation_1_no_pov_xfrmr_upgrades.glm" does not exist then we can proceed with editing the
                # Substation_1.glm file directly since Substation_1.glm file will be the original .glm file from
                # tesp. Trying to avoid any bugs in case a user tries to run this script multiple times without
                # knowing the detail behind how the pipeline is setup.
                if os.path.isfile(basedir + '/Substation_1_no_pov_xfrmr_upgrades.glm'):
                    shutil.copy2(base_case + "/Substation_1/Substation_1_no_pov_xfrmr_upgrades.glm",
                                 base_case + "/Substation_1/Substation_1.glm")
                    os.remove(base_case + "/Substation_1/Substation_1_no_pov_xfrmr_upgrades.glm")


                # get house data using networkx
                res_xfmr_file_dir, res_xfmr_file_name = get_house_info_networkx(basedir)
                res_xfmr_dict = load_json(basedir, res_xfmr_file_name)

                ########################### Load Agent Data ###############################
                ###########################################################################
                agent_file = (base_case + agent_prefix + str(dso) + '/Substation_' + str(dso) + '_agent_dict.json')
                f = open(agent_file, "r")
                # Reading from file
                agent_data = json.loads(f.read())
                houses = list(agent_data['hvacs'].keys())
                meters = list(agent_data['site_agent'].keys())

                ########################### Load House Data ###############################
                ###########################################################################
                print("Processing metrics_house.h5 data ....")
                hse_attr = 'total_load_max'  ### Adjust the attribute that you want to collect
                house_att_df = pd.DataFrame()
                for day in day_range:
                    meta_house_df_base, data_house_df_base = load_system_data(base_case, '/Substation_', str(dso), str(day),
                                                                              'house')
                    print('List of Attributes in house.h5 data:  ... \n {}'.format(meta_house_df_base['name'].values))
                    if house_att_df.empty:
                        house_att_df = get_attributes_from_metrics_data(data_house_df_base, houses, hse_attr)
                    else:
                        temp1 = get_attributes_from_metrics_data(data_house_df_base, houses, hse_attr)
                        # house_att_df = house_att_df.append(temp1)
                        house_att_df = pd.concat([house_att_df, temp1])

                print("House Data DF is complete.")

                ##############  Finding Peak Load of a Residential XFMR ###################
                ###########################################################################
                xfmr_max_load_dict = {}
                for keys, val in res_xfmr_dict.items():
                    if keys != "substation_transformer":
                        combined_load = house_att_df[val].sum(axis=1)
                        max_xfmr_loading = max(combined_load)
                        xfmr_max_load_dict[keys] = max_xfmr_loading
                os.chdir(curr_dir)
                with open(basedir+"XFMR_peak_load.json", 'w') as fp:
                    json.dump(xfmr_max_load_dict, fp)

                xfmr_load_file_name = "XFMR_peak_load.json"
                xfmr_max_load_dict = load_json(basedir, xfmr_load_file_name)
                # alpha_xfmr_pwr_mult = 1.5

                glm_mgr = GLMManager(basedir + '/Substation_1.glm', model_is_path=True)

                xfmr_config_peak_dict={}
                for k, v in glm_mgr.model_dict.items():
                    item_type = glm_mgr._get_item_type(v)
                    if item_type == 'object' and v['object'] == 'transformer':
                        xfmr_name = v["name"]
                        if xfmr_name != "substation_transformer":
                            xfmr_config = v["configuration"]
                            if xfmr_config in xfmr_config_peak_dict:
                                xfmr_config_peak_dict[xfmr_config] = max(xfmr_config_peak_dict[xfmr_config], xfmr_max_load_dict[xfmr_name])
                            else:
                                xfmr_config_peak_dict[xfmr_config] = xfmr_max_load_dict[xfmr_name]

                for k, v in glm_mgr.model_dict.items():
                    item_type = glm_mgr._get_item_type(v)
                    if item_type == 'object' and v['object'] == 'transformer_configuration' and v['name']!="substation_xfmr_config":
                        updated_power_rating = (
                                float(xfmr_config_peak_dict[v['name']])*(1/0.9)*((random.randint(97,105))/100))
                        # also converted the kws to kva using 0.9, because rating update on xfrmr and xfrm name to size
                        # json must be in kva.
                        pwr = [0, 0, 0]
                        if float(v['powerA_rating']) != 0.0:
                            pwr[0] = 1
                        if float(v['powerB_rating']) != 0.0:
                            pwr[1] = 1
                        if float(v['powerC_rating']) != 0.0:
                            pwr[2] = 1
                        tot_phase = sum(pwr)
                        pwr_rating_per_phase = [max(float(v['powerA_rating']), (updated_power_rating)*pwr[0]/tot_phase), max(float(v['powerB_rating']), (updated_power_rating)*pwr[1]/tot_phase),
                                           max(float(v['powerC_rating']), (updated_power_rating)*pwr[2]/tot_phase)]

                        load_dict = {'object': 'transformer_configuration', 'power_rating': max(float(v['power_rating']), updated_power_rating),
                                     'powerA_rating': pwr_rating_per_phase[0],
                                     'powerB_rating': pwr_rating_per_phase[1],
                                     'powerC_rating': pwr_rating_per_phase[2],
                                     'name': v['name']}
                        glm_mgr.modify_item(load_dict)
                        # break

                # glm_mgr.add_item({'object': 'group_recorder',
                #                   'name': 'transformer_kva',
                #                   'group': 'class=transformer',
                #                   'property': 'power_out',
                #                   'interval': '3600',
                #                   'limit': '100000',
                #                   'file': 'transformer_va_data.csv',
                #                   'complex_part': 'MAG'})

                # save original file as backup and delete the original file before saving the modified glm by the same name.
                shutil.copy2(base_case + "/Substation_1/Substation_1.glm", base_case + "/Substation_1/Substation_1_no_pov_xfrmr_upgrades.glm")
                os.remove(base_case + "/Substation_1/Substation_1.glm")
                uid = 0
                model = basedir + '/Substation_1.glm'.format(uid)
                glm_mgr.write_model(model)

                k = 1
                # result = utils.run_gld(model)