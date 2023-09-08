
import json

import tesp_support.api.store as fle


def te30_store(case_name):
    challenge = 'TE_ChallengeH'
    challenge0 = 'TE_ChallengeH0'
    h5 = "_metrics.h5"
    json = "_metrics.json"
    my_store = fle.Store(case_name + '.json')

    my_path = my_store.add_path("../te30", "TE30 Directory")
    sub = my_path.set_includeDir(".", False)

    names = ['billing_meter_', 'capacitor_', 'evchargerdet_', 'house_', 'inverter_',
             'line_', 'substation_', 'transformer_']
    for i in range(len(names)):
        name = names[i] + challenge + h5
        my_file = my_store.add_file(name, names[i] + 'for ' + challenge)
        tables = my_file.get_tables()
        my_path.set_includeFile(sub, name)

        name = names[i] + challenge0 + h5
        my_file = my_store.add_file(name, names[i] + 'for ' + challenge0)
        tables = my_file.get_tables()
        my_path.set_includeFile(sub, name)

    my_file = my_store.add_file(challenge + ".csv", 'CSV for TE_ChallengeH')
    tables = my_file.get_tables()
    my_path.set_includeFile(sub, challenge + ".csv")
    my_file = my_store.add_file(challenge0 + ".csv", 'CSV for TE_ChallengeH0')
    tables = my_file.get_tables()
    my_path.set_includeFile(sub, challenge0 + ".csv")
    my_file = my_store.add_file("eplus_load.csv", 'eplus load CSV')
    tables = my_file.get_tables()
    my_path.set_includeFile(sub, "eplus_load.csv")
    my_file = my_store.add_file("weather.csv", 'eplus load CSV')
    tables = my_file.get_tables()
    my_path.set_includeFile(sub, "weather.csv")

    # are in json and store.py can't read them
    # but will be place in to the .zip
    names = ['auction_', 'controller_', 'eplus_', 'bus_', 'gen_', 'sys_']
    for i in range(len(names)):
        my_path.set_includeFile(sub, names[i] + challenge + json)
        my_path.set_includeFile(sub, names[i] + challenge0 + json)
    names = ['agent_dict', '_glm_dict', 'model_dict']
    for i in range(len(names)):
        my_path.set_includeFile(sub, challenge + names[i] + ".json")

    my_store.write()
    my_store.zip('te30_store.zip')

if __name__ == "__main__":
    te30_store("te30_store")