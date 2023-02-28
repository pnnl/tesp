# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: main.py

# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import json
import sqlite3
import pandas as pd
import numpy as np

from tesp_support.api.entity import assign_defaults
from tesp_support.api.entity import assign_item_defaults
from tesp_support.api.entity import Entity
from tesp_support.api.model import GLModel
from tesp_support.api.modifier import GLMModifier
from tesp_support.api.store import entities_path
from tesp_support.api.store import feeders_path


class mytest:
    def test(self):
        return


def fredtest():
    testMod = GLMModifier()
    testMod.model.read(feeders_path + "/GLD_three_phase_house.glm")
    loads = testMod.get_object('load')
    meter_counter = 0
    house_counter = 0
    house_meter_counter = 0
    for obj_id in loads.instance:
        # add meter for this load
        meter_counter = meter_counter + 1
        meter_name = 'meter_' + str(meter_counter)
        meter = testMod.add_object('meter', meter_name, [])
        meter['parent'] = obj_id
        # how much power is going to be needed
        # while kva < total_kva:
        house_meter_counter = house_meter_counter + 1
        # add parent meter for houses to follow
        house_meter_name = 'house_meter_' + str(house_meter_counter)
        meter = testMod.add_object('meter', house_meter_name, [])
        meter['parent'] = meter_name
        # add house
        house_counter = house_counter + 1
        house_name = 'house_' + str(house_counter)
        house = testMod.add_object('house', house_name, [])
        house['parent'] = house_meter_name
    testMod.write_model("test.glm")


def test1():
    # entity_names = ["SimulationConfig", "BackboneFiles",  "WeatherPrep", "FeederGenerator",
    #             "EplusConfiguration", "PYPOWERConfiguration", "AgentPrep", "ThermostatSchedule"]
    # entity_names = ['house', 'inverter', 'battery', 'object solar', 'waterheater']

    try:
        conn = sqlite3.connect(entities_path + 'test.db')
        print("Opened database successfully")
    except:
        print("Database Sqlite3.db not formed")

    # this a config  -- file probably going to be static json
    file_name = entities_path + 'feeder_defaults.json'
    myEntity = mytest()
    assign_defaults(myEntity, file_name)
    name = 'rgnPenResHeat'
    print(name)
    print(type(myEntity.__getattribute__(name)))
    print(myEntity.__getattribute__(name))

    # this a config  -- file probably going to be static
    myEntity = mytest()
    assign_item_defaults(myEntity, file_name)
    print(myEntity.rgnPenResHeat.datatype)
    print(myEntity.rgnPenResHeat.item)
    print(myEntity.rgnPenResHeat)
    print(myEntity.rgnPenResHeat.value)

    # Better to use Entity as subclass like substation for metrics
    # Better to use Entity as object models for editing and persistence like glm_model,

    # this a multiple config file a using dictionary list persistence
    file_name = 'glm_objects.json'
    with open(entities_path + file_name, 'r', encoding='utf-8') as json_file:
        entities = json.load(json_file)
        mylist = {}
        for name in entities:
            mylist[name] = Entity(name, entities[name])
            print(mylist[name].toHelp())
            mylist[name].toSQLite(conn)
            # mylist[name].instanceToSQLite(conn)
    conn.close()


def test2():
    # Test model.py
    model_file = GLModel()
    tval = model_file.read(feeders_path + "R1-12.47-1.glm")
    # tval = model_file.read(feeders_path + "GLD_three_phase_house.glm")
    # Output json with new parameters
    model_file.write(entities_path + "test.glm")

    model_file.instancesToSQLite()
    print(model_file.entitiesToHelp())
    print(model_file.instancesToGLM())

    op = open(entities_path + 'glm_objects2.json', 'w', encoding='utf-8')
    json.dump(model_file.entitiesToJson(), op, ensure_ascii=False, indent=2)
    op.close()


def test3():
    modobject = GLMModifier()

    tval = modobject.read_model(feeders_path + "R1-12.47-1.glm")

    for name in modobject.model.entities:
        print(modobject.model.entities[name].toHelp())


# Synchronizes a list of time series dataframes
# Synchronization includes resampling the time series based
# upon the synch_interval and interval_unit entered
def synch_time_series(series_list, synch_interval, interval_unit):
    synched_series = []

    for df in series_list:
        synched_df = df.resample(str(synch_interval) + interval_unit).interpolate()
        synched_series.append(synched_df)
    return synched_series


# Gets the latest start time and the earliest time from a list
# of time series
def get_synch_date_range(time_series):
    t_start = time_series[0].index[0]
    t_end = time_series[0].index[len(time_series[0].index)-1]
    for tserie in time_series:
        if tserie.index[0] > t_start:
            t_start = tserie.index[0]
        if tserie.index[len(tserie.index) - 1] < t_end:
            t_end = tserie.index[len(tserie.index) - 1]
    return t_start, t_end


# Clips the time series in the list to the same start and stop times
def synch_series_lengths(time_series):
    synched_series = []
    synch_start, synch_end = get_synch_date_range(time_series)
    for tseries in time_series:
        synch_series = tseries.query('index > @synch_start and index < @synch_end')
        synched_series.append(synch_series)
    return synched_series


# Sychronizes the length and time intervals of a list of time series dataframes
def synch_series(time_series, synch_interval, interval_unit):
    clipped_series = []
    synched_series = []
    sampled_series = []
    clipped_series = synch_series_lengths(time_series)
    synched_series = synch_time_series(clipped_series, 1, "T")
    sampled_series = synch_time_series(clipped_series, synch_interval, interval_unit)
    return sampled_series


def debug_resample():
    np.random.seed(0)
    tseries = []
    synched_series = []
    start, end = '2000-01-01 22:00:00', '2001-01-01 22:35:00'
    start1, end1 = '2000-01-01 22:05:00', '2001-01-01 22:40:00'
    start2, end2 = '2000-01-01 22:10:00', '2001-01-01 22:45:00'
    start3, end3 = '2000-01-01 22:15:00', '2001-01-01 22:30:00'
    rng = pd.date_range(start, end, freq='1min')
    ts = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, 2)), columns=['temp', 'humidity'], index=rng)
    rng = pd.date_range(start1, end1, freq='1min')
    ts1 = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, 2)), columns=['temp', 'humidity'], index=rng)
    rng = pd.date_range(start2, end2, freq='1min')
    ts2 = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, 2)), columns=['temp', 'humidity'], index=rng)
    rng = pd.date_range(start3, end3, freq='1min')
    ts3 = pd.DataFrame(np.random.randint(0, 20, size=(rng.size, 2)), columns=['temp', 'humidity'], index=rng)
    tseries.append(ts1)
    tseries.append(ts2)
    tseries.append(ts3)
    tseries.append(ts)
    synched_series = synch_series(tseries, 2, "T")
    print(tseries[0])


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    test1()
    test2()
    test3()
    fredtest()
    debug_resample()
