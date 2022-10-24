# Copyright (C) 2018-2022 Battelle Memorial Institute
# file: feederGenerator.py
"""Replaces ZIP loads with houses, and optional storage and solar generation.

As this module populates the feeder backbone with houses and DER, it uses
the Networkx package to perform graph-based capacity analysis, upgrading
fuses, transformers and lines to serve the expected load. Transformers have
a margin of 20% to avoid overloads, while fuses have a margin of 150% to
avoid overloads. These can be changed by editing tables and variables in the 
source file.

There are two kinds of house populating methods implemented:

* :Feeders with Service Transformers: This case applies to the full PNNL taxonomy feeders. Do not specify the *taxchoice* argument to *populate_feeder*.
   Each service transformer receiving houses will have a short service drop and a small number of houses attached.

* :Feeders without Service Transformers: This applies to the reduced-order ERCOT feeders. To invoke this mode, specify the *taxchoice* argument to *populate_feeder*.
   Each primary load to receive houses will have a large service transformer, large service drop and large number of houses attached.

References:
    `GridAPPS-D Feeder Models <https://github.com/GRIDAPPSD/Powergrid-Models>`

Public Functions:
    :populate_feeder: processes one GridLAB-D input file

Todo:
    * Verify the level zero mobile home thermal integrity properties; these were copied from the MATLAB feeder generator

"""
import json
import os.path
import re
import sys
import networkx as nx
import numpy as np
from math import ceil
from math import floor
from math import sqrt

from .data import feeders_path, weather_path
from .helpers import parse_kva, gld_strict_name

forERCOT = False
port = 5570
case_name = 'Tesp'
name_prefix = ''
work_path = './Dummy/'
dso_substation_bus_id = 1
base_feeder_name = ''
solar_path = ''
solar_P_player = ''
solar_Q_player = ''

transmissionVoltage = 138000.0
transmissionXfmrMVAbase = 12.0
transmissionXfmrXpct = 8.0
transmissionXfmrRpct = 1.0
transmissionXfmrNLLpct = 0.4
transmissionXfmrImagpct = 1.0

max208kva = 100.0
xfmrMargin = 1.20
fuseMargin = 2.50

starttime = '2010-06-01 00:00:00'
endtime = '2010-06-03 00:00:00'
timestep = 15
timezone = ''
metrics_interval = 300
metrics_interim = 7200
metrics_type = "json"
metrics = [
    "house",
    "waterheater",
    "meter",
    "line",
    "transformer",
    "capacitor",
    "inverter",
    "regulator",
    "substation"
]
Eplus_Bus = ''
Eplus_Volts = 480.0
Eplus_kVA = 150.0

electric_cooling_percentage = 0.0  # if not provided in JSON config, use a regional default
solar_percentage = 0.2
storage_percentage = 0.5
water_heater_percentage = 0.0  # if not provided in JSON config, use a regional default
water_heater_participation = 0.5
solar_inv_mode = 'CONSTANT_PF'

latitude = 30.0
longitude = -110.0
weather_name = 'localWeather'
tz_meridian = 0.0
altitude = 0.0

rated_power = 5000
max_charge_rate = 5000
max_discharge_rate = 5000
inverter_efficiency = 0.97
battery_capacity = 13500
round_trip_efficiency = 0.86


def write_solar_inv_settings(op):
    """Writes volt-var and volt-watt settings for solar inverters

    Args:
        op (file): an open GridLAB-D input file
    """
    print('    four_quadrant_control_mode ${' + name_prefix + 'INVERTER_MODE};', file=op)
    print('    V_base ${INV_VBASE};', file=op)
    print('    V1 ${INV_V1};', file=op)
    print('    Q1 ${INV_Q1};', file=op)
    print('    V2 ${INV_V2};', file=op)
    print('    Q2 ${INV_Q2};', file=op)
    print('    V3 ${INV_V3};', file=op)
    print('    Q3 ${INV_Q3};', file=op)
    print('    V4 ${INV_V4};', file=op)
    print('    Q4 ${INV_Q4};', file=op)
    print('    V_In ${INV_VIN};', file=op)
    print('    I_In ${INV_IIN};', file=op)
    print('    volt_var_control_lockout ${INV_VVLOCKOUT};', file=op)
    print('    VW_V1 ${INV_VW_V1};', file=op)
    print('    VW_V2 ${INV_VW_V2};', file=op)
    print('    VW_P1 ${INV_VW_P1};', file=op)
    print('    VW_P2 ${INV_VW_P2};', file=op)


storage_inv_mode = 'LOAD_FOLLOWING'
weather_file = 'AZ-Tucson_International_Ap.tmy3'
bill_mode = 'UNIFORM'
kwh_price = 0.1243
monthly_fee = 5.00
tier1_energy = 0.0
tier1_price = 0.0
tier2_energy = 0.0
tier2_price = 0.0
tier3_energy = 0.0
tier3_price = 0.0


def write_tariff(op):
    """Writes tariff information to billing meters

    Args:
        op (file): an open GridLAB-D input file
    """
    print('  bill_mode', bill_mode + ';', file=op)
    print('  price', '{:.4f}'.format(kwh_price) + ';', file=op)
    print('  monthly_fee', '{:.2f}'.format(monthly_fee) + ';', file=op)
    print('  bill_day 1;', file=op)
    if 'TIERED' in bill_mode:
        if tier1_energy > 0.0:
            print('  first_tier_energy', '{:.1f}'.format(tier1_energy) + ';', file=op)
            print('  first_tier_price', '{:.6f}'.format(tier1_price) + ';', file=op)
        if tier2_energy > 0.0:
            print('  second_tier_energy', '{:.1f}'.format(tier2_energy) + ';', file=op)
            print('  second_tier_price', '{:.6f}'.format(tier2_price) + ';', file=op)
        if tier3_energy > 0.0:
            print('  third_tier_energy', '{:.1f}'.format(tier3_energy) + ';', file=op)
            print('  third_tier_price', '{:.6f}'.format(tier3_price) + ';', file=op)


inverter_undersizing = 1.0
array_efficiency = 0.2
rated_insolation = 1000.0

# techdata dict:[heatgain fraction, Zpf, Ipf, Ppf, Z, I, P]
techdata = [0.9, 1.0, 1.0, 1.0, 0.2, 0.4, 0.4]

tiName = ['VERY_LITTLE',
          'LITTLE',
          'BELOW_NORMAL',
          'NORMAL',
          'ABOVE_NORMAL',
          'GOOD',
          'VERY_GOOD']
bldgTypeName = ['SINGLE_FAMILY', 'MULTI_FAMILY', 'MOBILE_HOME', 'SMALL_COMMERCIAL']
rgnName = ['West_Coast',
           'North_Central/Northeast',
           'Southwest',
           'Southeast_Central',
           'Southeast_Coast']
rgnTimeZone = ['PST+8PDT', 'EST+5EDT', 'MST+7MDT', 'CST+6CDT', 'EST+5EDT']
rgnWeather = ['CA-San_francisco', 'OH-Cleveland', 'AZ-Phoenix', 'TN-Nashville', 'FL-Miami']

# fraction of thermal integrity levels in each region
# index 0 is the region number (minus 1)
# index 1 is the home type:
#   0 = single family homes
#   1 = apartments
#   2 = mobile homes
# index 2 is the thermal integrity level (minus 1) corresponding to age of home
#       1:pre-1940, 2:1940-1949, 3:1950-1959, 4:1960-1969, 5:1970-1979, 6:1980-1989, 7:1990-2005
#       1:pre-1960, 2:1960-1989, 3:1990-2005
#       1:pre-1960, 2:1960-1989, 3:1990-2005
rgnThermalPct = [[[0.0805, 0.0724, 0.1090, 0.0867, 0.1384, 0.1264, 0.1297],  # Region 1, SF
                  [0.0356, 0.1223, 0.0256],  # Apt
                  [0.0000, 0.0554, 0.0181]],  # MH
                 [[0.1574, 0.0702, 0.1290, 0.0971, 0.0941, 0.0744, 0.1532],
                  [0.0481, 0.0887, 0.0303],
                  [0.0000, 0.0372, 0.0202]],
                 [[0.0448, 0.0252, 0.0883, 0.0843, 0.1185, 0.1315, 0.2411],
                  [0.0198, 0.1159, 0.0478],
                  [0.0000, 0.0524, 0.0302]],
                 [[0.0526, 0.0337, 0.0806, 0.0827, 0.1081, 0.1249, 0.2539],
                  [0.0217, 0.1091, 0.0502],
                  [0.0000, 0.0491, 0.0333]],
                 [[0.0526, 0.0337, 0.0806, 0.0827, 0.1081, 0.1249, 0.2539],
                  [0.0217, 0.1091, 0.0502],
                  [0.0000, 0.0491, 0.0333]]]


def selectResidentialBuilding(rgnTable, prob):
    """Selects the building with region and probability

    Args:
        rgnTable:
        prob:
    """
    total = 0
    for row in range(len(rgnTable)):
        for col in range(len(rgnTable[row])):
            total += rgnTable[row][col]
            if total >= prob:
                return row, col
    row = len(rgnTable) - 1
    col = len(rgnTable[row]) - 1
    return row, col


rgnFloorArea = [[2209, 820, 1054],  # single family, apartment, mobile home
                [2951, 798, 1035],
                [2370, 764, 1093],
                [2655, 901, 1069],
                [2655, 901, 1069]]

rgnOneStory = [0.6887, 0.5210, 0.7745, 0.7043, 0.7043]

rgnPenGasHeat = [0.7051, 0.8927, 0.6723, 0.4425, 0.4425]
rgnPenHeatPump = [0.0321, 0.0177, 0.0559, 0.1983, 0.1983]
rgnPenResHeat = [0.2628, 0.0896, 0.2718, 0.3592, 0.3592]
rgnPenElecCool = [0.4348, 0.7528, 0.5259, 0.9673, 0.9673]
rgnOversizeFactor = [0.1, 0.2, 0.2, 0.3, 0.3]

# Average heating and cooling set points
# index 0 for SF, Apt, MH
# index 1 for histogram bins
#  [histogram prob, nighttime average difference (+ indicates nightime is cooler), high bin value, low bin value]
bldgCoolingSetpoints = [[[0.098, 0.96, 69, 65],  # single-family
                         [0.140, 0.96, 70, 70],
                         [0.166, 0.96, 73, 71],
                         [0.306, 0.96, 76, 74],
                         [0.206, 0.96, 79, 77],
                         [0.084, 0.96, 85, 80]],
                        [[0.155, 0.49, 69, 65],  # apartment
                         [0.207, 0.49, 70, 70],
                         [0.103, 0.49, 73, 71],
                         [0.310, 0.49, 76, 74],
                         [0.155, 0.49, 79, 77],
                         [0.069, 0.49, 85, 80]],
                        [[0.138, 0.97, 69, 65],  # mobile home
                         [0.172, 0.97, 70, 70],
                         [0.172, 0.97, 73, 71],
                         [0.276, 0.97, 76, 74],
                         [0.138, 0.97, 79, 77],
                         [0.103, 0.97, 85, 80]]]

bldgHeatingSetpoints = [[[0.141, 0.80, 63, 59],  # single-family
                         [0.204, 0.80, 66, 64],
                         [0.231, 0.80, 69, 67],
                         [0.163, 0.80, 70, 70],
                         [0.120, 0.80, 73, 71],
                         [0.141, 0.80, 79, 74]],
                        [[0.085, 0.20, 63, 59],  # apartment
                         [0.132, 0.20, 66, 64],
                         [0.147, 0.20, 69, 67],
                         [0.279, 0.20, 70, 70],
                         [0.109, 0.20, 73, 71],
                         [0.248, 0.20, 79, 74]],
                        [[0.129, 0.88, 63, 59],  # mobile home
                         [0.177, 0.88, 66, 64],
                         [0.161, 0.88, 69, 67],
                         [0.274, 0.88, 70, 70],
                         [0.081, 0.88, 73, 71],
                         [0.177, 0.88, 79, 74]]]

# we pick the cooling setpoint bin first, and it must be higher than the heating setpoint bin
# given a cooling bin selection, we should be able to figure out conditional probabilities on the heating bin
allowedHeatingBins = [1, 3, 4, 5, 6, 6]

# index 0 is the building type
# index 1 is the cooling bin selection
# [conditional heating bin probabilities]
conditionalHeatingBinProb = [[[1.000, 0.000, 0.000, 0.000, 0.000, 0.000],  # SF, cooling bin 0
                              [0.333, 0.333, 0.333, 0.000, 0.000, 0.000],
                              [0.250, 0.250, 0.250, 0.250, 0.000, 0.000],
                              [0.200, 0.200, 0.200, 0.200, 0.200, 0.000],
                              [0.167, 0.167, 0.167, 0.167, 0.167, 0.167],
                              [0.167, 0.167, 0.167, 0.167, 0.167, 0.167]],
                             [[1.000, 0.000, 0.000, 0.000, 0.000, 0.000],  # APT, given cooling bin 0
                              [0.333, 0.333, 0.333, 0.000, 0.000, 0.000],
                              [0.250, 0.250, 0.250, 0.250, 0.000, 0.000],
                              [0.200, 0.200, 0.200, 0.200, 0.200, 0.000],
                              [0.167, 0.167, 0.167, 0.167, 0.167, 0.167],
                              [0.167, 0.167, 0.167, 0.167, 0.167, 0.167]],
                             [[1.000, 0.000, 0.000, 0.000, 0.000, 0.000],  # MH, given cooling bin 0
                              [0.333, 0.333, 0.333, 0.000, 0.000, 0.000],
                              [0.250, 0.250, 0.250, 0.250, 0.000, 0.000],
                              [0.200, 0.200, 0.200, 0.200, 0.200, 0.000],
                              [0.167, 0.167, 0.167, 0.167, 0.167, 0.167],
                              [0.167, 0.167, 0.167, 0.167, 0.167, 0.167]]]

cooling_bins = [[0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0]]

heating_bins = [[0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0]]


def selectSetpointBins(bldg, rand):
    """Randomly choose a histogram row from the cooling and heating setpoints

    The random number for the heating and cooling set points row is generated internally.

    Args:
        bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
        rand (float): random number [0..1] for the cooling setpoint row
    """
    cBin = hBin = 0
    total = 0
    tbl = bldgCoolingSetpoints[bldg]
    for row in range(len(tbl)):
        total += tbl[row][0]
        if total >= rand:
            cBin = row
            break
    tbl = conditionalHeatingBinProb[bldg][cBin]
    rand_heat = np.random.uniform(0, 1)
    total = 0
    for col in range(len(tbl)):
        total += tbl[col]
        if total >= rand_heat:
            hBin = col
            break
    cooling_bins[bldg][cBin] -= 1
    heating_bins[bldg][hBin] -= 1
    return bldgCoolingSetpoints[bldg][cBin], bldgHeatingSetpoints[bldg][hBin]


