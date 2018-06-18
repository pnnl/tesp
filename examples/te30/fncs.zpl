name = tesp_monitor
time_delta = 5m
broker = tcp://localhost:5570
values
    vpos7
        topic = pypower/three_phase_voltage_B7
        default = 0
    LMP7
        topic = pypower/LMP_B7
        default = 0
    clear_price
        topic = auction/clear_price
        default = 0
    distribution_load
        topic = gridlabdSimulator1/distribution_load
        default = 0
    power_A
        topic = eplus_json/power_A
        default = 0
    electric_demand_power
        topic = eplus/WHOLE BUILDING FACILITY TOTAL ELECTRIC DEMAND POWER
        default = 0

