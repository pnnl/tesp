# Copyright (C) 2018-2019 Battelle Memorial Institute
# file: feederGenerator.py
"""Replaces ZIP loads with houses, and optional storage and solar generation.

As this module populates the feeder backbone wiht houses and DER, it uses
the Networkx package to perform graph-based capacity analysis, upgrading
fuses, transformers and lines to serve the expected load. Transformers have
a margin of 20% to avoid overloads, while fuses have a margin of 150% to
avoid overloads. These can be changed by editing tables and variables in the 
source file.

There are two kinds of house populating methods implemented:

    * :Feeders with Service Transfomers: This case applies to the full PNNL taxonomy feeders. Do not specify the *taxchoice* argument to *populate_feeder*. Each service transformer receiving houses will have a short service drop and a small number of houses attached.
    * :Feeders without Service Transformers: This applies to the reduced-order ERCOT feeders. To invoke this mode, specify the *taxchoice* argument to *populate_feeder*. Each primary load to receive houses will have a large service transformer, large service drop and large number of houses attached.

References:
    `GridAPPS-D Feeder Models <https://github.com/GRIDAPPSD/Powergrid-Models>`_

Public Functions:
    :populate_feeder: processes one GridLAB-D input file

Todo:
    * Verify the level zero mobile home thermal integrity properties; these were copied from the MATLAB feeder generator
    * Populate commercial building loads

"""
import sys
import re
import os.path
import networkx as nx
import numpy as np
import math
import json
import pandas as pd
# import tesp_support.commbldgenerator as tesp_support.commbldgenerator
import tesp_support
from tesp_support.helpers import random_norm_trunc, gld_strict_name

forDSOT = False

transmissionVoltage = 138000.0
transmissionXfmrMVAbase = 12.0
transmissionXfmrXpct = 8.0
transmissionXfmrRpct = 1.0
transmissionXfmrNLLpct = 0.4
transmissionXfmrImagpct = 1.0
fncs_case = ''
helics_case = ''

base_feeder_name = ''

max208kva = 100.0
xfmrMargin = 1.20
fuseMargin = 2.50

starttime = '2010-06-01 00:00:00'
endtime = '2010-06-03 00:00:00'
timestep = 15
use_fncs = True
use_houses = True
use_Eplus = True
Eplus_Bus = ''
Eplus_Volts = 480.0
Eplus_kVA = 150.0
# solar_percentage = 0.2
# storage_percentage = 0.0
# water_heater_percentage = 0.0  # if not provided in JSON config, use a regional default
# water_heater_participation = 0.5
solar_inv_mode = 'CONSTANT_PF'
latitude = 30.0
longitude = -110.0
weather_name = 'localWeather'
port = 5570


def get_dist(mean, var):
    """
    get a random number from a distribution given mean and %variability
    :param mean: mean of distribution
    :param var: % variability
    :return: one random entry from distribution
    """
    dev = (1 - var/100) + np.random.uniform(0, 1)*var/100*2
    return mean*dev
def write_solar_inv_settings(op):
    """Writes volt-var and volt-watt settings for solar inverters

    Args:
        op (file): an open GridLAB-D input file
    """
    print ('    four_quadrant_control_mode ${INVERTER_MODE};', file=op)
    print ('    V_base ${INV_VBASE};', file=op)
    print ('    V1 ${INV_V1};', file=op)
    print ('    Q1 ${INV_Q1};', file=op)
    print ('    V2 ${INV_V2};', file=op)
    print ('    Q2 ${INV_Q2};', file=op)
    print ('    V3 ${INV_V3};', file=op)
    print ('    Q3 ${INV_Q3};', file=op)
    print ('    V4 ${INV_V4};', file=op)
    print ('    Q4 ${INV_Q4};', file=op)
    print ('    V_In ${INV_VIN};', file=op)
    print ('    I_In ${INV_IIN};', file=op)
    print ('    volt_var_control_lockout ${INV_VVLOCKOUT};', file=op)
    print ('    VW_V1 ${INV_VW_V1};', file=op)
    print ('    VW_V2 ${INV_VW_V2};', file=op)
    print ('    VW_P1 ${INV_VW_P1};', file=op)
    print ('    VW_P2 ${INV_VW_P2};', file=op)

# storage_inv_mode = 'LOAD_FOLLOWING'
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
def write_tariff (op):
    """Writes tariff information to billing meters

    Args:
        op (file): an open GridLAB-D input file
    """
    print ('  bill_mode', bill_mode + ';', file=op)
    print ('  price', '{:.4f}'.format (kwh_price) + ';', file=op)
    print ('  monthly_fee', '{:.2f}'.format (monthly_fee) + ';', file=op)
    print ('  bill_day 1;', file=op)
    if 'TIERED' in bill_mode:
        if tier1_energy > 0.0:
            print ('  first_tier_energy', '{:.1f}'.format (tier1_energy) + ';', file=op)
            print ('  first_tier_price', '{:.6f}'.format (tier1_price) + ';', file=op)
        if tier2_energy > 0.0:
            print ('  second_tier_energy', '{:.1f}'.format (tier2_energy) + ';', file=op)
            print ('  second_tier_price', '{:.6f}'.format (tier2_price) + ';', file=op)
        if tier3_energy > 0.0:
            print ('  third_tier_energy', '{:.1f}'.format (tier3_energy) + ';', file=op)
            print ('  third_tier_price', '{:.6f}'.format (tier3_price) + ';', file=op)

inv_undersizing = 1.0
inv_efficiency = 0.97

array_efficiency = 0.2
rated_insolation = 1000.0

# bat_rt_efficiency = 0.86

#TODO: move the following data to metadta.json
# heatgain fraction, Zpf, Ipf, Ppf, Z, I, P
techdata = [0.9,1.0,1.0,1.0,0.2,0.4,0.4]

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

dso_ind = {'Urban': 0, 'Suburban': 1, 'Rural': 2}
bldg_type = ['single_family', 'apartment', 'mobile_home']
vint_type = ['pre_1950', '1950-1959', '1960-1969', '1970-1979', '1980-1989', '1990-1999', '2000-2009', '2010-2015']

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
    if total >1.01 or total<0.99:
        raise UserWarning('House vintage distribution does not sum to 1!')
    # print(rgnName, 'dsoThermalPct sums to', '{:.4f}'.format(total))
    return dsoThermalPct
    # print(dsoThermalPct)
def selectResidentialBuilding(rgnTable, prob):
    """Selects the building and vintage type
    Args:
        op (file): an open GridLAB-D input file
    """
    row = 0
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

    The random number for the heating setpoint row is generated internally.

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
        #        print (bldg, binZeroReserve, binZeroMargin)
        for cBin in range(1, 6):
            denom = binZeroMargin
            for hBin in range(1, allowedHeatingBins[cBin]):
                denom += bldgHeatingSetpoints[bldg][hBin][0]
            conditionalHeatingBinProb[bldg][cBin][0] = binZeroMargin / denom
            for hBin in range(1, allowedHeatingBins[cBin]):
                conditionalHeatingBinProb[bldg][cBin][hBin] = bldgHeatingSetpoints[bldg][hBin][0] / denom


#    print ('conditionalHeatingBinProb', conditionalHeatingBinProb)

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
commercial_skew_max = 8100
commercial_skew_std = 2700
residential_skew_max = 8100
residential_skew_std = 2700

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