def checkResidentialBuildingTable():
    """Verify that the regional building parameter histograms sum to one
    """
    for tbl in range(len(rgnThermalPct)):
        total = 0
        for row in range(len(rgnThermalPct[tbl])):
            for col in range(len(rgnThermalPct[tbl][row])):
                total += rgnThermalPct[tbl][row][col]
        print(rgnName[tbl], 'rgnThermalPct sums to', '{:.4f}'.format(total))
    for tbl in range(len(bldgCoolingSetpoints)):
        total = 0
        for row in range(len(bldgCoolingSetpoints[tbl])):
            total += bldgCoolingSetpoints[tbl][row][0]
        print('bldgCoolingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
    for tbl in range(len(bldgHeatingSetpoints)):
        total = 0
        for row in range(len(bldgHeatingSetpoints[tbl])):
            total += bldgHeatingSetpoints[tbl][row][0]
        print('bldgHeatingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
    for bldg in range(3):
        binZeroReserve = bldgCoolingSetpoints[bldg][0][0]
        binZeroMargin = bldgHeatingSetpoints[bldg][0][0] - binZeroReserve
        if binZeroMargin < 0.0:
            binZeroMargin = 0.0
        #        print(bldg, binZeroReserve, binZeroMargin)
        for cBin in range(1, 6):
            denom = binZeroMargin
            for hBin in range(1, allowedHeatingBins[cBin]):
                denom += bldgHeatingSetpoints[bldg][hBin][0]
            conditionalHeatingBinProb[bldg][cBin][0] = binZeroMargin / denom
            for hBin in range(1, allowedHeatingBins[cBin]):
                conditionalHeatingBinProb[bldg][cBin][hBin] = bldgHeatingSetpoints[bldg][hBin][0] / denom
    # print('conditionalHeatingBinProb', conditionalHeatingBinProb)


rgnPenPoolPump = [0.0904, 0.0591, 0.0818, 0.0657, 0.0657]

rgnPenElecWH = [0.7455, 0.7485, 0.6520, 0.3572, 0.3572]
# index 0 is the region (minus one)
# index 0 is <=30 gal, 31-49 gal, >= 50gal
rgnWHSize = [[0.0000, 0.3333, 0.6667],
             [0.1459, 0.5836, 0.2706],
             [0.2072, 0.5135, 0.2793],
             [0.2259, 0.5267, 0.2475],
             [0.2259, 0.5267, 0.2475]]

coolingScheduleNumber = 8
heatingScheduleNumber = 6
waterHeaterScheduleNumber = 6

# these are in seconds
commercial_skew_max = 5400
commercial_skew_std = 1800
residential_skew_max = 8100
residential_skew_std = 2700


def randomize_skew(value, skew_max):
    sk = value * np.random.randn()
    if sk < skew_max:
        sk = skew_max
    elif sk > skew_max:
        sk = skew_max
    return sk


def randomize_commercial_skew():
    return randomize_skew(commercial_skew_std, commercial_skew_max)


def randomize_residential_skew():
    return randomize_skew(residential_skew_std, residential_skew_max)


# commercial configuration data; over_sizing_factor is by region
c_z_pf = 0.97
c_i_pf = 0.97
c_p_pf = 0.97
c_z_frac = 0.2
c_i_frac = 0.4
c_p_frac = 1.0 - c_z_frac - c_i_frac

normalized_loadshape_scalar = 1.0
cooling_COP = 3.0
light_scalar_comm = 1.0
over_sizing_factor = [0.1, 0.2, 0.2, 0.3, 0.3, 0.3]

# Index 0 is the level (minus one)
# Rceiling, Rwall, Rfloor, WindowLayers, WindowGlass,Glazing,WindowFrame,Rdoor,AirInfil,COPhi,COPlo
singleFamilyProperties = [[16.0, 10.0, 10.0, 1, 1, 1, 1, 3, .75, 2.8, 2.4],
                          [19.0, 11.0, 12.0, 2, 1, 1, 1, 3, .75, 3.0, 2.5],
                          [19.0, 14.0, 16.0, 2, 1, 1, 1, 3, .5, 3.2, 2.6],
                          [30.0, 17.0, 19.0, 2, 1, 1, 2, 3, .5, 3.4, 2.8],
                          [34.0, 19.0, 20.0, 2, 1, 1, 2, 3, .5, 3.6, 3.0],
                          [36.0, 22.0, 22.0, 2, 2, 1, 2, 5, 0.25, 3.8, 3.0],
                          [48.0, 28.0, 30.0, 3, 2, 2, 4, 11, 0.25, 4.0, 3.0]]

apartmentProperties = [[13.4, 11.7, 9.4, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
                       [20.3, 11.7, 12.7, 2, 1, 2, 2, 2.7, 0.25, 3.0, 2.0],
                       [28.7, 14.3, 12.7, 2, 2, 3, 4, 6.3, .125, 3.2, 2.1]]

mobileHomeProperties = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # is it really this bad?
                        [13.4, 9.2, 11.7, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
                        [24.1, 11.7, 18.1, 2, 2, 1, 2, 3, .75, 3.5, 2.2]]


def selectThermalProperties(bldgIdx, tiIdx):
    """Retrieve the building thermal properties for a given type and integrity level

    Args:
        bldgIdx (int): 0 for single-family, 1 for apartment, 2 for mobile home
        tiIdx (int): 0..6 for single-family, 0..2 for apartment or mobile home
    """
    if bldgIdx == 0:
        tiProps = singleFamilyProperties[tiIdx]
    elif bldgIdx == 1:
        tiProps = apartmentProperties[tiIdx]
    else:
        tiProps = mobileHomeProperties[tiIdx]
    return tiProps


# kva, %r, %x, %nll, %imag
three_phase = [[30, 1.90, 1.77, 0.79, 4.43],
               [45, 1.75, 2.12, 0.70, 3.94],
               [75, 1.60, 2.42, 0.63, 3.24],
               [112.5, 1.45, 2.85, 0.59, 2.99],
               [150, 1.30, 3.25, 0.54, 2.75],
               [225, 1.30, 3.52, 0.50, 2.50],
               [300, 1.30, 4.83, 0.46, 2.25],
               [500, 1.10, 4.88, 0.45, 2.26],
               [750, 0.97, 5.11, 0.44, 1.89],
               [1000, 0.85, 5.69, 0.43, 1.65],
               [1500, 0.78, 5.70, 0.39, 1.51],
               [2000, 0.72, 5.70, 0.36, 1.39],
               [2500, 0.70, 5.71, 0.35, 1.36],
               [3750, 0.62, 5.72, 0.31, 1.20],
               [5000, 0.55, 5.72, 0.28, 1.07],
               [7500, 0.55, 5.72, 0.28, 1.07],
               [10000, 0.55, 5.72, 0.28, 1.07]]

# kva, %r, %x, %nll, %imag
single_phase = [[5, 2.10, 1.53, 0.90, 3.38],
                [10, 1.90, 1.30, 0.68, 2.92],
                [15, 1.70, 1.47, 0.60, 2.53],
                [25, 1.60, 1.51, 0.52, 1.93],
                [37.5, 1.45, 1.65, 0.47, 1.74],
                [50, 1.30, 1.77, 0.45, 1.54],
                [75, 1.25, 1.69, 0.42, 1.49],
                [100, 1.20, 2.19, 0.40, 1.45],
                [167, 1.15, 2.77, 0.38, 1.66],
                [250, 1.10, 3.85, 0.36, 1.81],
                [333, 1.00, 4.90, 0.34, 1.97],
                [500, 1.00, 4.90, 0.29, 1.98]]

# leave off intermediate fuse sizes 8, 12, 20, 30, 50, 80, 140
# leave off 6, 10, 15, 25 from the smallest sizes, too easily blown
standard_fuses = [40, 65, 100, 200]
standard_reclosers = [280, 400, 560, 630, 800]
standard_breakers = [600, 1200, 2000]


def FindFuseLimit(amps):
    """ Find a Fuse size that's unlikely to melt during power flow

    Will choose a fuse size of 40, 65, 100 or 200 Amps.
    If that's not large enough, will choose a recloser size
    of 280, 400, 560, 630 or 800 Amps. If that's not large
    enough, will choose a breaker size of 600 (skipped), 1200
    or 2000 Amps. If that's not large enough, will choose 999999.

    Args:
        amps (float): the maximum load current expected; some margin will be added

    Returns:
        float: the GridLAB-D fuse size to insert
    """
    amps *= fuseMargin
    for row in standard_fuses:
        if row >= amps:
            return row
    for row in standard_reclosers:
        if row >= amps:
            return row
    for row in standard_breakers:
        if row >= amps:
            return row
    return 999999


def Find1PhaseXfmrKva(kva):
    """Select a standard 1-phase transformer size, with some margin

    Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

    Args:
        kva (float): the minimum transformer rating

    Returns:
        float: the kva size, or 0 if none found
    """
    kva *= xfmrMargin
    for row in single_phase:
        if row[0] >= kva:
            return row[0]
    n500 = int((kva + 250.0) / 500.0)
    return 500.0 * n500


def Find3PhaseXfmrKva(kva):
    """Select a standard 3-phase transformer size, with some margin

    Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500, 
    2000, 2500, 3750, 5000, 7500 or 10000 kVA

    Args:
        kva (float): the minimum transformer rating

    Returns:
        float: the kva size, or 0 if none found
    """
    kva *= xfmrMargin
    for row in three_phase:
        if row[0] >= kva:
            return row[0]
    n10 = int((kva + 5000.0) / 10000.0)
    return 500.0 * n10


def Find1PhaseXfmr(kva):
    """Select a standard 1-phase transformer size, with data

    Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

    Args:
        kva (float): the minimum transformer rating

    Returns:
        [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
    """
    for row in single_phase:
        if row[0] >= kva:
            return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
    return Find1PhaseXfmrKva(kva), 0.01, 0.06, 0.005, 0.01


def Find3PhaseXfmr(kva):
    """Select a standard 3-phase transformer size, with data

    Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500, 
    2000, 2500, 3750, 5000, 7500 or 10000 kVA

    Args:
        kva (float): the minimum transformer rating

    Returns:
        [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
    """
    for row in three_phase:
        if row[0] >= kva:
            return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
    return Find3PhaseXfmrKva(kva), 0.01, 0.08, 0.005, 0.01


# Root Name, VLL, VLN, Avg House, Avg Commercial
taxchoice = [['R1-12.47-1', 12470.0, 7200.0, 4000.0, 20000.0],
             ['R1-12.47-2', 12470.0, 7200.0, 4500.0, 30000.0],
             ['R1-12.47-3', 12470.0, 7200.0, 8000.0, 15000.0],
             ['R1-12.47-4', 12470.0, 7200.0, 4000.0, 15000.0],
             ['R1-25.00-1', 24900.0, 14400.0, 6000.0, 25000.0],
             ['R2-12.47-1', 12470.0, 7200.0, 7000.0, 20000.0],
             ['R2-12.47-2', 12470.0, 7200.0, 15000.0, 25000.0],
             ['R2-12.47-3', 12470.0, 7200.0, 5000.0, 30000.0],
             ['R2-25.00-1', 24900.0, 14400.0, 6000.0, 15000.0],
             ['R2-35.00-1', 34500.0, 19920.0, 15000.0, 30000.0],
             ['R3-12.47-1', 12470.0, 7200.0, 12000.0, 40000.0],
             ['R3-12.47-2', 12470.0, 7200.0, 14000.0, 30000.0],
             ['R3-12.47-3', 12470.0, 7200.0, 7000.0, 15000.0],
             ['R4-12.47-1', 13800.0, 7970.0, 9000.0, 30000.0],
             ['R4-12.47-2', 12470.0, 7200.0, 6000.0, 20000.0],
             ['R4-25.00-1', 24900.0, 14400.0, 6000.0, 20000.0],
             ['R5-12.47-1', 13800.0, 7970.0, 6500.0, 20000.0],
             ['R5-12.47-2', 12470.0, 7200.0, 4500.0, 15000.0],
             ['R5-12.47-3', 13800.0, 7970.0, 4000.0, 15000.0],
             ['R5-12.47-4', 12470.0, 7200.0, 6000.0, 30000.0],
             ['R5-12.47-5', 12470.0, 7200.0, 4500.0, 25000.0],
             ['R5-25.00-1', 22900.0, 13200.0, 3000.0, 20000.0],
             ['R5-35.00-1', 34500.0, 19920.0, 6000.0, 25000.0],
             ['GC-12.47-1', 12470.0, 7200.0, 8000.0, 13000.0],
             ['TE_Base', 12470.0, 7200.0, 8000.0, 13000.0]]
# casefiles = [['R2-12.47-2',12470.0, 7200.0,15000.0, 25000.0]]
casefiles = [['R1-12.47-1', 12470.0, 7200.0, 4000.0, 20000.0]]


def is_node_class(s):
    """Identify node, load, meter, triplex_node or triplex_meter instances

    Args:
        s (str): the GridLAB-D class name

    Returns:
        Boolean: True if a node class, False otherwise
    """
    if s == 'node':
        return True
    if s == 'load':
        return True
    if s == 'meter':
        return True
    if s == 'triplex_node':
        return True
    if s == 'triplex_meter':
        return True
    return False


def is_edge_class(s):
    """Identify switch, fuse, recloser, regulator, transformer, overhead_line,
    underground_line and triplex_line instances

    Edge class is networkx terminology. In GridLAB-D, edge classes are called links.

    Args:
        s (str): the GridLAB-D class name

    Returns:
        Boolean: True if an edge class, False otherwise
    """
    if s == 'switch':
        return True
    if s == 'fuse':
        return True
    if s == 'recloser':
        return True
    if s == 'regulator':
        return True
    if s == 'transformer':
        return True
    if s == 'overhead_line':
        return True
    if s == 'underground_line':
        return True
    if s == 'triplex_line':
        return True
    return False


def obj(parent, model, line, itr, oidh, octr):
    """Store an object in the model structure

    Args:
        parent (str): name of parent object (used for nested object defs)
        model (dict): dictionary model structure
        line (str): glm line containing the object definition
        itr (iter): iterator over the list of lines
        oidh (dict): hash of object id's to object names
        octr (int): object counter

    Returns:
        str, int: the current line and updated octr
    """
    octr += 1
    # Identify the object type
    m = re.search('object ([^:{\s]+)[:{\s]', line, re.IGNORECASE)
    _type = m.group(1)
    # If the object has an id number, store it
    n = re.search('object ([^:]+:[^{\s]+)', line, re.IGNORECASE)
    if n:
        oid = n.group(1)
    line = next(itr)
    # Collect parameters
    oend = 0
    oname = None
    params = {}
    if parent is not None:
        params['parent'] = parent
    while not oend:
        m = re.match('\s*(\S+) ([^;{]+)[;{]', line)
        if m:
            # found a parameter
            param = m.group(1)
            val = m.group(2)
            intobj = 0
            if param == 'name':
                oname = gld_strict_name(name_prefix + val)
            elif param == 'object':
                # found a nested object
                intobj += 1
                if oname is None:
                    print('ERROR: nested object defined before parent name')
                    quit()
                line, octr = obj(oname, model, line, itr, oidh, octr)
            elif re.match('object', val):
                # found an inline object
                intobj += 1
                line, octr = obj(None, model, line, itr, oidh, octr)
                params[param] = 'ID_' + str(octr)
            else:
                params[param] = val
        if re.search('}', line):
            if intobj:
                intobj -= 1
                line = next(itr)
            else:
                oend = 1
        else:
            line = next(itr)
    # If undefined, use a default name
    if oname is None:
        oname = name_prefix + 'ID_' + str(octr)
    oidh[oname] = oname
    # Hash an object identifier to the object name
    if n:
        oidh[oid] = oname
    # Add the object to the model
    if _type not in model:
        # New object type
        model[_type] = {}
    model[_type][oname] = {}
    for param in params:
        model[_type][oname][param] = params[param]
    return line, octr


def write_config_class(model, h, t, op):
    """Write a GridLAB-D configuration (i.e. not a link or node) class

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class
        op (file): an open GridLAB-D input file
    """
    if t in model:
        for o in model[t]:
            #            print('object ' + t + ':' + o + ' {', file=op)
            print('object ' + t + ' {', file=op)
            print('  name ' + o + ';', file=op)
            for p in model[t][o]:
                if ':' in model[t][o][p]:
                    print('  ' + p + ' ' + h[model[t][o][p]] + ';', file=op)
                else:
                    print('  ' + p + ' ' + model[t][o][p] + ';', file=op)
            print('}', file=op)


def write_link_class(model, h, t, seg_loads, op, want_metrics=False):
    """Write a GridLAB-D link (i.e. edge) class

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class
        seg_loads (dict) : a dictionary of downstream loads for each link
        op (file): an open GridLAB-D input file
    """
    if t in model:
        for o in model[t]:
            #            print('object ' + t + ':' + o + ' {', file=op)
            print('object ' + t + ' {', file=op)
            print('  name ' + o + ';', file=op)
            if o in seg_loads:
                print('// downstream', '{:.2f}'.format(seg_loads[o][0]), 'kva on', seg_loads[o][1], file=op)
            for p in model[t][o]:
                if ':' in model[t][o][p]:
                    print('  ' + p + ' ' + h[model[t][o][p]] + ';', file=op)
                else:
                    if p == "from" or p == "to" or p == "parent":
                        print('  ' + p + ' ' + gld_strict_name(model[t][o][p]) + ';', file=op)
                    else:
                        print('  ' + p + ' ' + model[t][o][p] + ';', file=op)
            if want_metrics and metrics_interval > 0:
                print('  object metrics_collector {', file=op)
                print('    interval', str(metrics_interval) + ';', file=op)
                print('  };', file=op)
            print('}', file=op)


# triplex_conductors dict:[name, r, gmr, ampacity]
triplex_conductors = [['triplex_4/0_aa', 0.48, 0.0158, 1000.0]]

# triplex_configurations dict:[name, hot, neutral, thickness, diameter]
triplex_configurations = [['tpx_config', 'triplex_4/0_aa', 'triplex_4/0_aa', 0.08, 0.522]]


def write_local_triplex_configurations(op):
    """Write a 4/0 AA triplex configuration

    Args:
        op (file): an open GridLAB-D input file
    """
    for row in triplex_conductors:
        print('object triplex_line_conductor {', file=op)
        print('  name', name_prefix + row[0] + ';', file=op)
        print('  resistance', str(row[1]) + ';', file=op)
        print('  geometric_mean_radius', str(row[2]) + ';', file=op)
        print('  rating.summer.continuous', str(row[3]) + ';', file=op)
        print('  rating.summer.emergency', str(row[3]) + ';', file=op)
        print('  rating.winter.continuous', str(row[3]) + ';', file=op)
        print('  rating.winter.emergency', str(row[3]) + ';', file=op)
        print('}', file=op)
    for row in triplex_configurations:
        print('object triplex_line_configuration {', file=op)
        print('  name', name_prefix + row[0] + ';', file=op)
        print('  conductor_1', name_prefix + row[1] + ';', file=op)
        print('  conductor_2', name_prefix + row[1] + ';', file=op)
        print('  conductor_N', name_prefix + row[2] + ';', file=op)
        print('  insulation_thickness', str(row[3]) + ';', file=op)
        print('  diameter', str(row[4]) + ';', file=op)
        print('}', file=op)


def buildingTypeLabel(rgn, bldg, ti):
    """Formatted name of region, building type name and thermal integrity level

    Args:
        rgn (int): region number 1..5
        bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
        ti (int): thermal integrity level, 0..6 for single-family, only 0..2 valid for apartment or mobile home
    """
    return rgnName[rgn - 1] + ': ' + bldgTypeName[bldg] + ': TI Level ' + str(ti + 1)


house_nodes = {}  # keyed on node, [nhouse, region, lg_v_sm, phs, bldg, ti, parent (for ERCOT only)]
small_nodes = {}  # keyed on node, [kva, phs, load_class]
comm_loads = {}  # keyed on load name, [parent, comm_type, nzones, kva, nphs, phases, vln, loadnum]

solar_count = 0
solar_kw = 0
battery_count = 0
ev_count = 0

# write single-phase transformers for houses and small loads
tpxR11 = 2.1645
tpxX11 = 0.6235
tpxR12 = 0.8808
tpxX12 = 0.6737
tpxAMP = 235.0


def connect_ercot_houses(model, h, op, vln, vsec):
    """For the reduced-order ERCOT feeders, add houses and a large service transformer to the load points

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        op (file): an open GridLAB-D input file
        vln (float): the primary line-to-neutral voltage
        vsec (float): the secondary line-to-neutral voltage
    """
    for key in house_nodes:
        #        bus = key[:-2]
        bus = house_nodes[key][6]
        phs = house_nodes[key][3]
        nh = house_nodes[key][0]
        xfkva = Find1PhaseXfmrKva(6.0 * nh)
        if xfkva > 100.0:
            npar = int(xfkva / 100.0 + 0.5)
            xfkva = 100.0
        elif xfkva <= 0.0:
            xfkva = 100.0
            npar = int(0.06 * nh + 0.5)
        else:
            npar = 1
        # print (key, bus, phs, nh, xfkva, npar)
        # write the service transformer==>TN==>TPX==>TM for all houses
        kvat = npar * xfkva
        row = Find1PhaseXfmr(xfkva)
        print('object transformer_configuration {', file=op)
        print('  name ' + key + '_xfconfig;', file=op)
        print('  power_rating ' + format(kvat, '.2f') + ';', file=op)
        if 'A' in phs:
            print('  powerA_rating ' + format(kvat, '.2f') + ';', file=op)
        elif 'B' in phs:
            print('  powerB_rating ' + format(kvat, '.2f') + ';', file=op)
        elif 'C' in phs:
            print('  powerC_rating ' + format(kvat, '.2f') + ';', file=op)
        print('  install_type PADMOUNT;', file=op)
        print('  connect_type SINGLE_PHASE_CENTER_TAPPED;', file=op)
        print('  primary_voltage ' + str(vln) + ';', file=op)
        print('  secondary_voltage ' + format(vsec, '.1f') + ';', file=op)
        print('  resistance ' + format(row[1] * 0.5, '.5f') + ';', file=op)
        print('  resistance1 ' + format(row[1], '.5f') + ';', file=op)
        print('  resistance2 ' + format(row[1], '.5f') + ';', file=op)
        print('  reactance ' + format(row[2] * 0.8, '.5f') + ';', file=op)
        print('  reactance1 ' + format(row[2] * 0.4, '.5f') + ';', file=op)
        print('  reactance2 ' + format(row[2] * 0.4, '.5f') + ';', file=op)
        print('  shunt_resistance ' + format(1.0 / row[3], '.2f') + ';', file=op)
        print('  shunt_reactance ' + format(1.0 / row[4], '.2f') + ';', file=op)
        print('}', file=op)
        print('object transformer {', file=op)
        print('  name ' + key + '_xf;', file=op)
        print('  phases ' + phs + 'S;', file=op)
        print('  from ' + bus + ';', file=op)
        print('  to ' + key + '_tn;', file=op)
        print('  configuration ' + key + '_xfconfig;', file=op)
        print('}', file=op)
        print('object triplex_line_configuration {', file=op)
        print('  name ' + key + '_tpxconfig;', file=op)
        zs = format(tpxR11 / nh, '.5f') + '+' + format(tpxX11 / nh, '.5f') + 'j;'
        zm = format(tpxR12 / nh, '.5f') + '+' + format(tpxX12 / nh, '.5f') + 'j;'
        amps = format(tpxAMP * nh, '.1f') + ';'
        print('  z11 ' + zs, file=op)
        print('  z22 ' + zs, file=op)
        print('  z12 ' + zm, file=op)
        print('  z21 ' + zm, file=op)
        print('  rating.summer.continuous ' + amps, file=op)
        print('}', file=op)
        print('object triplex_line {', file=op)
        print('  name ' + key + '_tpx;', file=op)
        print('  phases ' + phs + 'S;', file=op)
        print('  from ' + key + '_tn;', file=op)
        print('  to ' + key + '_mtr;', file=op)
        print('  length 50;', file=op)
        print('  configuration ' + key + '_tpxconfig;', file=op)
        print('}', file=op)
        if 'A' in phs:
            vstart = str(vsec) + '+0.0j;'
        elif 'B' in phs:
            vstart = format(-0.5 * vsec, '.2f') + format(-0.866025 * vsec, '.2f') + 'j;'
        else:
            vstart = format(-0.5 * vsec, '.2f') + '+' + format(0.866025 * vsec, '.2f') + 'j;'
        print('object triplex_node {', file=op)
        print('  name ' + key + '_tn;', file=op)
        print('  phases ' + phs + 'S;', file=op)
        print('  voltage_1 ' + vstart, file=op)
        print('  voltage_2 ' + vstart, file=op)
        print('  voltage_N 0;', file=op)
        print('  nominal_voltage ' + format(vsec, '.1f') + ';', file=op)
        print('}', file=op)
        print('object triplex_meter {', file=op)
        print('  name ' + key + '_mtr;', file=op)
        print('  phases ' + phs + 'S;', file=op)
        print('  voltage_1 ' + vstart, file=op)
        print('  voltage_2 ' + vstart, file=op)
        print('  voltage_N 0;', file=op)
        print('  nominal_voltage ' + format(vsec, '.1f') + ';', file=op)
        write_tariff(op)
        if metrics_interval > 0 and "meter" in metrics:
            print('  object metrics_collector {', file=op)
            print('    interval', str(metrics_interval) + ';', file=op)
            print('  };', file=op)
        print('}', file=op)


def connect_ercot_commercial(op):
    """For the reduced-order ERCOT feeders, add a billing meter to the commercial load points, except small ZIPLOADs

    Args:
      op (file): an open GridLAB-D input file
    """
    meters_added = set()
    for key in comm_loads:
        mtr = comm_loads[key][0]
        comm_type = comm_loads[key][1]
        if comm_type == 'ZIPLOAD':
            continue
        phases = comm_loads[key][5]
        vln = float(comm_loads[key][6])
        idx = mtr.rfind('_')
        parent = mtr[:idx]

        if mtr not in meters_added:
            meters_added.add(mtr)
            print('object meter {', file=op)
            print('  name ' + mtr + ';', file=op)
            print('  parent ' + parent + ';', file=op)
            print('  phases ' + phases + ';', file=op)
            print('  nominal_voltage ' + format(vln, '.1f') + ';', file=op)
            write_tariff(op)
            if metrics_interval > 0 and "meter" in metrics:
                print('  object metrics_collector {', file=op)
                print('    interval', str(metrics_interval) + ';', file=op)
                print('  };', file=op)
            print('}', file=op)


def write_ercot_small_loads(basenode, op, vnom):
    """For the reduced-order ERCOT feeders, write loads that are too small for houses

    Args:
        basenode (str): the GridLAB-D node name
        op (file): an open GridLAB-D input file
        vnom (float): the primary line-to-neutral voltage
    """
    kva = float(small_nodes[basenode][0])
    phs = small_nodes[basenode][1]
    parent = small_nodes[basenode][2]
    cls = small_nodes[basenode][3]

    if 'A' in phs:
        vstart = '  voltage_A ' + str(vnom) + '+0.0j;'
        constpower = '  constant_power_A_real ' + format(1000.0 * kva, '.2f') + ';'
    elif 'B' in phs:
        vstart = '  voltage_B ' + format(-0.5 * vnom, '.2f') + format(-0.866025 * vnom, '.2f') + 'j;'
        constpower = '  constant_power_B_real ' + format(1000.0 * kva, '.2f') + ';'
    else:
        vstart = '  voltage_C ' + format(-0.5 * vnom, '.2f') + '+' + format(0.866025 * vnom, '.2f') + 'j;'
        constpower = '  constant_power_C_real ' + format(1000.0 * kva, '.2f') + ';'

    print('object load {', file=op)
    print('  name', basenode + ';', file=op)
    print('  parent', parent + ';', file=op)
    print('  phases', phs + ';', file=op)
    print('  nominal_voltage ' + str(vnom) + ';', file=op)
    print('  load_class ' + cls + ';', file=op)
    print(vstart, file=op)
    print('  //', '{:.3f}'.format(kva), 'kva is less than 1/2 avg_house', file=op)
    print(constpower, file=op)
    print('}', file=op)


# look at primary loads, not the service transformers
def identify_ercot_houses(model, h, t, avgHouse, rgn):
    """For the reduced-order ERCOT feeders, scan each primary load to determine the number of houses it should have

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class name to scan
        avgHouse (float): the average house load in kva
        rgn (int): the region number, 1..5
    """
    print('Average ERCOT House', avgHouse, rgn)
    total_houses = {'A': 0, 'B': 0, 'C': 0}
    total_small = {'A': 0, 'B': 0, 'C': 0}
    total_small_kva = {'A': 0, 'B': 0, 'C': 0}
    total_sf = 0
    total_apt = 0
    total_mh = 0
    if t in model:
        for o in model[t]:
            node = o
            parent = gld_strict_name(model[t][o]['parent'])
            for phs in ['A', 'B', 'C']:
                tok = 'constant_power_' + phs
                key = node + '_' + phs
                if tok in model[t][o]:
                    kva = parse_kva(model[t][o][tok])
                    nh = 0
                    cls = 'U'
                    # don't populate houses onto A, C, I or U load_class nodes
                    if 'load_class' in model[t][o]:
                        cls = model[t][o]['load_class']
                        if cls == 'R':
                            if kva > 1.0:
                                nh = int((kva / avgHouse) + 0.5)
                                total_houses[phs] += nh
                    if nh > 0:
                        lg_v_sm = kva / avgHouse - nh  # >0 if we rounded down the number of houses
                        bldg, ti = selectResidentialBuilding(rgnThermalPct[rgn - 1], np.random.uniform(0, 1))
                        if bldg == 0:
                            total_sf += nh
                        elif bldg == 1:
                            total_apt += nh
                        else:
                            total_mh += nh
                        # parent is the primary node, only for ERCOT
                        house_nodes[key] = [nh, rgn, lg_v_sm, phs, bldg, ti, parent]
                    elif kva > 0.1:
                        total_small[phs] += 1
                        total_small_kva[phs] += kva
                        small_nodes[key] = [kva, phs, parent, cls]  # parent is the primary node, only for ERCOT
    for phs in ['A', 'B', 'C']:
        print('phase', phs, ':', total_houses[phs], 'Houses and', total_small[phs],
              'Small Loads totaling', '{:.2f}'.format(total_small_kva[phs]), 'kva')
    print(len(house_nodes), 'primary house nodes, [SF,APT,MH]=', total_sf, total_apt, total_mh)
    for i in range(6):
        heating_bins[0][i] = round(total_sf * bldgHeatingSetpoints[0][i][0] + 0.5)
        heating_bins[1][i] = round(total_apt * bldgHeatingSetpoints[1][i][0] + 0.5)
        heating_bins[2][i] = round(total_mh * bldgHeatingSetpoints[2][i][0] + 0.5)
        cooling_bins[0][i] = round(total_sf * bldgCoolingSetpoints[0][i][0] + 0.5)
        cooling_bins[1][i] = round(total_apt * bldgCoolingSetpoints[1][i][0] + 0.5)
        cooling_bins[2][i] = round(total_mh * bldgCoolingSetpoints[2][i][0] + 0.5)
    print('cooling bins target', cooling_bins)
    print('heating bins target', heating_bins)


extra_billing_meters = set()


def replace_commercial_loads(model, h, t, avgBuilding):
    """For the full-order feeders, scan each load with load_class==C to determine the number of zones it should have

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class name to scan
        avgBuilding (float): the average building in kva
    """
    print('Average Commercial Building', avgBuilding)
    total_commercial = 0
    total_comm_kva = 0
    total_comm_zones = 0
    total_zipload = 0
    total_office = 0
    total_big_box = 0
    total_strip_mall = 0
    if t in model:
        for o in list(model[t].keys()):
            if 'load_class' in model[t][o]:
                if model[t][o]['load_class'] == 'C':
                    kva = accumulate_load_kva(model[t][o])
                    total_commercial += 1
                    total_comm_kva += kva
                    vln = float(model[t][o]['nominal_voltage'])
                    nphs = 0
                    phases = model[t][o]['phases']
                    if 'A' in phases:
                        nphs += 1
                    if 'B' in phases:
                        nphs += 1
                    if 'C' in phases:
                        nphs += 1
                    nzones = int((kva / avgBuilding) + 0.5)
                    total_comm_zones += nzones
                    if nzones > 14 and nphs == 3:
                        comm_type = 'OFFICE'
                        total_office += 1
                    elif nzones > 5 and nphs > 1:
                        comm_type = 'BIGBOX'
                        total_big_box += 1
                    elif nzones > 0:
                        comm_type = 'STRIPMALL'
                        total_strip_mall += 1
                    else:
                        comm_type = 'ZIPLOAD'
                        total_zipload += 1
                    mtr = gld_strict_name(model[t][o]['parent'])
                    if forERCOT:
                        # the parent node is actually a meter, but we have to add the tariff and metrics_collector unless only ZIPLOAD
                        if comm_type != 'ZIPLOAD':
                            extra_billing_meters.add(mtr)
                    else:
                        extra_billing_meters.add(mtr)
                    comm_loads[o] = [mtr, comm_type, nzones, kva, nphs, phases, vln, total_commercial]
                    model[t][o]['groupid'] = comm_type + '_' + str(nzones)
                    del model[t][o]
    # Print commercial info
    print('Found', total_commercial, 'commercial loads totaling ', '{:.2f}'.format(total_comm_kva), 'KVA')
    print('  ', total_office, 'offices,')
    print('  ', total_big_box, 'big box retail,')
    print('  ', total_strip_mall, 'strip malls,')
    print('  ', total_zipload, 'ZIP loads')
    print(total_comm_zones, 'total commercial HVAC zones')


def identify_xfmr_houses(model, h, t, seg_loads, avgHouse, rgn):
    """For the full-order feeders, scan each service transformer to determine the number of houses it should have

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class name to scan
        seg_loads (dict): dictionary of downstream load (kva) served by each GridLAB-D link
        avgHouse (float): the average house load in kva
        rgn (int): the region number, 1..5
    """
    print('Average House', avgHouse)
    total_houses = 0
    total_sf = 0
    total_apt = 0
    total_mh = 0
    total_small = 0
    total_small_kva = 0
    if t in model:
        for o in model[t]:
            if o in seg_loads:
                tkva = seg_loads[o][0]
                phs = seg_loads[o][1]
                if 'S' in phs:
                    nhouse = int((tkva / avgHouse) + 0.5)  # round to nearest int
                    node = gld_strict_name(model[t][o]['to'])
                    if nhouse <= 0:
                        total_small += 1
                        total_small_kva += tkva
                        small_nodes[node] = [tkva, phs]
                    else:
                        total_houses += nhouse
                        lg_v_sm = tkva / avgHouse - nhouse  # >0 if we rounded down the number of houses
                        bldg, ti = selectResidentialBuilding(rgnThermalPct[rgn - 1], np.random.uniform(0, 1))
                        if bldg == 0:
                            total_sf += nhouse
                        elif bldg == 1:
                            total_apt += nhouse
                        else:
                            total_mh += nhouse
                        house_nodes[node] = [nhouse, rgn, lg_v_sm, phs, bldg, ti]
    print(total_small, 'small loads totaling', '{:.2f}'.format(total_small_kva), 'kva')
    print(total_houses, 'houses on', len(house_nodes), 'transformers, [SF,APT,MH]=', total_sf, total_apt, total_mh)
    for i in range(6):
        heating_bins[0][i] = round(total_sf * bldgHeatingSetpoints[0][i][0] + 0.5)
        heating_bins[1][i] = round(total_apt * bldgHeatingSetpoints[1][i][0] + 0.5)
        heating_bins[2][i] = round(total_mh * bldgHeatingSetpoints[2][i][0] + 0.5)
        cooling_bins[0][i] = round(total_sf * bldgCoolingSetpoints[0][i][0] + 0.5)
        cooling_bins[1][i] = round(total_apt * bldgCoolingSetpoints[1][i][0] + 0.5)
        cooling_bins[2][i] = round(total_mh * bldgCoolingSetpoints[2][i][0] + 0.5)
    # print('cooling bins target', cooling_bins)
    # print('heating bins target', heating_bins)


def write_small_loads(basenode, op, vnom):
    """Write loads that are too small for a house, onto a node

    Args:
        basenode (str): GridLAB-D node name
        op (file): open file to write to
        vnom (float): nominal line-to-neutral voltage at basenode
    """
    kva = float(small_nodes[basenode][0])
    phs = small_nodes[basenode][1]

    if 'A' in phs:
        vstart = str(vnom) + '+0.0j'
    elif 'B' in phs:
        vstart = format(-0.5 * vnom, '.2f') + format(-0.866025 * vnom, '.2f') + 'j'
    else:
        vstart = format(-0.5 * vnom, '.2f') + '+' + format(0.866025 * vnom, '.2f') + 'j'

    tpxname = basenode + '_tpx_1'
    mtrname = basenode + '_mtr_1'
    loadname = basenode + '_load_1'
    print('object triplex_node {', file=op)
    print('  name', basenode + ';', file=op)
    print('  phases', phs + ';', file=op)
    print('  nominal_voltage ' + str(vnom) + ';', file=op)
    print('  voltage_1 ' + vstart + ';', file=op)
    print('  voltage_2 ' + vstart + ';', file=op)
    print('}', file=op)
    print('object triplex_line {', file=op)
    print('  name', tpxname + ';', file=op)
    print('  from', basenode + ';', file=op)
    print('  to', mtrname + ';', file=op)
    print('  phases', phs + ';', file=op)
    print('  length 30;', file=op)
    print('  configuration', name_prefix + triplex_configurations[0][0] + ';', file=op)
    print('}', file=op)
    print('object triplex_meter {', file=op)
    print('  name', mtrname + ';', file=op)
    print('  phases', phs + ';', file=op)
    print('  meter_power_consumption 1+7j;', file=op)
    write_tariff(op)
    print('  nominal_voltage ' + str(vnom) + ';', file=op)
    print('  voltage_1 ' + vstart + ';', file=op)
    print('  voltage_2 ' + vstart + ';', file=op)
    if metrics_interval > 0 and "meter" in metrics:
        print('  object metrics_collector {', file=op)
        print('    interval', str(metrics_interval) + ';', file=op)
        print('  };', file=op)
    print('}', file=op)
    print('object triplex_load {', file=op)
    print('  name', loadname + ';', file=op)
    print('  parent', mtrname + ';', file=op)
    print('  phases', phs + ';', file=op)
    print('  nominal_voltage ' + str(vnom) + ';', file=op)
    print('  voltage_1 ' + vstart + ';', file=op)
    print('  voltage_2 ' + vstart + ';', file=op)
    print('  //', '{:.3f}'.format(kva), 'kva is less than 1/2 avg_house', file=op)
    print('  constant_power_12_real 10.0;', file=op)
    print('  constant_power_12_reac 8.0;', file=op)
    print('}', file=op)


def write_one_commercial_zone(bldg, op):
    """Write one pre-configured commercial zone as a house

    Args:
        bldg: dictionary of GridLAB-D house and zipload attributes
        op (file): open file to write to
    """
    print('object house {', file=op)
    print('  name', bldg['zonename'] + ';', file=op)
    print('  parent', bldg['parent'] + ';', file=op)
    print('  groupid', bldg['groupid'] + ';', file=op)
    print('  motor_model BASIC;', file=op)
    print('  schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('  floor_area {:.0f};'.format(bldg['floor_area']), file=op)
    print('  design_internal_gains {:.0f};'.format(bldg['int_gains'] * bldg['floor_area'] * 3.413), file=op)
    print('  number_of_doors {:.0f};'.format(bldg['no_of_doors']), file=op)
    print('  aspect_ratio {:.2f};'.format(bldg['aspect_ratio']), file=op)
    print('  total_thermal_mass_per_floor_area {:1.2f};'.format(bldg['thermal_mass_per_floor_area']), file=op)
    print('  interior_surface_heat_transfer_coeff {:1.2f};'.format(bldg['surface_heat_trans_coeff']), file=op)
    print('  interior_exterior_wall_ratio {:.2f};'.format(bldg['interior_exterior_wall_ratio']), file=op)
    print('  exterior_floor_fraction {:.3f};'.format(bldg['exterior_floor_fraction']), file=op)
    print('  exterior_ceiling_fraction {:.3f};'.format(bldg['exterior_ceiling_fraction']), file=op)
    print('  Rwall {:2.1f};'.format(bldg['Rwall']), file=op)
    print('  Rroof {:2.1f};'.format(bldg['Rroof']), file=op)
    print('  Rfloor {:.2f};'.format(bldg['Rfloor']), file=op)
    print('  Rdoors {:2.1f};'.format(bldg['Rdoors']), file=op)
    print('  exterior_wall_fraction {:.2f};'.format(bldg['exterior_wall_fraction']), file=op)
    print('  glazing_layers {:s};'.format(bldg['glazing_layers']), file=op)
    print('  glass_type {:s};'.format(bldg['glass_type']), file=op)
    print('  glazing_treatment {:s};'.format(bldg['glazing_treatment']), file=op)
    print('  window_frame {:s};'.format(bldg['window_frame']), file=op)
    print('  airchange_per_hour {:.2f};'.format(bldg['airchange_per_hour']), file=op)
    print('  window_wall_ratio {:0.3f};'.format(bldg['window_wall_ratio']), file=op)
    print('  heating_system_type {:s};'.format(bldg['heat_type']), file=op)
    print('  auxiliary_system_type {:s};'.format(bldg['aux_type']), file=op)
    print('  fan_type {:s};'.format(bldg['fan_type']), file=op)
    print('  cooling_system_type {:s};'.format(bldg['cool_type']), file=op)
    print('  air_temperature {:.2f};'.format(bldg['init_temp']), file=op)
    print('  mass_temperature {:.2f};'.format(bldg['init_temp']), file=op)
    print('  over_sizing_factor {:.1f};'.format(bldg['os_rand']), file=op)
    print('  cooling_COP {:2.2f};'.format(bldg['COP_A']), file=op)
    print('  cooling_setpoint 80.0; // {:s}_cooling'.format(bldg['base_schedule']), file=op)
    print('  heating_setpoint 60.0; // {:s}_heating'.format(bldg['base_schedule']), file=op)
    print('  object ZIPload { // lights', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 1.0;', file=op)
    print('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
    print('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
    print('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
    print('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
    print('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
    print('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
    print('    base_power {:s}_lights*{:.2f};'.format(bldg['base_schedule'], bldg['adj_lights']), file=op)
    print('  };', file=op)
    print('  object ZIPload { // plug loads', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 1.0;', file=op)
    print('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
    print('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
    print('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
    print('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
    print('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
    print('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
    print('    base_power {:s}_plugs*{:.2f};'.format(bldg['base_schedule'], bldg['adj_plugs']), file=op)
    print('  };', file=op)
    print('  object ZIPload { // gas waterheater', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 1.0;', file=op)
    print('    power_fraction 0;', file=op)
    print('    impedance_fraction 0;', file=op)
    print('    current_fraction 0;', file=op)
    print('    power_pf 1;', file=op)
    print('    base_power {:s}_gas*{:.2f};'.format(bldg['base_schedule'], bldg['adj_gas']), file=op)
    print('  };', file=op)
    print('  object ZIPload { // exterior lights', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 0.0;', file=op)
    print('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
    print('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
    print('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
    print('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
    print('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
    print('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
    print('    base_power {:s}_exterior*{:.2f};'.format(bldg['base_schedule'], bldg['adj_ext']), file=op)
    print('  };', file=op)
    print('  object ZIPload { // occupancy', file=op)
    print('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
    print('    heatgain_fraction 1.0;', file=op)
    print('    power_fraction 0;', file=op)
    print('    impedance_fraction 0;', file=op)
    print('    current_fraction 0;', file=op)
    print('    power_pf 1;', file=op)
    print('    base_power {:s}_occupancy*{:.2f};'.format(bldg['base_schedule'], bldg['adj_occ']), file=op)
    print('  };', file=op)
    if metrics_interval > 0:
        print('  object metrics_collector {', file=op)
        print('    interval', str(metrics_interval) + ';', file=op)
        print('  };', file=op)
    print('}', file=op)


def write_commercial_loads(rgn, key, op):
    """Put commercial building zones and ZIP loads into the model

    Args:
        rgn (int): region 1..5 where the building is located
        key (str): GridLAB-D load name that is being replaced
        op (file): open file to write to
    """
    mtr = comm_loads[key][0]
    comm_type = comm_loads[key][1]
    nz = int(comm_loads[key][2])
    kva = float(comm_loads[key][3])
    nphs = int(comm_loads[key][4])
    phases = comm_loads[key][5]
    vln = float(comm_loads[key][6])
    loadnum = int(comm_loads[key][7])

    bldg = {}
    bldg['parent'] = key
    bldg['mtr'] = mtr
    bldg['groupid'] = comm_type + '_' + str(loadnum)

    print('// load', key, 'mtr', bldg['mtr'], 'type', comm_type, 'nz', nz, 'kva', '{:.3f}'.format(kva),
          'nphs', nphs, 'phases', phases, 'vln', '{:.3f}'.format(vln), file=op)

    bldg['fan_type'] = 'ONE_SPEED'
    bldg['heat_type'] = 'GAS'
    bldg['cool_type'] = 'ELECTRIC'
    bldg['aux_type'] = 'NONE'
    bldg['no_of_stories'] = 1
    bldg['surface_heat_trans_coeff'] = 0.59
    bldg['oversize'] = over_sizing_factor[rgn - 1]
    bldg['glazing_layers'] = 'TWO'
    bldg['glass_type'] = 'GLASS'
    bldg['glazing_treatment'] = 'LOW_S'
    bldg['window_frame'] = 'NONE'
    bldg['c_z_frac'] = c_z_frac
    bldg['c_i_frac'] = c_i_frac
    bldg['c_p_frac'] = c_p_frac
    bldg['c_z_pf'] = c_z_pf
    bldg['c_i_pf'] = c_i_pf
    bldg['c_p_pf'] = c_p_pf

    if comm_type == 'OFFICE':
        bldg['ceiling_height'] = 13.
        bldg['airchange_per_hour'] = 0.69
        bldg['Rroof'] = 19.
        bldg['Rwall'] = 18.3
        bldg['Rfloor'] = 46.
        bldg['Rdoors'] = 3.
        bldg['int_gains'] = 3.24  # W/sf
        bldg['thermal_mass_per_floor_area'] = 1  # TODO
        bldg['exterior_ceiling_fraction'] = 1  # TODO
        bldg['base_schedule'] = 'office'
        num_offices = int(round(nz / 15))  # each with 3 floors of 5 zones
        for jjj in range(num_offices):
            floor_area_choose = 40000. * (0.5 * np.random.random() + 0.5)
            for floor_lvl in range(1, 4):
                bldg['skew_value'] = randomize_commercial_skew()
                total_depth = sqrt(floor_area_choose / (3. * 1.5))
                total_width = 1.5 * total_depth
                if floor_lvl == 3:
                    bldg['exterior_ceiling_fraction'] = 1
                else:
                    bldg['exterior_ceiling_fraction'] = 0
                for zone in range(1, 6):
                    if zone == 5:
                        bldg['window_wall_ratio'] = 0  # this was not in the CCSI version
                        bldg['exterior_wall_fraction'] = 0
                        w = total_depth - 30.
                        d = total_width - 30.
                    else:
                        bldg['window_wall_ratio'] = 0.33
                        d = 15.
                        if zone == 1 or zone == 3:
                            w = total_width - 15.
                        else:
                            w = total_depth - 15.
                        bldg['exterior_wall_fraction'] = w / (2. * (w + d))

                    floor_area = w * d
                    bldg['floor_area'] = floor_area
                    bldg['aspect_ratio'] = w / d

                    if floor_lvl > 1:
                        bldg['exterior_floor_fraction'] = 0
                    else:
                        bldg['exterior_floor_fraction'] = w / (2. * (w + d)) / (floor_area / (floor_area_choose / 3.))

                    bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * np.random.random())
                    bldg['interior_exterior_wall_ratio'] = floor_area / (bldg['ceiling_height'] * 2. * (w + d)) - 1. + \
                                                           bldg['window_wall_ratio'] * bldg['exterior_wall_fraction']
                    bldg[
                        'no_of_doors'] = 0.1  # will round to zero, presumably the exterior doors are treated like windows

                    bldg['init_temp'] = 68. + 4. * np.random.random()
                    bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
                    bldg['COP_A'] = cooling_COP * (0.8 + 0.4 * np.random.random())

                    # randomize 10# then convert W/sf -> kW
                    bldg['adj_lights'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
                    bldg['adj_plugs'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
                    bldg['adj_gas'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
                    bldg['adj_ext'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
                    bldg['adj_occ'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.

                    bldg['zonename'] = gld_strict_name(key + '_bldg_' + str(jjj + 1) + '_floor_' + str(floor_lvl) + '_zone_' + str(zone))
                    write_one_commercial_zone(bldg, op)

    elif comm_type == 'BIGBOX':
        bldg['ceiling_height'] = 14.
        bldg['airchange_per_hour'] = 1.5
        bldg['Rroof'] = 19.
        bldg['Rwall'] = 18.3
        bldg['Rfloor'] = 46.
        bldg['Rdoors'] = 3.
        bldg['int_gains'] = 3.6  # W/sf
        bldg['thermal_mass_per_floor_area'] = 1  # TODO
        bldg['exterior_ceiling_fraction'] = 1  # TODO
        bldg['base_schedule'] = 'bigbox'

        num_bigboxes = int(round(nz / 6.))
        for jjj in range(num_bigboxes):
            bldg['skew_value'] = randomize_commercial_skew()
            floor_area_choose = 20000. * (0.5 + 1. * np.random.random())
            floor_area = floor_area_choose / 6.
            bldg['floor_area'] = floor_area
            bldg['thermal_mass_per_floor_area'] = 3.9 * (0.8 + 0.4 * np.random.random())  # +/- 20#
            bldg['exterior_ceiling_fraction'] = 1.
            bldg['aspect_ratio'] = 1.28301275561855
            total_depth = sqrt(floor_area_choose / bldg['aspect_ratio'])
            total_width = bldg['aspect_ratio'] * total_depth
            d = total_width / 3.
            w = total_depth / 2.

            for zone in range(1, 7):
                if zone == 2 or zone == 5:
                    bldg['exterior_wall_fraction'] = d / (2. * (d + w))
                    bldg['exterior_floor_fraction'] = (0. + d) / (2. * (total_width + total_depth)) / \
                                                      (floor_area / floor_area_choose)
                else:
                    bldg['exterior_wall_fraction'] = 0.5
                    bldg['exterior_floor_fraction'] = (w + d) / (2. * (total_width + total_depth)) / \
                                                      (floor_area / floor_area_choose)
                if zone == 2:
                    bldg['window_wall_ratio'] = 0.76
                else:
                    bldg['window_wall_ratio'] = 0.

                if zone < 4:
                    bldg['no_of_doors'] = 0.1  # this will round to 0
                elif zone == 5:
                    bldg['no_of_doors'] = 24.
                else:
                    bldg['no_of_doors'] = 1.

                bldg['interior_exterior_wall_ratio'] = (floor_area + bldg['no_of_doors'] * 20.) / \
                                                       (bldg['ceiling_height'] * 2. * (w + d)) - 1. + \
                                                       bldg['window_wall_ratio'] * bldg['exterior_wall_fraction']
                bldg['init_temp'] = 68. + 4. * np.random.random()
                bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
                bldg['COP_A'] = cooling_COP * (0.8 + 0.4 * np.random.random())

                # randomize 10# then convert W/sf -> kW
                bldg['adj_lights'] = 1.2 * (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
                bldg['adj_plugs'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
                bldg['adj_gas'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
                bldg['adj_ext'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
                bldg['adj_occ'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.

                bldg['zonename'] = gld_strict_name(key + '_bldg_' + str(jjj + 1) + '_zone_' + str(zone))
                write_one_commercial_zone(bldg, op)

    elif comm_type == 'STRIPMALL':
        bldg['ceiling_height'] = 12  # T)D)
        bldg['airchange_per_hour'] = 1.76
        bldg['Rroof'] = 19.
        bldg['Rwall'] = 18.3
        bldg['Rfloor'] = 40.
        bldg['Rdoors'] = 3.
        bldg['int_gains'] = 3.6  # W/sf
        bldg['exterior_ceiling_fraction'] = 1.
        bldg['base_schedule'] = 'stripmall'
        midzone = int(floor(nz / 2.) + 1.)
        for zone in range(1, nz + 1):
            bldg['skew_value'] = randomize_commercial_skew()
            floor_area_choose = 2400. * (0.7 + 0.6 * np.random.random())
            bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * np.random.random())
            bldg['no_of_doors'] = 1
            if zone == 1 or zone == midzone:
                floor_area = floor_area_choose
                bldg['aspect_ratio'] = 1.5
                bldg['window_wall_ratio'] = 0.05
                bldg['exterior_wall_fraction'] = 0.4
                bldg['exterior_floor_fraction'] = 0.8
                bldg['interior_exterior_wall_ratio'] = -0.05
            else:
                floor_area = floor_area_choose / 2.
                bldg['aspect_ratio'] = 3.0
                bldg['window_wall_ratio'] = 0.03
                if zone == nz:
                    bldg['exterior_wall_fraction'] = 0.63
                    bldg['exterior_floor_fraction'] = 2.
                else:
                    bldg['exterior_wall_fraction'] = 0.25
                    bldg['exterior_floor_fraction'] = 0.8
                bldg['interior_exterior_wall_ratio'] = -0.40

            bldg['floor_area'] = floor_area

            bldg['init_temp'] = 68. + 4. * np.random.random()
            bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
            bldg['COP_A'] = cooling_COP * (0.8 + 0.4 * np.random.random())

            bldg['adj_lights'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
            bldg['adj_plugs'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
            bldg['adj_gas'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
            bldg['adj_ext'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
            bldg['adj_occ'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.

            bldg['zonename'] = gld_strict_name(key + '_zone_' + str(zone))
            write_one_commercial_zone(bldg, op)

    if comm_type == 'ZIPLOAD':
        phsva = 1000.0 * kva / nphs
        print('object load { // street lights', file=op)
        print('  name {:s};'.format(key + '_streetlights'), file=op)
        print('  parent {:s};'.format(mtr), file=op)
        print('  groupid STREETLIGHTS;', file=op)
        print('  nominal_voltage {:2f};'.format(vln), file=op)
        print('  phases {:s};'.format(phases), file=op)
        for phs in ['A', 'B', 'C']:
            if phs in phases:
                print('  impedance_fraction_{:s} {:f};'.format(phs, c_z_frac), file=op)
                print('  current_fraction_{:s} {:f};'.format(phs, c_i_frac), file=op)
                print('  power_fraction_{:s} {:f};'.format(phs, c_p_frac), file=op)
                print('  impedance_pf_{:s} {:f};'.format(phs, c_z_pf), file=op)
                print('  current_pf_{:s} {:f};'.format(phs, c_i_pf), file=op)
                print('  power_pf_{:s} {:f};'.format(phs, c_p_pf), file=op)
                print('  base_power_{:s} street_lighting*{:.2f};'.format(phs, light_scalar_comm * phsva), file=op)
        print('};', file=op)
    else:
        print('object load { // accumulate zones', file=op)
        print('  name {:s};'.format(key), file=op)
        print('  parent {:s};'.format(mtr), file=op)
        print('  groupid {:s};'.format(comm_type), file=op)
        print('  nominal_voltage {:2f};'.format(vln), file=op)
        print('  phases {:s};'.format(phases), file=op)
        print('};', file=op)


def write_houses(basenode, op, vnom, bIgnoreThermostatSchedule=True, bWriteService=True, bTriplex=True,
                 setpoint_offset=1.0):
    """Put houses, along with solar panels and batteries, onto a node

    Args:
        basenode (str): GridLAB-D node name
        op (file): open file to write to
        vnom (float): nominal line-to-neutral voltage at basenode
    """
    global solar_count, solar_kw, battery_count

    meter_class = 'triplex_meter'
    node_class = 'triplex_node'
    if not bTriplex:
        meter_class = 'meter'
        node_class = 'node'

    nhouse = int(house_nodes[basenode][0])
    rgn = int(house_nodes[basenode][1])
    lg_v_sm = float(house_nodes[basenode][2])
    phs = house_nodes[basenode][3]
    bldg = house_nodes[basenode][4]
    ti = house_nodes[basenode][5]
    rgnTable = rgnThermalPct[rgn - 1]

    if 'A' in phs:
        vstart = str(vnom) + '+0.0j'
    elif 'B' in phs:
        vstart = format(-0.5 * vnom, '.2f') + format(-0.866025 * vnom, '.2f') + 'j'
    else:
        vstart = format(-0.5 * vnom, '.2f') + '+' + format(0.866025 * vnom, '.2f') + 'j'

    if forERCOT:
        phs = phs + 'S'
        tpxname = gld_strict_name(basenode + '_tpx')
        mtrname = gld_strict_name(basenode + '_mtr')
    elif bWriteService:
        print('object {:s} {{'.format(node_class), file=op)
        print('  name', basenode + ';', file=op)
        print('  phases', phs + ';', file=op)
        print('  nominal_voltage ' + str(vnom) + ';', file=op)
        print('  voltage_1 ' + vstart + ';', file=op)  # TODO: different attributes for regular node
        print('  voltage_2 ' + vstart + ';', file=op)
        print('}', file=op)
    else:
        mtrname = gld_strict_name(basenode + '_mtr')
    for i in range(nhouse):
        if not forERCOT and bWriteService:
            tpxname = gld_strict_name(basenode + '_tpx_' + str(i + 1))
            mtrname = gld_strict_name(basenode + '_mtr_' + str(i + 1))
            print('object triplex_line {', file=op)
            print('  name', tpxname + ';', file=op)
            print('  from', basenode + ';', file=op)
            print('  to', mtrname + ';', file=op)
            print('  phases', phs + ';', file=op)
            print('  length 30;', file=op)
            print('  configuration', name_prefix + triplex_configurations[0][0] + ';', file=op)
            print('}', file=op)
            print('object triplex_meter {', file=op)
            print('  name', mtrname + ';', file=op)
            print('  phases', phs + ';', file=op)
            print('  meter_power_consumption 1+7j;', file=op)
            write_tariff(op)
            print('  nominal_voltage ' + str(vnom) + ';', file=op)
            print('  voltage_1 ' + vstart + ';', file=op)
            print('  voltage_2 ' + vstart + ';', file=op)
            if metrics_interval > 0 and "meter" in metrics:
                print('  object metrics_collector {', file=op)
                print('    interval', str(metrics_interval) + ';', file=op)
                print('  };', file=op)
            print('}', file=op)
        hsename = gld_strict_name(basenode + '_hse_' + str(i + 1))
        whname = gld_strict_name(basenode + '_wh_' + str(i + 1))
        solname = gld_strict_name(basenode + '_sol_' + str(i + 1))
        batname = gld_strict_name(basenode + '_bat_' + str(i + 1))
        sol_i_name = gld_strict_name(basenode + '_isol_' + str(i + 1))
        bat_i_name = gld_strict_name(basenode + '_ibat_' + str(i + 1))
        hse_m_name = gld_strict_name(basenode + '_mhse_' + str(i + 1))
        sol_m_name = gld_strict_name(basenode + '_msol_' + str(i + 1))
        bat_m_name = gld_strict_name(basenode + '_mbat_' + str(i + 1))
        if forERCOT:
            hse_m_name = mtrname
        else:
            print('object {:s} {{'.format(meter_class), file=op)
            print('  name', hse_m_name + ';', file=op)
            print('  parent', mtrname + ';', file=op)
            print('  phases', phs + ';', file=op)
            print('  nominal_voltage ' + str(vnom) + ';', file=op)
            print('}', file=op)

        fa_base = rgnFloorArea[rgn - 1][bldg]
        fa_rand = np.random.uniform(0, 1)
        stories = 1
        ceiling_height = 8
        if bldg == 0:  # SF homes
            floor_area = fa_base + 0.5 * fa_base * fa_rand * (ti - 3) / 3
            if np.random.uniform(0, 1) > rgnOneStory[rgn - 1]:
                stories = 2
            ceiling_height += np.random.randint(0, 2)
        else:  # apartment or MH
            floor_area = fa_base + 0.5 * fa_base * (0.5 - fa_rand)  # +/- 50%
        floor_area = (1 + lg_v_sm) * floor_area  # adjustment depends on whether nhouses rounded up or down
        if floor_area > 4000:
            floor_area = 3800 + fa_rand * 200
        elif floor_area < 300:
            floor_area = 300 + fa_rand * 100

        # ********** residential skew and scalar for schedule files **********
        scalar1 = 324.9 / 8907 * floor_area ** 0.442
        scalar2 = 0.8 + 0.4 * np.random.uniform(0, 1)
        scalar3 = 0.8 + 0.4 * np.random.uniform(0, 1)
        resp_scalar = scalar1 * scalar2
        unresp_scalar = scalar1 * scalar3

        skew_value = randomize_residential_skew()

        oversize = rgnOversizeFactor[rgn - 1] * (0.8 + 0.4 * np.random.uniform(0, 1))
        tiProps = selectThermalProperties(bldg, ti)
        # Rceiling(roof), Rwall, Rfloor, WindowLayers, WindowGlass,Glazing,WindowFrame,Rdoor,AirInfil,COPhi,COPlo
        Rroof = tiProps[0] * (0.8 + 0.4 * np.random.uniform(0, 1))
        Rwall = tiProps[1] * (0.8 + 0.4 * np.random.uniform(0, 1))
        Rfloor = tiProps[2] * (0.8 + 0.4 * np.random.uniform(0, 1))
        glazing_layers = int(tiProps[3])
        glass_type = int(tiProps[4])
        glazing_treatment = int(tiProps[5])
        window_frame = int(tiProps[6])
        Rdoor = tiProps[7] * (0.8 + 0.4 * np.random.uniform(0, 1))
        airchange = tiProps[8] * (0.8 + 0.4 * np.random.uniform(0, 1))
        init_temp = 68 + 4 * np.random.uniform(0, 1)
        mass_floor = 2.5 + 1.5 * np.random.uniform(0, 1)
        h_COP = c_COP = tiProps[10] + np.random.uniform(0, 1) * (tiProps[9] - tiProps[10])

        print('object house {', file=op)
        print('  name', hsename + ';', file=op)
        print('  parent', hse_m_name + ';', file=op)
        print('  groupid', bldgTypeName[bldg] + ';', file=op)
        # why thermal integrity level is not used ?
        # this sets the default house R* and other parameters
        print('  // thermal_integrity_level', tiName[ti] + ';', file=op)
        print('  schedule_skew', '{:.0f}'.format(skew_value) + ';', file=op)
        print('  floor_area', '{:.0f}'.format(floor_area) + ';', file=op)
        print('  number_of_stories', str(stories) + ';', file=op)
        print('  ceiling_height', str(ceiling_height) + ';', file=op)
        print('  over_sizing_factor', '{:.4f}'.format(oversize) + ';', file=op)
        print('  Rroof', '{:.2f}'.format(Rroof) + ';', file=op)
        print('  Rwall', '{:.2f}'.format(Rwall) + ';', file=op)
        print('  Rfloor', '{:.2f}'.format(Rfloor) + ';', file=op)
        print('  glazing_layers', str(glazing_layers) + ';', file=op)
        print('  glass_type', str(glass_type) + ';', file=op)
        print('  glazing_treatment', str(glazing_treatment) + ';', file=op)
        print('  window_frame', str(window_frame) + ';', file=op)
        print('  Rdoors', '{:.2f}'.format(Rdoor) + ';', file=op)
        print('  airchange_per_hour', '{:.2f}'.format(airchange) + ';', file=op)
        print('  cooling_COP', '{:.1f}'.format(c_COP) + ';', file=op)
        print('  air_temperature', '{:.2f}'.format(init_temp) + ';', file=op)
        print('  mass_temperature', '{:.2f}'.format(init_temp) + ';', file=op)
        print('  total_thermal_mass_per_floor_area', '{:.3f}'.format(mass_floor) + ';', file=op)
        print('  breaker_amps 1000;', file=op)
        print('  hvac_breaker_rating 1000;', file=op)
        heat_rand = np.random.uniform(0, 1)
        cool_rand = np.random.uniform(0, 1)
        if heat_rand <= rgnPenGasHeat[rgn - 1]:
            print('  heating_system_type GAS;', file=op)
            if cool_rand <= electric_cooling_percentage:
                print('  cooling_system_type ELECTRIC;', file=op)
            else:
                print('  cooling_system_type NONE;', file=op)
        elif heat_rand <= rgnPenGasHeat[rgn - 1] + rgnPenHeatPump[rgn - 1]:
            print('  heating_system_type HEAT_PUMP;', file=op)
            print('  heating_COP', '{:.1f}'.format(h_COP) + ';', file=op)
            print('  cooling_system_type ELECTRIC;', file=op)
            print('  auxiliary_strategy DEADBAND;', file=op)
            print('  auxiliary_system_type ELECTRIC;', file=op)
            print('  motor_model BASIC;', file=op)
            print('  motor_efficiency AVERAGE;', file=op)
        elif floor_area * ceiling_height > 12000.0:  # electric heat not allowed on large homes
            print('  heating_system_type GAS;', file=op)
            if cool_rand <= electric_cooling_percentage:
                print('  cooling_system_type ELECTRIC;', file=op)
            else:
                print('  cooling_system_type NONE;', file=op)
        else:
            print('  heating_system_type RESISTANCE;', file=op)
            if cool_rand <= electric_cooling_percentage:
                print('  cooling_system_type ELECTRIC;', file=op)
                print('  motor_model BASIC;', file=op)
                print('  motor_efficiency GOOD;', file=op)
            else:
                print('  cooling_system_type NONE;', file=op)

        cooling_sch = np.ceil(coolingScheduleNumber * np.random.uniform(0, 1))
        heating_sch = np.ceil(heatingScheduleNumber * np.random.uniform(0, 1))
        # Set point bins dict:[Bin Prob, NightTimeAvgDiff, HighBinSetting, LowBinSetting]
        cooling_bin, heating_bin = selectSetpointBins(bldg, np.random.uniform(0, 1))
        # randomly choose setpoints within bins, and then widen the separation to account for deadband
        cooling_set = cooling_bin[3] + np.random.uniform(0, 1) * (cooling_bin[2] - cooling_bin[3]) + setpoint_offset
        heating_set = heating_bin[3] + np.random.uniform(0, 1) * (heating_bin[2] - heating_bin[3]) - setpoint_offset
        cooling_diff = 2.0 * cooling_bin[1] * np.random.uniform(0, 1)
        heating_diff = 2.0 * heating_bin[1] * np.random.uniform(0, 1)
        cooling_scale = np.random.uniform(0.95, 1.05)
        heating_scale = np.random.uniform(0.95, 1.05)
        cooling_str = 'cooling{:.0f}*{:.4f}+{:.2f}'.format(cooling_sch, cooling_scale, cooling_diff)
        heating_str = 'heating{:.0f}*{:.4f}+{:.2f}'.format(heating_sch, heating_scale, heating_diff)
        # default heating and cooling setpoints are 70 and 75 degrees in GridLAB-D
        # we need more separation to assure no overlaps during transactive simulations
        if bIgnoreThermostatSchedule == True:
            print('  cooling_setpoint 80.0; // ', cooling_str + ';', file=op)
            print('  heating_setpoint 60.0; // ', heating_str + ';', file=op)
        else:
            print('  cooling_setpoint {:s};'.format(cooling_str), file=op)
            print('  heating_setpoint {:s};'.format(heating_str), file=op)

        # heatgain fraction, Zpf, Ipf, Ppf, Z, I, P
        print('  object ZIPload { // responsive', file=op)
        print('    schedule_skew', '{:.0f}'.format(skew_value) + ';', file=op)
        print('    base_power', 'responsive_loads*' + '{:.2f}'.format(resp_scalar) + ';', file=op)
        print('    heatgain_fraction', '{:.2f}'.format(techdata[0]) + ';', file=op)
        print('    impedance_pf', '{:.2f}'.format(techdata[1]) + ';', file=op)
        print('    current_pf', '{:.2f}'.format(techdata[2]) + ';', file=op)
        print('    power_pf', '{:.2f}'.format(techdata[3]) + ';', file=op)
        print('    impedance_fraction', '{:.2f}'.format(techdata[4]) + ';', file=op)
        print('    current_fraction', '{:.2f}'.format(techdata[5]) + ';', file=op)
        print('    power_fraction', '{:.2f}'.format(techdata[6]) + ';', file=op)
        print('  };', file=op)
        print('  object ZIPload { // unresponsive', file=op)
        print('    schedule_skew', '{:.0f}'.format(skew_value) + ';', file=op)
        print('    base_power', 'unresponsive_loads*' + '{:.2f}'.format(unresp_scalar) + ';', file=op)
        print('    heatgain_fraction', '{:.2f}'.format(techdata[0]) + ';', file=op)
        print('    impedance_pf', '{:.2f}'.format(techdata[1]) + ';', file=op)
        print('    current_pf', '{:.2f}'.format(techdata[2]) + ';', file=op)
        print('    power_pf', '{:.2f}'.format(techdata[3]) + ';', file=op)
        print('    impedance_fraction', '{:.2f}'.format(techdata[4]) + ';', file=op)
        print('    current_fraction', '{:.2f}'.format(techdata[5]) + ';', file=op)
        print('    power_fraction', '{:.2f}'.format(techdata[6]) + ';', file=op)
        print('  };', file=op)
        if np.random.uniform(0, 1) <= water_heater_percentage:  # rgnPenElecWH[rgn-1]:
            heat_element = 3.0 + 0.5 * np.random.randint(1, 6)  # numpy randint (lo, hi) returns lo..(hi-1)
            tank_set = 110 + 16 * np.random.uniform(0, 1)
            therm_dead = 4 + 4 * np.random.uniform(0, 1)
            tank_UA = 2 + 2 * np.random.uniform(0, 1)
            water_sch = np.ceil(waterHeaterScheduleNumber * np.random.uniform(0, 1))
            water_var = 0.95 + np.random.uniform(0, 1) * 0.1  # +/-5% variability
            wh_demand_type = 'large_'
            sizeIncr = np.random.randint(0, 3)  # MATLAB randi(imax) returns 1..imax
            sizeProb = np.random.uniform(0, 1)
            if sizeProb <= rgnWHSize[rgn - 1][0]:
                wh_size = 20 + sizeIncr * 5
                wh_demand_type = 'small_'
            elif sizeProb <= (rgnWHSize[rgn - 1][0] + rgnWHSize[rgn - 1][1]):
                wh_size = 30 + sizeIncr * 10
                if floor_area < 2000.0:
                    wh_demand_type = 'small_'
            else:
                if floor_area < 2000.0:
                    wh_size = 30 + sizeIncr * 10
                else:
                    wh_size = 50 + sizeIncr * 10
            wh_demand_str = wh_demand_type + '{:.0f}'.format(water_sch) + '*' + '{:.2f}'.format(water_var)
            wh_skew_value = 3 * residential_skew_std * np.random.randn()
            if wh_skew_value < -6 * residential_skew_max:
                wh_skew_value = -6 * residential_skew_max
            elif wh_skew_value > 6 * residential_skew_max:
                wh_skew_value = 6 * residential_skew_max
            print('  object waterheater {', file=op)
            print('    name', whname + ';', file=op)
            print('    schedule_skew', '{:.0f}'.format(wh_skew_value) + ';', file=op)
            print('    heating_element_capacity', '{:.1f}'.format(heat_element), 'kW;', file=op)
            print('    thermostat_deadband', '{:.1f}'.format(therm_dead) + ';', file=op)
            print('    location INSIDE;', file=op)
            print('    tank_diameter 1.5;', file=op)
            print('    tank_UA', '{:.1f}'.format(tank_UA) + ';', file=op)
            print('    water_demand', wh_demand_str + ';', file=op)
            print('    tank_volume', '{:.0f}'.format(wh_size) + ';', file=op)
            if np.random.uniform(0, 1) <= water_heater_participation:
                print('    waterheater_model MULTILAYER;', file=op)
                print('    discrete_step_size 60.0;', file=op)
                print('    lower_tank_setpoint', '{:.1f}'.format(tank_set - 5.0) + ';', file=op)
                print('    upper_tank_setpoint', '{:.1f}'.format(tank_set + 5.0) + ';', file=op)
                print('    T_mixing_valve', '{:.1f}'.format(tank_set) + ';', file=op)
            else:
                print('    tank_setpoint', '{:.1f}'.format(tank_set) + ';', file=op)
            if metrics_interval > 0 and "waterheater" in metrics:
                print('    object metrics_collector {', file=op)
                print('      interval', str(metrics_interval) + ';', file=op)
                print('    };', file=op)
            print('  };', file=op)
        if metrics_interval > 0 and "house" in metrics:
            print('  object metrics_collector {', file=op)
            print('    interval', str(metrics_interval) + ';', file=op)
            print('  };', file=op)
        print('}', file=op)
        # if PV is allowed, then only single-family houses can buy it,
        # and only the single-family houses with PV will also consider storage
        # if PV is not allowed, then any single-family house may consider storage (if allowed)
        # apartments and mobile homes may always consider storage, but not PV
        bConsiderStorage = True
        if bldg == 0:  # Single-family homes
            if solar_percentage > 0.0:
                bConsiderStorage = False
            if np.random.uniform(0, 1) <= solar_percentage:  # some single-family houses have PV
                bConsiderStorage = True
                panel_area = 0.1 * floor_area
                if panel_area < 162:
                    panel_area = 162
                elif panel_area > 270:
                    panel_area = 270
                inv_power = inverter_undersizing * (panel_area / 10.7642) * rated_insolation * array_efficiency
                solar_count += 1
                solar_kw += 0.001 * inv_power
                print('object {:s} {{'.format(meter_class), file=op)
                #                print('object triplex_meter {', file=op)
                print('  name', sol_m_name + ';', file=op)
                print('  parent', mtrname + ';', file=op)
                print('  phases', phs + ';', file=op)
                print('  nominal_voltage ' + str(vnom) + ';', file=op)
                print('  object inverter {', file=op)
                print('    name', sol_i_name + ';', file=op)
                print('    phases', phs + ';', file=op)
                print('    generator_status ONLINE;', file=op)
                print('    inverter_type FOUR_QUADRANT;', file=op)
                print('    inverter_efficiency 1;', file=op)
                print('    rated_power', '{:.0f}'.format(inv_power) + ';', file=op)
                print('    power_factor 1.0;', file=op)
                write_solar_inv_settings(op)
                print('    object solar {', file=op)
                print('      name', solname + ';', file=op)
                print('      panel_type SINGLE_CRYSTAL_SILICON;', file=op)
                print('      efficiency', '{:.2f}'.format(array_efficiency) + ';', file=op)
                print('      area', '{:.2f}'.format(panel_area) + ';', file=op)
                print('    };', file=op)
                if metrics_interval > 0 and "inverter" in metrics:
                    print('    object metrics_collector {', file=op)
                    print('      interval', str(metrics_interval) + ';', file=op)
                    print('    };', file=op)
                print('  };', file=op)
                print('}', file=op)
        if bConsiderStorage:
            if np.random.uniform(0, 1) <= storage_percentage:
                battery_count += 1
                print('object {:s} {{'.format(meter_class), file=op)
                #                print('object triplex_meter {', file=op)
                print('  name', bat_m_name + ';', file=op)
                print('  parent', mtrname + ';', file=op)
                print('  phases', phs + ';', file=op)
                print('  nominal_voltage ' + str(vnom) + ';', file=op)
                print('  object inverter {', file=op)
                print('    name', bat_i_name + ';', file=op)
                print('    phases', phs + ';', file=op)
                print('    generator_status ONLINE;', file=op)
                print('    generator_mode CONSTANT_PQ;', file=op)
                print('    inverter_type FOUR_QUADRANT;', file=op)
                print('    four_quadrant_control_mode', storage_inv_mode + ';', file=op)
                print('    V_base ${INV_VBASE};', file=op)
                print('    charge_lockout_time 1;', file=op)
                print('    discharge_lockout_time 1;', file=op)
                print('    rated_power', '{:.2f}'.format(rated_power) + ';', file=op)
                print('    max_charge_rate', '{:.2f}'.format(max_charge_rate) + ';', file=op)
                print('    max_discharge_rate', '{:.2f}'.format(max_discharge_rate) + ';', file=op)
                print('    sense_object', mtrname + ';', file=op)
                print('    charge_on_threshold -100;', file=op)
                print('    charge_off_threshold 0;', file=op)
                print('    discharge_off_threshold 2000;', file=op)
                print('    discharge_on_threshold 3000;', file=op)
                print('    inverter_efficiency', '{:.2f}'.format(inverter_efficiency) + ';', file=op)
                print('    power_factor 1.0;', file=op)
                print('    object battery { // Tesla Powerwall 2', file=op)
                print('      name', batname + ';', file=op)
                print('      use_internal_battery_model true;', file=op)
                print('      battery_type LI_ION;', file=op)
                print('      nominal_voltage 480;', file=op)
                print('      battery_capacity', '{:.2f}'.format(battery_capacity) + ';', file=op)
                print('      round_trip_efficiency', '{:.2f}'.format(round_trip_efficiency) + ';', file=op)
                print('      state_of_charge 0.50;', file=op)
                print('    };', file=op)
                if metrics_interval > 0 and "inverter" in metrics:
                    print('    object metrics_collector {', file=op)
                    print('      interval', str(metrics_interval) + ';', file=op)
                    print('    };', file=op)
                print('  };', file=op)
                print('}', file=op)


def write_substation(op, name, phs, vnom, vll):
    """Write the substation swing node, transformer, metrics collector and fncs_msg object

    Args:
        op (file): an open GridLAB-D input file
        name (str): node name of the primary (not transmission) substation bus
        phs (str): primary phasing in the substation
        vnom (float): not used
        vll (float): feeder primary line-to-line voltage
    """
    # if this feeder will be combined with others, need USE_FNCS to appear first as a marker for the substation
    if len(case_name) > 0:
        print('#ifdef USE_FNCS', file=op)
        print('object fncs_msg {', file=op)
        print('  name gld_' + str(dso_substation_bus_id) + ';', file=op)
        print('  parent network_node;', file=op)
        print('  configure', case_name + '_gridlabd.txt;', file=op)
        print('  option "transport:hostname localhost, port ' + str(port) + '";', file=op)
        print('  aggregate_subscriptions true;', file=op)
        print('  aggregate_publications true;', file=op)
        print('}', file=op)
        print('#endif', file=op)
        print('', file=op)
        print('#ifdef USE_HELICS', file=op)
        print('object helics_msg {', file=op)
        print('  name gld_' + str(dso_substation_bus_id) + ';', file=op)
        print('  configure', case_name + '_gridlabd.json;', file=op)
        print('}', file=op)
        print('#endif', file=op)
    print('object transformer_configuration {', file=op)
    print('  name substation_xfmr_config;', file=op)
    print('  connect_type WYE_WYE;', file=op)
    print('  install_type PADMOUNT;', file=op)
    print('  primary_voltage', '{:.2f}'.format(transmissionVoltage) + ';', file=op)
    print('  secondary_voltage', '{:.2f}'.format(vll) + ';', file=op)
    print('  power_rating', '{:.2f}'.format(transmissionXfmrMVAbase * 1000.0) + ';', file=op)
    print('  resistance', '{:.2f}'.format(0.01 * transmissionXfmrRpct) + ';', file=op)
    print('  reactance', '{:.2f}'.format(0.01 * transmissionXfmrXpct) + ';', file=op)
    print('  shunt_resistance', '{:.2f}'.format(100.0 / transmissionXfmrNLLpct) + ';', file=op)
    print('  shunt_reactance', '{:.2f}'.format(100.0 / transmissionXfmrImagpct) + ';', file=op)
    print('}', file=op)
    print('object transformer {', file=op)
    print('  name substation_transformer;', file=op)
    print('  from network_node;', file=op)
    print('  to', name + ';', file=op)
    print('  phases', phs + ';', file=op)
    print('  configuration substation_xfmr_config;', file=op)
    print('}', file=op)
    vsrcln = transmissionVoltage / sqrt(3.0)
    print('object substation {', file=op)
    print('  name network_node;', file=op)
    print('  groupid', base_feeder_name + ';', file=op)
    print('  bustype SWING;', file=op)
    print('  nominal_voltage', '{:.2f}'.format(vsrcln) + ';', file=op)
    print('  positive_sequence_voltage', '{:.2f}'.format(vsrcln) + ';', file=op)
    print('  base_power', '{:.2f}'.format(transmissionXfmrMVAbase * 1000000.0) + ';', file=op)
    print('  power_convergence_value 100.0;', file=op)
    print('  phases', phs + ';', file=op)
    if metrics_interval > 0 and "substation" in metrics:
        print('  object metrics_collector {', file=op)
        print('    interval', str(metrics_interval) + ';', file=op)
        print('  };', file=op)
        # debug
        # print('  object recorder {', file=op)
        # print('    property distribution_power_A;', file=op)
        # print('    file sub_power.csv;', file=op)
        # print('    interval 300;')
        # print('  };', file=op)
    print('}', file=op)


# if triplex load, node or meter, the nominal voltage is 120
#   if the name or parent attribute is found in secmtrnode, we look up the nominal voltage there
#   otherwise, the nominal voltage is vprim
# secmtrnode[mtr_node] = [kva_total, phases, vnom]
#   the transformer phasing was not changed, and the transformers were up-sized to the largest phase kva
#   therefore, it should not be necessary to look up kva_total, but phases might have changed N==>S
# if the phasing did change N==>S, we have to prepend triplex_ to the class, write power_1 and voltage_1
# when writing commercial buildings, if load_class is present and == C, skip the instance
def write_voltage_class(model, h, t, op, vprim, vll, secmtrnode):
    """Write GridLAB-D instances that have a primary nominal voltage, i.e., node, meter and load

    Args:
        model (dict): a parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class name to write
        op (file): an open GridLAB-D input file
        vprim (float): the primary nominal line-to-neutral voltage
        vll (float): the primary nominal line-to-line voltage
        secmtrnode (dict): key to [transfomer kva, phasing, nominal voltage] by secondary node name
    """
    if t in model:
        for o in model[t]:
            #            if 'load_class' in model[t][o]:
            #                if model[t][o]['load_class'] == 'C':
            #                    continue
            name = o  # model[t][o]['name']
            phs = model[t][o]['phases']
            vnom = vprim
            if 'bustype' in model[t][o]:
                if model[t][o]['bustype'] == 'SWING':
                    write_substation(op, name, phs, vnom, vll)
            parent = ''
            prefix = ''
            if str.find(phs, 'S') >= 0:
                bHadS = True
            else:
                bHadS = False
            if str.find(name, '_tn_') >= 0 or str.find(name, '_tm_') >= 0:
                vnom = 120.0
            if name in secmtrnode:
                vnom = secmtrnode[name][2]
                phs = secmtrnode[name][1]
            if 'parent' in model[t][o]:
                parent = gld_strict_name(model[t][o]['parent'])
                if parent in secmtrnode:
                    vnom = secmtrnode[parent][2]
                    phs = secmtrnode[parent][1]
            if str.find(phs, 'S') >= 0:
                bHaveS = True
            else:
                bHaveS = False
            if bHaveS and not bHadS:
                prefix = 'triplex_'
            print('object ' + prefix + t + ' {', file=op)
            if len(parent) > 0:
                print('  parent ' + parent + ';', file=op)
            print('  name ' + gld_strict_name(name) + ';', file=op)
            if 'groupid' in model[t][o]:
                print('  groupid ' + model[t][o]['groupid'] + ';', file=op)
            if 'bustype' in model[t][o]:  # already moved the SWING bus behind substation transformer
                if model[t][o]['bustype'] != 'SWING':
                    print('  bustype ' + model[t][o]['bustype'] + ';', file=op)
            print('  phases ' + phs + ';', file=op)
            print('  nominal_voltage ' + str(vnom) + ';', file=op)
            if 'load_class' in model[t][o]:
                print('  load_class ' + model[t][o]['load_class'] + ';', file=op)
            if 'constant_power_A' in model[t][o]:
                if bHaveS:
                    print('  power_1 ' + model[t][o]['constant_power_A'] + ';', file=op)
                else:
                    print('  constant_power_A ' + model[t][o]['constant_power_A'] + ';', file=op)
            if 'constant_power_B' in model[t][o]:
                if bHaveS:
                    print('  power_1 ' + model[t][o]['constant_power_B'] + ';', file=op)
                else:
                    print('  constant_power_B ' + model[t][o]['constant_power_B'] + ';', file=op)
            if 'constant_power_C' in model[t][o]:
                if bHaveS:
                    print('  power_1 ' + model[t][o]['constant_power_C'] + ';', file=op)
                else:
                    print('  constant_power_C ' + model[t][o]['constant_power_C'] + ';', file=op)
            if 'power_1' in model[t][o]:
                print('  power_1 ' + model[t][o]['power_1'] + ';', file=op)
            if 'power_2' in model[t][o]:
                print('  power_2 ' + model[t][o]['power_2'] + ';', file=op)
            if 'power_12' in model[t][o]:
                print('  power_12 ' + model[t][o]['power_12'] + ';', file=op)
            vstarta = str(vnom) + '+0.0j'
            vstartb = format(-0.5 * vnom, '.2f') + format(-0.866025 * vnom, '.2f') + 'j'
            vstartc = format(-0.5 * vnom, '.2f') + '+' + format(0.866025 * vnom, '.2f') + 'j'
            if 'voltage_A' in model[t][o]:
                if bHaveS:
                    print('  voltage_1 ' + vstarta + ';', file=op)
                    print('  voltage_2 ' + vstarta + ';', file=op)
                else:
                    print('  voltage_A ' + vstarta + ';', file=op)
            if 'voltage_B' in model[t][o]:
                if bHaveS:
                    print('  voltage_1 ' + vstartb + ';', file=op)
                    print('  voltage_2 ' + vstartb + ';', file=op)
                else:
                    print('  voltage_B ' + vstartb + ';', file=op)
            if 'voltage_C' in model[t][o]:
                if bHaveS:
                    print('  voltage_1 ' + vstartc + ';', file=op)
                    print('  voltage_2 ' + vstartc + ';', file=op)
                else:
                    print('  voltage_C ' + vstartc + ';', file=op)
            if 'power_1' in model[t][o]:
                print('  power_1 ' + model[t][o]['power_1'] + ';', file=op)
            if 'power_2' in model[t][o]:
                print('  power_2 ' + model[t][o]['power_2'] + ';', file=op)
            if 'voltage_1' in model[t][o]:
                if str.find(phs, 'A') >= 0:
                    print('  voltage_1 ' + vstarta + ';', file=op)
                    print('  voltage_2 ' + vstarta + ';', file=op)
                if str.find(phs, 'B') >= 0:
                    print('  voltage_1 ' + vstartb + ';', file=op)
                    print('  voltage_2 ' + vstartb + ';', file=op)
                if str.find(phs, 'C') >= 0:
                    print('  voltage_1 ' + vstartc + ';', file=op)
                    print('  voltage_2 ' + vstartc + ';', file=op)
            if name in extra_billing_meters:
                write_tariff(op)
                if metrics_interval > 0 and "meter" in metrics:
                    print('  object metrics_collector {', file=op)
                    print('    interval', str(metrics_interval) + ';', file=op)
                    print('  };', file=op)
            print('}', file=op)


def write_xfmr_config(key, phs, kvat, vnom, vsec, install_type, vprimll, vprimln, op):
    """Write a transformer_configuration

    Args:
        key (str): name of the configuration
        phs (str): primary phasing
        kvat (float): transformer rating in kVA
        vnom (float): primary voltage rating, not used any longer (see vprimll and vprimln)
        vsec (float): secondary voltage rating,
                      should be line-to-neutral for single-phase or line-to-line for three-phase
        install_type (str): should be VAULT, PADMOUNT or POLETOP
        vprimll (float): primary line-to-line voltage, used for three-phase transformers
        vprimln (float): primary line-to-neutral voltage, used for single-phase transformers
        op (file): an open GridLAB-D input file
    """
    print('object transformer_configuration {', file=op)
    print('  name ' + name_prefix + key + ';', file=op)
    print('  power_rating ' + format(kvat, '.2f') + ';', file=op)
    kvaphase = kvat
    if 'XF2' in key:
        kvaphase /= 2.0
    if 'XF3' in key:
        kvaphase /= 3.0
    if 'A' in phs:
        print('  powerA_rating ' + format(kvaphase, '.2f') + ';', file=op)
    else:
        print('  powerA_rating 0.0;', file=op)
    if 'B' in phs:
        print('  powerB_rating ' + format(kvaphase, '.2f') + ';', file=op)
    else:
        print('  powerB_rating 0.0;', file=op)
    if 'C' in phs:
        print('  powerC_rating ' + format(kvaphase, '.2f') + ';', file=op)
    else:
        print('  powerC_rating 0.0;', file=op)
    print('  install_type ' + install_type + ';', file=op)
    if 'S' in phs:
        row = Find1PhaseXfmr(kvat)
        print('  connect_type SINGLE_PHASE_CENTER_TAPPED;', file=op)
        print('  primary_voltage ' + str(vprimln) + ';', file=op)
        print('  secondary_voltage ' + format(vsec, '.1f') + ';', file=op)
        print('  resistance ' + format(row[1] * 0.5, '.5f') + ';', file=op)
        print('  resistance1 ' + format(row[1], '.5f') + ';', file=op)
        print('  resistance2 ' + format(row[1], '.5f') + ';', file=op)
        print('  reactance ' + format(row[2] * 0.8, '.5f') + ';', file=op)
        print('  reactance1 ' + format(row[2] * 0.4, '.5f') + ';', file=op)
        print('  reactance2 ' + format(row[2] * 0.4, '.5f') + ';', file=op)
        print('  shunt_resistance ' + format(1.0 / row[3], '.2f') + ';', file=op)
        print('  shunt_reactance ' + format(1.0 / row[4], '.2f') + ';', file=op)
    else:
        row = Find3PhaseXfmr(kvat)
        print('  connect_type WYE_WYE;', file=op)
        print('  primary_voltage ' + str(vprimll) + ';', file=op)
        print('  secondary_voltage ' + format(vsec, '.1f') + ';', file=op)
        print('  resistance ' + format(row[1], '.5f') + ';', file=op)
        print('  reactance ' + format(row[2], '.5f') + ';', file=op)
        print('  shunt_resistance ' + format(1.0 / row[3], '.2f') + ';', file=op)
        print('  shunt_reactance ' + format(1.0 / row[4], '.2f') + ';', file=op)
    print('}', file=op)


def log_model(model, h):
    """Prints the whole parsed model for debugging

    Args:
        model (dict): parsed GridLAB-D model
        h (dict): object ID hash
    """
    for t in model:
        print(t + ':')
        for o in model[t]:
            print('\t' + o + ':')
            for p in model[t][o]:
                if ':' in model[t][o][p]:
                    print('\t\t' + p + '\t-->\t' + h[model[t][o][p]])
                else:
                    print('\t\t' + p + '\t-->\t' + model[t][o][p])


def accumulate_load_kva(data):
    """Add up the total kva in a load-bearing object instance

    Considers constant_power_A/B/C/1/2/12 and power_1/2/12 attributes

    Args:
        data (dict): dictionary of data for a selected GridLAB-D instance
    """
    kva = 0.0
    if 'constant_power_A' in data:
        kva += parse_kva(data['constant_power_A'])
    if 'constant_power_B' in data:
        kva += parse_kva(data['constant_power_B'])
    if 'constant_power_C' in data:
        kva += parse_kva(data['constant_power_C'])
    if 'constant_power_1' in data:
        kva += parse_kva(data['constant_power_1'])
    if 'constant_power_2' in data:
        kva += parse_kva(data['constant_power_2'])
    if 'constant_power_12' in data:
        kva += parse_kva(data['constant_power_12'])
    if 'power_1' in data:
        kva += parse_kva(data['power_1'])
    if 'power_2' in data:
        kva += parse_kva(data['power_2'])
    if 'power_12' in data:
        kva += parse_kva(data['power_12'])
    return kva


def union_of_phases(phs1, phs2):
    """Collect all phases on both sides of a connection

    Args:
        phs1 (str): first phasing
        phs2 (str): second phasing

    Returns:
        str: union of phs1 and phs2
    """
    phs = ''
    if 'A' in phs1 or 'A' in phs2:
        phs += 'A'
    if 'B' in phs1 or 'B' in phs2:
        phs += 'B'
    if 'C' in phs1 or 'C' in phs2:
        phs += 'C'
    if 'S' in phs1 or 'S' in phs2:
        phs += 'S'
    return phs


def ProcessTaxonomyFeeder(outname, rootname, vll, vln, avghouse, avgcommercial):
    """Parse and re-populate one backbone feeder, usually but not necessarily one of the PNNL taxonomy feeders

    This function:

        * reads and parses the backbone model from *rootname.glm*
        * replaces loads with houses and DER
        * upgrades transformers and fuses as needed, based on a radial graph analysis
        * writes the repopulated feeder to *outname.glm*

    Args:
        outname (str): the output feeder model name
        rootname (str): the input (usually taxonomy) feeder model name
        vll (float): the feeder primary line-to-line voltage
        vln (float): the feeder primary line-to-neutral voltage
        avghouse (float): the average house load in kVA
        avgcommercial (float): the average commercial load in kVA, not used
    """
    global solar_count, solar_kw, battery_count, ev_count, base_feeder_name
    global electric_cooling_percentage, storage_percentage, solar_percentage, ev_percentage
    global water_heater_percentage, water_heater_participation

    solar_count = 0
    solar_kw = 0
    battery_count = 0
    ev_count = 0

    base_feeder_name = gld_strict_name(rootname)
    fname = feeders_path + rootname + '.glm'
    print('Populating From:', fname)
    rootname = gld_strict_name(rootname)
    rgn = 0
    if 'R1' in rootname:
        rgn = 1
    elif 'R2' in rootname:
        rgn = 2
    elif 'R3' in rootname:
        rgn = 3
    elif 'R4' in rootname:
        rgn = 4
    elif 'R5' in rootname:
        rgn = 5
    print('using', solar_percentage, 'solar and', storage_percentage, 'storage penetration')
    if electric_cooling_percentage <= 0.0:
        electric_cooling_percentage = rgnPenElecCool[rgn - 1]
        print('using regional default', electric_cooling_percentage, 'air conditioning penetration')
    else:
        print('using', electric_cooling_percentage, 'air conditioning penetration from JSON config')
    if water_heater_percentage <= 0.0:
        water_heater_percentage = rgnPenElecWH[rgn - 1]
        print('using regional default', water_heater_percentage, 'water heater penetration')
    else:
        print('using', water_heater_percentage, 'water heater penetration from JSON config')
    if os.path.isfile(fname):
        ip = open(fname, 'r')
        lines = []
        line = ip.readline()
        while line != '':
            while re.match('\s*//', line) or re.match('\s+$', line):
                # skip comments and white space
                line = ip.readline()
            lines.append(line.rstrip())
            line = ip.readline()
        ip.close()

        op = open(work_path + outname + '.glm', 'w')
        print('###### Writing to', work_path + outname + '.glm')
        octr = 0
        model = {}
        h = {}  # OID hash
        itr = iter(lines)
        for line in itr:
            if re.search('object', line):
                line, octr = obj(None, model, line, itr, h, octr)
            else:  # should be the pre-amble, need to replace timestamp and stoptime
                if 'timestamp' in line or 'starttime' in line:
                    print('  starttime \'' + starttime + '\';', file=op)
                elif 'stoptime' in line:
                    print('  stoptime \'' + endtime + '\';', file=op)
                else:
                    print(line, file=op)

        # apply the nameing prefix if necessary
        if len(name_prefix) > 0:
            for t in model:
                for o in model[t]:
                    elem = model[t][o]
                    for tok in ['name', 'parent', 'from', 'to', 'configuration', 'spacing',
                                'conductor_1', 'conductor_2', 'conductor_N',
                                'conductor_A', 'conductor_B', 'conductor_C']:
                        if tok in elem:
                            elem[tok] = name_prefix + elem[tok]

        #        log_model (model, h)

        # construct a graph of the model, starting with known links
        G = nx.Graph()
        for t in model:
            if is_edge_class(t):
                for o in model[t]:
                    n1 = gld_strict_name(model[t][o]['from'])
                    n2 = gld_strict_name(model[t][o]['to'])
                    G.add_edge(n1, n2, eclass=t, ename=o, edata=model[t][o])

        # add the parent-child node links
        for t in model:
            if is_node_class(t):
                for o in model[t]:
                    if 'parent' in model[t][o]:
                        p = gld_strict_name(model[t][o]['parent'])
                        G.add_edge(o, p, eclass='parent', ename=o, edata={})

        # now we backfill node attributes
        for t in model:
            if is_node_class(t):
                for o in model[t]:
                    if o in G.nodes():
                        G.nodes()[o]['nclass'] = t
                        G.nodes()[o]['ndata'] = model[t][o]
                    else:
                        print('orphaned node', t, o)

        swing_node = ''
        for n1, data in G.nodes(data=True):
            if 'nclass' in data:
                if 'bustype' in data['ndata']:
                    if data['ndata']['bustype'] == 'SWING':
                        swing_node = n1

        sub_graphs = nx.connected_components(G)
        seg_loads = {}  # [name][kva, phases]
        total_kva = 0.0
        for n1, data in G.nodes(data=True):
            if 'ndata' in data:
                kva = accumulate_load_kva(data['ndata'])
                # need to account for large-building loads added through transformer connections
                if n1 == Eplus_Bus:
                    kva += Eplus_kVA
                if kva > 0:
                    total_kva += kva
                    nodes = nx.shortest_path(G, n1, swing_node)
                    edges = zip(nodes[0:], nodes[1:])
                    for u, v in edges:
                        eclass = G[u][v]['eclass']
                        if is_edge_class(eclass):
                            ename = G[u][v]['ename']
                            if ename not in seg_loads:
                                seg_loads[ename] = [0.0, '']
                            seg_loads[ename][0] += kva
                            seg_loads[ename][1] = union_of_phases(seg_loads[ename][1], data['ndata']['phases'])

        print('  swing node', swing_node, 'with', len(list(sub_graphs)), 'subgraphs and',
              '{:.2f}'.format(total_kva), 'total kva')

        # preparatory items for TESP
        print('module climate;', file=op)
        print('module generators;', file=op)
        print('module connection;', file=op)
        print('module residential {', file=op)
        print('  implicit_enduses NONE;', file=op)
        print('}', file=op)
        print('#include "${TESPDIR}/data/schedules/appliance_schedules.glm";', file=op)
        print('#include "${TESPDIR}/data/schedules/water_and_setpoint_schedule_v5.glm";', file=op)
        print('#include "${TESPDIR}/data/schedules/commercial_schedules.glm";', file=op)
        print('#set minimum_timestep=' + str(timestep) + ';', file=op)
        print('#set relax_naming_rules=1;', file=op)
        print('#set warn=0;', file=op)

        if metrics_interval > 0:
            print('object metrics_collector_writer {', file=op)
            print('  interval', str(metrics_interval) + ';', file=op)
            print('  interim', str(metrics_interim) + ';', file=op)
            print('  filename ${METRICS_FILE};', file=op)
            print('}', file=op)

        print('object climate {', file=op)
        print('  name', str(weather_name) + ';', file=op)
        print('  // tmyfile "' + weather_file + '";', file=op)
        print('  interpolate QUADRATIC;', file=op)
        print('  latitude', str(latitude) + ';', file=op)
        print('  longitude', str(longitude) + ';', file=op)
        print('  // altitude', str(altitude) + ';', file=op)
        print('  tz_meridian', str(tz_meridian) + ';', file=op)
        print('}', file=op)

        #        print('// taxonomy_base_feeder', rootname, file=op)
        #        print('// region_name', rgnName[rgn-1], file=op)
        if solar_percentage > 0.0:
            print('// default IEEE 1547-2018 settings for Category B', file=op)
            print('// solar inverter mode on this feeder', file=op)
            print('#define ' + name_prefix + 'INVERTER_MODE=' + solar_inv_mode, file=op)
            print('#define INV_VBASE=240.0', file=op)
            print('#define INV_V1=0.92', file=op)
            print('#define INV_V2=0.98', file=op)
            print('#define INV_V3=1.02', file=op)
            print('#define INV_V4=1.08', file=op)
            print('#define INV_Q1=0.44', file=op)
            print('#define INV_Q2=0.00', file=op)
            print('#define INV_Q3=0.00', file=op)
            print('#define INV_Q4=-0.44', file=op)
            print('#define INV_VIN=200.0', file=op)
            print('#define INV_IIN=32.5', file=op)
            print('#define INV_VVLOCKOUT=300.0', file=op)
            print('#define INV_VW_V1=1.05 // 1.05833', file=op)
            print('#define INV_VW_V2=1.10', file=op)
            print('#define INV_VW_P1=1.0', file=op)
            print('#define INV_VW_P2=0.0', file=op)

            if solar_path + solar_P_player != "":
                print('// player class and object for solar P_out and Q_out', file=op)
                print('class player {', file=op)
                print('  double value; // must defined the filed "value"', file=op)
                print('}', file=op)
                print('object player {', file=op)
                print('  name P_out_inj;', file=op)
                print('  file "' + solar_path + solar_P_player + '";', file=op)
                print('}', file=op)
                if solar_Q_player != "":
                    print('object player {', file=op)
                    print('  name Q_out_inj;', file=op)
                    print('  file "' + solar_path + solar_Q_player + '";', file=op)
                    print('}', file=op)

        # write the optional volt_dump and curr_dump for validation
        print('#ifdef WANT_VI_DUMP', file=op)
        print('object voltdump {', file=op)
        print('  filename Voltage_Dump_' + outname + '.csv;', file=op)
        # print('  mode POLAR;', file=op)
        print('}', file=op)
        print('object currdump {', file=op)
        print('  filename Current_Dump_' + outname + '.csv;', file=op)
        # print('  mode POLAR;', file=op)
        print('}', file=op)
        print('#endif // &&& end of common section for combining TESP cases', file=op)

        # NEW STRATEGY - loop through transformer instances and assign a standard size based on the downstream load
        #              - change the referenced transformer_configuration attributes
        #              - write the standard transformer_configuration instances we actually need
        xfused = {}  # ID, phases, total kva, vnom (LN), vsec, poletop/padmount
        secnode = {}  # Node, st, phases, vnom
        t = 'transformer'
        if t not in model:
            model[t] = {}
        for o in model[t]:
            seg_kva = seg_loads[o][0]
            seg_phs = seg_loads[o][1]
            nphs = 0
            if 'A' in seg_phs:
                nphs += 1
            if 'B' in seg_phs:
                nphs += 1
            if 'C' in seg_phs:
                nphs += 1
            if nphs > 1:
                kvat = Find3PhaseXfmrKva(seg_kva)
            else:
                kvat = Find1PhaseXfmrKva(seg_kva)
            if 'S' in seg_phs:
                vnom = 120.0
                vsec = 120.0
            else:
                if 'N' not in seg_phs:
                    seg_phs += 'N'
                if kvat > max208kva:
                    vsec = 480.0
                    vnom = 277.0
                else:
                    vsec = 208.0
                    vnom = 120.0

            secnode[gld_strict_name(model[t][o]['to'])] = [kvat, seg_phs, vnom]

            old_key = h[model[t][o]['configuration']]
            install_type = model['transformer_configuration'][old_key]['install_type']

            raw_key = 'XF' + str(nphs) + '_' + install_type + '_' + seg_phs + '_' + str(kvat)
            key = raw_key.replace('.', 'p')

            model[t][o]['configuration'] = name_prefix + key
            model[t][o]['phases'] = seg_phs
            if key not in xfused:
                xfused[key] = [seg_phs, kvat, vnom, vsec, install_type]

        for key in xfused:
            write_xfmr_config(key, xfused[key][0], xfused[key][1], xfused[key][2], xfused[key][3],
                              xfused[key][4], vll, vln, op)

        t = 'capacitor'
        if t in model:
            for o in model[t]:
                model[t][o]['nominal_voltage'] = str(int(vln))
                model[t][o]['cap_nominal_voltage'] = str(int(vln))

        t = 'fuse'
        if t not in model:
            model[t] = {}
        for o in model[t]:
            if o in seg_loads:
                seg_kva = seg_loads[o][0]
                seg_phs = seg_loads[o][1]
                nphs = 0
                if 'A' in seg_phs:
                    nphs += 1
                if 'B' in seg_phs:
                    nphs += 1
                if 'C' in seg_phs:
                    nphs += 1
                if nphs == 3:
                    amps = 1000.0 * seg_kva / sqrt(3.0) / vll
                elif nphs == 2:
                    amps = 1000.0 * seg_kva / 2.0 / vln
                else:
                    amps = 1000.0 * seg_kva / vln
                model[t][o]['current_limit'] = str(FindFuseLimit(amps))

        write_local_triplex_configurations(op)

        write_config_class(model, h, 'regulator_configuration', op)
        write_config_class(model, h, 'overhead_line_conductor', op)
        write_config_class(model, h, 'line_spacing', op)
        write_config_class(model, h, 'line_configuration', op)
        write_config_class(model, h, 'triplex_line_conductor', op)
        write_config_class(model, h, 'triplex_line_configuration', op)
        write_config_class(model, h, 'underground_line_conductor', op)

        write_link_class(model, h, 'fuse', seg_loads, op)
        write_link_class(model, h, 'switch', seg_loads, op)
        write_link_class(model, h, 'recloser', seg_loads, op)
        write_link_class(model, h, 'sectionalizer', seg_loads, op)

        write_link_class(model, h, 'overhead_line', seg_loads, op)
        write_link_class(model, h, 'underground_line', seg_loads, op)
        write_link_class(model, h, 'series_reactor', seg_loads, op)

        write_link_class(model, h, 'regulator', seg_loads, op, want_metrics=True)
        write_link_class(model, h, 'transformer', seg_loads, op)
        write_link_class(model, h, 'capacitor', seg_loads, op, want_metrics=True)

        if forERCOT:
            replace_commercial_loads(model, h, 'load', 0.001 * avgcommercial)
            # connect_ercot_commercial (op)
            identify_ercot_houses(model, h, 'load', 0.001 * avghouse, rgn)
            connect_ercot_houses(model, h, op, vln, 120.0)
            for key in house_nodes:
                write_houses(key, op, 120.0)
            for key in small_nodes:
                write_ercot_small_loads(key, op, vln)
            for key in comm_loads:
                write_commercial_loads(rgn, key, op)
        else:
            replace_commercial_loads(model, h, 'load', 0.001 * avgcommercial)
            identify_xfmr_houses(model, h, 'transformer', seg_loads, 0.001 * avghouse, rgn)
            for key in house_nodes:
                write_houses(key, op, 120.0)
            for key in small_nodes:
                write_small_loads(key, op, 120.0)
            for key in comm_loads:
                write_commercial_loads(rgn, key, op)

        write_voltage_class(model, h, 'node', op, vln, vll, secnode)
        write_voltage_class(model, h, 'meter', op, vln, vll, secnode)
        if not forERCOT:
            write_voltage_class(model, h, 'load', op, vln, vll, secnode)
        if len(Eplus_Bus) > 0 and Eplus_Volts > 0.0 and Eplus_kVA > 0.0:
            print('////////// EnergyPlus large-building load ///////////////', file=op)
            row = Find3PhaseXfmr(Eplus_kVA)
            actual_kva = row[0]
            watts_per_phase = 1000.0 * actual_kva / 3.0
            Eplus_vln = Eplus_Volts / sqrt(3.0)
            vstarta = format(Eplus_vln, '.2f') + '+0.0j'
            vstartb = format(-0.5 * Eplus_vln, '.2f') + format(-0.866025 * Eplus_vln, '.2f') + 'j'
            vstartc = format(-0.5 * Eplus_vln, '.2f') + '+' + format(0.866025 * Eplus_vln, '.2f') + 'j'
            print('object transformer_configuration {', file=op)
            print('  name ' + name_prefix + 'Eplus_transformer_configuration;', file=op)
            print('  connect_type WYE_WYE;', file=op)
            print('  install_type PADMOUNT;', file=op)
            print('  power_rating', str(actual_kva) + ';', file=op)
            print('  primary_voltage ' + str(vll) + ';', file=op)
            print('  secondary_voltage ' + format(Eplus_Volts, '.1f') + ';', file=op)
            print('  resistance ' + format(row[1], '.5f') + ';', file=op)
            print('  reactance ' + format(row[2], '.5f') + ';', file=op)
            print('  shunt_resistance ' + format(1.0 / row[3], '.2f') + ';', file=op)
            print('  shunt_reactance ' + format(1.0 / row[4], '.2f') + ';', file=op)
            print('}', file=op)
            print('object transformer {', file=op)
            print('  name ' + name_prefix + 'Eplus_transformer;', file=op)
            print('  phases ABCN;', file=op)
            print('  from ' + name_prefix + Eplus_Bus + ';', file=op)
            print('  to ' + name_prefix + 'Eplus_meter;', file=op)
            print('  configuration ' + name_prefix + 'Eplus_transformer_configuration;', file=op)
            print('}', file=op)
            print('object meter {', file=op)
            print('  name ' + name_prefix + 'Eplus_meter;', file=op)
            print('  phases ABCN;', file=op)
            print('  meter_power_consumption 1+15j;', file=op)
            print('  nominal_voltage', '{:.4f}'.format(Eplus_vln) + ';', file=op)
            print('  voltage_A ' + vstarta + ';', file=op)
            print('  voltage_B ' + vstartb + ';', file=op)
            print('  voltage_C ' + vstartc + ';', file=op)
            write_tariff(op)
            if metrics_interval > 0 and "meter" in metrics:
                print('  object metrics_collector {', file=op)
                print('    interval', str(metrics_interval) + ';', file=op)
                print('  };', file=op)
            print('}', file=op)
            print('object load {', file=op)
            print('  name ' + name_prefix + 'Eplus_load;', file=op)
            print('  parent ' + name_prefix + 'Eplus_meter;', file=op)
            print('  phases ABCN;', file=op)
            print('  nominal_voltage', '{:.4f}'.format(Eplus_vln) + ';', file=op)
            print('  voltage_A ' + vstarta + ';', file=op)
            print('  voltage_B ' + vstartb + ';', file=op)
            print('  voltage_C ' + vstartc + ';', file=op)
            print('  constant_power_A', '{:.1f}'.format(watts_per_phase) + ';', file=op)
            print('  constant_power_B', '{:.1f}'.format(watts_per_phase) + ';', file=op)
            print('  constant_power_C', '{:.1f}'.format(watts_per_phase) + ';', file=op)
            print('}', file=op)

        print('cooling bins unused', cooling_bins)
        print('heating bins unused', heating_bins)
        print(solar_count, 'pv totaling', '{:.1f}'.format(solar_kw), 'kw with', battery_count, 'batteries')

        op.close()


def write_kersting_triplex(fp, kva):
    """Writes a triplex_line_configuration based on 1/0 AA example from Kersting's book

    The conductor capacity is 202 amps, so the number of triplex in parallel will be kva/0.12/202
    """
    key = 'tpx_cfg_{:d}'.format(int(kva))
    amps = kva / 0.12
    npar = ceil(amps / 202.0)
    apar = 202.0 * npar
    scale = 5280.0 / 100.0 / npar  # for impedance per mile of parallel circuits
    r11 = 0.0271 * scale
    x11 = 0.0146 * scale
    r12 = 0.0087 * scale
    x12 = 0.0081 * scale
    print('object triplex_line_configuration {{ // {:d} 1/0 AA in parallel'.format(int(npar)), file=fp)
    print('  name {:s};'.format(key), file=fp)
    print('  z11 {:.4f}+{:.4f}j;'.format(r11, x11), file=fp)
    print('  z12 {:.4f}+{:.4f}j;'.format(r12, x12), file=fp)
    print('  z21 {:.4f}+{:.4f}j;'.format(r12, x12), file=fp)
    print('  z22 {:.4f}+{:.4f}j;'.format(r11, x11), file=fp)
    print('  rating.summer.continuous {:.1f};'.format(apar), file=fp)
    print('  rating.summer.emergency {:.1f};'.format(apar), file=fp)
    print('  rating.winter.continuous {:.1f};'.format(apar), file=fp)
    print('  rating.winter.emergency {:.1f};'.format(apar), file=fp)
    print('}', file=fp)


def write_kersting_quadriplex(fp, kva):
    """Writes a quadriplex_line_configuration based on 1/0 AA example from Kersting's book

    The conductor capacity is 202 amps, so the number of triplex in parallel will be kva/sqrt(3)/0.208/202
    """
    key = 'quad_cfg_{:d}'.format(int(kva))
    amps = kva / sqrt(3.0) / 0.208
    npar = ceil(amps / 202.0)
    apar = 202.0 * npar
    scale = 5280.0 / 100.0 / npar  # for impedance per mile of parallel circuits
    r11 = 0.0268 * scale
    x11 = 0.0160 * scale
    r12 = 0.0080 * scale
    x12 = 0.0103 * scale
    r13 = 0.0085 * scale
    x13 = 0.0095 * scale
    r22 = 0.0258 * scale
    x22 = 0.0176 * scale
    print('object line_configuration {{ // {:d} 1/0 AA in parallel'.format(int(npar)), file=fp)
    print('  name {:s};'.format(key), file=fp)
    print('  z11 {:.4f}+{:.4f}j;'.format(r11, x11), file=fp)
    print('  z12 {:.4f}+{:.4f}j;'.format(r12, x12), file=fp)
    print('  z13 {:.4f}+{:.4f}j;'.format(r13, x13), file=fp)
    print('  z21 {:.4f}+{:.4f}j;'.format(r12, x12), file=fp)
    print('  z22 {:.4f}+{:.4f}j;'.format(r22, x22), file=fp)
    print('  z23 {:.4f}+{:.4f}j;'.format(r12, x12), file=fp)
    print('  z31 {:.4f}+{:.4f}j;'.format(r13, x13), file=fp)
    print('  z32 {:.4f}+{:.4f}j;'.format(r12, x12), file=fp)
    print('  z33 {:.4f}+{:.4f}j;'.format(r11, x11), file=fp)
    print('  rating.summer.continuous {:.1f};'.format(apar), file=fp)
    print('  rating.summer.emergency {:.1f};'.format(apar), file=fp)
    print('  rating.winter.continuous {:.1f};'.format(apar), file=fp)
    print('  rating.winter.emergency {:.1f};'.format(apar), file=fp)
    print('}', file=fp)


def write_node_house_configs(fp, xfkva, xfkvll, xfkvln, phs, want_inverter=False):
    """Writes transformers, inverter settings for GridLAB-D houses at a primary load point.

    An aggregated single-phase triplex or three-phase quadriplex line configuration is also
    written, based on estimating enough parallel 1/0 AA to supply xfkva load.
    This function should only be called once for each combination of xfkva and phs to use,
    and it should be called before write_node_houses.

    Args:
        fp (file): Previously opened text file for writing; the caller closes it.
        xfkva (float): the total transformer size to serve expected load; make this big enough to avoid overloads
        xfkvll (float): line-to-line voltage [kV] on the primary. The secondary voltage will be 208 three-phase
        xfkvln (float): line-to-neutral voltage [kV] on the primary. The secondary voltage will be 120/240 for split secondary
        phs (str): either 'ABC' for three-phase, or concatenation of 'A', 'B', and/or 'C' with 'S' for single-phase to triplex
        want_inverter (boolean): True to write the IEEE 1547-2018 smarter inverter function setpoints
    """
    if want_inverter:
        print('#define INVERTER_MODE=CONSTANT_PF', file=fp)
        print('//#define INVERTER_MODE=VOLT_VAR', file=fp)
        print('//#define INVERTER_MODE=VOLT_WATT', file=fp)
        print('// default IEEE 1547-2018 settings for Category B', file=fp)
        print('#define INV_V1=0.92', file=fp)
        print('#define INV_V2=0.98', file=fp)
        print('#define INV_V3=1.02', file=fp)
        print('#define INV_V4=1.08', file=fp)
        print('#define INV_Q1=0.44', file=fp)
        print('#define INV_Q2=0.00', file=fp)
        print('#define INV_Q3=0.00', file=fp)
        print('#define INV_Q4=-0.44', file=fp)
        print('#define INV_VIN=200.0', file=fp)
        print('#define INV_IIN=32.5', file=fp)
        print('#define INV_VVLOCKOUT=300.0', file=fp)
        print('#define INV_VW_V1=1.05 // 1.05833', file=fp)
        print('#define INV_VW_V2=1.10', file=fp)
        print('#define INV_VW_P1=1.0', file=fp)
        print('#define INV_VW_P2=0.0', file=fp)
    if 'S' in phs:
        for secphs in phs.rstrip('S'):
            xfkey = 'XF{:s}_{:d}'.format(secphs, int(xfkva))
            write_xfmr_config(xfkey, secphs + 'S', kvat=xfkva, vnom=None, vsec=120.0, install_type='PADMOUNT',
                              vprimll=None, vprimln=1000.0 * xfkvln, op=fp)
        write_kersting_triplex(fp, xfkva)
    else:
        xfkey = 'XF3_{:d}'.format(int(xfkva))
        write_xfmr_config(xfkey, phs, kvat=xfkva, vnom=None, vsec=208.0, install_type='PADMOUNT',
                          vprimll=1000.0 * xfkvll, vprimln=None, op=fp)
        write_kersting_quadriplex(fp, xfkva)


def write_node_houses(fp, node, region, xfkva, phs, nh=None, loadkw=None, house_avg_kw=None, secondary_ft=None,
                      storage_fraction=0.0, solar_fraction=0.0, electric_cooling_fraction=0.5,
                      node_metrics_interval=None, random_seed=False):
    """Writes GridLAB-D houses to a primary load point.

    One aggregate service transformer is included, plus an optional aggregate secondary service drop. Each house
    has a separate meter or triplex_meter, each with a common parent, either a node or triplex_node on either the
    transformer secondary, or the end of the service drop. The houses may be written per phase, i.e., unbalanced load,
    or as a balanced three-phase load. The houses should be #included into a master GridLAB-D file. Before using this
    function, call write_node_house_configs once, and only once, for each combination xfkva/phs that will be used.

    Args:
        fp (file): Previously opened text file for writing; the caller closes it.
        node (str): the GridLAB-D primary node name
        region (int): the taxonomy region for housing population, 1..6
        xfkva (float): the total transformer size to serve expected load; make this big enough to avoid overloads
        phs (str): 'ABC' for three-phase balanced distribution, 'AS', 'BS', or 'CS' for single-phase triplex
        nh (int): directly specify the number of houses; an alternative to loadkw and house_avg_kw
        loadkw (float): total load kW that the houses will represent; with house_avg_kw, an alternative to nh
        house_avg_kw (float): average house load in kW; with loadkw, an alternative to nh
        secondary_ft (float): if not None, the length of adequately sized secondary circuit from transformer to the meters
        electric_cooling_fraction (float): fraction of houses to have air conditioners
        solar_fraction (float): fraction of houses to have rooftop solar panels
        storage_fraction (float): fraction of houses with solar panels that also have residential storage systems
        node_metrics_interval (int): if not None, the metrics collection interval in seconds for houses, meters, solar and storage at this node
        random_seed (boolean): if True, reseed each function call. Default value False provides repeatability of output.
    """
    global house_nodes, storage_percentage, solar_percentage, electric_cooling_percentage, metrics_interval
    house_nodes = {}
    if not random_seed:
        np.random.seed(0)
    bTriplex = False
    if 'S' in phs:
        bTriplex = True
    storage_percentage = storage_fraction
    solar_percentage = solar_fraction
    electric_cooling_percentage = electric_cooling_fraction
    lg_v_sm = 0.0
    vnom = 120.0
    if node_metrics_interval is not None:
        metrics_interval = node_metrics_interval
    else:
        metrics_interval = 0
    if nh is not None:
        nhouse = nh
    else:
        nhouse = int((loadkw / house_avg_kw) + 0.5)
        if nhouse > 0:
            lg_v_sm = loadkw / house_avg_kw - nhouse  # >0 if we rounded down the number of houses
    bldg, ti = selectResidentialBuilding(rgnThermalPct[region - 1],
                                         np.random.uniform(0, 1))  # TODO - these will all be identical!
    if nhouse > 0:
        # write the transformer and one billing meter at the house, with optional secondary circuit
        if bTriplex:
            xfkey = 'XF{:s}_{:d}'.format(phs[0], int(xfkva))
            linekey = 'tpx_cfg_{:d}'.format(int(xfkva))
            meter_class = 'triplex_meter'
            line_class = 'triplex_line'
        else:
            xfkey = 'XF3_{:d}'.format(int(xfkva))
            linekey = 'quad_cfg_{:d}'.format(int(xfkva))
            meter_class = 'meter'
            line_class = 'overhead_line'
        if secondary_ft is None:
            xfmr_meter = '{:s}_mtr'.format(node)  # same as the house meter
        else:
            xfmr_meter = '{:s}_xfmtr'.format(node)  # needs its own secondary meter
        if (solar_percentage > 0.0) or (storage_percentage > 0.0):
            if bTriplex:
                print('// inverter base voltage for volt-var functions, on triplex circuit', file=fp)
                print('#define INV_VBASE=240.0', file=fp)
            else:
                print('// inverter base voltage for volt-var functions, on 208-V three-phase circuit', file=fp)
                print('#define INV_VBASE=208.0', file=fp)
        print('object transformer {', file=fp)
        print('  name {:s}_xfmr;'.format(node), file=fp)
        print('  phases {:s};'.format(phs), file=fp)
        print('  from {:s};'.format(node), file=fp)
        print('  to {:s};'.format(xfmr_meter), file=fp)
        print('  configuration {:s};'.format(xfkey), file=fp)
        print('}', file=fp)
        if secondary_ft is not None:
            print('object {:s} {{'.format(meter_class), file=fp)
            print('  name {:s};'.format(xfmr_meter), file=fp)
            print('  phases {:s};'.format(phs), file=fp)
            print('  nominal_voltage {:.2f};'.format(vnom), file=fp)
            print('}', file=fp)
            print('object {:s} {{'.format(line_class), file=fp)
            print('  name {:s}_secondary;'.format(node), file=fp)
            print('  phases {:s};'.format(phs), file=fp)
            print('  from {:s};'.format(xfmr_meter), file=fp)
            print('  to {:s}_mtr;'.format(node), file=fp)
            print('  length {:.1f};'.format(secondary_ft), file=fp)
            print('  configuration {:s};'.format(linekey), file=fp)
            print('}', file=fp)

        print('object {:s} {{'.format(meter_class), file=fp)
        print('  name {:s}_mtr;'.format(node), file=fp)
        print('  phases {:s};'.format(phs), file=fp)
        print('  nominal_voltage {:.2f};'.format(vnom), file=fp)
        write_tariff(fp)
        if metrics_interval > 0:
            print('  object metrics_collector {', file=fp)
            print('    interval', str(metrics_interval) + ';', file=fp)
            print('  };', file=fp)
        print('}', file=fp)
        # write all the houses on that meter
        house_nodes[node] = [nhouse, region, lg_v_sm, phs, bldg, ti]
        write_houses(node, fp, vnom, bIgnoreThermostatSchedule=False, bWriteService=False, bTriplex=bTriplex,
                     setpoint_offset=1.0)
    else:
        print('// Zero houses at {:s} phases {:s}'.format(node, phs), file=fp)


def populate_feeder(configfile=None, config=None, taxconfig=None):
    """Wrapper function that processes one feeder. One or two keyword arguments must be supplied.

    Args:
        configfile (str): JSON file name for the feeder population data, mutually exclusive with config
        config (dict): dictionary of feeder population data already read in, mutually exclusive with configfile
        taxconfig (dict): dictionary of custom taxonomy data for ERCOT processing
    """
    global tier1_energy, tier1_price, tier2_energy, tier2_price, tier3_energy, tier3_price
    global bill_mode, kwh_price, monthly_fee
    global Eplus_Bus, Eplus_Volts, Eplus_kVA
    global transmissionVoltage, transmissionXfmrMVAbase, dso_substation_bus_id
    global storage_inv_mode, solar_inv_mode, solar_percentage, storage_percentage
    global work_path, weather_file
    global starttime, endtime, timestep
    global metrics_interval, electric_cooling_percentage
    global water_heater_percentage, water_heater_participation
    global case_name, name_prefix, forERCOT
    global house_nodes, small_nodes, comm_loads
    global latitude, longitude, altitude, tz_meridian, weather_name, feeder_commercial_building_number

    if configfile is not None:
        checkResidentialBuildingTable()
    if config is None:
        lp = open(configfile).read()
        config = json.loads(lp)

    # we want the same pseudo-random variables each time, for repeatability
    np.random.seed(0)
    rootname = config['BackboneFiles']['TaxonomyChoice']
    if 'NamePrefix' in config['BackboneFiles']:
        name_prefix = config['BackboneFiles']['NamePrefix']
    work_path = './' + config['SimulationConfig']['CaseName'] + '/'
    if 'WorkingDirectory' in config['SimulationConfig']:
        work_path = config['SimulationConfig']['WorkingDirectory'] + '/'
    starttime = config['SimulationConfig']['StartTime']
    endtime = config['SimulationConfig']['EndTime']
    timestep = int(config['FeederGenerator']['MinimumStep'])
    metrics_interval = int(config['FeederGenerator']['MetricsInterval'])
    electric_cooling_percentage = 0.01 * float(config['FeederGenerator']['ElectricCoolingPercentage'])
    water_heater_percentage = 0.01 * float(config['FeederGenerator']['WaterHeaterPercentage'])
    water_heater_participation = 0.01 * float(config['FeederGenerator']['WaterHeaterParticipation'])
    solar_percentage = 0.01 * float(config['FeederGenerator']['SolarPercentage'])
    storage_percentage = 0.01 * float(config['FeederGenerator']['StoragePercentage'])
    solar_inv_mode = config['FeederGenerator']['SolarInverterMode']
    storage_inv_mode = config['FeederGenerator']['StorageInverterMode']
    weather_file = config['WeatherPrep']['DataSource']
    bill_mode = config['FeederGenerator']['BillingMode']
    kwh_price = float(config['FeederGenerator']['Price'])
    monthly_fee = float(config['FeederGenerator']['MonthlyFee'])
    tier1_energy = float(config['FeederGenerator']['Tier1Energy'])
    tier1_price = float(config['FeederGenerator']['Tier1Price'])
    tier2_energy = float(config['FeederGenerator']['Tier2Energy'])
    tier2_price = float(config['FeederGenerator']['Tier2Price'])
    tier3_energy = float(config['FeederGenerator']['Tier3Energy'])
    tier3_price = float(config['FeederGenerator']['Tier3Price'])
    Eplus_Bus = config['EplusConfiguration']['EnergyPlusBus']
    Eplus_Volts = float(config['EplusConfiguration']['EnergyPlusServiceV'])
    Eplus_kVA = float(config['EplusConfiguration']['EnergyPlusXfmrKva'])
    transmissionXfmrMVAbase = float(config['PYPOWERConfiguration']['TransformerBase'])
    transmissionVoltage = 1000.0 * float(config['PYPOWERConfiguration']['TransmissionVoltage'])
    dso_substation_bus_id = int(config['PYPOWERConfiguration']['GLDBus'])
    if "Name" in config['WeatherPrep']:
        weather_name = config['WeatherPrep']['Name']
    latitude = float(config['WeatherPrep']['Latitude'])
    longitude = float(config['WeatherPrep']['Longitude'])
    altitude = float(config['WeatherPrep']['Altitude'])
    tz_meridian = float(config['WeatherPrep']['TZmeridian'])

    house_nodes = {}
    small_nodes = {}
    comm_loads = {}

    if taxconfig is not None:
        print('called with a custom taxonomy configuration')
        forERCOT = True
        if rootname in taxconfig['backbone_feeders']:
            taxrow = taxconfig['backbone_feeders'][rootname]
            vll = taxrow['vll']
            vln = taxrow['vln']
            avg_house = taxrow['avg_house']
            avg_comm = taxrow['avg_comm']
            case_name = config['SimulationConfig']['CaseName']
            work_path = taxconfig['work_path']
            print(case_name, rootname, vll, vln, avg_house, avg_comm, feeders_path, work_path, weather_path)
            ProcessTaxonomyFeeder(case_name, rootname, vll, vln, avg_house, avg_comm)
        else:
            print(rootname, 'not found in taxconfig backbone_feeders')
    else:
        print('using the built-in taxonomy')
        print(rootname, 'to', work_path, 'using', weather_file)
        print('times', starttime, endtime)
        print('steps', timestep, metrics_interval)
        print('hvac', electric_cooling_percentage)
        print('pv', solar_percentage, solar_inv_mode)
        print('storage', storage_percentage, storage_inv_mode)
        print('billing', kwh_price, monthly_fee)
        for c in taxchoice:
            if c[0] in rootname:
                case_name = config['SimulationConfig']['CaseName']
                ProcessTaxonomyFeeder(case_name, rootname, c[1], c[2], c[3], c[4])
#                quit()


def populate_all_feeders():
    """Wrapper function that batch processes all taxonomy feeders in the casefiles table (see source file)
    """
    if sys.platform == 'win32':
        batname = 'run_all.bat'
    else:
        batname = 'run_all.sh'
    op = open(work_path + batname, 'w')
    for c in casefiles:
        print('gridlabd -D WANT_VI_DUMP=1 -D METRICS_FILE=' + c[0] + '.json', c[0] + '.glm', file=op)
    op.close()
    for c in casefiles:
        ProcessTaxonomyFeeder(c[0], c[0], c[1], c[2], c[3], c[4])


if __name__ == "__main__":
    populate_all_feeders()
