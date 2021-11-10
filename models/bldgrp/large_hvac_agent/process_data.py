import numpy as np
import pandas as pd


def process_mass_flow_data_for_regression(mass_flow,
                                          zone_temp,
                                          zone_temp_sp,
                                          outside_temp,
                                          internal_load,
                                          hvac_availability):

    y = pd.DataFrame(mass_flow.values[1:])
    y.columns = ['y']

    x1 = pd.DataFrame(zone_temp[:-1].values - zone_temp_sp[1:].values)
    x1.columns = ['x1']

    x2 = pd.DataFrame(outside_temp[1:].values)
    x2.columns = ['x2']

    x3 = pd.DataFrame(internal_load[1:].values)
    x3.columns = ['x3']

    x4 = pd.DataFrame(hvac_availability[:-1].values)
    x4.columns = ['x4']

    return y, x1, x2, x3, x4
    # return y, x1, x2, x3


def process_bicubic_Twetbulb(sim_data_Temperature_WetBulb, sim_data_Temperature_Outside, sim_data_Air_Humidity_Ratio,
                             ttl):

    x1 = pd.DataFrame(sim_data_Temperature_Outside.values)  # Outdoor Temperature
    x1.columns = ['x1']
    x2 = pd.DataFrame(sim_data_Air_Humidity_Ratio.values)  # Air humidity Ratio
    x2.columns = ['x2']

    x1_sq = pd.DataFrame(x1.values * x1.values)
    x1_sq.columns = ['x1_sq']

    x1_cube = pd.DataFrame(
        x1.values * x1.values * x1.values)
    x1_cube.columns = ['x1_cube']

    x2_sq = pd.DataFrame(x2.values * x2.values)
    x2_sq.columns = ['x2_sq']

    x2_cube = pd.DataFrame(
        x2.values * x2.values * x2.values)
    x2_cube.columns = ['x2_cube']

    x1_sq_x2 = pd.DataFrame(x1.values * x1.values * x2.values)
    x1_sq_x2.columns = ['x1_sq_x2']

    x2_sq_x1 = pd.DataFrame(x1.values * x2.values * x2.values)
    x2_sq_x1.columns = ['x2_sq_x1']

    x1_x2 = pd.DataFrame(x1.values * x2.values)
    x1_x2.columns = ['x1_x2']

    df = pd.concat((x1, x2, x1_sq, x2_sq, x1_x2, x1_sq_x2, x2_sq_x1, x1_cube, x2_cube), axis=1)

    return df


def process_vav_floor_data_for_regression(vav_power, mass_flow_floor_VAV):
 #   y = pd.DataFrame(vav_power[1:].values)
    y = pd.DataFrame(vav_power.values)
    y.columns = ['y']
    x1 = pd.DataFrame(mass_flow_floor_VAV)
    x1.columns = ['x1']
    x1_sq = pd.DataFrame(x1.values * x1.values)
    x1_sq.columns = ['x1_sq']
    x1_cube = pd.DataFrame(x1.values * x1.values * x1.values)
    x1_cube.columns = ['x1_cube']
    df = pd.concat((x1, x1_sq, x1_cube), axis=1)
    return y, df


def process_basement_power_for_regression(CAV_Power_Basement, Internal_Load_Basement, ZoneTemperature_Basement):
    # y = pd.DataFrame(CAV_Power_Basement[1:].values)
    # y.columns = ['y']
    # x1 = pd.DataFrame(Internal_Load_Basement[1:].values)
    # x1.columns = ['x1']
    # x2 = pd.DataFrame(ZoneTemperature_Basement[:-1].values)
    y = pd.DataFrame(CAV_Power_Basement.values)
    y.columns = ['y']
    x1 = pd.DataFrame(Internal_Load_Basement.values)
    x1.columns = ['x1']
    x2 = pd.DataFrame(ZoneTemperature_Basement.values)
    x2.columns = ['x2']
    x1_sq = pd.DataFrame(x1.values * x1.values)
    x1_sq.columns = ['x1_sq']
    x1_cube = pd.DataFrame(
    x1.values * x1.values * x1.values)
    x1_cube.columns = ['x1_cube']

    x2_sq = pd.DataFrame(x2.values * x2.values)
    x2_sq.columns = ['x2_sq']

    x2_cube = pd.DataFrame(
    x2.values * x2.values * x2.values)
    x2_cube.columns = ['x2_cube']

    x1_sq_x2 = pd.DataFrame(x1.values * x1.values * x2.values)
    x1_sq_x2.columns = ['x1_sq_x2']

    x2_sq_x1 = pd.DataFrame(x1.values * x2.values * x2.values)
    x2_sq_x1.columns = ['x2_sq_x1']

    x1_x2 = pd.DataFrame(x1.values * x2.values)
    x1_x2.columns = ['x1_x2']

    df = pd.concat((x1, x2, x1_sq, x2_sq, x1_x2, x1_sq_x2, x2_sq_x1, x1_cube, x2_cube), axis=1)

    return y, df