mobileHomeProperties = [[13.4, 9.2, 11.7, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
                        [13.4, 9.2, 11.7, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
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
        tiIdx (int): 0..7
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


def parse_kva_old(arg):
    """Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form

    DEPRECATED

    Args:
        cplx (str): the GridLAB-D P+jQ value

    Returns:
        float: the parsed kva value
    """
    tok = arg.strip('; MWVAKdrij')
    nsign = nexp = ndot = 0
    for i in range(len(tok)):
        if (tok[i] == '+') or (tok[i] == '-'):
            nsign += 1
        elif (tok[i] == 'e') or (tok[i] == 'E'):
            nexp += 1
        elif tok[i] == '.':
            ndot += 1
        if nsign == 2 and nexp == 0:
            kpos = i
            break
        if nsign == 3:
            kpos = i
            break

    vals = [tok[:kpos], tok[kpos:]]
    #    print(arg,vals)

    vals = [float(v) for v in vals]

    if 'd' in arg:
        vals[1] *= (math.pi / 180.0)
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    elif 'r' in arg:
        p = vals[0] * math.cos(vals[1])
        q = vals[0] * math.sin(vals[1])
    else:
        p = vals[0]
        q = vals[1]

    if 'KVA' in arg:
        p *= 1.0
        q *= 1.0
    elif 'MVA' in arg:
        p *= 1000.0
        q *= 1000.0
    else:  # VA
        p /= 1000.0
        q /= 1000.0

    return math.sqrt (p*p + q*q)

def parse_kva(cplx):  # this drops the sign of p and q
    """Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form

    Args:
        cplx (str): the GridLAB-D P+jQ value

    Returns:
        float: the parsed kva value
    """
    toks = list(filter(None,re.split('[\+j-]',cplx)))
    p = float(toks[0])
    q = float(toks[1])
    return 0.001 * math.sqrt(p*p + q*q)

# leave off intermediate fuse sizes 8, 12, 20, 30, 50, 80, 140
# leave off 6, 10, 15, 25 from the smallest sizes, too easily blown
standard_fuses = [40, 65, 100, 200]
standard_reclosers = [280, 400, 560, 630, 800]
standard_breakers = [600, 1200, 2000]

def FindFuseLimit (amps):
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

def Find1PhaseXfmrKva (kva):
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

def Find3PhaseXfmrKva (kva):
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

def Find1PhaseXfmr (kva):
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
    return 0,0,0,0,0

def Find3PhaseXfmr (kva):
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
taxchoice = [['R1-12.47-1',12470.0, 7200.0, 4000.0, 20000.0],
             ['R1-12.47-2',12470.0, 7200.0, 4500.0, 30000.0],
             ['R1-12.47-3',12470.0, 7200.0, 8000.0, 15000.0],
             ['R1-12.47-4',12470.0, 7200.0, 4000.0, 15000.0],
             ['R1-25.00-1',24900.0,14400.0, 6000.0, 25000.0],
             ['R2-12.47-1',12470.0, 7200.0, 7000.0, 20000.0],
             ['R2-12.47-2',12470.0, 7200.0,15000.0, 25000.0],
             ['R2-12.47-3',12470.0, 7200.0, 5000.0, 30000.0],
             ['R2-25.00-1',24900.0,14400.0, 6000.0, 15000.0],
             ['R2-35.00-1',34500.0,19920.0,15000.0, 30000.0],
             ['R3-12.47-1',12470.0, 7200.0,12000.0, 40000.0],
             ['R3-12.47-2',12470.0, 7200.0,14000.0, 30000.0],
             ['R3-12.47-3',12470.0, 7200.0, 7000.0, 15000.0],
             ['R4-12.47-1',13800.0, 7970.0, 9000.0, 30000.0],
             ['R4-12.47-2',12470.0, 7200.0, 6000.0, 20000.0],
             ['R4-25.00-1',24900.0,14400.0, 6000.0, 20000.0],
             ['R5-12.47-1',13800.0, 7970.0, 6500.0, 20000.0],
             ['R5-12.47-2',12470.0, 7200.0, 4500.0, 15000.0],
             ['R5-12.47-3',13800.0, 7970.0, 4000.0, 15000.0],
             ['R5-12.47-4',12470.0, 7200.0, 6000.0, 30000.0],
             ['R5-12.47-5',12470.0, 7200.0, 4500.0, 25000.0],
             ['R5-25.00-1',22900.0,13200.0, 3000.0, 20000.0],
             ['R5-35.00-1',34500.0,19920.0, 6000.0, 25000.0],
             ['GC-12.47-1',12470.0, 7200.0, 8000.0, 13000.0],
             ['TE_Base',   12470.0, 7200.0, 8000.0, 13000.0],
             ['IEEE-123',  4160.0, 2401.7771, 3000.0, 25000.0]]
#casefiles = [['R2-12.47-2',12470.0, 7200.0,15000.0, 25000.0]]
casefiles = [['R1-12.47-1',12470.0, 7200.0, 4000.0, 20000.0]]

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
    """Identify switch, fuse, recloser, regulator, transformer, overhead_line, underground_line and triplex_line instances

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

def obj(parent,model,line,itr,oidh,octr):
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
    m = re.search('object ([^:{\s]+)[:{\s]',line,re.IGNORECASE)
    type = m.group(1)
    # If the object has an id number, store it
    n = re.search('object ([^:]+:[^{\s]+)',line,re.IGNORECASE)
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
        m = re.match('\s*(\S+) ([^;{]+)[;{]',line)
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
                line,octr = obj(oname,model,line,itr,oidh,octr)
            elif re.match('object',val):
                # found an inline object
                intobj += 1
                line,octr = obj(None,model,line,itr,oidh,octr)
                params[param] = 'ID_'+str(octr)
            else:
                params[param] = val
        if re.search('}',line):
            if intobj:
                intobj -= 1
                line = next(itr)
            else:
                oend = 1
        else:
            line = next(itr)
    # If undefined, use a default name
    if oname is None:
        oname = 'ID_'+str(octr)
    oidh[oname] = oname
    # Hash an object identifier to the object name
    if n:
        oidh[oid] = oname
    # Add the object to the model
    if type not in model:
        # New object type
        model[type] = {}
    model[type][oname] = {}
    for param in params:
        model[type][oname][param] = params[param]
    return line,octr

def write_config_class (model, h, t, op):
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
                    print ('  ' + p + ' ' + h[model[t][o][p]] + ';', file=op)
                else:
                    print ('  ' + p + ' ' + model[t][o][p] + ';', file=op)
            print('}', file=op)

def write_link_class (model, h, t, seg_loads, op):
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
                    print ('  ' + p + ' ' + h[model[t][o][p]] + ';', file=op)
                else:
                    if p == "from" or p == "to" or p == "parent":
                        print('  ' + p + ' ' + gld_strict_name(model[t][o][p]) + ';', file=op)
                    else:
                        print ('  ' + p + ' ' + model[t][o][p] + ';', file=op)
            print('}', file=op)

# name, r, gmr, ampacity
triplex_conductors = [['triplex_4/0_aa', 0.48, 0.0158, 1000.0]]

# name, hot, neutral, thickness, diameter
triplex_configurations = [['tpx_config', 'triplex_4/0_aa', 'triplex_4/0_aa', 0.08, 0.522]]

def write_local_triplex_configurations (op):
    """Write a 4/0 AA triplex configuration

  Args:
    op (file): an open GridLAB-D input file
  """
    for row in triplex_conductors:
        print ('object triplex_line_conductor {', file=op)
        print ('  name', row[0] + ';', file=op)
        print ('  resistance', str(row[1]) + ';', file=op)
        print ('  geometric_mean_radius', str(row[2]) + ';', file=op)
        print ('  rating.summer.continuous', str(row[3]) + ';', file=op)
        print ('  rating.summer.emergency', str(row[3]) + ';', file=op)
        print ('  rating.winter.continuous', str(row[3]) + ';', file=op)
        print ('  rating.winter.emergency', str(row[3]) + ';', file=op)
        print ('}', file=op)
    for row in triplex_configurations:
        print ('object triplex_line_configuration {', file=op)
        print ('  name', row[0] + ';', file=op)
        print ('  conductor_1', row[1] + ';', file=op)
        print ('  conductor_2', row[1] + ';', file=op)
        print ('  conductor_N', row[2] + ';', file=op)
        print ('  insulation_thickness', str(row[3]) + ';', file=op)
        print ('  diameter', str(row[4]) + ';', file=op)
        print ('}', file=op)

def buildingTypeLabel (rgn, bldg, ti):
    """Formatted name of region, building type name and thermal integrity level

    Args:
        rgn (int): region number 1..5
        bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
        ti (int): thermal integrity level, 0..6 for single-family, only 0..2 valid for apartment or mobile home
    """
    return rgnName[rgn-1] + ': ' + bldgTypeName[bldg] + ': TI Level ' + str (ti+1)

house_nodes = {} # keyed on node, [nhouse, region, lg_v_sm, phs, bldg, ti, parent (for ERCOT only)]
small_nodes = {} # keyed on node, [kva, phs, load_class]
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
def connect_ercot_houses (model, h, op, vln, vsec):
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
        xfkva = Find1PhaseXfmrKva (6.0 * nh)
        if xfkva > 100.0:
            npar = int (xfkva / 100.0 + 0.5)
            xfkva = 100.0
        elif xfkva <= 0.0:
            xfkva = 100.0
            npar = int (0.06 * nh + 0.5)
        else:
            npar = 1
        # write the service transformer==>TN==>TPX==>TM for all houses
        kvat = npar * xfkva
        row = Find1PhaseXfmr (xfkva)
        print ('object transformer_configuration {', file=op)
        print ('  name ' + key + '_xfconfig;', file=op)
        print ('  power_rating ' + format(kvat, '.2f') + ';', file=op)
        if 'A' in phs:
            print ('  powerA_rating ' + format(kvat, '.2f') + ';', file=op)
        elif 'B' in phs:
            print ('  powerB_rating ' + format(kvat, '.2f') + ';', file=op)
        elif 'C' in phs:
            print ('  powerC_rating ' + format(kvat, '.2f') + ';', file=op)
        print ('  install_type PADMOUNT;', file=op)
        print ('  connect_type SINGLE_PHASE_CENTER_TAPPED;', file=op)
        print ('  primary_voltage ' + str(vln) + ';', file=op)
        print ('  secondary_voltage ' + format(vsec, '.1f') + ';', file=op)
        print ('  resistance ' + format(row[1] * 0.5, '.5f') + ';', file=op)
        print ('  resistance1 ' + format(row[1], '.5f') + ';', file=op)
        print ('  resistance2 ' + format(row[1], '.5f') + ';', file=op)
        print ('  reactance ' + format(row[2] * 0.8, '.5f') + ';', file=op)
        print ('  reactance1 ' + format(row[2] * 0.4, '.5f') + ';', file=op)
        print ('  reactance2 ' + format(row[2] * 0.4, '.5f') + ';', file=op)
        print ('  shunt_resistance ' + format(1.0 / row[3], '.2f') + ';', file=op)
        print ('  shunt_reactance ' + format(1.0 / row[4], '.2f') + ';', file=op)
        print ('}', file=op)
        print ('object transformer {', file=op)
        print ('  name ' + key + '_xf;', file=op)
        print ('  phases ' + phs + 'S;', file=op)
        print ('  from ' + bus + ';', file=op)
        print ('  to ' + key + '_tn;', file=op)
        print ('  configuration ' + key + '_xfconfig;', file=op)
        print ('}', file=op)
        print ('object triplex_line_configuration {', file=op)
        print ('  name ' + key + '_tpxconfig;', file=op)
        zs = format (tpxR11/nh, '.5f') + '+' + format (tpxX11/nh, '.5f') + 'j;'
        zm = format (tpxR12/nh, '.5f') + '+' + format (tpxX12/nh, '.5f') + 'j;'
        amps = format (tpxAMP * nh, '.1f') + ';'
        print ('  z11 ' + zs, file=op)
        print ('  z22 ' + zs, file=op)
        print ('  z12 ' + zm, file=op)
        print ('  z21 ' + zm, file=op)
        print ('  rating.summer.continuous ' + amps, file=op)
        print ('}', file=op)
        print ('object triplex_line {', file=op)
        print ('  name ' + key + '_tpx;', file=op)
        print ('  phases ' + phs + 'S;', file=op)
        print ('  from ' + key + '_tn;', file=op)
        print ('  to ' + key + '_mtr;', file=op)
        print ('  length 50;', file=op)
        print ('  configuration ' + key + '_tpxconfig;', file=op)
        print ('}', file=op)
        if 'A' in phs:
            vstart = str(vsec) + '+0.0j;'
        elif 'B' in phs:
            vstart = format(-0.5*vsec,'.2f') + format(-0.866025*vsec,'.2f') + 'j;'
        else:
            vstart = format(-0.5*vsec,'.2f') + '+' + format(0.866025*vsec,'.2f') + 'j;'
        print ('object triplex_node {', file=op)
        print ('  name ' + key + '_tn;', file=op)
        print ('  phases ' + phs + 'S;', file=op)
        print ('  voltage_1 ' + vstart, file=op)
        print ('  voltage_2 ' + vstart, file=op)
        print ('  voltage_N 0;', file=op)
        print ('  nominal_voltage ' + format(vsec, '.1f') + ';', file=op)
        print ('}', file=op)
        print ('object triplex_meter {', file=op)
        print ('  name ' + key + '_mtr;', file=op)
        print ('  phases ' + phs + 'S;', file=op)
        print ('  voltage_1 ' + vstart, file=op)
        print ('  voltage_2 ' + vstart, file=op)
        print ('  voltage_N 0;', file=op)
        print ('  nominal_voltage ' + format(vsec, '.1f') + ';', file=op)
        """
        write_tariff (op)
        if metrics_interval > 0 and "meter" in metrics:
            print ('  object metrics_collector {', file=op)
            print ('    interval', str(metrics_interval) + ';', file=op)
            print ('  };', file=op)
        """
        print ('}', file=op)

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
            print ('object meter {', file=op)
            print ('  name ' + mtr + ';', file=op)
            print ('  parent ' + parent + ';', file=op)
            print ('  phases ' + phases + ';', file=op)
            print ('  nominal_voltage ' + format(vln, '.1f') + ';', file=op)
            write_tariff (op)
            if metrics_interval > 0 and "meter" in metrics:
                print ('  object metrics_collector {', file=op)
                print ('    interval', str(metrics_interval) + ';', file=op)
                print ('  };', file=op)
            print ('}', file=op)

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
        constpower = '  constant_power_A_real ' + format (1000.0 * kva, '.2f') + ';'
    elif 'B' in phs:
        vstart = '  voltage_B ' + format(-0.5*vnom,'.2f') + format(-0.866025*vnom,'.2f') + 'j;'
        constpower = '  constant_power_B_real ' + format (1000.0 * kva, '.2f') + ';'
    else:
        vstart = '  voltage_C ' + format(-0.5*vnom,'.2f') + '+' + format(0.866025*vnom,'.2f') + 'j;'
        constpower = '  constant_power_C_real ' + format (1000.0 * kva, '.2f') + ';'

    print ('object load {', file=op)
    print ('  name', basenode + ';', file=op)
    print ('  parent', parent + ';', file=op)
    print ('  phases', phs + ';', file=op)
    print ('  nominal_voltage ' + str(vnom) + ';', file=op)
    print ('  load_class ' + cls + ';', file=op)
    print (vstart, file=op)
    print ('  //', '{:.3f}'.format(kva), 'kva is less than 1/2 avg_house', file=op)
    print (constpower, file=op)
    print ('}', file=op)

# look at primary loads, not the service transformers
def identify_ercot_houses (model, h, t, avgHouse, rgn):
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
    print ('Average ERCOT House', avgHouse, rgn)
    total_houses = {'A': 0, 'B': 0, 'C': 0}
    total_small =  {'A': 0, 'B': 0, 'C': 0}
    total_small_kva =  {'A': 0, 'B': 0, 'C': 0}
    total_sf = 0
    total_apt = 0
    total_mh = 0
    if t in model:
        for o in model[t]:
            name = o
            node = o
            parent = gld_strict_name(model[t][o]['parent'])
            for phs in ['A', 'B', 'C']:
                tok = 'constant_power_' + phs
                key = node + '_' + phs
                if tok in model[t][o]:
                    kva = parse_kva (model[t][o][tok])
                    nh = 0
                    cls = 'U'
                    # don't populate houses onto A, C, I or U load_class nodes
                    if 'load_class' in model[t][o]:
                        cls = model[t][o]['load_class']
                        if cls == 'R':
                            if kva > 1.0:
                                nh = int ((kva / avgHouse) + 0.5)
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
                        house_nodes[key] = [nh, rgn, lg_v_sm, phs, bldg, ti, parent] # parent is the primary node, only for ERCOT
                    elif kva > 0.1:
                        total_small[phs] += 1
                        total_small_kva[phs] += kva
                        small_nodes[key] = [kva, phs, parent, cls] # parent is the primary node, only for ERCOT
    for phs in ['A', 'B', 'C']:
        print ('phase', phs, ':', total_houses[phs], 'Houses and', total_small[phs],
               'Small Loads totaling', '{:.2f}'.format (total_small_kva[phs]), 'kva')
    print (len(house_nodes), 'primary house nodes, [SF,APT,MH]=', total_sf, total_apt, total_mh)
    for i in range(6):
        heating_bins[0][i] = round (total_sf * bldgHeatingSetpoints[0][i][0] + 0.5)
        heating_bins[1][i] = round (total_apt * bldgHeatingSetpoints[1][i][0] + 0.5)
        heating_bins[2][i] = round (total_mh * bldgHeatingSetpoints[2][i][0] + 0.5)
        cooling_bins[0][i] = round (total_sf * bldgCoolingSetpoints[0][i][0] + 0.5)
        cooling_bins[1][i] = round (total_apt * bldgCoolingSetpoints[1][i][0] + 0.5)
        cooling_bins[2][i] = round (total_mh * bldgCoolingSetpoints[2][i][0] + 0.5)
    print ('cooling bins target', cooling_bins)
    print ('heating bins target', heating_bins)

extra_billing_meters = set()

def replace_commercial_loads (model, h, t, avgBuilding):
    """For the full-order feeders, scan each load with load_class==C to determine the number of zones it should have

  Args:
      model (dict): the parsed GridLAB-D model
      h (dict): the object ID hash
      t (str): the GridLAB-D class name to scan
      avgBuilding (float): the average building in kva
  """
    print ('Average Commercial Building', avgBuilding)
    total_commercial = 0
    total_comm_kva = 0
    total_comm_zones = 0
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
                    kva = accumulate_load_kva (model[t][o])
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
                    # total_comm_zones += nzones
                    target_sqft = kva / sqft_kva_ratio
                    sqft_error = -target_sqft
                    select_bldg = None
                    # TODO: Need a way to place all remaining buildings if this is the last/fourth feeder.
                    # TODO: Need a way to place link for j-modelica buildings on fourth feeder of Urban DSOs
                    # TODO: Need to work out what to do if we run out of commercial buildings before we get to the fourth feeder.
                    for bldg in comm_bldgs_pop:
                        if (comm_bldgs_pop[bldg][1] - target_sqft) <= 0 and (comm_bldgs_pop[bldg][1] - target_sqft) > sqft_error:
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

                        #code = 'total_' + comm_type + ' += 1'
                        #exec(code)
                        #my_exec(code)
                        #eval(compile(code, '<string>', 'exec'))

                        del(comm_bldgs_pop[select_bldg])
                    else:
                        if nzones > 0:
                            print('Commercial building could not be found for ', '{:.2f}'.format(kva), ' KVA load')
                        comm_name = 'streetlights'
                        comm_type = 'ZIPLOAD'
                        comm_size = 0
                        total_zipload += 1
                    mtr = gld_strict_name(model[t][o]['parent'])
                    # Laurentiu Marinovici - 01/30/2020
                    # updating according to the changes on TESP public
                    #if forERCOT == True:
                    # the parent node is actually a meter, but we have to add the tariff and metrics_collector unless only ZIPLOAD
                    #    mtr = model[t][o]['parent']  # + '_mtr'
                    #    if comm_type != 'ZIPLOAD':
                    #        extra_billing_meters.add(mtr)
                    #else:
                    extra_billing_meters.add(mtr)
                    comm_loads[o] = [mtr, comm_type, comm_size, kva, nphs, phases, vln, total_commercial, comm_name]
                    model[t][o]['groupid'] = comm_type + '_' + str(comm_size)
                    del model[t][o]
    print ('found', total_commercial, 'commercial loads totaling ', '{:.2f}'.format(total_comm_kva), 'KVA')
    print (total_office, ' med/small offices,',
           total_warehouse_storage, ' warehouses,', total_big_box, 'bigbox retail,', total_strip_mall, 'strip malls,',
           total_education, ' education,', total_food_service, ' food service,', total_food_sales, ' food sales,',
           total_lodging, ' lodging,', total_healthcare_inpatient, ' healthcare,', total_low_occupancy, ' low occupancy,',
           total_zipload, 'ZIP loads')
    # print (total_comm_zones, 'total commercial HVAC zones')
    remain_comm_kva = 0
    for bldg in comm_bldgs_pop:
        remain_comm_kva += comm_bldgs_pop[bldg][1] * sqft_kva_ratio
    print(len(comm_bldgs_pop),' commercial buildings (approximately ', int(remain_comm_kva),' kVA) still to be assigned.')

def identify_xfmr_houses (model, h, t, seg_loads, avgHouse, rgn):
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
                    name = o
                    node = gld_strict_name(model[t][o]['to'])
                    if nhouse <= 0:
                        total_small += 1
                        total_small_kva += tkva
                        small_nodes[node] = [tkva, phs]
                    else:
                        total_houses += nhouse
                        lg_v_sm = tkva / avgHouse - nhouse  # >0 if we rounded down the number of houses
                        bldg, ti = selectResidentialBuilding(dsoThermalPct, np.random.uniform(0, 1))
                        # bldg = 2
                        # ti = 5
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
        vstart = format(-0.5*vnom,'.2f') + format(-0.866025*vnom,'.2f') + 'j'
    else:
        vstart = format(-0.5*vnom,'.2f') + '+' + format(0.866025*vnom,'.2f') + 'j'

    tpxname = basenode + '_tpx_1'
    mtrname = basenode + '_mtr_1'
    loadname = basenode + '_load_1'
    print ('object triplex_node {', file=op)
    print ('  name', basenode + ';', file=op)
    print ('  phases', phs + ';', file=op)
    print ('  nominal_voltage ' + str(vnom) + ';', file=op)
    print ('  voltage_1 ' + vstart + ';', file=op)
    print ('  voltage_2 ' + vstart + ';', file=op)
    print ('}', file=op)
    print ('object triplex_line {', file=op)
    print ('  name', tpxname + ';', file=op)
    print ('  from', basenode + ';', file=op)
    print ('  to', mtrname + ';', file=op)
    print ('  phases', phs + ';', file=op)
    print ('  length 30;', file=op)
    print ('  configuration', triplex_configurations[0][0] + ';', file=op)
    print ('}', file=op)
    print ('object triplex_meter {', file=op)
    print ('  name', mtrname + ';', file=op)
    print ('  phases', phs + ';', file=op)
    print ('  meter_power_consumption 1+7j;', file=op)
    write_tariff (op)
    print ('  nominal_voltage ' + str(vnom) + ';', file=op)
    print ('  voltage_1 ' + vstart + ';', file=op)
    print ('  voltage_2 ' + vstart + ';', file=op)
    if metrics_interval > 0 and "meter" in metrics:
        print ('  object metrics_collector {', file=op)
        print ('    interval', str(metrics_interval) + ';', file=op)
        print ('  };', file=op)
    print ('}', file=op)
    print ('object triplex_load {', file=op)
    print ('  name', loadname + ';', file=op)
    print ('  parent', mtrname + ';', file=op)
    print ('  phases', phs + ';', file=op)
    print ('  nominal_voltage ' + str(vnom) + ';', file=op)
    print ('  voltage_1 ' + vstart + ';', file=op)
    print ('  voltage_2 ' + vstart + ';', file=op)
    print ('  //', '{:.3f}'.format(kva), 'kva is less than 1/2 avg_house', file=op)
    print ('  power_12_real 10.0;', file=op)
    print ('  power_12_reac 8.0;', file=op)
    print ('}', file=op)

# =======  This function is now performed in commbldggenerator.py  - H. Reeve
# def write_one_commercial_zone(bldg, op):
#   """Write one pre-configured commercial zone as a house
#
#   Args:
#       bldg: dictionary of GridLAB-D house and zipload attributes
#       op (file): open file to write to
#   """
#   print ('object house {', file=op)
#   print ('  name', bldg['zonename'] + ';', file=op)
#   print ('  parent', bldg['parent'] + ';', file=op)
#   print ('  groupid', bldg['groupid'] + ';', file=op)
#   print ('  motor_model BASIC;', file=op)
#   print ('  schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
#   print ('  floor_area {:.0f};'.format(bldg['floor_area']), file=op)
#   print ('  design_internal_gains {:.0f};'.format(bldg['int_gains'] * bldg['floor_area'] * 3.413), file=op)
#   print ('  number_of_doors {:.0f};'.format(bldg['no_of_doors']), file=op)
#   print ('  aspect_ratio {:.2f};'.format(bldg['aspect_ratio']), file=op)
#   print ('  total_thermal_mass_per_floor_area {:1.2f};'.format(bldg['thermal_mass_per_floor_area']), file=op)
#   print ('  interior_surface_heat_transfer_coeff {:1.2f};'.format(bldg['surface_heat_trans_coeff']), file=op)
#   print ('  interior_exterior_wall_ratio {:.2f};'.format(bldg['interior_exterior_wall_ratio']), file=op)
#   print ('  exterior_floor_fraction {:.3f};'.format(bldg['exterior_floor_fraction']), file=op)
#   print ('  exterior_ceiling_fraction {:.3f};'.format(bldg['exterior_ceiling_fraction']), file=op)
#   print ('  Rwall {:2.1f};'.format(bldg['Rwall']), file=op)
#   print ('  Rroof {:2.1f};'.format(bldg['Rroof']), file=op)
#   print ('  Rfloor {:.2f};'.format(bldg['Rfloor']), file=op)
#   print ('  Rdoors {:2.1f};'.format(bldg['Rdoors']), file=op)
#   print ('  exterior_wall_fraction {:.2f};'.format(bldg['exterior_wall_fraction']), file=op)
#   print ('  glazing_layers {:s};'.format(bldg['glazing_layers']), file=op)
#   print ('  glass_type {:s};'.format(bldg['glass_type']), file=op)
#   print ('  glazing_treatment {:s};'.format(bldg['glazing_treatment']), file=op)
#   print ('  window_frame {:s};'.format(bldg['window_frame']), file=op)
#   print ('  airchange_per_hour {:.2f};'.format(bldg['airchange_per_hour']), file=op)
#   print ('  window_wall_ratio {:0.3f};'.format(bldg['window_wall_ratio']), file=op)
#   print ('  heating_system_type {:s};'.format(bldg['heat_type']), file=op)
#   print ('  auxiliary_system_type {:s};'.format(bldg['aux_type']), file=op)
#   print ('  fan_type {:s};'.format(bldg['fan_type']), file=op)
#   print ('  cooling_system_type {:s};'.format(bldg['cool_type']), file=op)
#   print ('  air_temperature {:.2f};'.format(bldg['init_temp']), file=op)
#   print ('  mass_temperature {:.2f};'.format(bldg['init_temp']), file=op)
#   print ('  over_sizing_factor {:.1f};'.format(bldg['os_rand']), file=op)
#   print ('  cooling_COP {:2.2f};'.format(bldg['COP_A']), file=op)
#   print ('  cooling_setpoint 80.0; // {:s}_cooling'.format(bldg['base_schedule']), file=op)
#   print ('  heating_setpoint 60.0; // {:s}_heating'.format(bldg['base_schedule']), file=op)
#   print ('  object ZIPload { // lights', file=op)
#   print ('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
#   print ('    heatgain_fraction 1.0;', file=op)
#   print ('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
#   print ('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
#   print ('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
#   print ('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
#   print ('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
#   print ('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
#   print ('    base_power {:s}_lights*{:.2f};'.format(bldg['base_schedule'], bldg['adj_lights']), file=op)
#   print ('  };', file=op)
#   print ('  object ZIPload { // plug loads', file=op)
#   print ('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
#   print ('    heatgain_fraction 1.0;', file=op)
#   print ('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
#   print ('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
#   print ('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
#   print ('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
#   print ('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
#   print ('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
#   print ('    base_power {:s}_plugs*{:.2f};'.format(bldg['base_schedule'], bldg['adj_plugs']), file=op)
#   print ('  };', file=op)
#   print ('  object ZIPload { // gas waterheater', file=op)
#   print ('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
#   print ('    heatgain_fraction 1.0;', file=op)
#   print ('    power_fraction 0;', file=op)
#   print ('    impedance_fraction 0;', file=op)
#   print ('    current_fraction 0;', file=op)
#   print ('    power_pf 1;', file=op)
#   print ('    base_power {:s}_gas*{:.2f};'.format(bldg['base_schedule'], bldg['adj_gas']), file=op)
#   print ('  };', file=op)
#   print ('  object ZIPload { // exterior lights', file=op)
#   print ('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
#   print ('    heatgain_fraction 0.0;', file=op)
#   print ('    power_fraction {:.2f};'.format(bldg['c_p_frac']), file=op)
#   print ('    impedance_fraction {:.2f};'.format(bldg['c_z_frac']), file=op)
#   print ('    current_fraction {:.2f};'.format(bldg['c_i_frac']), file=op)
#   print ('    power_pf {:.2f};'.format(bldg['c_p_pf']), file=op)
#   print ('    current_pf {:.2f};'.format(bldg['c_i_pf']), file=op)
#   print ('    impedance_pf {:.2f};'.format(bldg['c_z_pf']), file=op)
#   print ('    base_power {:s}_exterior*{:.2f};'.format(bldg['base_schedule'], bldg['adj_ext']), file=op)
#   print ('  };', file=op)
#   print ('  object ZIPload { // occupancy', file=op)
#   print ('    schedule_skew {:.0f};'.format(bldg['skew_value']), file=op)
#   print ('    heatgain_fraction 1.0;', file=op)
#   print ('    power_fraction 0;', file=op)
#   print ('    impedance_fraction 0;', file=op)
#   print ('    current_fraction 0;', file=op)
#   print ('    power_pf 1;', file=op)
#   print ('    base_power {:s}_occupancy*{:.2f};'.format(bldg['base_schedule'], bldg['adj_occ']), file=op)
#   print ('  };', file=op)
#   if metrics_interval > 0 and "house" in metrics:
#     print ('  object metrics_collector {', file=op)
#     print ('    interval', str(metrics_interval) + ';', file=op)
#     print ('  };', file=op)
#   print ('}', file=op)

def randomize_commercial_skew():
    sk = commercial_skew_std * np.random.randn ()
    if sk < -commercial_skew_max:
        sk = -commercial_skew_max
    elif sk > commercial_skew_max:
        sk = commercial_skew_max
    return sk

# This function is now done by commbldgenerator.py
# def write_commercial_loads(rgn, key, op):
#     """Put commercial building zones and ZIP loads into the model
#
#   Args:
#       rgn (int): region 1..5 where the building is located
#       key (str): GridLAB-D load name that is being replaced
#       op (file): open file to write to
#   """
#     mtr = comm_loads[key][0]
#     comm_type = comm_loads[key][1]
#     nz = int(comm_loads[key][2])
#     kva = float(comm_loads[key][3])
#     nphs = int(comm_loads[key][4])
#     phases = comm_loads[key][5]
#     vln = float(comm_loads[key][6])
#     loadnum = int(comm_loads[key][7])
#
#     bldg = {}
#     bldg['parent'] = key
#     bldg['mtr'] = mtr
#     bldg['groupid'] = comm_type + '_' + str(loadnum)
#
#     print ('// load', key, 'mtr', bldg['mtr'], 'type', comm_type, 'nz', nz, 'kva', '{:.3f}'.format(kva),
#            'nphs', nphs, 'phases', phases, 'vln', '{:.3f}'.format(vln), file=op)
#
#     bldg['fan_type'] = 'ONE_SPEED'
#     bldg['heat_type'] = 'GAS'
#     bldg['cool_type'] = 'ELECTRIC'
#     bldg['aux_type'] = 'NONE'
#     bldg['no_of_stories'] = 1
#     bldg['surface_heat_trans_coeff'] = 0.59
#     bldg['oversize'] = over_sizing_factor[rgn-1]
#     bldg['glazing_layers'] = '2' # 'TWO'
#     bldg['glass_type'] = '2' # GLASS'
#     bldg['glazing_treatment'] = '4' # 'LOW_S'
#     bldg['window_frame'] = '0' # 'NONE'
#     bldg['c_z_frac'] = c_z_frac
#     bldg['c_i_frac'] = c_i_frac
#     bldg['c_p_frac'] = c_p_frac
#     bldg['c_z_pf'] = c_z_pf
#     bldg['c_i_pf'] = c_i_pf
#     bldg['c_p_pf'] = c_p_pf
#
#     if comm_type == 'OFFICE':
#         bldg['ceiling_height'] = 13.
#         bldg['airchange_per_hour'] = 0.69
#         bldg['Rroof'] = 19.
#         bldg['Rwall'] = 18.3
#         bldg['Rfloor'] = 46.
#         bldg['Rdoors'] = 3.
#         bldg['int_gains'] = 3.24  # W/sf
#         bldg['thermal_mass_per_floor_area'] = 1 # TODO
#         bldg['exterior_ceiling_fraction'] = 1 # TODO
#         bldg['base_schedule'] = 'office'
#         num_offices = int(round(nz/15))  # each with 3 floors of 5 zones
#         for jjj in range(num_offices):
#             floor_area_choose = 40000. * (0.5 * np.random.random() + 0.5)
#             for floor in range(1, 4):
#                 bldg['skew_value'] = randomize_commercial_skew()
#                 total_depth = math.sqrt(floor_area_choose / (3. * 1.5))
#                 total_width = 1.5 * total_depth
#                 if floor == 3:
#                     bldg['exterior_ceiling_fraction'] = 1
#                 else:
#                     bldg['exterior_ceiling_fraction'] = 0
#                 for zone in range(1, 6):
#                     if zone == 5:
#                         bldg['window_wall_ratio'] = 0  # this was not in the CCSI version
#                         bldg['exterior_wall_fraction'] = 0
#                         w = total_depth - 30.
#                         d = total_width - 30.
#                     else:
#                         bldg['window_wall_ratio'] = 0.33
#                         d = 15.
#                         if zone == 1 or zone == 3:
#                             w = total_width - 15.
#                         else:
#                             w = total_depth - 15.
#                         bldg['exterior_wall_fraction'] = w / (2. * (w + d))
#
#                     floor_area = w * d
#                     bldg['floor_area'] = floor_area
#                     bldg['aspect_ratio'] = w / d
#
#                     if floor > 1:
#                         bldg['exterior_floor_fraction'] = 0
#                     else:
#                         bldg['exterior_floor_fraction'] = w / (2. * (w + d)) / (floor_area / (floor_area_choose / 3.))
#
#                     bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * np.random.random())
#                     bldg['interior_exterior_wall_ratio'] = floor_area / (bldg['ceiling_height'] * 2. * (w + d)) - 1. \
#                       + bldg['window_wall_ratio'] * bldg['exterior_wall_fraction']
#                     bldg['no_of_doors'] = 0.1  # will round to zero, presumably the exterior doors are treated like windows
#
#                     bldg['init_temp'] = 68. + 4. * np.random.random()
#                     bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
#                     bldg['COP_A'] = cooling_COP * (0.8 + 0.4 * np.random.random())
#
#                     bldg['adj_lights'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.  # randomize 10# then convert W/sf -> kW
#                     bldg['adj_plugs'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
#                     bldg['adj_gas'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
#                     bldg['adj_ext'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
#                     bldg['adj_occ'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
#
#                     bldg['zonename'] = gld_strict_name (key + '_bldg_' + str(jjj+1) + '_floor_' + str(floor) + '_zone_' + str(zone))
#                     write_one_commercial_zone (bldg, op)
#
#     elif comm_type == 'BIGBOX':
#         bldg['ceiling_height'] = 14.
#         bldg['airchange_per_hour'] = 1.5
#         bldg['Rroof'] = 19.
#         bldg['Rwall'] = 18.3
#         bldg['Rfloor'] = 46.
#         bldg['Rdoors'] = 3.
#         bldg['int_gains'] = 3.6  # W/sf
#         bldg['thermal_mass_per_floor_area'] = 1 # TODO
#         bldg['exterior_ceiling_fraction'] = 1 # TODO
#         bldg['base_schedule'] = 'bigbox'
#
#         num_bigboxes = int(round(nz / 6.))
#         for jjj in range(num_bigboxes):
#             bldg['skew_value'] = randomize_commercial_skew()
#             floor_area_choose = 20000. * (0.5 + 1. * np.random.random())
#             floor_area = floor_area_choose / 6.
#             bldg['floor_area'] = floor_area
#             bldg['thermal_mass_per_floor_area'] = 3.9 * (0.8 + 0.4 * np.random.random())  # +/- 20#
#             bldg['exterior_ceiling_fraction'] = 1.
#             bldg['aspect_ratio'] = 1.28301275561855
#             total_depth = math.sqrt(floor_area_choose / bldg['aspect_ratio'])
#             total_width = bldg['aspect_ratio'] * total_depth
#             d = total_width / 3.
#             w = total_depth / 2.
#
#             for zone in range(1,7):
#                 if zone == 2 or zone == 5:
#                     bldg['exterior_wall_fraction'] = d / (2. * (d + w))
#                     bldg['exterior_floor_fraction'] = (0. + d) / (2. * (total_width + total_depth)) / (floor_area / floor_area_choose)
#                 else:
#                     bldg['exterior_wall_fraction'] = 0.5
#                     bldg['exterior_floor_fraction'] = (w + d) / (2. * (total_width + total_depth)) / (floor_area / floor_area_choose)
#                 if zone == 2:
#                     bldg['window_wall_ratio'] = 0.76
#                 else:
#                     bldg['window_wall_ratio'] = 0.
#
#                 if zone < 4:
#                     bldg['no_of_doors'] = 0.1  # this will round to 0
#                 elif zone == 5:
#                     bldg['no_of_doors'] = 24.
#                 else:
#                     bldg['no_of_doors'] = 1.
#
#                 bldg['interior_exterior_wall_ratio'] = (floor_area + bldg['no_of_doors'] * 20.) \
#                   / (bldg['ceiling_height'] * 2. * (w + d)) - 1. + bldg['window_wall_ratio'] * bldg['exterior_wall_fraction']
#                 bldg['init_temp'] = 68. + 4. * np.random.random()
#                 bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
#                 bldg['COP_A'] = cooling_COP * (0.8 + 0.4 * np.random.random())
#
#                 bldg['adj_lights'] = 1.2 * (0.9 + 0.1 * np.random.random()) * floor_area / 1000.  # randomize 10# then convert W/sf -> kW
#                 bldg['adj_plugs'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
#                 bldg['adj_gas'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
#                 bldg['adj_ext'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
#                 bldg['adj_occ'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
#
#                 bldg['zonename'] = gld_strict_name (key + '_bldg_' + str(jjj+1) + '_zone_' + str(zone))
#                 write_one_commercial_zone (bldg, op)
#
#     elif comm_type == 'STRIPMALL':
#         bldg['ceiling_height'] = 12 # T)D)
#         bldg['airchange_per_hour'] = 1.76
#         bldg['Rroof'] = 19.
#         bldg['Rwall'] = 18.3
#         bldg['Rfloor'] = 40.
#         bldg['Rdoors'] = 3.
#         bldg['int_gains'] = 3.6  # W/sf
#         bldg['exterior_ceiling_fraction'] = 1.
#         bldg['base_schedule'] = 'stripmall'
#         midzone = int (math.floor(nz / 2.) + 1.)
#         for zone in range (1, nz+1):
#             bldg['skew_value'] = randomize_commercial_skew()
#             floor_area_choose = 2400. * (0.7 + 0.6 * np.random.random())
#             bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * np.random.random())
#             bldg['no_of_doors'] = 1
#             if zone == 1 or zone == midzone:
#                 floor_area = floor_area_choose
#                 bldg['aspect_ratio'] = 1.5
#                 bldg['window_wall_ratio'] = 0.05
#                 bldg['exterior_wall_fraction'] = 0.4
#                 bldg['exterior_floor_fraction'] = 0.8
#                 bldg['interior_exterior_wall_ratio'] = -0.05
#             else:
#                 floor_area = floor_area_choose / 2.
#                 bldg['aspect_ratio'] = 3.0
#                 bldg['window_wall_ratio'] = 0.03
#                 if zone == nz:
#                     bldg['exterior_wall_fraction'] = 0.63
#                     bldg['exterior_floor_fraction'] = 2.
#                 else:
#                     bldg['exterior_wall_fraction'] = 0.25
#                     bldg['exterior_floor_fraction'] = 0.8
#                 bldg['interior_exterior_wall_ratio'] = -0.40
#
#             bldg['floor_area'] = floor_area
#
#             bldg['init_temp'] = 68. + 4. * np.random.random()
#             bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
#             bldg['COP_A'] = cooling_COP * (0.8 + 0.4 * np.random.random())
#
#             bldg['adj_lights'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
#             bldg['adj_plugs'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
#             bldg['adj_gas'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
#             bldg['adj_ext'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
#             bldg['adj_occ'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
#
#             bldg['zonename'] = gld_strict_name (key + '_zone_' + str(zone))
#             write_one_commercial_zone (bldg, op)
#
#     if comm_type == 'ZIPLOAD':
#         phsva = 1000.0 * kva / nphs
#         print ('object load { // street lights', file=op)
#         print ('  name {:s};'.format (key + '_streetlights'), file=op)
#         print ('  parent {:s};'.format (mtr), file=op)
#         print ('  groupid STREETLIGHTS;', file=op)
#         print ('  nominal_voltage {:2f};'.format(vln), file=op)
#         print ('  phases {:s};'.format (phases), file=op)
#         for phs in ['A', 'B', 'C']:
#             if phs in phases:
#                 print ('  impedance_fraction_{:s} {:f};'.format (phs, c_z_frac), file=op)
#                 print ('  current_fraction_{:s} {:f};'.format (phs, c_i_frac), file=op)
#                 print ('  power_fraction_{:s} {:f};'.format (phs, c_p_frac), file=op)
#                 print ('  impedance_pf_{:s} {:f};'.format (phs, c_z_pf), file=op)
#                 print ('  current_pf_{:s} {:f};'.format (phs, c_i_pf), file=op)
#                 print ('  power_pf_{:s} {:f};'.format (phs, c_p_pf), file=op)
#                 print ('  base_power_{:s} street_lighting*{:.2f};'.format (phs, light_scalar_comm * phsva), file=op)
#         print ('};', file=op)
#     else:
#         print ('object load { // accumulate zones', file=op)
#         print ('  name {:s};'.format (key), file=op)
#         print ('  parent {:s};'.format (mtr), file=op)
#         print ('  groupid {:s};'.format (comm_type), file=op)
#         print ('  nominal_voltage {:2f};'.format(vln), file=op)
#         print ('  phases {:s};'.format (phases), file=op)
#         print ('};', file=op)

def write_houses(basenode, op, vnom):
    """Put houses, along with solar panels and batteries, onto a node

    Args:
        basenode (str): GridLAB-D node name
        op (file): open file to write to
        vnom (float): nominal line-to-neutral voltage at basenode
    """
    global solar_count
    global solar_kw
    global battery_count

    nhouse = int(house_nodes[basenode][0])
    rgn = int(house_nodes[basenode][1])
    lg_v_sm = float(house_nodes[basenode][2])
    phs = house_nodes[basenode][3]
    bldg = house_nodes[basenode][4]
    ti = house_nodes[basenode][5]
    # rgnTable = dsoThermalPct

    if 'A' in phs:
        vstart = str(vnom) + '+0.0j'
    elif 'B' in phs:
        vstart = format(-0.5*vnom,'.2f') + format(-0.866025*vnom,'.2f') + 'j'
    else:
        vstart = format(-0.5*vnom,'.2f') + '+' + format(0.866025*vnom,'.2f') + 'j'

    if forERCOT:
        phs = phs + 'S'
        tpxname = gld_strict_name (basenode + '_tpx')
        mtrname = gld_strict_name (basenode + '_mtr')
    else:
        print ('object triplex_node {', file=op)
        print ('  name', basenode + ';', file=op)
        print ('  phases', phs + ';', file=op)
        print ('  nominal_voltage ' + str(vnom) + ';', file=op)
        print ('  voltage_1 ' + vstart + ';', file=op)
        print ('  voltage_2 ' + vstart + ';', file=op)
        print ('}', file=op)
    for i in range(nhouse):
        if not forERCOT:
            tpxname = gld_strict_name (basenode + '_tpx_' + str(i+1))
            mtrname = gld_strict_name (basenode + '_mtr_' + str(i+1))
            print ('object triplex_line {', file=op)
            print ('  name', tpxname + ';', file=op)
            print ('  from', basenode + ';', file=op)
            print ('  to', mtrname + ';', file=op)
            print ('  phases', phs + ';', file=op)
            print ('  length 30;', file=op)
            print ('  configuration', triplex_configurations[0][0] + ';', file=op)
            print ('}', file=op)
            print ('object triplex_meter {', file=op)
            print ('  name', mtrname + ';', file=op)
            print ('  phases', phs + ';', file=op)
            print ('  meter_power_consumption 1+7j;', file=op)
            write_tariff (op)
            print ('  nominal_voltage ' + str(vnom) + ';', file=op)
            print ('  voltage_1 ' + vstart + ';', file=op)
            print ('  voltage_2 ' + vstart + ';', file=op)
            if metrics_interval > 0 and "meter" in metrics:
                print ('  object metrics_collector {', file=op)
                print ('    interval', str(metrics_interval) + ';', file=op)
                print ('  };', file=op)
            print ('}', file=op)
        # LAurentiu MArinovici - 03/05/2020
        else:
            mtrname1 = gld_strict_name (basenode + '_mtr_' + str(i+1))
            print ('object triplex_meter {', file=op)
            print ('  name', mtrname1 + ';', file=op)
            print ('  parent', mtrname + ';', file=op)
            print ('  phases', phs + ';', file=op)
            print ('  meter_power_consumption 1+7j;', file=op)
            write_tariff (op)
            print ('  nominal_voltage ' + str(vnom) + ';', file=op)
            print ('  voltage_1 ' + vstart + ';', file=op)
            print ('  voltage_2 ' + vstart + ';', file=op)
            if metrics_interval > 0 and "meter" in metrics:
                print ('  object metrics_collector {', file=op)
                print ('    interval', str(metrics_interval) + ';', file=op)
                print ('  };', file=op)
            print ('}', file=op)
        hsename = gld_strict_name (basenode + '_hse_' + str(i+1))
        whname = gld_strict_name (basenode + '_wh_' + str(i+1))
        solname = gld_strict_name (basenode + '_sol_' + str(i+1))
        batname = gld_strict_name (basenode + '_bat_' + str(i+1))
        sol_i_name = gld_strict_name (basenode + '_isol_' + str(i+1))
        bat_i_name = gld_strict_name (basenode + '_ibat_' + str(i+1))
        # hse_m_name = gld_strict_name (basenode + '_mhse_' + str(i+1))
        sol_m_name = gld_strict_name (basenode + '_msol_' + str(i+1))
        bat_m_name = gld_strict_name (basenode + '_mbat_' + str(i+1))
        # Laurentiu Marinovici - 01/30/2020
        # updating according to the changes on TESP public
        if forERCOT:
            # hse_m_name = mtrname
            hse_m_name = gld_strict_name(basenode + '_mhse_' + str(i + 1))
            print ('object triplex_meter {', file=op)
            print ('  name', hse_m_name + ';', file=op)
            print ('  parent', mtrname1 + ';', file=op)
            print ('  phases', phs + ';', file=op)
            print ('  nominal_voltage ' + str(vnom) + ';', file=op)
            print ('}', file=op)
        else:
            hse_m_name = gld_strict_name(basenode + '_mhse_' + str(i + 1))
            print ('object triplex_meter {', file=op)
            print ('  name', hse_m_name + ';', file=op)
            print ('  parent', mtrname + ';', file=op)
            print ('  phases', phs + ';', file=op)
            print ('  nominal_voltage ' + str(vnom) + ';', file=op)
            print ('}', file=op)

        # ************* Floor area, ceiling height and stories *************************
        fa_array ={}  # distribution array for floor area min, max, mean, standard deviation
        stories = 1
        ceiling_height = 8
        if bldg == 0:  # SF
            fa_bldg = 'single_family_detached'  # then pick single_Family_detached values for floor_area
            if np.random.uniform(0, 1) > res_bldg_metadata['num_stories'][dso_type]['one_story']:
                stories = 2  # all SF homes which are not single story are 2 stories
            ceiling_height += np.random.randint(0, 2)
        elif bldg == 1:  # apartments
            fa_bldg = 'apartment_2_4_units'  # then pick apartment_2_4_units for floor area
        elif bldg == 2:  # mh
            fa_bldg = 'mobile_home'
        else:
            raise ValueError("Wrong building type chosen !")
        vint = vint_type[ti]
        # creating distribution array for floor_area
        for ind in ['min', 'max', 'mean', 'standard_deviation']:
            fa_array[ind] = res_bldg_metadata['floor_area'][ind][fa_bldg][vint]
            next_ti = ti
            while not fa_array[ind]: # if value is null/None, check the next vintage bin
                next_ti += 1
                fa_array[ind] = res_bldg_metadata['floor_area'][ind][fa_bldg][vint_type[next_ti]]
        # print(i)
        # print(nhouse)
        floor_area = random_norm_trunc(fa_array) # truncated normal distribution
        floor_area = (1 + lg_v_sm) * floor_area  # adjustment depends on whether nhouses rounded up or down
        fa_rand = np.random.uniform(0, 1)
        if floor_area > 6000:  # TODO: do we need this condition ? it was originally 4000
            floor_area = 5800 + fa_rand * 200
        elif floor_area < 300:
            floor_area = 300 + fa_rand * 100

        # ********** residential skew and scalar for schedule files **********
        scalar1 = 324.9 / 8907 * floor_area ** 0.442
        scalar2 = 0.6 + 0.4 * np.random.uniform(0, 1)
        scalar3 = 0.6 + 0.4 * np.random.uniform(0, 1)
        resp_scalar = scalar1 * scalar2
        unresp_scalar = scalar1 * scalar3
        skew_value = residential_skew_std * np.random.randn()
        if skew_value < -residential_skew_max:
            skew_value = -residential_skew_max
        elif skew_value > residential_skew_max:
            skew_value = residential_skew_max

        #  *************** Aspect ratio, ewf, ecf, eff, wwr ****************************
        if bldg == 0:  # SF homes
            dist_array = res_bldg_metadata['aspect_ratio']['single_family']  # min, max, mean, std
            aspect_ratio = random_norm_trunc(dist_array)
            # Exterior wall and ceiling and floor fraction
            # A normal single family house has all walls exterior, has a ceiling and a floor
            ewf = 1  # exterior wall fraction
            ecf = 1  # exterior ceiling fraction
            eff = 1  # exterior floor fraction
            wwr = (res_bldg_metadata['window_wall_ratio']['single_family']['mean'])  # window wall ratio
        elif bldg == 1:  # APT
            dist_array = res_bldg_metadata['aspect_ratio']['apartments']  # min, max, mean, std
            aspect_ratio = random_norm_trunc(dist_array)
            wwr = (res_bldg_metadata['window_wall_ratio']['apartments']['mean'])  # window wall ratio
            # Two type of apts assumed:
            #       1. small apt: 8 units with 4 units on each level: total 2 levels
            #       2. large apt: 16 units with 8 units on each level: total 2 levels
            # Let's decide if this unit belongs to a small apt (8 units) or large (16 units)
            small_apt_pct = res_bldg_metadata['housing_type'][dso_type]['apartment_2_4_units']
            large_apt_pct = res_bldg_metadata['housing_type'][dso_type]['apartment_5_units']
            if np.random.uniform(0, 1) < small_apt_pct/(small_apt_pct+large_apt_pct):  # 2-level small apt (8 units)
                # in these apt, all 4 upper units are identical and all 4 lower units are identical
                # So, only two types of units: upper and lower (50% chances of each)
                ewf = 0.5  # all units have 50% walls exterior
                if np.random.uniform(0, 1) < 0.5:  # for 50% units: has floor but no ceiling
                    ecf = 0
                    eff = 1
                else:  # for other 50% units: has ceiling but not floor
                    ecf = 1
                    eff = 0
            else:  # double-loaded (2-level) 16 units apts
                # In these apts, there are 4 type of units: 4 corner bottom floor, 4 corner upper,
                # 4 middle upper and 4 middle lower floor units. Each unit type has 25% chances
                if np.random.uniform(0, 1) < 0.25:  # 4: corner bottom floor units
                    ewf = 0.5
                    ecf = 0
                    eff = 1
                elif np.random.uniform(0, 1) < 0.5:  # 4: corner upper floor units
                    ewf = 0.5
                    ecf = 1
                    eff = 0
                elif np.random.uniform(0, 1) < 0.75:  # 4: middle bottom floor units
                    ewf = aspect_ratio / (1 + aspect_ratio) / 2
                    ecf = 0
                    eff = 1
                else:  # np.random.uniform(0, 1) < 1  # 4: middle upper floor units
                    ewf = aspect_ratio / (1 + aspect_ratio) / 2
                    ecf = 1
                    eff = 0
        else:  # bldg == 2  # Mobile Homes
            # select between single and double wide
            wwr = (res_bldg_metadata['window_wall_ratio']['mobile_home']['mean'])  # window wall ratio
            sw_pct = res_bldg_metadata['mobile_home_single_wide'][vint]  # single wide percentage for given vintage bin
            next_ti = ti
            while not sw_pct:  # if the value is null or 'None', check the next vintage bin
                next_ti += 1
                sw_pct = res_bldg_metadata['mobile_home_single_wide'][vint_type[next_ti]]
            if np.random.uniform(0, 1) < sw_pct:  # Single wide
                aspect_ratio = random_norm_trunc(res_bldg_metadata['aspect_ratio']['mobile_home_single_wide'])
            else:  # double wide
                aspect_ratio = random_norm_trunc(res_bldg_metadata['aspect_ratio']['mobile_home_double_wide'])
            # A normal MH has all walls exterior, has a ceiling and a floor
            ewf = 1  # exterior wall fraction
            ecf = 1  # exterior ceiling fraction
            eff = 1  # exterior floor fraction

        # oversize = rgnOversizeFactor[rgn-1] * (0.8 + 0.4 * np.random.uniform(0,1))
        # data from https://collaborate.pnl.gov/projects/Transactive/Shared%20Documents/DSO+T/Setup%20Assumptions%205.3/Residential%20HVAC.xlsx
        oversize = random_norm_trunc(res_bldg_metadata['hvac_oversize']) # hvac_oversize factor
        wetc = random_norm_trunc(res_bldg_metadata['window_shading'])  # window_exterior_transmission_coefficient
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
        mass_solar_gain_frac = 0.5
        mass_int_gain_frac = 0.5
        # ***********COP*********************************
        # pick any one year value randomly from the bin in cop_lookup
        h_COP = c_COP = np.random.choice(cop_lookup[ti])*(0.9 + np.random.uniform(0,1)*0.2) # +- 10% of mean value
        # h_COP = c_COP = tiProps[10] + np.random.uniform(0, 1) * (tiProps[9] - tiProps[10])

        print('object house {', file=op)
        print('  name', hsename + ';', file=op)
        print('  parent', hse_m_name + ';', file=op)
        print('  groupid', bldgTypeName[bldg] + ';', file=op)
        print('  // thermal_integrity_level', tiName[ti] + ';', file=op) #TODO: why thermal integrity level is not used ?
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
        print('  mass_solar_gain_fraction', '{}'.format(mass_solar_gain_frac) + ';', file=op)
        print('  mass_internal_gain_fraction', '{}'.format(mass_int_gain_frac) + ';', file=op)
        print('  aspect_ratio', '{:.2f}'.format(aspect_ratio) + ';', file=op)
        print('  exterior_wall_fraction', '{:.2f}'.format(ewf) + ';', file=op)
        print('  exterior_floor_fraction', '{:.2f}'.format(eff) + ';', file=op)
        print('  exterior_ceiling_fraction', '{:.2f}'.format(ecf) + ';', file=op)
        print('  window_exterior_transmission_coefficient', '{:.2f}'.format(wetc) + ';', file=op)
        print('  window_wall_ratio', '{:.2f}'.format(wwr) + ';', file=op)
        print('  breaker_amps 1000;', file=op)
        print('  hvac_breaker_rating 1000;', file=op)
        heat_rand = np.random.uniform(0, 1)
        cool_rand = np.random.uniform(0, 1)
        house_fuel_type = 'electric'
        if heat_rand <= res_bldg_metadata['gas_heating'][dso_type]:
            house_fuel_type = 'gas'
            print('  heating_system_type GAS;', file=op)
            if cool_rand <= electric_cooling_percentage:
                print('  cooling_system_type ELECTRIC;', file=op)
            else:
                print('  cooling_system_type NONE;', file=op)
        elif heat_rand <= res_bldg_metadata['gas_heating'][dso_type] + res_bldg_metadata['heat_pump'][dso_type]:
            print('  heating_system_type HEAT_PUMP;', file=op)
            print('  heating_COP', '{:.1f}'.format(h_COP) + ';', file=op)
            print('  cooling_system_type ELECTRIC;', file=op)
            print('  auxiliary_strategy DEADBAND;', file=op)
            print('  auxiliary_system_type ELECTRIC;', file=op)
            print('  motor_model BASIC;', file=op)
            print('  motor_efficiency AVERAGE;', file=op)
        # TODO: check with Rob if following large home condition is needed or not:
        # elif floor_area * ceiling_height > 12000.0:  # electric heat not allowed on large homes
        #     print('  heating_system_type GAS;', file=op)
        #     if cool_rand <= electric_cooling_percentage:
        #         print('  cooling_system_type ELECTRIC;', file=op)
        #     else:
        #         print('  cooling_system_type NONE;', file=op)
        else:
            print('  heating_system_type RESISTANCE;', file=op)
            if cool_rand <= electric_cooling_percentage:
                print('  cooling_system_type ELECTRIC;', file=op)
                print('  motor_model BASIC;', file=op);
                print('  motor_efficiency GOOD;', file=op);
            else:
                print('  cooling_system_type NONE;', file=op)

        cooling_sch = np.ceil(coolingScheduleNumber * np.random.uniform(0, 1))
        heating_sch = np.ceil(heatingScheduleNumber * np.random.uniform(0, 1))
        # [Bin Prob, NightTimeAvgDiff, HighBinSetting, LowBinSetting]
        cooling_bin, heating_bin = selectSetpointBins(bldg, np.random.uniform(0, 1))
        # randomly choose setpoints within bins, and then widen the separation to account for deadband
        cooling_set = cooling_bin[3] + np.random.uniform(0, 1) * (cooling_bin[2] - cooling_bin[3]) + 1
        heating_set = heating_bin[3] + np.random.uniform(0, 1) * (heating_bin[2] - heating_bin[3]) - 1
        cooling_diff = 2.0 * cooling_bin[1] * np.random.uniform(0, 1)
        heating_diff = 2.0 * heating_bin[1] * np.random.uniform(0, 1)
        cooling_str = 'cooling' + '{:.0f}'.format(cooling_sch) + '*' + '{:.2f}'.format(
            cooling_diff) + '+' + '{:.2f}'.format(cooling_set)
        heating_str = 'heating' + '{:.0f}'.format(heating_sch) + '*' + '{:.2f}'.format(
            heating_diff) + '+' + '{:.2f}'.format(heating_set)
        # default heating and cooling setpoints are 70 and 75 degrees in GridLAB-D
        # we need more separation to assure no overlaps during transactive simulations
        #print('  cooling_setpoint 80.0; // ', cooling_str + ';', file=op)
        #print('  heating_setpoint 60.0; // ', heating_str + ';', file=op)
        ## decreased seperation for Transactive Microgrids
        print('  cooling_setpoint 75.0; // ', cooling_str + ';', file=op)
        print('  heating_setpoint 60.0; // ', heating_str + ';', file=op) ##MuMonish: Preventing heating mode

        # heatgain fraction, Zpf, Ipf, Ppf, Z, I, P
        print('  object ZIPload { // responsive', file=op)
        print('    schedule_skew', '{:.0f}'.format(skew_value) + ';', file=op)
        print('    heatgain_fraction', '{:.2f}'.format(techdata[0]) + ';', file=op)
        print('    base_power', 'responsive_loads*' + '{:.2f}'.format(resp_scalar) + ';', file=op)
        print('    impedance_pf', '{:.2f}'.format(techdata[1]) + ';', file=op)
        print('    current_pf', '{:.2f}'.format(techdata[2]) + ';', file=op)
        print('    power_pf', '{:.2f}'.format(techdata[3]) + ';', file=op)
        print('    impedance_fraction', '{:.2f}'.format(techdata[4]) + ';', file=op)
        print('    current_fraction', '{:.2f}'.format(techdata[5]) + ';', file=op)
        print('    power_fraction', '{:.2f}'.format(techdata[6]) + ';', file=op)
        print('  };', file=op)
        print('  object ZIPload { // unresponsive', file=op)
        print('    schedule_skew', '{:.0f}'.format(skew_value) + ';', file=op)
        print('    heatgain_fraction', '{:.2f}'.format(techdata[0]) + ';', file=op)
        print('    base_power', 'unresponsive_loads*' + '{:.2f}'.format(unresp_scalar) + ';', file=op)
        print('    impedance_pf', '{:.2f}'.format(techdata[1]) + ';', file=op)
        print('    current_pf', '{:.2f}'.format(techdata[2]) + ';', file=op)
        print('    power_pf', '{:.2f}'.format(techdata[3]) + ';', file=op)
        print('    impedance_fraction', '{:.2f}'.format(techdata[4]) + ';', file=op)
        print('    current_fraction', '{:.2f}'.format(techdata[5]) + ';', file=op)
        print('    power_fraction', '{:.2f}'.format(techdata[6]) + ';', file=op)
        print('  };', file=op)
        # if np.random.uniform(0, 1) <= water_heater_percentage:  # rgnPenElecWH[rgn-1]:
        if house_fuel_type == 'electric':  # if the house fuel type is electric, install wh
            heat_element = 3.0 + 0.5 * np.random.randint(1, 6);  # numpy randint (lo, hi) returns lo..(hi-1)
            tank_set = 110 + 16 * np.random.uniform(0, 1);
            therm_dead = 1  # 4 + 4 * np.random.uniform(0, 1);
            tank_UA = 2 + 2 * np.random.uniform(0, 1);
            water_sch = np.ceil(waterHeaterScheduleNumber * np.random.uniform(0, 1))
            water_var = 0.95 + np.random.uniform(0, 1) * 0.1  # +/-5% variability
            wh_demand_type = 'large_'
            sizeIncr = np.random.randint(0, 3)  # MATLAB randi(imax) returns 1..imax
            sizeProb = np.random.uniform(0, 1);
            # old wh size implementation
            # if sizeProb <= rgnWHSize[rgn - 1][0]:
            #     wh_size = 20 + sizeIncr * 5
            #     wh_demand_type = 'small_'
            # elif sizeProb <= (rgnWHSize[rgn - 1][0] + rgnWHSize[rgn - 1][1]):
            #     wh_size = 30 + sizeIncr * 10
            #     if floor_area < 2000.0:
            #         wh_demand_type = 'small_'
            # else:
            #     if floor_area < 2000.0:
            #         wh_size = 30 + sizeIncr * 10
            #     else:
            #         wh_size = 50 + sizeIncr * 10

            # new wh size implementation
            wh_data = res_bldg_metadata['water_heater_tank_size']
            if floor_area <= wh_data['floor_area']['1_2_people']['floor_area_max']:
                size_array = range(wh_data['tank_size']['1_2_people']['min'],
                                   wh_data['tank_size']['1_2_people']['max']+1,
                                   5)
                wh_size =np.random.choice(size_array)
                wh_demand_type = 'small_'
            elif floor_area <= wh_data['floor_area']['2_3_people']['floor_area_max']:
                size_array = range(wh_data['tank_size']['2_3_people']['min'],
                                   wh_data['tank_size']['2_3_people']['max']+1,
                                   5)
                wh_size =np.random.choice(size_array)
                wh_demand_type = 'small_'
            elif floor_area <= wh_data['floor_area']['3_4_people']['floor_area_max']:
                size_array = range(wh_data['tank_size']['3_4_people']['min'],
                                   wh_data['tank_size']['3_4_people']['max']+1,
                                   10)
                wh_size =np.random.choice(size_array)
            else:
                size_array = range(wh_data['tank_size']['5_plus_people']['min'],
                                   wh_data['tank_size']['5_plus_people']['max'] + 1,
                                   10)
                wh_size = np.random.choice(size_array)

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
#            if np.random.uniform(0, 1) <= water_heater_participation:
            print('    waterheater_model MULTILAYER;', file=op)
            print('    discrete_step_size 60.0;', file=op)
            print('    lower_tank_setpoint', '{:.1f}'.format(tank_set - 5.0) + ';', file=op)
            print('    upper_tank_setpoint', '{:.1f}'.format(tank_set + 5.0) + ';', file=op)
            print('    T_mixing_valve', '{:.1f}'.format(tank_set) + ';', file=op)
#            else:
#                print('    tank_setpoint', '{:.1f}'.format(tank_set) + ';', file=op)
            if metrics_interval > 0 and "waterheater" in metrics:
                print('    object metrics_collector {', file=op)
                print('      interval', str(metrics_interval) + ';', file=op)
                print('    };', file=op)
            print('  };', file=op)
        if metrics_interval > 0 and "house" in metrics:
            print ('  object metrics_collector {', file=op)
            print ('    interval', str(metrics_interval) + ';', file=op)
            print ('  };', file=op)
        print ('}', file=op)
        # if PV is allowed, then only single-family houses can buy it, and only the single-family houses with PV will also consider storage
        # if PV is not allowed, then any single-family house may consider storage (if allowed)
        # apartments and mobile homes may always consider storage, but not PV
        # bConsiderStorage = True
        if bldg == 0:  # Single-family homes
            if solar_percentage > 0.0:
                pass
                # bConsiderStorage = False
            if np.random.uniform(0, 1) <= solar_percentage:  # some single-family houses have PV
                # bConsiderStorage = True
                panel_area = 0.1 * floor_area
                if panel_area < 162:
                    panel_area = 162
                elif panel_area > 270:
                    panel_area = 270
                inv_power = inv_undersizing * (panel_area / 10.7642) * rated_insolation * array_efficiency
                solar_count += 1
                solar_kw += 0.001 * inv_power
                print('object triplex_meter {', file=op)
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
                print('      generator_mode SUPPLY_DRIVEN;', file=op)
                print('      generator_status ONLINE;', file=op)
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
        if np.random.uniform (0, 1) <= storage_percentage:
            batt_capacity = get_dist(batt_metadata['capacity(kWh)']['mean'],
                                     batt_metadata['capacity(kWh)']['deviation_range_per'])*1000
            max_charge_rt = get_dist(batt_metadata['rated_charging_power(kW)']['mean'],
                                     batt_metadata['rated_charging_power(kW)']['deviation_range_per']) * 1000
            max_discharge_rt = max_charge_rt
            inv_eff = batt_metadata['inv_efficiency(per)'] / 100
            charging_loss = get_dist(batt_metadata['rated_charging_loss(per)']['mean'],
                                     batt_metadata['rated_charging_loss(per)']['deviation_range_per'])/100
            discharging_loss = charging_loss
            bat_rt_efficiency = charging_loss * discharging_loss
            rated_power = max(max_charge_rt, max_discharge_rt)

            if caseType['batteryCase']:
                battery_count += 1
                print ('object triplex_meter {', file=op)
                print ('  name', bat_m_name + ';', file=op)
                print ('  parent', mtrname + ';', file=op)
                print ('  phases', phs + ';', file=op)
                print ('  nominal_voltage ' + str(vnom) + ';', file=op)
                print ('  object inverter {', file=op)
                print ('    name', bat_i_name + ';', file=op)
                print ('    phases', phs + ';', file=op)
                print ('    generator_status ONLINE;', file=op)
                print ('    generator_mode CONSTANT_PQ;', file=op)
                print ('    inverter_type FOUR_QUADRANT;', file=op)
                print ('    four_quadrant_control_mode', storage_inv_mode + ';', file=op)
                print ('    charge_lockout_time 1;', file=op)
                print ('    discharge_lockout_time 1;', file=op)
                print ('    rated_power', '{:.2f}'.format(rated_power) + ';', file=op)
                print ('    max_charge_rate', '{:.2f}'.format(max_charge_rt) + ';', file=op)
                print ('    max_discharge_rate', '{:.2f}'.format(max_discharge_rt) + ';', file=op)
                print ('    sense_object', mtrname + ';', file=op)
                # print ('    charge_on_threshold -100;', file=op)
                # print ('    charge_off_threshold 0;', file=op)
                # print ('    discharge_off_threshold 2000;', file=op)
                # print ('    discharge_on_threshold 3000;', file=op)
                print ('    inverter_efficiency', '{:.2f}'.format(inv_eff) + ';', file=op)
                print ('    power_factor 1.0;', file=op)
                print ('    object battery { // Tesla Powerwall 2', file=op)
                print ('      name', batname + ';', file=op)
                print ('      generator_status ONLINE;', file=op)
                print ('      use_internal_battery_model true;', file=op)
                print ('      generator_mode CONSTANT_PQ;', file=op)
                print ('      battery_type LI_ION;', file=op)
                print ('      nominal_voltage 480;', file=op)
                print ('      battery_capacity', '{:.2f}'.format(batt_capacity) + ';', file=op)
                print ('      round_trip_efficiency', '{:.2f}'.format(bat_rt_efficiency) + ';', file=op)
                print ('      state_of_charge 0.50;', file=op)
                print ('      generator_mode SUPPLY_DRIVEN;', file=op)
                print ('    };', file=op)
                if metrics_interval > 0 and "inverter" in metrics:
                    print ('    object metrics_collector {', file=op)
                    print ('      interval', str(metrics_interval) + ';', file=op)
                    print ('    };', file=op)
                print ('  };', file=op)
                print ('}', file=op)

def write_substation (op, name, phs, vnom, vll):
    """Write the substation swing node, transformer, metrics collector and fncs_msg object

    Args:
        op (file): an open GridLAB-D input file
        name (str): node name of the primary (not transmission) substation bus
        phs (str): primary phasing in the substation
        vnom (float): not used
        vll (float): feeder primary line-to-line voltage
    """
    # if this feeder will be combined with others, need USE_FNCS to appear first as a marker for the substation
    if len(fncs_case) > 0:
        print ('#ifdef USE_FNCS', file=op)
        print ('object fncs_msg {', file=op)
        #if forERCOT == True:
        #    print ('  name gridlabd' + substationName + ';', file=op) # fncs_case
        #else:
        print ('  name gridlabd' + substationName + ';', file=op)  # for full-order DSOT
        print ('  parent network_node;', file=op)
        print ('  configure', fncs_case + '_FNCS_Config.txt;', file=op)
        print ('  option "transport:hostname localhost, port ' + str(port) + '";', file=op)
        print ('  aggregate_subscriptions true;', file=op)
        print ('  aggregate_publications true;', file=op)
        print ('}', file=op)
        print ('#endif', file=op)
    ##### adding HELICS MSG links  ######
    if len(helics_case) > 0:
        print('#ifdef USE_HELICS', file=op)
        print('object helics_msg {', file=op)
        # if forERCOT == True:
        #    print ('  name gridlabd' + substationName + ';', file=op) # fncs_case
        # else:
        print('  name gridlabd' + substationName + ';', file=op)  # for full-order DSOT
        print('  parent network_node;', file=op)
        print('  configure', helics_case + '_HELICS_Config.json;', file=op)
        print('}', file=op)
        print('#endif', file=op)

    print ('object transformer_configuration {', file=op)
    print ('  name substation_xfmr_config;', file=op)
    print ('  connect_type WYE_WYE;', file=op)
    print ('  install_type PADMOUNT;', file=op)
    print ('  primary_voltage', '{:.2f}'.format (transmissionVoltage) + ';', file=op)
    print ('  secondary_voltage', '{:.2f}'.format (vll) + ';', file=op)
    print ('  power_rating', '{:.2f}'.format (transmissionXfmrMVAbase * 1000.0) + ';', file=op)
    print ('  resistance', '{:.2f}'.format (0.01 * transmissionXfmrRpct) + ';', file=op)
    print ('  reactance', '{:.2f}'.format (0.01 * transmissionXfmrXpct) + ';', file=op)
    print ('  shunt_resistance', '{:.2f}'.format (100.0 / transmissionXfmrNLLpct) + ';', file=op)
    print ('  shunt_reactance', '{:.2f}'.format (100.0 / transmissionXfmrImagpct) + ';', file=op)
    print ('}', file=op)
    print ('object transformer {', file=op)
    print ('  name substation_transformer;', file=op)
    print ('  from network_node;', file=op)
    print ('  to', name + ';', file=op)
    print ('  phases', phs + ';', file=op)
    print ('  configuration substation_xfmr_config;', file=op)
    print ('}', file=op)
    vsrcln = transmissionVoltage / math.sqrt (3.0)
    print ('object substation {', file=op)
    print ('  name network_node;', file=op)
    print ('  groupid', base_feeder_name + ';', file=op)
    print ('  bustype SWING;', file=op)
    print ('  nominal_voltage', '{:.2f}'.format (vsrcln) + ';', file=op)
    print ('  positive_sequence_voltage', '{:.2f}'.format (vsrcln) + ';', file=op)
    print ('  base_power', '{:.2f}'.format (transmissionXfmrMVAbase * 1000000.0) + ';', file=op)
    print ('  power_convergence_value 100.0;', file=op)
    print ('  phases', phs + ';', file=op)
    if metrics_interval > 0 and "substation" in metrics:
        print ('  object metrics_collector {', file=op)
        print ('    interval', str(metrics_interval) + ';', file=op)
        print ('  };', file=op)
    print ('}', file=op)

# if triplex load, node or meter, the nominal voltage is 120
#   if the name or parent attribute is found in secmtrnode, we look up the nominal voltage there
#   otherwise, the nominal voltage is vprim
# secmtrnode[mtr_node] = [kva_total, phases, vnom]
#   the transformer phasing was not changed, and the transformers were up-sized to the largest phase kva
#   therefore, it should not be necessary to look up kva_total, but phases might have changed N==>S
# if the phasing did change N==>S, we have to prepend triplex_ to the class, write power_1 and voltage_1
# when writing commercial buildings, if load_class is present and == C, skip the instance
def write_voltage_class (model, h, t, op, vprim, vll, secmtrnode):
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
            name = o # model[t][o]['name']
            phs = model[t][o]['phases']
            vnom = vprim
            if 'bustype' in model[t][o]:
                if model[t][o]['bustype'] == 'SWING':
                    write_substation (op, name, phs, vnom, vll)
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
            if str.find(phs,'S') >= 0:
                bHaveS = True
            else:
                bHaveS = False
            if bHaveS == True and bHadS == False:
                prefix = 'triplex_'
            print('object ' + prefix + t + ' {', file=op)
            if len(parent) > 0:
                print('  parent ' + parent + ';', file=op)
            print('  name ' + gld_strict_name(name) + ';', file=op)
            if 'groupid' in model[t][o]:
                print('  groupid ' + model[t][o]['groupid'] + ';', file=op)
            if 'bustype' in model[t][o]: # already moved the SWING bus behind substation transformer
                if model[t][o]['bustype'] != 'SWING':
                    print('  bustype ' + model[t][o]['bustype'] + ';', file=op)
            print('  phases ' + phs + ';', file=op)
            print('  nominal_voltage ' + str(vnom) + ';', file=op)
            if 'load_class' in model[t][o]:
                print('  load_class ' + model[t][o]['load_class'] + ';', file=op)
            if 'constant_power_A' in model[t][o]:
                if bHaveS == True:
                    print('  power_1 ' + model[t][o]['constant_power_A'] + ';', file=op)
                else:
                    print('  constant_power_A ' + model[t][o]['constant_power_A'] + ';', file=op)
            if 'constant_power_B' in model[t][o]:
                if bHaveS == True:
                    print('  power_1 ' + model[t][o]['constant_power_B'] + ';', file=op)
                else:
                    print('  constant_power_B ' + model[t][o]['constant_power_B'] + ';', file=op)
            if 'constant_power_C' in model[t][o]:
                if bHaveS == True:
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
            vstartb = format(-0.5*vnom,'.2f') + format(-0.866025*vnom,'.2f') + 'j'
            vstartc = format(-0.5*vnom,'.2f') + '+' + format(0.866025*vnom,'.2f') + 'j'
            if 'voltage_A' in model[t][o]:
                if bHaveS == True:
                    print('  voltage_1 ' + vstarta + ';', file=op)
                    print('  voltage_2 ' + vstarta + ';', file=op)
                else:
                    print('  voltage_A ' + vstarta + ';', file=op)
            if 'voltage_B' in model[t][o]:
                if bHaveS == True:
                    print('  voltage_1 ' + vstartb + ';', file=op)
                    print('  voltage_2 ' + vstartb + ';', file=op)
                else:
                    print('  voltage_B ' + vstartb + ';', file=op)
            if 'voltage_C' in model[t][o]:
                if bHaveS == True:
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
                write_tariff (op)
                if metrics_interval > 0 and "meter" in metrics:
                    print ('  object metrics_collector {', file=op)
                    print ('    interval', str(metrics_interval) + ';', file=op)
                    print ('  };', file=op)
            elif "meter" in t:
                write_tariff (op)
                if metrics_interval > 0 and "meter" in metrics:
                    print ('  object metrics_collector {', file=op)
                    print ('    interval', str(metrics_interval) + ';', file=op)
                    print ('  };', file=op)
            print('}', file=op)

def write_xfmr_config (key, phs, kvat, vnom, vsec, install_type, vprimll, vprimln, op):
    """Write a transformer_configuration

    Args:
        key (str): name of the configuration
        phs (str): primary phasing
        kvat (float): transformer rating in kVA
        vnom (float): primary voltage rating, not used any longer (see vprimll and vprimln)
        vsec (float): secondary voltage rating, should be line-to-neutral for single-phase or line-to-line for three-phase
        install_type (str): should be VAULT, PADMOUNT or POLETOP
        vprimll (float): primary line-to-line voltage, used for three-phase transformers
        vprimln (float): primary line-to-neutral voltage, used for single-phase transformers
        op (file): an open GridLAB-D input file
    """
    print ('object transformer_configuration {', file=op)
    print ('  name ' + key + ';', file=op)
    print ('  power_rating ' + format(kvat, '.2f') + ';', file=op)
    kvaphase = kvat
    if 'XF2' in key:
        kvaphase /= 2.0
    if 'XF3' in key:
        kvaphase /= 3.0
    if 'A' in phs:
        print ('  powerA_rating ' + format(kvaphase, '.2f') + ';', file=op)
    else:
        print ('  powerA_rating 0.0;', file=op)
    if 'B' in phs:
        print ('  powerB_rating ' + format(kvaphase, '.2f') + ';', file=op)
    else:
        print ('  powerB_rating 0.0;', file=op)
    if 'C' in phs:
        print ('  powerC_rating ' + format(kvaphase, '.2f') + ';', file=op)
    else:
        print ('  powerC_rating 0.0;', file=op)
    print ('  install_type ' + install_type + ';', file=op)
    if 'S' in phs:
        row = Find1PhaseXfmr (kvat)
        print ('  connect_type SINGLE_PHASE_CENTER_TAPPED;', file=op)
        print ('  primary_voltage ' + str(vprimln) + ';', file=op)
        print ('  secondary_voltage ' + format(vsec, '.1f') + ';', file=op)
        print ('  resistance ' + format(row[1] * 0.5, '.5f') + ';', file=op)
        print ('  resistance1 ' + format(row[1], '.5f') + ';', file=op)
        print ('  resistance2 ' + format(row[1], '.5f') + ';', file=op)
        print ('  reactance ' + format(row[2] * 0.8, '.5f') + ';', file=op)
        print ('  reactance1 ' + format(row[2] * 0.4, '.5f') + ';', file=op)
        print ('  reactance2 ' + format(row[2] * 0.4, '.5f') + ';', file=op)
        print ('  shunt_resistance ' + format(1.0 / row[3], '.2f') + ';', file=op)
        print ('  shunt_reactance ' + format(1.0 / row[4], '.2f') + ';', file=op)
    else:
        row = Find3PhaseXfmr (kvat)
        print ('  connect_type WYE_WYE;', file=op)
        print ('  primary_voltage ' + str(vprimll) + ';', file=op)
        print ('  secondary_voltage ' + format(vsec, '.1f') + ';', file=op)
        print ('  resistance ' + format(row[1], '.5f') + ';', file=op)
        print ('  reactance ' + format(row[2], '.5f') + ';', file=op)
        print ('  shunt_resistance ' + format(1.0 / row[3], '.2f') + ';', file=op)
        print ('  shunt_reactance ' + format(1.0 / row[4], '.2f') + ';', file=op)
    print('}', file=op)

def log_model(model, h):
    """Prints the whole parsed model for debugging

    Args:
        model (dict): parsed GridLAB-D model
        h (dict): object ID hash
    """
    for t in model:
        print(t+':')
        for o in model[t]:
            print('\t'+o+':')
            for p in model[t][o]:
                if ':' in model[t][o][p]:
                    print('\t\t'+p+'\t-->\t'+h[model[t][o][p]])
                else:
                    print('\t\t'+p+'\t-->\t'+model[t][o][p])

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

def ProcessTaxonomyFeeder (outname, rootname, vll, vln, avghouse, avgcommercial):
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
    global solar_count, solar_kw, battery_count, base_feeder_name
    solar_count = 0
    solar_kw = 0
    battery_count = 0

    base_feeder_name = gld_strict_name(rootname)
    fname = glmpath + rootname + '.glm'
    print (fname)
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
    global electric_cooling_percentage, storage_percentage, solar_percentage
    global water_heater_percentage, water_heater_participation
    print ('using', solar_percentage, 'solar and', storage_percentage, 'storage penetration')
    if electric_cooling_percentage <= 0.0:
        electric_cooling_percentage = rgnPenElecCool[rgn-1]
        print ('using regional default', electric_cooling_percentage, 'air conditioning penetration')
    else:
        print ('using', electric_cooling_percentage, 'air conditioning penetration from JSON config')
    # if water_heater_percentage <= 0.0:
    #     water_heater_percentage = rgnPenElecWH[rgn-1]
    #     print ('using regional default', water_heater_percentage, 'water heater penetration')
    # else:
    #     print ('using', water_heater_percentage, 'water heater penetration from JSON config')
    if os.path.isfile(fname):
        ip = open (fname, 'r')
        lines = []
        line = ip.readline()
        while line is not '':
            while re.match('\s*//',line) or re.match('\s+$',line):
                # skip comments and white space
                line = ip.readline()
            lines.append(line.rstrip())
            line = ip.readline()
        ip.close()

        op = open (outpath + outname + '.glm', 'w')
        octr = 0
        model = {}
        h = {}  # OID hash
        itr = iter(lines)

        for line in itr:
            if re.search('object',line):
                line,octr = obj(None,model,line,itr,h,octr)
            else: # should be the pre-amble, need to replace timestamp and stoptime
                if 'timestamp' in line or 'starttime' in line:
                    print('  starttime \'' + starttime + '\';', file=op)
                elif 'stoptime' in line:
                    print ('  stoptime \'' + endtime + '\';', file=op)
                elif 'module powerflow' in line:
                    print ('module powerflow{', file=op)
                    print ('  lu_solver \"KLU\";', file=op)
                else:
                    print (line, file=op)

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
        #  nx.connected_component_subgraphs deprecated in earlier version.
        #  sub_graphs = nx.connected_component_subgraphs(G)
        sub_graphs = [G.subgraph(c).copy() for c in nx.connected_components(G)]
        seg_loads = {} # [name][kva, phases]
        total_kva = 0.0
        for n1, data in G.nodes(data=True):
            if 'ndata' in data:
                kva = accumulate_load_kva (data['ndata'])
                # need to account for large-building loads added through transformer connections
                if n1 == Eplus_Bus:
                    kva += Eplus_kVA
                if kva > 0:
                    total_kva += kva
                    nodes = nx.shortest_path(G, n1, swing_node)
                    edges = zip(nodes[0:], nodes[1:])
                    for u, v in edges:
                        eclass = G[u][v]['eclass']
                        if is_edge_class (eclass):
                            ename = G[u][v]['ename']
                            if ename not in seg_loads:
                                seg_loads[ename] = [0.0, '']
                            seg_loads[ename][0] += kva
                            seg_loads[ename][1] = union_of_phases (seg_loads[ename][1], data['ndata']['phases'])

        print ('  swing node', swing_node, 'with', len(list(sub_graphs)), 'subgraphs and',
               '{:.2f}'.format(total_kva), 'total kva')

        # preparatory items for TESP
        print ('module climate;', file=op)
        print ('module generators;', file=op)
        print ('module connection;', file=op)
        print ('module residential {', file=op)
        print ('  implicit_enduses NONE;', file=op)
        print ('};', file=op)
        print ('#include "' + supportpath + 'appliance_schedules.glm";', file=op)
        print ('#include "' + supportpath + 'water_and_setpoint_schedule_v5.glm";', file=op)
        print ('#include "' + supportpath + 'commercial_schedules.glm";', file=op)
        print ('#set minimum_timestep=' + str(timestep) + ';', file=op)
        print ('#set relax_naming_rules=1;', file=op)
        print ('#set warn=0;', file=op)
        if metrics_interval > 0:
            print ('object metrics_collector_writer {', file=op)
            print ('  interval', str(metrics_interval) + ';', file=op)
            print ('  interim', str(metrics_interim) + ';', file=op)
            print ('  filename ${METRICS_FILE};', file=op)
            print ('  // filename your_metrics;', file=op)
            print ('  alternate yes;', file=op)
            print ('  extension {0:s};'.format(metrics_type), file=op)
            print ('};', file=op)
        print ('object climate {', file=op)
        print ('  name', str(weather_name) + ';', file=op)
        print ('  // tmyfile "' + weatherpath + weather_file + '";', file=op)
        print ('  interpolate QUADRATIC;', file=op)
        print ('  latitude', str(latitude) + ';', file=op)
        print ('  longitude', str(longitude) + ';', file=op)
        print ('  tz_meridian {0:.2f};'.format(15 * time_zone_offset), file=op)
        print ('};', file=op)
        #        print ('// taxonomy_base_feeder', rootname, file=op)
        #        print ('// region_name', rgnName[rgn-1], file=op)
        if solar_percentage > 0.0:
            print ('// default IEEE 1547-2018 for Category B; modes are CONSTANT_PF, VOLT_VAR, VOLT_WATT', file=op)
            print ('#define INVERTER_MODE=' + solar_inv_mode, file=op)
            print ('#define INV_VBASE=240.0', file=op)
            print ('#define INV_V1=0.92', file=op)
            print ('#define INV_V2=0.98', file=op)
            print ('#define INV_V3=1.02', file=op)
            print ('#define INV_V4=1.08', file=op)
            print ('#define INV_Q1=0.44', file=op)
            print ('#define INV_Q2=0.00', file=op)
            print ('#define INV_Q3=0.00', file=op)
            print ('#define INV_Q4=-0.44', file=op)
            print ('#define INV_VIN=200.0', file=op)
            print ('#define INV_IIN=32.5', file=op)
            print ('#define INV_VVLOCKOUT=300.0', file=op)
            print ('#define INV_VW_V1=1.05 // 1.05833', file=op)
            print ('#define INV_VW_V2=1.10', file=op)
            print ('#define INV_VW_P1=1.0', file=op)
            print ('#define INV_VW_P2=0.0', file=op)
# write the optional volt_dump and curr_dump for validation
        print ('#ifdef WANT_VI_DUMP', file=op)
        print ('object voltdump {', file=op)
        print ('  filename Voltage_Dump_' + outname + '.csv;', file=op)
        print ('  mode polar;', file=op)
        print ('}', file=op)
        print ('object currdump {', file=op)
        print ('  filename Current_Dump_' + outname + '.csv;', file=op)
        print ('  mode polar;', file=op)
        print ('}', file=op)
        print ('#endif', file=op)

        # NEW STRATEGY - loop through transformer instances and assign a standard size based on the downstream load
        #              - change the referenced transformer_configuration attributes
        #              - write the standard transformer_configuration instances we actually need
        xfused = {} # ID, phases, total kva, vnom (LN), vsec, poletop/padmount
        secnode = {} # Node, st, phases, vnom
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
                kvat = Find3PhaseXfmrKva (seg_kva)
            else:
                kvat = Find1PhaseXfmrKva (seg_kva)
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

            model[t][o]['configuration'] = key
            model[t][o]['phases'] = seg_phs
            if key not in xfused:
                xfused[key] = [seg_phs, kvat, vnom, vsec, install_type]

        for key in xfused:
            write_xfmr_config (key, xfused[key][0], xfused[key][1], xfused[key][2], xfused[key][3],
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
                    amps = 1000.0 * seg_kva / math.sqrt(3.0) / vll
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

        write_link_class(model, h, 'regulator', seg_loads, op)
        write_link_class(model, h, 'transformer', seg_loads, op)
        write_link_class(model, h, 'capacitor', seg_loads, op)

        if forERCOT:
            replace_commercial_loads (model, h, 'load', 0.001 * avgcommercial)
            # connect_ercot_commercial (op)
            identify_ercot_houses(model, h, 'load', 0.001 * avghouse, rgn)
            connect_ercot_houses(model, h, op, vln, 120.0)
            for key in house_nodes:
                write_houses(key, op, 120.0)
            for key in small_nodes:
                write_ercot_small_loads(key, op, vln)
            for key in comm_loads:
                # write_commercial_loads (rgn, key, op)
                bldg_definition = tesp_support.commbldgenerator.define_comm_loads(comm_loads[key][1], comm_loads[key][2], dso_type, ashrae_zone, comm_bldg_metadata)
                tesp_support.commbldgenerator.create_comm_zones(bldg_definition, comm_loads, key, op, batt_metadata, storage_percentage, caseType, metrics, metrics_interval, None)
        else:
            replace_commercial_loads(model, h, 'load', 0.001 * avgcommercial)
            identify_xfmr_houses(model, h, 'transformer', seg_loads, 0.001 * avghouse, rgn)
            for key in house_nodes:
                write_houses(key, op, 120.0)
            for key in small_nodes:
                write_small_loads(key, op, 120.0)
            for key in comm_loads:
                # write_commercial_loads (rgn, key, op)
                bldg_definition = tesp_support.commbldgenerator.define_comm_loads(comm_loads[key][1], comm_loads[key][2], dso_type, ashrae_zone, comm_bldg_metadata)
                tesp_support.commbldgenerator.create_comm_zones(bldg_definition, comm_loads, key, op, batt_metadata, storage_percentage, caseType, metrics, metrics_interval, None)

        write_voltage_class(model, h, 'node', op, vln, vll, secnode)
        write_voltage_class(model, h, 'meter', op, vln, vll, secnode)
        if forERCOT == False:
            write_voltage_class(model, h, 'load', op, vln, vll, secnode)
        if len(Eplus_Bus) > 0 and Eplus_Volts > 0.0 and Eplus_kVA > 0.0:
            print('////////// EnergyPlus large-building load ///////////////', file=op)
            row = Find3PhaseXfmr(Eplus_kVA)
            actual_kva = row[0]
            watts_per_phase = 1000.0 * actual_kva / 3.0
            Eplus_vln = Eplus_Volts / math.sqrt (3.0)
            vstarta = format(Eplus_vln, '.2f') + '+0.0j'
            vstartb = format(-0.5 * Eplus_vln, '.2f') + format(-0.866025 * Eplus_vln, '.2f') + 'j'
            vstartc = format(-0.5 * Eplus_vln, '.2f') + '+' + format(0.866025 * Eplus_vln, '.2f') + 'j'
            print('object transformer_configuration {', file=op)
            print('  name Eplus_transformer_configuration;', file=op)
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
            print('  name Eplus_transformer;', file=op)
            print('  phases ABCN;', file=op)
            print('  from', Eplus_Bus + ';', file=op)
            print('  to Eplus_meter;', file=op)
            print('  configuration Eplus_transformer_configuration;', file=op)
            print('}', file=op)
            print('object meter {', file=op)
            print('  name Eplus_meter;', file=op)
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
            print('  name Eplus_load;', file=op)
            print('  parent Eplus_meter;', file=op)
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

        for gen in generators:
            gen_vln = float(generators[gen]['voltage'])
            vstarta = format(gen_vln, '.2f') + '+0.0j'
            vstartb = format(-0.5 * gen_vln, '.2f') + format(-0.866025 * gen_vln, '.2f') + 'j'
            vstartc = format(-0.5 * gen_vln, '.2f') + '+' + format(0.866025 * gen_vln, '.2f') + 'j'
            print('object load {', file=op)
            print('  name', generators[gen]['name'] + ';', file=op)
            print('  parent', generators[gen]['parent'] + ';', file=op)
            print('  phases ABCN;', file=op)
            print('  nominal_voltage', '{:.4f}'.format(gen_vln) + ';', file=op)
            print('  voltage_A ' + vstarta + ';', file=op)
            print('  voltage_B ' + vstartb + ';', file=op)
            print('  voltage_C ' + vstartc + ';', file=op)
            print('}', file=op)

        op.close()


def populate_feeder(fncs_flag = bool(True), helics_flag = bool(False), configfile=None, config=None, taxconfig=None):
    """Wrapper function that processes one feeder. One or two keyword arguments must be supplied.

    Args:
        configfile (str): JSON file name for the feeder population data, mutually exclusive with config
        config (dict): dictionary of feeder population data already read in, mutually exclusive with configfile
        taxconfig (dict): dictionary of custom taxonomy data for ERCOT processing
    """
    global tier1_energy, tier1_price, tier2_energy, tier2_price, tier3_energy, tier3_price, bill_mode, kwh_price, monthly_fee
    global Eplus_Bus, Eplus_Volts, Eplus_kVA
    global transmissionVoltage, transmissionXfmrMVAbase
    global storage_inv_mode, solar_inv_mode, solar_percentage, storage_percentage
    global outpath, glmpath, supportpath, weatherpath, weather_file
    global starttime, endtime, timestep, metrics, metrics_type, metrics_interval, metrics_interim, electric_cooling_percentage
    global water_heater_percentage, water_heater_participation
    global fncs_case, helics_case, port, forERCOT, forDSOT, substationName
    global house_nodes, small_nodes, comm_loads
    global inv_efficiency, bat_rt_efficiency
    global latitude, longitude, time_zone_offset, weather_name, feeder_commercial_building_number
    global dso_type
    global caseType
    global ashrae_zone, comm_bldg_metadata, comm_bldgs_pop
    # (Laurentiu Marinovici 11/18/2019)
    global res_bldg_metadata # to store residential metadata
    global batt_metadata  # to store battery metadata
    global cop_lookup
    global generators # To store generator metadata

    if configfile is not None:
        checkResidentialBuildingTable()
    if config is None:
        lp = open(configfile).read()
        config = json.loads(lp)

    # This seeding has already been done in the prepare_case_dsot_v3.py for each DSO
    # No need to reseed.
    # we want the same pseudo-random variables each time, for repeatability
    # if 'RandomSeed' in config['BackboneFiles']:
    #     np.random.seed(config['BackboneFiles']['RandomSeed'])
    # else:
    #     np.random.seed(0)
    rootname = config['BackboneFiles']['TaxonomyChoice']
    tespdir = config['SimulationConfig']['SourceDirectory']
    glmpath = tespdir + '/feeders/'
    supportpath = ''  # tespdir + '/schedules'
    if 'supportpath' in config['BackboneFiles']:
        supportpath = config['BackboneFiles']['supportpath']
    weatherpath = ''  # tespdir + '/weather'
    if 'weatherpath' in config['BackboneFiles']:
        weatherpath = config['BackboneFiles']['weatherpath']
    outpath = './' + config['SimulationConfig']['CaseName'] + '/'
    if 'OutputPath' in config['SimulationConfig']:
        outpath = './' + config['SimulationConfig']['OutputPath'] + '/'
    if 'DSOTCase' in config['SimulationConfig']:
        forDSOT = config['SimulationConfig']['DSOTCase']
    substationName = config['SimulationConfig']['Substation']
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
    solar_inv_mode = config['FeederGenerator']['SolarInverterMode']
    storage_inv_mode = config['FeederGenerator']['StorageInverterMode']
    # if 'InverterEfficiency' in config['FeederGenerator']:
    #     inv_efficiency = config['FeederGenerator']['InverterEfficiency']
    # if 'BatteryRoundTripEfficiency' in config['FeederGenerator']:
    #     bat_rt_efficiency = config['FeederGenerator']['BatteryRoundTripEfficiency']
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
    time_zone_offset = float(config['WeatherPrep']['TimeZoneOffset'])
    if 'AgentName' in config['WeatherPrep']:
        weatherName = config['WeatherPrep']['AgentName']
    dso_type = config['SimulationConfig']['DSO_type']
    res_bldg_metadata = config['BuildingPrep']['ResBldgMetaData']
    batt_metadata = config['BuildingPrep']['BattMetaData']
    electric_cooling_percentage = res_bldg_metadata['air_conditioning']  # if not provided in JSON config, use a regional default
    ashrae_zone = config['BuildingPrep']['ASHRAEZone']
    comm_bldg_metadata = config['BuildingPrep']['CommBldgMetaData']
    comm_bldgs_pop = config['BuildingPrep']['CommBldgPopulation']
    caseType = config['SimulationConfig']['caseType']

    try:
        generators = config['SimulationConfig']['dso'][next(iter(config['SimulationConfig']['dso']))]['generators']
        print("Found {} generators in SimulationConfig".format(len(generators)))
    except:
        generators = {}
        print("Found No generators in SimulationConfig")
    #-------- create cop lookup table by vintage bin-----------
    # (Laurentiu MArinovici 11/18/2019) moving the cop_lookup inside this function as it requires
    # residential building metadata
    cop_mat = res_bldg_metadata['COP_average']
    years_bin = [range(1945,1950), range(1950,1960), range(1960,1970), range(1970,1980),
                range(1980,1990), range(1990,2000),range(2000, 2010), range(2010,2016)]
    years_bin = [list(years_bin[ind]) for ind in range(len(years_bin))]
    cop_lookup = []
    for bin in range(len(years_bin)):
        temp = []
        for yr in years_bin[bin]:
            temp.append(cop_mat[str(yr)])
        cop_lookup.append(temp)
    # cop_lookup will have similar structure as years bin with years replaced with corresponding mean cop value
    # cop_lookup: index 0: vintage bins (0,1..7)
    #               index 1: each year in the corresponding vintage bin

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
            fncs_case = config['SimulationConfig']['CaseName']
            glmpath = taxconfig['glmpath']
            outpath = taxconfig['outpath']
            supportpath = taxconfig['supportpath']
            weatherpath = taxconfig['weatherpath']
            print(fncs_case, rootname, vll, vln, avg_house, avg_comm, glmpath, outpath, supportpath, weatherpath)
            ProcessTaxonomyFeeder(fncs_case, rootname, vll, vln, avg_house, avg_comm)
        else:
            print(rootname, 'not found in taxconfig backbone_feeders')
    else:
        forERCOT = config['SimulationConfig']['simplifiedFeeders']
        print('using the built-in taxonomy')
        print(rootname, 'to', outpath, 'using', weather_file)
        print('times', starttime, endtime)
        print('steps', timestep, metrics_interval)
        print('hvac', electric_cooling_percentage)
        print('pv', solar_percentage, solar_inv_mode)
        print('storage', storage_percentage, storage_inv_mode)
        print('billing', kwh_price, monthly_fee)
        for c in taxchoice:
            # if c[0] == rootname:
            if c[0] in rootname:
                if fncs_flag:
                    fncs_case = config['SimulationConfig']['CaseName']
                    # ProcessTaxonomyFeeder(fncs_case, c[0], c[1], c[2], c[3], c[4])
                    ProcessTaxonomyFeeder(fncs_case, rootname, c[1], c[2], c[3], c[4])
                #### helics case for adding helics simulation ####
                if helics_flag:
                    helics_case = config['SimulationConfig']['CaseName']
                    # ProcessTaxonomyFeeder(fncs_case, c[0], c[1], c[2], c[3], c[4])
                    ProcessTaxonomyFeeder(helics_case, rootname, c[1], c[2], c[3], c[4])
#                quit()

def populate_all_feeders():
    """Wrapper function that batch processes all taxonomy feeders in the casefiles table (see source file)
    """
    if sys.platform == 'win32':
        batname = 'run_all.bat'
    else:
        batname = 'run_all.sh'
    op = open(outpath + batname, 'w')
    for c in casefiles:
        print('gridlabd -D WANT_VI_DUMP=1 -D METRICS_FILE=' + c[0] + '.json', c[0] + '.glm', file=op)
    op.close()
    for c in casefiles:
        ProcessTaxonomyFeeder(c[0], c[0], c[1], c[2], c[3], c[4])
