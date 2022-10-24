# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: pv_dsot.py #
"""Class that controls the Photovoltaic Solar agents
for now, it only provides day ahead forecast for each agent.
It does not participate in bidding
"""
import numpy as np

from datetime import datetime, timedelta


class PVDSOT:
    """This agent manages the PV solar

    Args:
        TODO: update inputs for this agent

        model_diag_level (int): Specific level for logging errors; set it to 11
        sim_time (str): Current time in the simulation; should be human-readable

    Attributes: #TODO: update attributes for this agent
        #initialize from Args:
        name (str): name of this agent



    """

    def __init__(self, pv_dict, inv_properties, key, model_diag_level, sim_time):  # TODO: update inputs for class
        """Initializes the class
        """
        # TODO: update attributes of class
        # initialize from Args:
        self.name = key
        self.participating = pv_dict['participating']
        self.rating = pv_dict['rating']
        self.scaling_factor = pv_dict['scaling_factor']
        self.slider = pv_dict['slider_setting']

        self.windowLength = 48
        self.TIME = range(0, self.windowLength)

    def scale_pv_forecast(self, solar_f):
        # scaling factor multiplication gives in watts..need to convert to kW
        return (np.array(solar_f)*self.scaling_factor/1000).tolist()


if __name__ == "__main__":
    """Testing
    
    Makes a single battery agent and run DA 
    """
    import pandas as pd

    a = pd.read_csv('solar/auto_run/solar_pv_power_profiles/8-node_dist_hourly_forecast_power.csv',index_col=0, header=None)
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

    BID = [[-5.0, 0.42129778616103297], [-0.39676675, 0.30192681471917215], [-0.39676675, 0.17229206883635942],
           [5.0, 0.03234319929066909]]

    ### Uncomment for testing logging functionality.
    ### Supply these values when using the battery agent in the simulation.
    start_time = '2016-08-12 13:59:00'
    time_format = '%Y-%m-%d %H:%M:%S'
    sim_time = datetime.strptime(start_time, time_format)
    obj1 = PVDSOT(agent, agent, 'test', 11, sim_time)  # make object; add model_diag_level and sim_time
    quant = obj1.get_pv_forecast(sim_time)



