name = tesp
time_delta = 5m
broker = tcp://localhost:5570
values
    LMP7
        topic = pypower/LMP_B7
        default = 0
    vpos7
        topic = pypower/three_phase_voltage_B7
        default = 0
    clear_price
        topic = auction_Market_1/clear_price
        default = 0
    distribution_load
        topic = gridlabdSimulator1/distribution_load
        default = 0
    power_A
        topic = eplus_json/power_A
        default = 0
    cooling_setpoint_delta
        topic = eplus_json/cooling_setpoint_delta
        default = 0
    heating_setpoint_delta
        topic = eplus_json/heating_setpoint_delta
        default = 0
    electric_demand_power
        topic = eplus/WHOLE BUILDING FACILITY TOTAL ELECTRIC DEMAND POWER
        default = 0
    controller_cooling_setpoint
        topic = controller_F1_house_B22_thermostat_controller/cooling_setpoint
        default = 0
    house_air_temperature
        topic = gridlabdSimulator1/F1_house_B22/air_temperature
        default = 0
    house_power_state
        topic = gridlabdSimulator1/F1_house_B22/power_state
        default = 0
    house_hvac_load
        topic = gridlabdSimulator1/F1_house_B22/hvac_load
        default = 0

