# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: pv_dsot.py
"""Class that controls the Photovoltaic Solar agents
for now, it only provides day ahead forecast for each agent.
It does not participate in bidding
"""
import numpy as np

from datetime import datetime, timedelta


class PVDSOT:
    """ This agent manages the PV solar

    Args:
        pv_dict (diction): dictionary to populate attributes
        inv_properties (diction):
        key (str): name of this agent
        model_diag_level (int): Specific level for logging errors; set it to 11
        sim_time (str): Current time in the simulation; should be human-readable

    Attributes:
        Initialize from Args
        name (str): name of this agent
        participating (bool): participating from pv_dict dictionary
        rating (float): rating from pv_dict dictionary
        scaling_factor (float): scaling_factor from pv_dict dictionary
        slider (float): slider_setting from pv_dict dictionary
        windowLength (int): 48 always for now
        TIME (list): range(0, self.windowLength)
    """

    def __init__(self, pv_dict, inv_properties, key, model_diag_level, sim_time):
        # Initializes the class
        self.name = key
        self.participating = pv_dict['participating']
        self.rating = pv_dict['rating']
        self.scaling_factor = pv_dict['scaling_factor']
        self.slider = pv_dict['slider_setting']

        self.windowLength = 48
        self.TIME = range(0, self.windowLength)

    def scale_pv_forecast(self, solar_f):
        # scaling factor multiplication gives in watts, need to convert to kW
        return (np.array(solar_f)*self.scaling_factor/1000).tolist()


def test():
    """ Makes a single pv agent and run DA
    """
    import pandas as pd
    from tesp_support.api.data import tesp_test

    a = pd.read_csv(tesp_test + 'dsot/pv_hourly_forecast_power.csv', index_col=0, header=None)
    a.index = pd.to_datetime(a.index)
    sim_time = 7200
    a.loc[pd.date_range(sim_time + timedelta(0, 60), periods=48, freq='H')][1]

    agent = {"evName": "R5_12_47_2_tn_1_ev_1",
             "meterName": "R5_12_47_2_tn_1_mtr_1",
             "work_charging": "FALSE",
             "initial_soc": "100",
             "max_charge": 3300.0,
             "daily_miles": 40.527,
             "arrival_work": 1400,
             "arrival_home": 1840,
             "work_duration": 15000.0,
             "home_duration": 67800.0,
             "miles_per_kwh": 3.333,
             "range_miles": 151.0,
             "efficiency": 0.9,
             "slider_setting": 0.5119,
             "profit_margin": 12.321,
             "participating": True
             }

    BID = [[-5.0, 0.42129778616103297],
           [-0.39676675, 0.30192681471917215],
           [-0.39676675, 0.17229206883635942],
           [5.0, 0.03234319929066909]]

    # ## Uncomment for testing logging functionality.
    # ## Supply these values when using the pv agent in the simulation.
    start_time = '2016-08-12 13:59:00'
    time_format = '%Y-%m-%d %H:%M:%S'
    sim_time = datetime.strptime(start_time, time_format)
    # make object; add model_diag_level and sim_time
    obj1 = PVDSOT(agent, agent, 'test', 11, sim_time)
    quant = obj1.get_pv_forecast(sim_time)


if __name__ == "__main__":
    test()
