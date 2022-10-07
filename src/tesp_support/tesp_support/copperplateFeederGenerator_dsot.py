# Copyright (C) 2018-2022 Battelle Memorial Institute
# file: copperplateFeederGenerator_dsot.py
"""Replaces ZIP loads with houses, and optional storage and solar generation.

As this module populates the feeder backbone wiht houses and DER, it uses
the Networkx package to perform graph-based capacity analysis, upgrading
fuses, transformers and lines to serve the expected load. Transformers have
a margin of 20% to avoid overloads, while fuses have a margin of 150% to
avoid overloads. These can be changed by editing tables and variables in the 
source file.

There are two kinds of house populating methods implemented:

    * :Feeders with Service Transfomers: This case applies to the full PNNL taxonomy feeders.
    Do not specify the *taxchoice* argument to *populate_feeder*.
    Each service transformer receiving houses will have a short service drop and a small number of houses attached.
    * :Feeders without Service Transformers: This applies to the reduced-order ERCOT feeders.
    To invoke this mode, specify the *taxchoice* argument to *populate_feeder*.
    Each primary load to receive houses will have a large service transformer,
    large service drop and large number of houses attached.

References:
    `GridAPPS-D Feeder Models <https://github.com/GRIDAPPSD/Powergrid-Models>`_

Public Functions:
    :populate_feeder: processes one GridLAB-D input file

Todo:
    * Verify the level zero mobile home thermal integrity properties; these were copied from the MATLAB feeder generator
    * Populate commercial building loads

"""

import os.path
import re
import networkx as nx
import numpy as np
import pandas as pd
from math import sqrt

from .data import feeders_path, weather_path
from .helpers import parse_kva, gld_strict_name
from .commbldgenerator import define_comm_loads, create_comm_zones

transmissionVoltage = 138000.0
transmissionXfmrMVAbase = 12.0
transmissionXfmrXpct = 8.0
transmissionXfmrRpct = 1.0
transmissionXfmrNLLpct = 0.4
transmissionXfmrImagpct = 1.0
caseName = ''

base_feeder_name = ''

max208kva = 100.0
xfmrMargin = 1.20
fuseMargin = 2.50

starttime = '2010-06-01 00:00:00'
endtime = '2010-06-03 00:00:00'
timestep = 15
Eplus_Bus = ''
Eplus_Volts = 480.0
Eplus_kVA = 150.0
# solar_percentage = 0.2
# storage_percentage = 0.5
# water_heater_percentage = 0.0  # if not provided in JSON config, use a regional default
# water_heater_participation = 0.5
solar_inv_mode = 'CONSTANT_PF'
latitude = 30.0
longitude = -110.0
weather_name = 'localWeather'


def write_solar_inv_settings(op):
    """Writes volt-var and volt-watt settings for solar inverters

    Args:
        op (file): an open GridLAB-D input file
    """
    print('    four_quadrant_control_mode ${INVERTER_MODE};', file=op)
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
inverter_efficiency = 0.97
array_efficiency = 0.2
rated_insolation = 1000.0
round_trip_efficiency = 0.86

# techdata dict:[heatgain fraction, Zpf, Ipf, Ppf, Z, I, P]
techdata = [0.9, 1.0, 1.0, 1.0, 0.2, 0.4, 0.4]