def process_evaporator_load_chiller_for_regression(sim_data_Evaporator_Load_Chiller1, approx_CAV_VAV_Fan_Power,
                                                   approx_Twet_bulb):
    # y = pd.DataFrame(sim_data_Evaporator_Load_Chiller1[1:].values)
    y = pd.DataFrame(sim_data_Evaporator_Load_Chiller1.values)
    y.columns = ['y']
    x1 = pd.DataFrame(approx_CAV_VAV_Fan_Power.values)
    x1.columns = ['x1']
    # x2 = pd.DataFrame(approx_Twet_bulb[1:].values)
    x2 = pd.DataFrame(approx_Twet_bulb.values)
    x2.columns = ['x2']
    x1_sq = pd.DataFrame(x1.values * x1.values)
    x1_sq.columns = ['x1_sq']
    x1_cube = pd.DataFrame(
        x1.values * x1.values * x1.values)
    x1_cube.columns = ['x1_cube']

    x2_sq = pd.DataFrame(x2.values * x2.values)
    x2_sq.columns = ['x2_sq']

    x2_cube = pd.DataFrame(
        x2.values * x2.values * x2.values)
    x2_cube.columns = ['x2_cube']

    x1_sq_x2 = pd.DataFrame(x1.values * x1.values * x2.values)
    x1_sq_x2.columns = ['x1_sq_x2']

    x2_sq_x1 = pd.DataFrame(x1.values * x2.values * x2.values)
    x2_sq_x1.columns = ['x2_sq_x1']

    x1_x2 = pd.DataFrame(x1.values * x2.values)
    x1_x2.columns = ['x1_x2']

    df = pd.concat((x1, x2, x1_sq, x2_sq, x1_x2, x1_sq_x2, x2_sq_x1, x1_cube, x2_cube), axis=1)

    return y, df


def process_condenser1_leaving_temp(Condenser_Leaving_Temperature_Chiller1, approx_Evaporator_Load_Chiller1,
                                   approx_Twet_bulb):
    # y = pd.DataFrame(Condenser_Leaving_Temperature_Chiller1[1:].values)
    y = pd.DataFrame(Condenser_Leaving_Temperature_Chiller1.values)
    y.columns = ['y']
    # x1_temp = approx_Evaporator_Load_Chiller1/approx_Evaporator_Load_Chiller1.max(axis=0)
    x1 = pd.DataFrame(approx_Evaporator_Load_Chiller1.values)
    x1.columns = ['x1']
    # x2_temp = approx_Twet_bulb/approx_Twet_bulb.max(axis=0)
    # x2 = pd.DataFrame(approx_Twet_bulb[1:].values)
    x2 = pd.DataFrame(approx_Twet_bulb.values)
    x2.columns = ['x2']
    x1_sq = pd.DataFrame(x1.values * x1.values)
    x1_sq.columns = ['x1_sq']
    x1_cube = pd.DataFrame(
        x1.values * x1.values * x1.values)
    x1_cube.columns = ['x1_cube']

    x2_sq = pd.DataFrame(x2.values * x2.values)
    x2_sq.columns = ['x2_sq']

    x2_cube = pd.DataFrame(
        x2.values * x2.values * x2.values)
    x2_cube.columns = ['x2_cube']

    x1_sq_x2 = pd.DataFrame(x1.values * x1.values * x2.values)
    x1_sq_x2.columns = ['x1_sq_x2']

    x2_sq_x1 = pd.DataFrame(x1.values * x2.values * x2.values)
    x2_sq_x1.columns = ['x2_sq_x1']

    x1_x2 = pd.DataFrame(x1.values * x2.values)
    x1_x2.columns = ['x1_x2']

    df = pd.concat((x1, x2, x1_sq, x2_sq, x1_x2, x1_sq_x2, x2_sq_x1, x1_cube, x2_cube), axis=1)

    return y, df

def process_condenser2_leaving_temp(Condenser_Leaving_Temperature_Chiller2, approx_Evaporator_Load_Chiller2,
                                   approx_Twet_bulb):
    # y = pd.DataFrame(Condenser_Leaving_Temperature_Chiller2[1:].values)
    y = pd.DataFrame(Condenser_Leaving_Temperature_Chiller2.values)
    y.columns = ['y']
    x1 = pd.DataFrame(approx_Evaporator_Load_Chiller2.values)
    x1.columns = ['x1']
    x2 = pd.DataFrame(approx_Twet_bulb.values)
