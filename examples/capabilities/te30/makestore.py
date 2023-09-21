
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

    # gridlabd metric file names =
    #   ['billing_meter_', 'capacitor_', 'evchargerdet_', 'house_',
    #    'inverter_', 'line_', 'substation_', 'transformer_']
    # Only these files have data in them
    names = ['billing_meter_', 'house_', 'inverter_']
    for i in range(len(names)):
        name = names[i] + challenge + h5
        my_file = my_store.add_file(name, names[i] + 'for ' + challenge)
        my_path.set_includeFile(sub, name)
        tables = my_file.get_tables()
        if len(tables) > 1:
            columns = my_file.get_columns(tables[1])
            my_file.set_date_bycol(tables[1], 'date')
            columns = my_file.get_columns(tables[2])
            my_file.set_date_bycol(tables[2], 'date')

        name = names[i] + challenge0 + h5
        my_file = my_store.add_file(name, names[i] + 'for ' + challenge0)
        my_path.set_includeFile(sub, name)
        tables = my_file.get_tables()
        if len(tables) > 1:
            columns = my_file.get_columns(tables[1])
            my_file.set_date_bycol(tables[1], 'date')
            columns = my_file.get_columns(tables[2])
            my_file.set_date_bycol(tables[2], 'date')

    my_file = my_store.add_file(challenge + ".csv", 'CSV for TE_ChallengeH')
    tables = my_file.get_tables()
    if len(tables):
        columns = my_file.get_columns(tables[0], 0)
        my_file.set_date_bycol(tables[0], 't[s]')
    my_path.set_includeFile(sub, challenge + ".csv")

    my_file = my_store.add_file(challenge0 + ".csv", 'CSV for TE_ChallengeH0')
    tables = my_file.get_tables()
    if len(tables):
        columns = my_file.get_columns(tables[0], 0)
        my_file.set_date_bycol(tables[0], 't[s]')
    my_path.set_includeFile(sub, challenge0 + ".csv")

    my_file = my_store.add_file("eplus_load.csv", 'eplus load CSV')
    tables = my_file.get_tables()
    if len(tables):
        columns = my_file.get_columns(tables[0], 8)
        my_file.set_date_bycol(tables[0], columns[0])
    my_path.set_includeFile(sub, "eplus_load.csv")

    my_file = my_store.add_file("weather.csv", 'weather CSV')
    tables = my_file.get_tables()
    if len(tables):
        columns = my_file.get_columns(tables[0], 8)
        my_file.set_date_bycol(tables[0], columns[0])
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


def _test(case_name):
    my_store = fle.Store(case_name + '.json')
    # this is a cvs file
    my_file = my_store.get_schema('weather')
    data = my_file.get_series_data('weather', '2013-07-01 00:00', '2013-07-02 00:00')
    tseries = [data]
    print(tseries)
    # this is a h5 file
    my_file = my_store.get_schema('inverter_TE_ChallengeH_metrics')
    data = my_file.get_series_data('index1', '2013-07-01 00:00', '2013-07-02 00:00')
    tseries = [data]
    print(tseries)


if __name__ == "__main__":
    # te30_store("te30_store")
    _test("te30_store")