tiName = ['VERY_LITTLE',
          'VERY_LITTLE',
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


# -----------fraction of vintage type by home type in a given dso type---------
# index 0 is the home type:
#   0 = sf: single family homes (single_family_detached + single_family_attached)
#   1 = apt: apartments (apartment_2_4_units + apartment_5_units)
#   2 = mh: mobile homes (mobile_home)
# index 1 is the vintage type
#       0:pre-1950, 1:1950-1959, 2:1960-1969, 3:1970-1979, 4:1980-1989, 5:1990-1999, 6:2000-2009, 7:2010-2015


def getDsoThermalTable(dso_type):
    vintage_mat = res_bldg_metadata['housing_vintage'][dso_type]
    df = pd.DataFrame(vintage_mat)
    # df = df.transpose()
    dsoThermalPct = np.zeros(shape=(3, 8))  # initialize array
    dsoThermalPct[0] = (df['single_family_detached'] + df['single_family_attached']).values
    dsoThermalPct[1] = (df['apartment_2_4_units'] + df['apartment_5_units']).values
    dsoThermalPct[2] = (df['mobile_home']).values
    dsoThermalPct = dsoThermalPct.tolist()
    # now check if the sum of all values is 1
    total = 0
    for row in range(len(dsoThermalPct)):
        for col in range(len(dsoThermalPct[row])):
            total += dsoThermalPct[row][col]
    if total > 1.01 or total < 0.99:
        raise UserWarning('House vintage distribution does not sum to 1!')
    # print(rgnName, 'dsoThermalPct sums to', '{:.4f}'.format(total))
    return dsoThermalPct
    # print(dsoThermalPct)


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


rgnPenGasHeat = [0.7051, 0.8927, 0.6723, 0.4425, 0.4425]
rgnPenHeatPump = [0.0321, 0.0177, 0.0559, 0.1983, 0.1983]
rgnPenResHeat = [0.2628, 0.0896, 0.2718, 0.3592, 0.3592]
rgnPenElecCool = [0.4348, 0.7528, 0.5259, 0.9673, 0.9673]
rgnOversizeFactor = [0.1, 0.2, 0.2, 0.3, 0.3]

# Average heating and cooling setpoints
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
# singleFamilyProperties = [[16.0, 10.0, 10.0, 1, 1, 1, 1,   3,  .75, 2.8, 2.4],
#                           [19.0, 11.0, 12.0, 2, 1, 1, 1,   3,  .75, 3.0, 2.5],
#                           [19.0, 14.0, 16.0, 2, 1, 1, 1,   3,   .5, 3.2, 2.6],
#                           [30.0, 17.0, 19.0, 2, 1, 1, 2,   3,   .5, 3.4, 2.8],
#                           [34.0, 19.0, 20.0, 2, 1, 1, 2,   3,   .5, 3.6, 3.0],
#                           [36.0, 22.0, 22.0, 2, 2, 1, 2,   5, 0.25, 3.8, 3.0],
#                           [48.0, 28.0, 30.0, 3, 2, 2, 4,  11, 0.25, 4.0, 3.0]]
#
# apartmentProperties = [[13.4, 11.7,  9.4, 1, 1, 1, 1, 2.2, .75, 2.8,  1.9],
#                        [20.3, 11.7, 12.7, 2, 1, 2, 2, 2.7, 0.25, 3.0, 2.0],
#                        [28.7, 14.3, 12.7, 2, 2, 3, 4, 6.3, .125, 3.2, 2.1]]
#
# mobileHomeProperties = [[   0,    0,    0, 0, 0, 0, 0,   0,   0,   0,   0], # is it really this bad?
#                         [13.4,  9.2, 11.7, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
#                         [24.1, 11.7, 18.1, 2, 2, 1, 2,   3, .75, 3.5, 2.2]]

# new vintage bins for all three home types: SF, APT, MH
# 0:pre-1950, 1:1950-1959, 2:1960-1969, 3:1970-1979, 4:1980-1989, 5:1990-1999, 6:2000-2009, 7:2010-2015

# Index 0 is the level
# Rceiling, Rwall, Rfloor, WindowLayers, WindowGlass,Glazing,WindowFrame,Rdoor,AirInfil,COPhi,COPlo
singleFamilyProperties = [[19.0, 11.0, 12.0, 2, 1, 1, 1, 3, .75, 3.0, 2.5],
                          [19.0, 14.0, 16.0, 2, 1, 1, 1, 3, .5, 3.2, 2.6],
                          [30.0, 17.0, 19.0, 2, 1, 1, 2, 3, .5, 3.4, 2.8],
                          [34.0, 19.0, 20.0, 2, 1, 1, 2, 3, .5, 3.6, 3.0],
                          [36.0, 22.0, 22.0, 2, 2, 1, 2, 5, 0.25, 3.8, 3.0],
                          [48.0, 28.0, 30.0, 3, 2, 2, 4, 11, 0.25, 4.0, 3.0],
                          [48.0, 28.0, 30.0, 3, 2, 2, 4, 11, 0.25, 4.0, 3.0],
                          [50.0, 30.0, 32.0, 3, 2, 2, 4, 13, 0.25, 4.2, 3.0]]  # adding a new line for new vintage bins

apartmentProperties = [[13.4, 11.7, 9.4, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
                       [13.4, 11.7, 9.4, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
                       [20.3, 11.7, 12.7, 2, 1, 2, 2, 2.7, 0.25, 3.0, 2.0],
                       [20.3, 11.7, 12.7, 2, 1, 2, 2, 2.7, 0.25, 3.0, 2.0],
                       [20.3, 11.7, 12.7, 2, 1, 2, 2, 2.7, 0.25, 3.0, 2.0],
                       [28.7, 14.3, 12.7, 2, 2, 3, 4, 6.3, .125, 3.2, 2.1],
                       [28.7, 14.3, 12.7, 2, 2, 3, 4, 6.3, .125, 3.2, 2.1],
                       [32.7, 17.3, 15.7, 2, 2, 3, 4, 10.3, .125, 3.2, 2.1]]

mobileHomeProperties = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # is it really this bad?
                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                        [13.4, 9.2, 11.7, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
                        [13.4, 9.2, 11.7, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
                        [13.4, 9.2, 11.7, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
                        [24.1, 11.7, 18.1, 2, 2, 1, 2, 3, .75, 3.5, 2.2],
                        [24.1, 11.7, 18.1, 2, 2, 1, 2, 3, .75, 3.5, 2.2],
                        [28.1, 13.7, 22.1, 2, 2, 1, 2, 3, .75, 3.5, 2.2]]


def selectThermalProperties(bldgIdx, tiIdx):
    """Retrieve the building thermal properties for a given type and integrity level

    Args:
        bldgIdx (int): 0 for single-family, 1 for apartment, 2 for mobile home
        tiIdx (int): 0..7 for single-family, apartment or mobile home
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
    return 0.0


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
    return 0.0


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
    return 0, 0, 0, 0, 0


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
    return 0, 0, 0, 0, 0


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
                oname = gld_strict_name(val)
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
        oname = 'ID_' + str(octr)
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


def write_link_class(model, h, t, seg_loads, op):
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
        print('  name', row[0] + ';', file=op)
        print('  resistance', str(row[1]) + ';', file=op)
        print('  geometric_mean_radius', str(row[2]) + ';', file=op)
        print('  rating.summer.continuous', str(row[3]) + ';', file=op)
        print('  rating.summer.emergency', str(row[3]) + ';', file=op)
        print('  rating.winter.continuous', str(row[3]) + ';', file=op)
        print('  rating.winter.emergency', str(row[3]) + ';', file=op)
        print('}', file=op)
    for row in triplex_configurations:
        print('object triplex_line_configuration {', file=op)
        print('  name', row[0] + ';', file=op)
        print('  conductor_1', row[1] + ';', file=op)
        print('  conductor_2', row[1] + ';', file=op)
        print('  conductor_N', row[2] + ';', file=op)
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
    # let's get the vintage table for dso_type
    dsoThermalPct = getDsoThermalTable(dso_type)
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
                        bldg, ti = selectResidentialBuilding(dsoThermalPct, np.random.uniform(0, 1))
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
    total_zipload = 0
    total_office = 0
    total_warehouse_storage = 0
    total_big_box = 0
    total_strip_mall = 0
    total_education = 0
    total_food_service = 0
    total_food_sales = 0
    total_lodging = 0
    total_healthcare_inpatient = 0
    total_low_occupancy = 0
    sqft_kva_ratio = 0.005  # Average com building design load is 5 W/sq ft.
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
                    target_sqft = kva / sqft_kva_ratio
                    sqft_error = -target_sqft
                    select_bldg = None
                    # TODO: Need a way to place all remaining buildings if this is the last/fourth feeder.
                    # TODO: Need a way to place link for j-modelica buildings on fourth feeder of Urban DSOs
                    # TODO: Need to work out what to do if we run out of commercial buildings before we get to the fourth feeder.
                    for bldg in comm_bldgs_pop:
                        if 0 >= (comm_bldgs_pop[bldg][1] - target_sqft) > sqft_error:
                            select_bldg = bldg
                            sqft_error = comm_bldgs_pop[bldg][1] - target_sqft

                    # if nzones > 14 and nphs == 3:
                    #   comm_type = 'OFFICE'
                    #   total_office += 1
                    # elif nzones > 5 and nphs > 1:
                    #   comm_type = 'BIGBOX'
                    #   total_bigbox += 1
                    # elif nzones > 0:
                    #   comm_type = 'STRIPMALL'
                    #   total_stripmall += 1
                    if select_bldg is not None:
                        comm_name = select_bldg
                        comm_type = comm_bldgs_pop[select_bldg][0]
                        comm_size = comm_bldgs_pop[select_bldg][1]
                        if comm_type == 'office':
                            total_office += 1
                        elif comm_type == 'warehouse_storage':
                            total_warehouse_storage += 1
                        elif comm_type == 'big_box':
                            total_big_box += 1
                        elif comm_type == 'strip_mall':
                            total_strip_mall += 1
                        elif comm_type == 'education':
                            total_education += 1
                        elif comm_type == 'food_service':
                            total_food_service += 1
                        elif comm_type == 'food_sales':
                            total_food_sales += 1
                        elif comm_type == 'lodging':
                            total_lodging += 1
                        elif comm_type == 'healthcare_inpatient':
                            total_healthcare_inpatient += 1
                        elif comm_type == 'low_occupancy':
                            total_low_occupancy += 1

                        # code = 'total_' + comm_type + ' += 1'
                        # exec(code)
                        # my_exec(code)
                        # eval(compile(code, '<string>', 'exec'))

                        del (comm_bldgs_pop[select_bldg])
                    else:
                        if nzones > 0:
                            print('Commercial building could not be found for ', '{:.2f}'.format(kva), ' KVA load')
                        comm_name = 'streetlights'
                        comm_type = 'ZIPLOAD'
                        comm_size = 0
                        total_zipload += 1
                    mtr = gld_strict_name(model[t][o]['parent'])
                    extra_billing_meters.add(mtr)
                    comm_loads[o] = [mtr, comm_type, comm_size, kva, nphs, phases, vln, total_commercial, comm_name]
                    model[t][o]['groupid'] = comm_type + '_' + str(comm_size)
                    del model[t][o]
    print('Found', total_commercial, 'commercial loads totaling', '{:.2f}'.format(total_comm_kva), 'KVA')
    print('  ', total_office, 'med/small offices,')
    print('  ', total_warehouse_storage, 'warehouses,')
    print('  ', total_big_box, 'big box retail,')
    print('  ', total_strip_mall, 'strip malls,')
    print('  ', total_education, 'education,')
    print('  ', total_food_service, 'food service,')
    print('  ', total_food_sales, 'food sales,')
    print('  ', total_lodging, 'lodging,')
    print('  ', total_healthcare_inpatient, 'healthcare,')
    print('  ', total_low_occupancy, 'low occupancy,')
    print('  ', total_zipload, 'ZIP loads')
    remain_comm_kva = 0
    for bldg in comm_bldgs_pop:
        remain_comm_kva += comm_bldgs_pop[bldg][1] * sqft_kva_ratio
    print(len(comm_bldgs_pop), 'commercial buildings (approximately', int(remain_comm_kva),
          'kVA) still to be assigned.')


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
    # let's get the vintage table for dso_type
    dsoThermalPct = getDsoThermalTable(dso_type)
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
                        bldg, ti = selectResidentialBuilding(dsoThermalPct, np.random.uniform(0, 1))
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
    print('  configuration', triplex_configurations[0][0] + ';', file=op)
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
    if len(caseName) > 0:
        print('#ifdef USE_FNCS', file=op)
        print('object fncs_msg {', file=op)
        print('  name gld' + substation_name + ';', file=op)  # for full-order DSOT
        print('  parent network_node;', file=op)
        print('  configure', caseName + '_gridlabd.txt;', file=op)
        print('  option "transport:hostname localhost, port 5570";', file=op)
        print('  aggregate_subscriptions true;', file=op)
        print('  aggregate_publications true;', file=op)
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
#   if the name or parent attribute is found in secmtrnode, 
#   we look up the nominal voltage there otherwise, the nominal voltage is vprim
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
            if bHaveS and bHadS is False:
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
    print('  name ' + key + ';', file=op)
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
    global base_feeder_name

    base_feeder_name = gld_strict_name(rootname)
    fname = feeders_path + rootname + '.glm'
    print('Populating From:', fname)

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
                elif 'timezone' in line:
                    print('  timezone ' + timezone + ';', file=op)
                else:
                    print(line, file=op)

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

        sub_graphs = [G.subgraph(c).copy() for c in nx.connected_components(G)]
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
        print('};', file=op)
        print('#include "${TESPDIR}/data/appliance_schedules.glm";', file=op)
        print('#include "${TESPDIR}/data/water_and_setpoint_schedule_v5.glm";', file=op)
        print('#include "${TESPDIR}/data/commercial_schedules.glm";', file=op)
        print('#set minimum_timestep=' + str(timestep) + ';', file=op)
        print('#set relax_naming_rules=1;', file=op)
        print('#set warn=0;', file=op)

        if metrics_interval > 0:
            print('object metrics_collector_writer {', file=op)
            print('  interval', str(metrics_interval) + ';', file=op)
            print('  interim', str(metrics_interim) + ';', file=op)
            print('  filename ${METRICS_FILE};', file=op)
            print('  // filename your_metrics;', file=op)
            print('  alternate yes;', file=op)
            print('  extension {0:s};'.format(metrics_type), file=op)
            print('};', file=op)

        print('object climate {', file=op)
        print('  name', str(weather_name) + ';', file=op)
        print('  // tmyfile "' + weather_path + weather_file + '";', file=op)
        print('  interpolate QUADRATIC;', file=op)
        print('  latitude', str(latitude) + ';', file=op)
        print('  longitude', str(longitude) + ';', file=op)
        print('};', file=op)
        #        print('// taxonomy_base_feeder', rootname, file=op)
        #        print('// region_name', rgnName[rgn-1], file=op)
        if solar_percentage > 0.0:
            print('// default IEEE 1547-2018 for Category B; modes are CONSTANT_PF, VOLT_VAR, VOLT_WATT', file=op)
            print('#define INVERTER_MODE=' + solar_inv_mode, file=op)
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

        # write the optional volt_dump and curr_dump for validation
        print('#ifdef WANT_VI_DUMP', file=op)
        print('object voltdump {', file=op)
        print('  filename Voltage_Dump_' + outname + '.csv;', file=op)
        print('  mode POLAR;', file=op)
        print('}', file=op)
        print('object currdump {', file=op)
        print('  filename Current_Dump_' + outname + '.csv;', file=op)
        print('  mode POLAR;', file=op)
        print('}', file=op)
        print('#endif', file=op)

        # NEW STRATEGY - loop through transformer instances and assign a standard size based on the downstream load
        #              - change the referenced transformer_configuration attributes
        #              - write the standard transformer_configuration instances we actually need
        xfused = {}  # ID, phases, total kva, vnom (LN), vsec, poletop/padmount
        secnode = {}  # Node, st, phases, vnom
        write_voltage_class(model, h, 'node', op, vln, vll, secnode)
        write_config_class(model, h, 'regulator_configuration', op)
        write_link_class(model, h, 'regulator', seg_loads, op)
        bldg_meter_model = model['meter']['bldg_meter']
        del model['meter']['bldg_meter']
        write_voltage_class(model, h, 'meter', op, vln, vll, secnode)

        tmp = {}
        comm_loads = {bldg_list: [None] * 9 for bldg_list in comm_bldgs_pop.keys()}
        for bldg in comm_bldgs_pop:
            tmp['meter'] = {}
            tmp['transformer_configuration'] = {}
            tmp['transformer'] = {}
            comm_loads[bldg][0] = "meter_" + bldg  # mtr
            extra_billing_meters.add(comm_loads[bldg][0])
            comm_loads[bldg][1] = comm_bldgs_pop[bldg][0]  # comm_type
            comm_loads[bldg][2] = comm_bldgs_pop[bldg][1]  # comm_size = int()
            comm_loads[bldg][3] = float(58)  # kva = float()
            comm_loads[bldg][4] = 3  # nphs = int()
            comm_loads[bldg][5] = "ABC"  # phases =
            comm_loads[bldg][6] = float(120)  # vln = float() nominal voltage for the secondary
            comm_loads[bldg][7] = 0  # loadnum = int()
            comm_loads[bldg][8] = bldg  # comm_name =

            tmp['meter'][comm_loads[bldg][0]] = bldg_meter_model
            tmp['transformer_configuration']['transf_conf_' + bldg] = model[
                'transformer_configuration']['feeder_XF3_POLETOP_ABCN_30']
            tmp['transformer']['transformer_' + bldg] = model['transformer']['feeder_head_transformer']
            tmp['transformer']['transformer_' + bldg]['configuration'] = 'transf_conf_' + bldg
            tmp['transformer']['transformer_' + bldg]['from'] = 'feeder_head_meter'
            tmp['transformer']['transformer_' + bldg]['to'] = "meter_" + bldg

            write_config_class(tmp, h, 'transformer_configuration', op)
            write_link_class(tmp, h, 'transformer', seg_loads, op)
            write_voltage_class(tmp, h, 'meter', op, comm_loads[bldg][6], vll, secnode)
            bldg_definition = define_comm_loads(comm_bldgs_pop[bldg][0], comm_bldgs_pop[bldg][1], dso_type,
                                                       ashrae_zone, comm_bldg_metadata)
            create_comm_zones(bldg_definition, comm_loads, bldg, op, batt_metadata,
                                     storage_percentage, ev_metadata, ev_percentage, solar_percentage,
                                     pv_rating_MW, solar_Q_player, case_type, metrics, metrics_interval, None)
        op.close()


def populate_feeder(config=None):
    """Wrapper function that processes one feeder. One or two keyword arguments must be supplied.

    Args:
        config (dict): dictionary of feeder population data already read in, mutually exclusive with configfile
    """
    global tier1_energy, tier1_price, tier2_energy, tier2_price, tier3_energy, tier3_price, bill_mode, kwh_price, monthly_fee
    global Eplus_Bus, Eplus_Volts, Eplus_kVA
    global transmissionVoltage, transmissionXfmrMVAbase
    global storage_inv_mode, solar_inv_mode, solar_percentage, storage_percentage
    global ev_percentage, ev_metadata, pv_rating_MW, solar_Q_player
    global work_path, weather_file
    global timezone, starttime, endtime, timestep
    global metrics, metrics_interval, metrics_interim, metrics_type, electric_cooling_percentage
    global water_heater_percentage, water_heater_participation
    global caseName, substation_name
    global house_nodes, small_nodes, comm_loads
    global inverter_efficiency, round_trip_efficiency
    global latitude, longitude, weather_name, feeder_commercial_building_number
    global dso_type
    global case_type
    global ashrae_zone, comm_bldg_metadata, comm_bldgs_pop
    # (Laurentiu Marinovici 11/18/2019)
    global res_bldg_metadata  # to store residential metadata
    global batt_metadata  # to store battery metadata
    global cop_lookup

    # we want the same pseudo-random variables each time, for repeatability
    np.random.seed(0)

    # we want the same pseudo-random variables each time, for repeatability
    if 'RandomSeed' in config['BackboneFiles']:
        np.random.seed(config['BackboneFiles']['RandomSeed'])
    else:
        np.random.seed(0)
    rootname = config['BackboneFiles']['TaxonomyChoice']
    work_path = './' + config['SimulationConfig']['CaseName'] + '/'
    if 'WorkingDirectory' in config['SimulationConfig']:
        work_path = config['SimulationConfig']['WorkingDirectory'] + '/'
    if 'OutputPath' in config['SimulationConfig']:
        work_path = config['SimulationConfig']['OutputPath'] + '/'
    substation_name = config['SimulationConfig']['Substation']
    timezone = config['SimulationConfig']['TimeZone']
    starttime = config['SimulationConfig']['StartTime']
    endtime = config['SimulationConfig']['EndTime']
    port = config['SimulationConfig']['port']
    timestep = int(config['FeederGenerator']['MinimumStep'])
    metrics = config['FeederGenerator']['Metrics']
    metrics_type = config['FeederGenerator']['MetricsType']
    metrics_interval = int(config['FeederGenerator']['MetricsInterval'])
    metrics_interim = int(config['FeederGenerator']['MetricsInterim'])
    # electric_cooling_percentage = 0.01 * float(config['FeederGenerator']['ElectricCoolingPercentage'])
    # water_heater_percentage = 0.01 * float(config['FeederGenerator']['WaterHeaterPercentage'])
    # water_heater_participation = 0.01 * float(config['FeederGenerator']['WaterHeaterParticipation'])
    solar_percentage = 0.01 * float(config['FeederGenerator']['SolarPercentage'])
    storage_percentage = 0.01 * float(config['FeederGenerator']['StoragePercentage'])
    ev_percentage = 0.01 * float(config['FeederGenerator']['EVPercentage'])
    ev_metadata = config['BuildingPrep']['EvModelMetaData']
    solar_Q_player = config['BuildingPrep']['SolarQPlayerFile']
    pv_rating_MW = config['SimulationConfig']['rooftop_pv_rating_MW']
    solar_inv_mode = config['FeederGenerator']['SolarInverterMode']
    storage_inv_mode = config['FeederGenerator']['StorageInverterMode']
    if 'InverterEfficiency' in config['FeederGenerator']:
        inverter_efficiency = config['FeederGenerator']['InverterEfficiency']
    if 'BatteryRoundTripEfficiency' in config['FeederGenerator']:
        round_trip_efficiency = config['FeederGenerator']['BatteryRoundTripEfficiency']
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
    Eplus_Bus = config['FeederGenerator']['EnergyPlusBus']
    Eplus_Volts = float(config['FeederGenerator']['EnergyPlusServiceV'])
    Eplus_kVA = float(config['FeederGenerator']['EnergyPlusXfmrKva'])
    transmissionXfmrMVAbase = float(config['PYPOWERConfiguration']['TransformerBase'])
    transmissionVoltage = 1000.0 * float(config['PYPOWERConfiguration']['TransmissionVoltage'])
    weather_name = config['WeatherPrep']['Name']
    latitude = float(config['WeatherPrep']['Latitude'])
    longitude = float(config['WeatherPrep']['Longitude'])
    dso_type = config['SimulationConfig']['DSO_type']
    res_bldg_metadata = config['BuildingPrep']['ResBldgMetaData']
    batt_metadata = config['BuildingPrep']['BattMetaData']
    electric_cooling_percentage = res_bldg_metadata[
        'air_conditioning']  # if not provided in JSON config, use a regional default
    ashrae_zone = config['BuildingPrep']['ASHRAEZone']
    comm_bldg_metadata = config['BuildingPrep']['CommBldgMetaData']
    comm_bldgs_pop = config['BuildingPrep']['CommBldgPopulation']
    case_type = config['SimulationConfig']['caseType']

    # -------- create cop lookup table by vintage bin-----------
    # (Laurentiu MArinovici 11/18/2019) moving the cop_lookup inside this function as it requires
    # residential building metadata
    cop_mat = res_bldg_metadata['COP_average']
    years_bin = [range(1945, 1950), range(1950, 1960), range(1960, 1970), range(1970, 1980),
                 range(1980, 1990), range(1990, 2000), range(2000, 2010), range(2010, 2016)]
    years_bin = [list(years_bin[ind]) for ind in range(len(years_bin))]
    cop_lookup = []
    for _bin in range(len(years_bin)):
        temp = []
        for yr in years_bin[_bin]:
            temp.append(cop_mat[str(yr)])
        cop_lookup.append(temp)
    # cop_lookup will have similar structure as years bin with years replaced with corresponding mean cop value
    # cop_lookup: index 0: vintage bins (0,1..7)
    #             index 1: each year in the corresponding vintage bin

    house_nodes = {}
    small_nodes = {}
    comm_loads = {}

    print(rootname, 'to', work_path, 'using', weather_file)
    print('times: start = {0:s}, end = {1:s}'.format(starttime, endtime))
    print('steps: simulation step = {0}, metrics interval = {1}'.format(timestep, metrics_interval))
    caseName = config['SimulationConfig']['CaseName']
    ProcessTaxonomyFeeder(caseName, rootname, 12470.0, 7200.0, 4000.0, 20000.0)