#    x2 = pd.DataFrame(approx_Twet_bulb[1:].values)
    x2.columns = ['x2']
    x1_sq = pd.DataFrame(x1.values * x1.values)
    x1_sq.columns = ['x1_sq']
    x1_cube = pd.DataFrame(
        x1.values * x1.values * x1.values)
    x1_cube.columns = ['x1_cube']

    x2_sq = pd.DataFrame(x2.values * x2.values)
    x2_sq.columns = ['x2_sq']

    x2_cube = pd.DataFrame(
        x2.values * x2.values * x2.values)
    x2_cube.columns = ['x2_cube']

    x1_sq_x2 = pd.DataFrame(x1.values * x1.values * x2.values)
    x1_sq_x2.columns = ['x1_sq_x2']

    x2_sq_x1 = pd.DataFrame(x1.values * x2.values * x2.values)
    x2_sq_x1.columns = ['x2_sq_x1']

    x1_x2 = pd.DataFrame(x1.values * x2.values)
    x1_x2.columns = ['x1_x2']

    df = pd.concat((x1, x2, x1_sq, x2_sq, x1_x2, x1_sq_x2, x2_sq_x1, x1_cube, x2_cube), axis=1)

    return y, df

def process_cooling_tower_fan(Fan_Power_CoolTower1, approx_Chiller1_Power, approx_Twet_bulb):
    # y = pd.DataFrame(Fan_Power_CoolTower1[1:].values)
    y = pd.DataFrame(Fan_Power_CoolTower1.values)
    y.columns = ['y']
    x1 = pd.DataFrame(approx_Chiller1_Power.values)
    x1.columns = ['x1']
    # x2 = pd.DataFrame(approx_Twet_bulb[1:].values)
    x2 = pd.DataFrame(approx_Twet_bulb.values)
    x2.columns = ['x2']
    x1_sq = pd.DataFrame(x1.values * x1.values)
    x1_sq.columns = ['x1_sq']
    x1_cube = pd.DataFrame(
        x1.values * x1.values * x1.values)
    x1_cube.columns = ['x1_cube']

    x2_sq = pd.DataFrame(x2.values * x2.values)
    x2_sq.columns = ['x2_sq']

    x2_cube = pd.DataFrame(
        x2.values * x2.values * x2.values)
    x2_cube.columns = ['x2_cube']

    x1_sq_x2 = pd.DataFrame(x1.values * x1.values * x2.values)
    x1_sq_x2.columns = ['x1_sq_x2']

    x2_sq_x1 = pd.DataFrame(x1.values * x2.values * x2.values)
    x2_sq_x1.columns = ['x2_sq_x1']

    x1_x2 = pd.DataFrame(x1.values * x2.values)
    x1_x2.columns = ['x1_x2']

    df = pd.concat((x1, x2, x1_sq, x2_sq, x1_x2, x1_sq_x2, x2_sq_x1, x1_cube, x2_cube), axis=1)

    return y, df

def process_pump_power(Pump_Power_Primary, approx_Chiller1_Power, approx_Twet_bulb):
    # y = pd.DataFrame(Pump_Power_Primary[1:].values)
    y = pd.DataFrame(Pump_Power_Primary.values)
    y.columns = ['y']
    x1 = pd.DataFrame(approx_Chiller1_Power.values)
    x1.columns = ['x1']
    # x2 = pd.DataFrame(approx_Twet_bulb[1:].values)
    x2 = pd.DataFrame(approx_Twet_bulb.values)
    x2.columns = ['x2']
    x1_sq = pd.DataFrame(x1.values * x1.values)
    x1_sq.columns = ['x1_sq']
    x1_cube = pd.DataFrame(
        x1.values * x1.values * x1.values)
    x1_cube.columns = ['x1_cube']

    x2_sq = pd.DataFrame(x2.values * x2.values)
    x2_sq.columns = ['x2_sq']

    x2_cube = pd.DataFrame(
        x2.values * x2.values * x2.values)
    x2_cube.columns = ['x2_cube']

    x1_sq_x2 = pd.DataFrame(x1.values * x1.values * x2.values)
    x1_sq_x2.columns = ['x1_sq_x2']

    x2_sq_x1 = pd.DataFrame(x1.values * x2.values * x2.values)
    x2_sq_x1.columns = ['x2_sq_x1']

    x1_x2 = pd.DataFrame(x1.values * x2.values)
    x1_x2.columns = ['x1_x2']

    df = pd.concat((x1, x2, x1_sq, x2_sq, x1_x2, x1_sq_x2, x2_sq_x1, x1_cube, x2_cube), axis=1)

    return y, df
