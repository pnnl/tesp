# Copyright (C) 2021-2024 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
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


def _test():
    """ Makes a single pv agent and run DA
    """
    from tesp_support.dsot.forecasting import Forecasting

    forecast_obj = Forecasting(5150,  { "correct": False })

    agent = {
        "pvName": "R4_12_47_1_tn_12_isol_1",
        "meterName": "R4_12_47_1_tn_12_mtr_1",
        "rating": 3500.0,
        "scaling_factor": 0.41427515570000395,
        "slider_setting": 0.4529,
        "participating": False
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
    solar_f = forecast_obj.get_solar_forecast(sim_time, 1)
    quant = obj1.scale_pv_forecast(solar_f)
    print(quant)


if __name__ == "__main__":
    _test()
