import pandas as pd
import json
import glob
import random
import os

pd.options.mode.chained_assignment = None


def extract_hour(data):
    df_time = data[['start_ts', 'end_ts']].copy()
    df_time['start_ts'] = pd.to_datetime(df_time['start_ts'])
    df_time['end_ts'] = pd.to_datetime(df_time['end_ts'])
    df_time['new_start_ts'] = df_time['end_ts'].dt.round('H').dt.strftime('%H')
    df_time['new_end_ts'] = df_time['start_ts'].dt.round('H').dt.strftime('%H')
    return df_time


def extract_nrel_fleet():
    files = glob.glob('nrel-fleet/*.csv')
    voc_id_start_end_time = {}
    for file in files:
        df = pd.read_csv(file)
        voc_ids = df['voc_id'].tolist()
        df_time = extract_hour(df)
        for idx in voc_ids:
            if str(idx) not in voc_id_start_end_time:
                voc_id_start_end_time[idx] = {'start_time': [], 'end_time': []}
            # find indices of voc id in dataframe:
            idxs = df.index[df['voc_id'] == idx].tolist()
            if voc_id_start_end_time[idx]['start_time']:
                voc_id_start_end_time[idx]['start_time'] += df_time['new_start_ts'][idxs].tolist()
                voc_id_start_end_time[idx]['end_time'] += df_time['new_end_ts'][idxs].tolist()
            else:
                voc_id_start_end_time[idx]['start_time'] = df_time['new_start_ts'][idxs].tolist()
                voc_id_start_end_time[idx]['end_time'] = df_time['new_end_ts'][idxs].tolist()
    return voc_id_start_end_time


def modify_time(voc_id_start_end_time, offset_main_logic):
    files = glob.glob('output_data/*.csv')
    data_classifiers = pd.read_csv('data_classifiers.csv')
    vocation_id_map = {}
    mapping = {'Buses': 'school bus', 'Vans': 'warehouse delivery', 'Trucks': 'mass transit', 'Ambulance': 'ambulance'}
    f = open('vehicle_name_dict.json')
    vehicle_name = json.load(f)

    for vehicle in vehicle_name['MHDV_name_dict']:
        for v in vehicle_name['MHDV_name_dict'][vehicle]:
            vocation_id_map[v.lower()] = mapping[vehicle]

    for vehicle in vehicle_name['LDV_name_dict']:
        for v in vehicle_name['LDV_name_dict'][vehicle]:
            if 'sedan' in v:
                vocation_id_map[v.lower()] = 'sedan'
            else:
                vocation_id_map[v.lower()] = 'telecom'
    vocation_id_map["LD POV"] = "ld_pov"
    # for k in len(data_classifiers):
    for file in files:
        print(file)
        try:
            df = pd.read_csv(file)
        except:
            df = pd.DataFrame()
        for k in range(len(df)):
            voc_id_name = vocation_id_map[df['Vehicle type (POV, M/H)'][k]]
            if voc_id_name == 'sedan':
                df['Reach office (24h)'][k] = 8
                df['Reach home (24h)'][k] = 18
            elif voc_id_name == 'ambulance':
                # Ambulance available for charging only for 6 hrs??
                time_idx = random.randint(0, 17)
                df['Reach office (24h)'][k] = time_idx
                df['Reach home (24h)'][k] = time_idx + 6
            elif voc_id_name == "ld_pov":
                # do nothing... leave the time as is since POV times are properly done by adoption team
                pass
            else:
                if offset_main_logic:
                    start_time = str(18)
                    end_time = str(8)
                else:
                    voc_id = data_classifiers.index[data_classifiers['Description'] == voc_id_name].tolist()[0]
                    voc_id = data_classifiers['ID'][voc_id]
                    num_samples = len(voc_id_start_end_time[voc_id]['start_time'])
                    time_idx = random.randint(0, num_samples)
                    start_time = voc_id_start_end_time[voc_id]['start_time'][time_idx - 1]
                    end_time = voc_id_start_end_time[voc_id]['end_time'][time_idx - 1]
                    if abs(int(float(start_time)) - int(float(end_time))) == 0:
                        # end_time = str(int(int(float(start_time)) + 6))
                        start_time = str(18)
                        end_time = str(8)
                    # if random.uniform(0,1) < 0.5:  # 50% randomly make vehicles have ev times during day
                    #     start_time = round(random.uniform(8,13))
                    #     end_time = start_time + 3
                    # else:
                    #     pass
                df['Reach office (24h)'][k] = end_time
                df['Reach home (24h)'][k] = start_time
        headers = df.columns
        # Some CSV files are empty
        if len(headers) > 0:
            del_col = [header for header in headers if 'Time of availability for charging' in header]
            del df[del_col[0]]
            df.to_csv('new_' + file, encoding='utf-8', index=False)
        else:
            df = pd.DataFrame()
            df.to_csv('new_' + file, encoding='utf-8', index=False)


def main(offset_main_logic):
    voc_id_start_end_time = extract_nrel_fleet()
    modify_time(voc_id_start_end_time, offset_main_logic)

if __name__ == '__main__':
    offset_main_logic = False
    output_path = "new_" + "output_data"
    os.makedirs(output_path, exist_ok=True)
    voc_id_start_end_time = extract_nrel_fleet()
    modify_time(voc_id_start_end_time, offset_main_logic)
