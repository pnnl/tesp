
# Copyright (C) 2018-2020 Battelle Memorial Institute
# file: feederGenerator.py
"""Replaces ZIP loads with houses, and optional storage and solar generation.

As this module populates the feeder backbone with houses and DER, it uses
the Networkx package to perform graph-based capacity analysis, upgrading
fuses, transformers and lines to serve the expected load. Transformers have
a margin of 20% to avoid overloads, while fuses have a margin of 150% to
avoid overloads. These can be changed by editing tables and variables in the
source file.

There are two kinds of house populating methods implemented:

    * :Feeders with Service Transformers: This case applies to the full PNNL 
        taxonomy feeders. Do not specify the *taxchoice* argument to 
        *populate_feeder*. Each service transformer receiving houses will have a
        short service drop and a small number of houses attached.
    * :Feeders without Service Transformers: This applies to the reduced-order 
        ERCOT feeders. To invoke this mode, specify the *taxchoice* argument to 
        *populate_feeder*. Each primary load to receive houses will have a large
        service transformer, large service drop and large number of houses attached.

References:
    `GridAPPS-D Feeder Models <https://github.com/GRIDAPPSD/Powergrid-Models>`_

Public Functions:
    :populate_feeder: processes one GridLAB-D input file

Todo:
    * Verify the level zero mobile home thermal integrity properties; 
        these were copied from the MATLAB feeder generator

"""
import sys
import re
import os.path
import networkx as nx
import numpy as np
import pandas as pd
import math
import json
import tesp_support.api.modify_GLM as glmmod
from tesp_support.api.helpers import gld_strict_name, random_norm_trunc
from tesp_support.api.parse_helpers import parse_kva
from tesp_support.api.time_helpers import is_hhmm_valid, subtract_hhmm_secs, add_hhmm_secs
from tesp_support.api.time_helpers import get_secs_from_hhmm, get_hhmm_from_secs, get_duration, get_dist

sys.path.append('./')
import gld_commercial_feeder as comm_FG
import recs_api as recs

global c_p_frac
extra_billing_meters = set()

#***************************************************************************************************
#***************************************************************************************************

# EV population functions
def process_nhts_data(glm_modifier, data_file):
    """
    read the large nhts survey data file containing driving data, process it and return a dataframe
    Args:
        glm_modifier: modify_GLM class object
        data_file: path of the file
    Returns:
        dataframe containing start_time, end_time, travel_day (weekday/weekend) and daily miles driven
    """
    # Read data from NHTS survey
    df_data = pd.read_csv(data_file, index_col=[0, 1])
    # filter based on trip leaving only from home and not from work or other places
    # take the earliest time leaving from home of a particular vehicle
    df_data_leave = df_data[df_data['WHYFROM'] == 1].groupby(level=['HOUSEID', 'VEHID']).min()[['STRTTIME', 'TRAVDAY']]
    # filter based on trip arriving only at home and not at work or other places
    # take the latest time arriving at home of a particular vehicle
    df_data_arrive = df_data[df_data['WHYTO'] == 1].groupby(level=['HOUSEID', 'VEHID']).max()[['ENDTIME', 'TRAVDAY']]
    # take the sum of trip miles by a particular vehicle in a day
    df_data_miles = df_data.groupby(level=['HOUSEID', 'VEHID']).sum()['TRPMILES']
    # limit daily miles to maximum possible range of EV from the ev model data as EVs cant travel more
    # than the range in a day if we don't consider the highway charging
    max_ev_range = max(glm_modifier.defaults.ev_metadata['Range (miles)'])
    df_data_miles = df_data_miles[df_data_miles < max_ev_range]
    df_data_miles = df_data_miles[df_data_miles > 0]

    # combine all 4 parameters: starttime, endtime, total_miles, travel_day.
    # Ignore vehicle ids that don't have both leaving and arrival time at home
    temp = df_data_leave.merge(df_data_arrive['ENDTIME'], left_index=True, right_index=True)
    df_fin = temp.merge(df_data_miles, left_index=True, right_index=True)
    return df_fin

#***************************************************************************************************
#***************************************************************************************************

def selectEVmodel(evTable, prob):
    """ Selects the building and vintage type
    Args:
        evTable (dict): models probability list
        prob (?): probability
    """
    total = 0
    for name, pr in evTable.items():
        total += pr
        if total >= prob:
            return name
    raise UserWarning('EV model sale distribution does not sum to 1!')

#***************************************************************************************************
#***************************************************************************************************
def match_driving_schedule(glm_modifier, ev_range, ev_mileage, ev_max_charge):
    """ Method to match the schedule of each vehicle from NHTS data based on vehicle ev_range"""
    # let's pick a daily travel mile randomly from the driving data that is less than the ev_range-margin to ensure
    # we can always maintain reserved soc level in EV
    while True:
        mile_ind = np.random.randint(0, len(glm_modifier.defaults.ev_driving_metadata['TRPMILES']))
        daily_miles = glm_modifier.defaults.ev_driving_metadata['TRPMILES'].iloc[mile_ind]
        if ev_range * 0.0 < daily_miles < ev_range * (1 - glm_modifier.defaults.ev_reserved_soc / 100):
            break
    daily_miles = max(daily_miles, ev_range * 0.2)
    home_leave_time = glm_modifier.defaults.ev_driving_metadata['STRTTIME'].iloc[mile_ind]
    home_arr_time = glm_modifier.defaults.ev_driving_metadata['ENDTIME'].iloc[mile_ind]
    home_duration = get_duration(home_arr_time, home_leave_time)

    # check if home_duration is enough to charge for daily_miles driven + margin
    margin_miles = daily_miles * 0.10  # 10% extra miles
    charge_hour_need = (daily_miles + margin_miles) / (ev_max_charge * ev_mileage)  # hours
    # since during v1g or v2g mode, we only allow charging start at the start of the next hour after vehicle
    # come home and charging must end at the full hour just before vehicle leaves home,
    # the actual chargeable hours duration may be smaller than the car home duration by maximum 2 hours.
    min_home_need = charge_hour_need + 2
    if min_home_need >= 23:
        raise UserWarning('A particular EV can not be charged fully even within 23 hours!')
    if home_duration < min_home_need * 3600:  # if home duration is less than required minimum
        home_duration = min_home_need * 3600
    if home_duration > 23 * 3600:
        home_duration = 23 * 3600 - 1  # -1 to ensure work duration is not 0 with 1 hour commute time
    # update home arrival time
    home_arr_time = subtract_hhmm_secs(home_leave_time, home_duration)

    # estimate work duration and arrival time
    commute_duration = min(3600, 24 * 3600 - home_duration)  # in secs, maximum 1 hour: 30 minutes for work-home and
    # 30 minutes for home-work. If remaining time is less than an hour,
    # make that commute time, but it should not occur as maximum home duration is always less than 23 hours
    work_duration = max(24 * 3600 - (home_duration + commute_duration), 1)  # remaining time at work
    # minimum work duration is 1 second to avoid 0 that may give error in GridLABD sometimes
    work_arr_secs = get_secs_from_hhmm(home_leave_time) + commute_duration / 2
    if work_arr_secs > 24 * 3600:  # if midnight crossing
        work_arr_secs = work_arr_secs - 24 * 3600
    work_arr_time = get_hhmm_from_secs(work_arr_secs)

    driving_sch = {'daily_miles': daily_miles,
                   'home_arr_time': int(home_arr_time),
                   'home_leave_time': int(home_leave_time),
                   'home_duration': home_duration,
                   'work_arr_time': int(work_arr_time),
                   'work_duration': work_duration
                   }
    return driving_sch

#***************************************************************************************************
#***************************************************************************************************

def randomize_residential_skew(glm_modifier):
    return randomize_skew(glm_modifier.defaults.residential_skew_std, glm_modifier.defaults.residential_skew_max)

#***************************************************************************************************
#***************************************************************************************************

def randomize_skew(value, skew_max):
    sk = value * np.random.randn()
    if sk < skew_max:
        sk = skew_max
    elif sk > skew_max:
        sk = skew_max
    return sk

#***************************************************************************************************
#***************************************************************************************************

def is_drive_time_valid(drive_sch):
    """
    checks if work arrival time and home arrival time adds up properly
    Args:
        drive_sch:
    Returns:
         true or false
    """
    home_leave_time = add_hhmm_secs(drive_sch['home_arr_time'], drive_sch['home_duration'])
    commute_secs = min(3600, 24 * 3600 - drive_sch['home_duration'])
    work_arr_time = add_hhmm_secs(home_leave_time, commute_secs / 2)
    work_duration = 24 * 3600 - drive_sch['home_duration'] - commute_secs
    if work_arr_time != drive_sch['work_arr_time'] or round(work_duration/60) != round(drive_sch['work_duration']/60):
        return False
    return True

#***************************************************************************************************
#***************************************************************************************************

def add_node_house_configs (glm_modifier, xfkva, xfkvll, xfkvln, phs, want_inverter=False):
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
    # print ('#define INVERTER_MODE=CONSTANT_PF', file=fp)
    # print ('//#define INVERTER_MODE=VOLT_VAR', file=fp)
    # print ('//#define INVERTER_MODE=VOLT_WATT', file=fp)
    # print ('// default IEEE 1547-2018 settings for Category B', file=fp)
    glm_modifier.model.define_lines.append("#define INV_V2=0.98")
    glm_modifier.model.define_lines.append("#define INV_V2=0.98")
    glm_modifier.model.define_lines.append("#define INV_V3=1.02")
    glm_modifier.model.define_lines.append("#define INV_V4=1.08")
    glm_modifier.model.define_lines.append("#define INV_Q1=0.44")
    glm_modifier.model.define_lines.append("#define INV_Q2=0.00")
    glm_modifier.model.define_lines.append("#define INV_Q3=0.00")
    glm_modifier.model.define_lines.append("#define INV_Q4=-0.44")
    glm_modifier.model.define_lines.append("#define INV_VIN=200.0")
    glm_modifier.model.define_lines.append("#define INV_IIN=32.5")
    glm_modifier.model.define_lines.append("#define INV_VVLOCKOUT=300.0")
    glm_modifier.model.define_lines.append("#define INV_VW_V1=1.05 // 1.05833")
    glm_modifier.model.define_lines.append("define INV_VW_V2=1.10")
    glm_modifier.model.define_lines.append("#define INV_VW_P1=1.0")
    glm_modifier.model.define_lines.append("#define INV_VW_P2=0.0")
  if 'S' in phs:
    for secphs in phs.rstrip('S'):
      xfkey = 'XF{:s}_{:d}'.format (secphs, int(xfkva))
      add_xfmr_config (glm_modifier, xfkey, secphs + 'S', kvat=xfkva, vnom=None, vsec=120.0, install_type='PADMOUNT', vprimll=None, vprimln=1000.0*xfkvln)
      add_kersting_triplex (glm_modifier, xfkva)
  else:
    xfkey = 'XF3_{:d}'.format (int(xfkva))
    add_xfmr_config (glm_modifier, xfkey, phs, kvat=xfkva, vnom=None, vsec=208.0, install_type='PADMOUNT', vprimll=1000.0*xfkvll, vprimln=None)
    add_kersting_quadriplex (glm_modifier, xfkva)

#***************************************************************************************************
#***************************************************************************************************

def add_kersting_quadriplex (glm_modifier, kva):
  """Writes a quadriplex_line_configuration based on 1/0 AA example from Kersting's book

  The conductor capacity is 202 amps, so the number of triplex in parallel will be kva/sqrt(3)/0.208/202
  """
  params = dict()
  params["key"]= 'quad_cfg_{:d}'.format (int(kva))
  params["amps"] = kva / math.sqrt(3.0) / 0.208
  params["npar"] = math.ceil (params["amps"] / 202.0)
  params["apar"] = 202.0 * params["npar"]
  params["scale"] = 5280.0 / 100.0 / params["npar"]  # for impedance per mile of parallel circuits
  params["r11"] = 0.0268 * params["scale"]
  params["x11"] = 0.0160 * params["scale"]
  params["r12"] = 0.0080 * params["scale"]
  params["x12"] = 0.0103 * params["scale"]
  params["r13"] = 0.0085 * params["scale"]
  params["x13"] = 0.0095 * params["scale"]
  params["r22"] = 0.0258 * params["scale"]
  params["x22"] = 0.0176 * params["scale"]
  glm_modifier.add_object("line_configuration", params["key"], params)

#***************************************************************************************************
#***************************************************************************************************

def add_kersting_triplex (glm_modifier, kva):
  """Writes a triplex_line_configuration based on 1/0 AA example from Kersting's book

  The conductor capacity is 202 amps, so the number of triplex in parallel will be kva/0.12/202
  """
  params = dict()
  params["key"] = 'tpx_cfg_{:d}'.format (int(kva))
  params["amps"] = kva / 0.12
  params["npar"] = math.ceil (params["amps"] / 202.0)
  params["apar"] = 202.0 * params["npar"]
  params["scale"] = 5280.0 / 100.0 / params["npar"]  # for impedance per mile of parallel circuits
  params["r11"] = 0.0271 * params["scale"]
  params["x11"] = 0.0146 * params["scale"]
  params["r12"] = 0.0087 * params["scale"]
  params["x12"] = 0.0081 * params["scale"]
  glm_modifier.add_object("triplex_line_configuration", params["key"], params)

#***************************************************************************************************
#***************************************************************************************************

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

#***************************************************************************************************
#***************************************************************************************************

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

#***************************************************************************************************
#***************************************************************************************************

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

#***************************************************************************************************
#***************************************************************************************************

def randomize_commercial_skew(glm_modifier):
    sk = glm_modifier.defaults.commercial_skew_std * np.random.randn()
    if sk < -glm_modifier.defaults.commercial_skew_max:
        sk = -glm_modifier.defaults.commercial_skew_max
    elif sk > glm_modifier.defaults.commercial_skew_max:
        sk = glm_modifier.defaults.commercial_skew_x
    return sk

#***************************************************************************************************
#***************************************************************************************************

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

#***************************************************************************************************
#***************************************************************************************************

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

#***************************************************************************************************
#***************************************************************************************************

def parse_kva_old(arg):
    """Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form

    DEPRECATED

    Args:

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

    vals = [tok[:kpos],tok[kpos:]]
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

#***************************************************************************************************
#***************************************************************************************************

# def parse_kva(cplx): # this drops the sign of p and q
#     """Parse the kVA magnitude from GridLAB-D P+jQ volt-amperes in rectangular form
#
#     Args:
#         cplx (str): the GridLAB-D P+jQ value
#
#     Returns:
#         float: the parsed kva value
#     """
#     toks = list(filter(None,re.split('[\+j-]',cplx)))
#     p = float(toks[0])
#     q = float(toks[1])
#     return 0.001 * math.sqrt(p*p + q*q)

#***************************************************************************************************
#***************************************************************************************************

def selectResidentialBuilding(rgnTable,prob):
    """Writes volt-var and volt-watt settings for solar inverters

    Args:
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


#***************************************************************************************************
#***************************************************************************************************
# -----------fraction of income level in a given dso type and state---------
# index 0 is the income level:
#   0 = Low
#   1 = Middle - No longer using Moderate
#   2 = Upper
def getDsoIncomeLevelTable(glm_modifier):
    income_mat = glm_modifier.defaults.res_bldg_metadata['income_level'][glm_modifier.defaults.state][glm_modifier.defaults.dso_type]
    dsoIncomePct = {key: income_mat[key] for key in glm_modifier.defaults.income_level} # Create new dictionary only with income levels of interest
    dsoIncomePct = list(dsoIncomePct.values())
    dsoIncomePct = [round(i/sum(dsoIncomePct),4) for i in dsoIncomePct] # Normalize so array adds up to 1
    # now check if the sum of all values is 1
    total = 0
    for row in range(len(dsoIncomePct)):
        total += dsoIncomePct[row]
    if total > 1.01 or total < 0.99:
        raise UserWarning('Income level distribution does not sum to 1!')
    return dsoIncomePct

#***************************************************************************************************
#***************************************************************************************************

def selectIncomeLevel(incTable, prob):
    """ Selects the income level with region and probability

    Args:
        rgnTable:
        prob:
    """
    total = 0
    for row in range(len(incTable)):
        total += incTable[row]
        if total >= prob:
            return row
    row = len(incTable) - 1
    return row


#***************************************************************************************************
#***************************************************************************************************
def buildingTypeLabel (glm_modifier, rgn, bldg, ti):
    """Formatted name of region, building type name and thermal integrity level

    Args:
        rgn (int): region number 1..5
        bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
        ti (int): thermal integrity level, 0..6 for single-family, only 0..2 valid for apartment or mobile home
    """
    return glm_modifier.defaults.rgnName[rgn-1] + ': ' +  glm_modifier.defaults.bldgTypeName[bldg] + ': TI Level ' + str (ti+1)

#***************************************************************************************************
#***************************************************************************************************

def Find3PhaseXfmr (glm_modifier, kva):
    """Select a standard 3-phase transformer size, with data

    Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500,
    2000, 2500, 3750, 5000, 7500 or 10000 kVA

    Args:
        kva (float): the minimum transformer rating

    Returns:
        [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
    """
    for row in glm_modifier.defaults.three_phase:
        if row[0] >= kva:
            return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
    return Find3PhaseXfmrKva(kva),0.01,0.08,0.005,0.01

#***************************************************************************************************
#***************************************************************************************************

def Find1PhaseXfmr (glm_modifier, kva):
    """Select a standard 1-phase transformer size, with data

    Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

    Args:
        kva (float): the minimum transformer rating

    Returns:
        [float,float,float,float,float]: the kva, %r, %x, %no-load loss, %magnetizing current
    """
    for row in glm_modifier.defaults.single_phase:
        if row[0] >= kva:
            return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
    return Find1PhaseXfmrKva(kva),0.01,0.06,0.005,0.01

#***************************************************************************************************
#***************************************************************************************************

def Find3PhaseXfmrKva (glm_modifier, kva):
    """Select a standard 3-phase transformer size, with some margin

    Standard sizes are 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500,
    2000, 2500, 3750, 5000, 7500 or 10000 kVA

    Args:
        kva (float): the minimum transformer rating

    Returns:
        float: the kva size, or 0 if none found
    """
    kva *= glm_modifier.defaults.xfmrMargin
    for row in glm_modifier.defaults.three_phase:
        if row[0] >= kva:
            return row[0]
    n10 = int ((kva + 5000.0) / 10000.0)
    return 500.0 * n10

#***************************************************************************************************
#***************************************************************************************************

def Find1PhaseXfmrKva (glm_modifier, kva):
    """Select a standard 1-phase transformer size, with some margin

    Standard sizes are 5, 10, 15, 25, 37.5, 50, 75, 100, 167, 250, 333 or 500 kVA

    Args:
        kva (float): the minimum transformer rating

    Returns:
        float: the kva size, or 0 if none found
    """
    kva *= glm_modifier.defaults.xfmrMargin
    for row in glm_modifier.defaults.single_phase:
        if row[0] >= kva:
            return row[0]
    n500 = int ((kva + 250.0) / 500.0)
    return 500.0 * n500

#***************************************************************************************************
#***************************************************************************************************

def checkResidentialBuildingTable(glm_modifier):
    """Verify that the regional building parameter histograms sum to one
    """

    for tbl in range(len(glm_modifier.defaults.dsoThermalPct)):
        total = 0
        for row in range(len(glm_modifier.defaults.dsoThermalPct[tbl])):
                for col in range(len(glm_modifier.defaults.dsoThermalPct[tbl][row])):
                    total += glm_modifier.defaults.dsoThermalPct[tbl][row][col]
        print(glm_modifier.defaults.rgnName[tbl],'rgnThermalPct sums to', '{:.4f}'.format(total))
    for tbl in range(len(glm_modifier.defaults.bldgCoolingSetpoints)):
        total = 0
        for row in range(len(glm_modifier.defaults.bldgCoolingSetpoints[tbl])):
                total += glm_modifier.defaults.bldgCoolingSetpoints[tbl][row][0]
        print ('bldgCoolingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
    for tbl in range(len(glm_modifier.defaults.bldgHeatingSetpoints)):
            total = 0
    for row in range(len(glm_modifier.defaults.bldgHeatingSetpoints[tbl])):
            total += glm_modifier.defaults.bldgHeatingSetpoints[tbl][row][0]
    print ('bldgHeatingSetpoints', tbl, 'histogram sums to', '{:.4f}'.format(total))
    for bldg in range(3):
        binZeroReserve = glm_modifier.defaults.bldgCoolingSetpoints[bldg][0][0]
        binZeroMargin = glm_modifier.defaults.bldgHeatingSetpoints[bldg][0][0] - binZeroReserve
        if binZeroMargin < 0.0:
            binZeroMargin = 0.0
        #        print(bldg, binZeroReserve, binZeroMargin)
        for cBin in range(1, 6):
            denom = binZeroMargin
            for hBin in range(1, glm_modifier.defaults.allowedHeatingBins[cBin]):
                    denom += glm_modifier.defaults.bldgHeatingSetpoints[bldg][hBin][0]
            glm_modifier.defaults.conditionalHeatingBinProb[bldg][cBin][0] = binZeroMargin / denom
            for hBin in range(1, glm_modifier.defaults.allowedHeatingBins[cBin]):
                    glm_modifier.defaults.conditionalHeatingBinProb[bldg][cBin][hBin] = glm_modifier.defaults.bldgHeatingSetpoints[bldg][hBin][0] / denom
    # print('conditionalHeatingBinProb', conditionalHeatingBinProb)

#***************************************************************************************************
#***************************************************************************************************

def selectThermalProperties(glm_modifier, bldgIdx, tiIdx):
    """Retrieve the building thermal properties for a given type and integrity level

    Args:
        bldgIdx (int): 0 for single-family, 1 for apartment, 2 for mobile home
        tiIdx (int): 0..7 for single-family, apartment or mobile home
    """
    if bldgIdx == 0:
        tiProps = glm_modifier.defaults.singleFamilyProperties[tiIdx]
    elif bldgIdx == 1:
        tiProps = glm_modifier.defaults.apartmentProperties[tiIdx]
    else:
        tiProps = glm_modifier.defaults.mobileHomeProperties[tiIdx]
    return tiProps


#***************************************************************************************************
#***************************************************************************************************

def FindFuseLimit (glm_modifier, amps):
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
    amps *= glm_modifier.defaults.fuseMargin
    for row in glm_modifier.defaults.standard_fuses:
        if row >= amps:
            return row
    for row in glm_modifier.defaults.standard_reclosers:
        if row >= amps:
            return row
    for row in glm_modifier.defaults.standard_breakers:
        if row >= amps:
            return row
    return 999999

#***************************************************************************************************
#***************************************************************************************************

def selectSetpointBins (glm_modifier, bldg, rand):
    """Randomly choose a histogram row from the cooling and heating setpoints
    The random number for the heating setpoint row is generated internally.
    Args:
        bldg (int): 0 for single-family, 1 for apartment, 2 for mobile home
        rand (float): random number [0..1] for the cooling setpoint row
    """
    cBin = hBin = 0
    total = 0
    tbl = glm_modifier.defaults.bldgCoolingSetpoints[bldg]
    for row in range(len(tbl)):
        total += tbl[row][0]
        if total >= rand:
            cBin = row
            break
    tbl = glm_modifier.defaults.conditionalHeatingBinProb[bldg][cBin]
    rand_heat = np.random.uniform (0, 1)
    total = 0
    for col in range(len(tbl)):
        total += tbl[col]
        if total >= rand_heat:
            hBin = col
            break
    glm_modifier.defaults.cooling_bins[bldg][cBin] -= 1
    glm_modifier.defaults.heating_bins[bldg][hBin] -= 1
    return glm_modifier.defaults.bldgCoolingSetpoints[bldg][cBin], glm_modifier.defaults.bldgHeatingSetpoints[bldg][hBin]

#***************************************************************************************************
#***************************************************************************************************

def initialize_glm_modifier(glmfilepath):
    glmMod = glmmod.GLMModifier()
#    glm, success = glmMod.read_model("/home/d3k205/tesp/data/feeders/R1-12.47-1.glm")
    glm, success = glmMod.read_model(glmfilepath)
    if not success:
        print('File not found or file not supported, exiting!')
        return None
    else:
        return glmMod

#***************************************************************************************************
#***************************************************************************************************

#fgconfig: path and name of the file that is to be used as the configuration json for loading
#ConfigDict dictionary
def initialize_config_dict(fgconfig):
    global ConfigDict
    global c_p_frac
    if fgconfig is not None:
        ConfigDict = {}
        with open(fgconfig,'r') as fgfile:
            confile = fgfile.read()
            ConfigDict = json.loads(confile)
            fgfile.close()
        tval2 = ConfigDict['feedergenerator']['constants']
        ConfigDict = tval2
        cval1 = ConfigDict['c_z_frac']['value']
        cval2 = ConfigDict['c_i_frac']['value']
        #c_p_frac = 1.0 - ConfigDict['c_z_frac'] - ConfigDict['c_i_frac']
        c_p_frac = 1.0 - cval1 - cval2
#       fgfile.close()

#***************************************************************************************************
#***************************************************************************************************

def add_solar_inv_settings (glm_modifier, params):
    """Writes volt-var and volt-watt settings for solar inverters

    Args:
        op (file): an open GridLAB-D input file
    """
    #print ('    four_quadrant_control_mode ${' + name_prefix + 'INVERTER_MODE};', file=op)
    params["four_quadrant_control_mode"] = glm_modifier.defaults.name_prefix + 'INVERTER_MODE'
    params["V_base"] = '${INV_VBASE}'
    params["V1"] = '${INV_V1}'
    params["Q1"] = '${INV_Q1}'
    params["V2"] = '${INV_V2}'
    params["Q2"] = '${INV_Q2}'
    params["V3"] = '${INV_V3}'
    params["Q3"] = '${INV_Q3}'
    params["V4"] = '${INV_V4}'
    params["Q4"] = '${INV_Q4}'
    params["V_In"] = '${INV_VIN}'
    params["I_In"] = '${INV_IIN}'
    params["volt_var_control_lockout"] = '${INV_VVLOCKOUT}'
    params["VW_V1"] = '${INV_VW_V1}'
    params["VW_V2"] = '${INV_VW_V2}'
    params["VW_P1"] = '${INV_VW_P1}'
    params["VW_P2"] = '${INV_VW_P2}'

#***************************************************************************************************
#***************************************************************************************************

def add_tariff(glm_modifier, params):
    """Writes tariff information to billing meters

    Args:
        op (file): an open GridLAB-D input file
    """
    params["bill_mode"] = glm_modifier.defaults.bill_mode
    params["price"] = glm_modifier.defaults.kwh_price
    params["monthly_fee"] = glm_modifier.defaults.monthly_fee
    params["bill_day"] = "1"
    if 'TIERED' in glm_modifier.defaults.bill_mode:
        if glm_modifier.defaults.tier1_energy > 0.0:
            params["first_tier_energy"] = glm_modifier.defaults.tier1_energy
            params["first_tier_price"] = glm_modifier.defaults.tier1_price
        if glm_modifier.defaults.tier2_energy > 0.0:
            params["second_tier_energy"] = glm_modifier.defaults.tier2_energy
            params["second_tier_price"] = glm_modifier.defaults.tier2_price
        if glm_modifier.defaults.tier3_energy > 0.0:
            params["third_tier_energy"] = glm_modifier.defaults.tier3_energy
            params["third_tier_price"] = glm_modifier.defaults.tier3_price


#***************************************************************************************************
#***************************************************************************************************

def getDsoThermalTable(glm_modifier, income):
    vintage_mat = glm_modifier.defaults.res_bldg_metadata['housing_vintage'][glm_modifier.defaults.state][glm_modifier.defaults.dso_type][income]
    df = pd.DataFrame(vintage_mat)
    # df = df.transpose()
    dsoThermalPct = np.zeros(shape=(3, 9))  # initialize array
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

#***************************************************************************************************
#***************************************************************************************************

def obj(glm_modifier, parent, model, line, itr, oidh, octr):
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
                oname = glm_modifier.defaults.name_prefix + val
            elif param == 'object':
                # found a nested object
                intobj += 1
                if oname is None:
                    print('ERROR: nested object defined before parent name')
                    quit()
                line,octr = obj(glm_modifier,oname,model,line,itr,oidh,octr)
            elif re.match('object',val):
                # found an inline object
                intobj += 1
                line,octr = obj(glm_modifier,None,model,line,itr,oidh,octr)
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
        oname = glm_modifier.defaults.name_prefix + 'ID_'+str(octr)
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

#***************************************************************************************************
#***************************************************************************************************

def add_link_class (glm_modifier, model, h, t, seg_loads,  want_metrics=False):
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
      params = dict()
      if o in seg_loads:
        #print('// downstream', '{:.2f}'.format(seg_loads[o][0]), 'kva on', seg_loads[o][1])
        for p in model[t][o]:
          if ':' in model[t][o][p]:
            params[p] = h[model[t][o][p]]
          else:
            if p == "from" or p == "to" or p == "parent":
              params[p] = gld_strict_name(model[t][o][p])
            else:
              params[p] = model[t][o][p]
            glm_modifier.add_object(t, o, params)
        if want_metrics and glm_modifier.defaults.metrics_interval > 0:
          params2 = dict()
          params2["parent"] = o
          params2["interval"] = str(glm_modifier.defaults.metrics_interval)
          glm_modifier.add_object("metrics_collector", "", params2)

#***************************************************************************************************
#***************************************************************************************************

def add_local_triplex_configurations (glm_modifier):
    params = dict()
    for row in glm_modifier.defaults.triplex_conductors:
        name = glm_modifier.defaults.name_prefix + row[0]
        params["resistance"] = row[1]
        params["geometric_mean_radius"] = row[2]
        rating_str = str(row[2])
        params["rating.summer.continuous"] = rating_str
        params["rating.summer.emergency"] = rating_str
        params["rating.winter.continuous"] = rating_str
        params["rating.winter.emergency"] = rating_str
        glm_modifier.add_object("triplex_line_conductor", name, params)
    for row in glm_modifier.defaults.triplex_configurations:
        params = dict()
        name = glm_modifier.defaults.name_prefix + row[0]
        params["conductor_1"] = glm_modifier.defaults.name_prefix + row[0]
        params["conductor_2"] = glm_modifier.defaults.name_prefix + row[1]
        params["conductor_N"] = glm_modifier.defaults.name_prefix + row[2]
        params["insulation_thickness"] = str(row[3])
        params["diameter"] = str(row[4])
        glm_modifier.add_object("triplex_line_configuration", name, params)

#***************************************************************************************************
#***************************************************************************************************

def add_ercot_houses (glm_modifier, model, h, vln, vsec):
    """For the reduced-order ERCOT feeders, add houses and a large service transformer to the load points

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        op (file): an open GridLAB-D input file
        vln (float): the primary line-to-neutral voltage
        vsec (float): the secondary line-to-neutral voltage
    """
    for key in glm_modifier.defaults.house_nodes:
#        bus = key[:-2]
        bus = glm_modifier.house_nodes[key][6]
        phs = glm_modifier.house_nodes[key][3]
        nh = glm_modifier.house_nodes[key][0]
        xfkva = Find1PhaseXfmrKva (6.0 * nh)
        if xfkva > 100.0:
            npar = int (xfkva / 100.0 + 0.5)
            xfkva = 100.0
        elif xfkva <= 0.0:
            xfkva = 100.0
            npar = int (0.06 * nh + 0.5)
        else:
            npar = 1
        # add the service transformer==>TN==>TPX==>TM for all houses
        kvat = npar * xfkva
        row = Find1PhaseXfmr (xfkva)
        params = dict()
        name = key + '_xfconfig'
        params["power_rating"] = format(kvat, '.2f')
        if 'A' in phs:
            params["powerA_rating"] = format(kvat, '.2f')
        elif 'B' in phs:
            params["powerB_rating"] = format(kvat, '.2f')
        elif 'C' in phs:
            params["powerC_rating"] = format(kvat, '.2f')
        params["install_type"] = "PADMOUNT"
        params["connect_type"] = "SINGLE_PHASE_CENTER_TAPPED"
        params["primary_voltage"] = str(vln)
        params["secondary_voltage"] = format(vsec, '.1f')
        params["resistance"] = format(row[1] * 0.5, '.5f')
        params["resistance1"] = format(row[1], '.5f')
        params["resistance2"] = format(row[1], '.5f')
        params["reactance"] = format(row[2] * 0.8, '.5f')
        params["reactance1"] = format(row[2] * 0.4, '.5f')
        params["reactance2"] = format(row[2] * 0.4, '.5f')
        params["shunt_resistance"] = format(1.0 / row[3], '.2f')
        params["shunt_reactance"] = format(1.0 / row[4], '.2f')
        glm_modifier.add_object("transformer_configuration", name, params)
        params2 = dict()
        name = key + '_xf'
        params2["phases"] = phs + 'S'
        params2["from"] = bus
        params2["to"] = key + '_tn'
        params2["configuration"] = key + '_xfconfig'
        glm_modifier.add_object("transformer", name, params2)
        params3 = dict()
        name = key + '_tpxconfig'
        zs = format (glm_modifier.defaults.tpxR11/nh, '.5f') + '+' + format (glm_modifier.defaults.tpxX11/nh, '.5f') + 'j;'
        zm = format (glm_modifier.defaults.tpxR12/nh, '.5f') + '+' + format (glm_modifier.defaults.tpxX12/nh, '.5f') + 'j;'
        amps = format (glm_modifier.defaults.tpxAMP * nh, '.1f') + ';'
        params3["z11"] = zs
        params3["z22"] = zs
        params3["z12"] = zm
        params3["z12"] = zm
        params3["rating.summer.continuous"] = amps
        glm_modifier.add_object("triplex_line_configuration", name, params3)
        params4 = dict()
        name = key + '_tpx'
        params4["phases"] = phs + 'S'
        params4["from"] = key + '_tn'
        params4["to"] = key + '_mtr'
        params4["length"] = 50
        params4["configuration"] = key + '_tpxconfig'
        glm_modifier.add_object("triplex_line", name, params4)
        if 'A' in phs:
            vstart = str(vsec) + '+0.0j;'
        elif 'B' in phs:
            vstart = format(-0.5*vsec,'.2f') + format(-0.866025*vsec,'.2f') + 'j;'
        else:
            vstart = format(-0.5*vsec,'.2f') + '+' + format(0.866025*vsec,'.2f') + 'j;'
        params5 = dict()
        t_name = key + '_tn'
        params5["phases"] = phs + 'S'
        params5["voltage_1"] = vstart
        params5["voltage_2"] = vstart
        params5["voltage_N"] = 0
        params5["nominal_voltage"] = format(vsec, '.1f')
        glm_modifier.add_object("triplex_node", t_name, params5)
        params6 = dict()
        t_name = key + '_mtr'
        params6["phases"] = phs + 'S'
        params6["voltage_1"] = vstart
        params6["voltage_2"] = vstart
        params6["voltage_N"] = 0
        params6["nominal_voltage"] = format(vsec, '.1f')
        add_tariff (glm_modifier)
        glm_modifier.add_object("triplex_meter", t_name, params6)
        if glm_modifier.defaults.metrics_interval > 0:
            params7 = dict()
            params7["parent"] = t_name
            params7["interval"] = str(glm_modifier.defaults.metrics_interval)
            glm_modifier.add_object("metrics_collector", "", params7)

#***************************************************************************************************
#***************************************************************************************************

def connect_ercot_commercial(glm_modifier):
  """For the reduced-order ERCOT feeders, add a billing meter to the commercial load points, except small ZIPLOADs

  Args:
      op (file): an open GridLAB-D input file
  """
  meters_added = set()
  for key in glm_modifier.defaults.comm_loads:
    mtr = glm_modifier.defaults.comm_loads[key][0]
    comm_type = glm_modifier.defaults.comm_loads[key][1]
    if comm_type == 'ZIPLOAD':
      continue
    phases = glm_modifier.defaults.comm_loads[key][5]
    vln = float(glm_modifier.defaults.comm_loads[key][6])
    idx = mtr.rfind('_')
    parent = mtr[:idx]
    if mtr not in meters_added:
      params = dict()
      meters_added.add(mtr)
      params["parent"] = parent
      params["phases"] = phases
      params["nominal_voltage"] = format(vln, '.1f')
      add_tariff(glm_modifier)
      glm_modifier.add_object("meter", mtr, params)
      if glm_modifier.defaults.metrics_interval > 0:
          params2 = dict()
          params2["parent"] = mtr
          params2["interval"] = str(glm_modifier.defaults.metrics_interval)
          glm_modifier.add_object("metrics_collector", "", params2)

#***************************************************************************************************
#***************************************************************************************************

def add_ercot_small_loads(glm_modifier, basenode, vnom):
  """For the reduced-order ERCOT feeders, write loads that are too small for houses

  Args:
    basenode (str): the GridLAB-D node name
    op (file): an open GridLAB-D input file
    vnom (float): the primary line-to-neutral voltage
  """
  kva = float(glm_modifier.defaults.small_nodes[basenode][0])
  phs = glm_modifier.defaults.small_nodes[basenode][1]
  parent = glm_modifier.defaults.small_nodes[basenode][2]
  cls = glm_modifier.defaults.small_nodes[basenode][3]
  if 'A' in phs:
      phase_class = "voltage_A"
      vstart = str(vnom) + '+0.0j;'
      constpower = '  constant_power_A_real ' + format (1000.0 * kva, '.2f')
  elif 'B' in phs:
      phase_class = "voltage_B"
      vstart = format(-0.5*vnom,'.2f') + format(-0.866025*vnom,'.2f') + 'j'
      constpower = '  constant_power_B_real ' + format (1000.0 * kva, '.2f') + ';'
  else:
      phase_class = "voltage_C"
      vstart = ' ' + format(-0.5*vnom,'.2f') + '+' + format(0.866025*vnom,'.2f') + 'j'
      constpower = '  constant_power_C_real ' + format (1000.0 * kva, '.2f') + ';'
  params = dict()
  name = basenode
  params["parent"] = parent
  params["phases"] = phs
  params["nominal_voltage"] = str(vnom)
  params["load_class"] = cls
  params["voltage_C"] = format(-0.5*vnom,'.2f') + '+' + format(0.866025*vnom,'.2f') + 'j'
  params[phase_class] = vstart
  #print (vstart, file=op)
  #waiting for the add comment function to be added to the modifier class
  #print ('  //', '{:.3f}'.format(kva), 'kva is less than 1/2 avg_house', file=op)
  params["constant_power_C_real"] = format (1000.0 * kva, '.2f')
  glm_modifier.add_object("load", name, params)

#***************************************************************************************************
#***************************************************************************************************

# look at primary loads, not the service transformers
def identify_ercot_houses (glm_modifier,model, h, t, avgHouse, rgn):
    """For the reduced-order ERCOT feeders, scan each primary load to determine 
    the number of houses it should have

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class name to scan
        avgHouse (float): the average house load in kva
        rgn (int): the region number, 1..5
    """
    print ('Average ERCOT House load:', avgHouse, 'kVA. Region number:', rgn)
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
            parent = model[t][o]['parent']
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
                            if (kva > 1.0):
                                nh = int ((kva / avgHouse) + 0.5)
                                total_houses[phs] += nh
                    if nh > 0:
                        lg_v_sm = kva / avgHouse - nh # >0 if we rounded down the number of houses
                        bldg, ti = selectResidentialBuilding (glm_modifier.defaults.rgnThermalPct[rgn-1], np.random.uniform (0, 1))
                        if bldg == 0:
                            total_sf += nh
                        elif bldg == 1:
                            total_apt += nh
                        else:
                            total_mh += nh
                        glm_modifier.defaults.house_nodes[key] = [nh, rgn, lg_v_sm, phs, bldg, ti, parent] # parent is the primary node, only for ERCOT
                    elif kva > 0.1:
                        total_small[phs] += 1
                        total_small_kva[phs] += kva
                        glm_modifier.defaults.small_nodes[key] = [kva, phs, parent, cls] # parent is the primary node, only for ERCOT
    for phs in ['A', 'B', 'C']:
        print ('phase', phs, ':', total_houses[phs], 'Houses and', total_small[phs],
               'Small Loads totaling', '{:.2f}'.format (total_small_kva[phs]), 'kva')
    print (len(glm_modifier.defaults.house_nodes), 'primary house nodes, [SF,APT,MH]=', total_sf, total_apt, total_mh)
    for i in range(6):
        glm_modifier.defaults.heating_bins[0][i] = round (total_sf * glm_modifier.defaults.bldgHeatingSetpoints[0][i][0] + 0.5)
        glm_modifier.defaults.heating_bins[1][i] = round (total_apt * glm_modifier.defaults.bldgHeatingSetpoints[1][i][0] + 0.5)
        glm_modifier.defaults.heating_bins[2][i] = round (total_mh * glm_modifier.defaults.bldgHeatingSetpoints[2][i][0] + 0.5)
        glm_modifier.defaults.cooling_bins[0][i] = round (total_sf * glm_modifier.defaults.bldgCoolingSetpoints[0][i][0] + 0.5)
        glm_modifier.defaults.cooling_bins[1][i] = round (total_apt * glm_modifier.defaults.bldgCoolingSetpoints[1][i][0] + 0.5)
        glm_modifier.defaults.cooling_bins[2][i] = round (total_mh * glm_modifier.defaults.bldgCoolingSetpoints[2][i][0] + 0.5)
    print ('cooling bins target', glm_modifier.defaults.cooling_bins)
    print ('heating bins target', glm_modifier.defaults.heating_bins)

#***************************************************************************************************
#***************************************************************************************************

def replace_commercial_loads(glm_modifier, model, h, t, avgBuilding):
    """For the full-order feeders, scan each load with load_class==C to determine the number of zones it should have

    Args:
        glm_modifier (modify_GLM): modify_GLM class object
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class name to scan
        avgBuilding (float): the average building in kva
    """
    print('Average Commercial Building load:', avgBuilding, 'kVA')
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
                    for bldg in glm_modifier.defaults.comm_bldgs_pop:
                        if 0 >= (glm_modifier.defaults.comm_bldgs_pop[bldg][1] - target_sqft) > sqft_error:
                            select_bldg = bldg
                            sqft_error = glm_modifier.defaults.comm_bldgs_pop[bldg][1] - target_sqft
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
                    comm_type = glm_modifier.defaults.comm_bldgs_pop[select_bldg][0]
                    comm_size = glm_modifier.defaults.comm_bldgs_pop[select_bldg][1]
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

                        del (glm_modifier.defaults.comm_bldgs_pop[select_bldg])
                    else:
                        if nzones > 0:
                            print('Commercial building could not be found for ', '{:.2f}'.format(kva), ' KVA load')
                        comm_name = 'streetlights'
                        comm_type = 'ZIPLOAD'
                        comm_size = 0
                        total_zipload += 1
                    mtr = gld_strict_name(model[t][o]['parent'])
                    extra_billing_meters.add(mtr)
                    glm_modifier.defaults.comm_loads[o] = [mtr, comm_type, comm_size, kva, nphs, phases, vln,
                                                           total_commercial, comm_name]
                    model[t][o]['groupid'] = comm_type + '_' + str(comm_size)
                    del model[t][o]
    # Print commercial info
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
    for bldg in glm_modifier.defaults.comm_bldgs_pop:
        remain_comm_kva += glm_modifier.defaults.comm_bldgs_pop[bldg][1] * sqft_kva_ratio
    print(len(glm_modifier.defaults.comm_bldgs_pop), 'commercial buildings (approximately', int(remain_comm_kva),
        'kVA) still to be assigned.')

#***************************************************************************************************
#***************************************************************************************************

def identify_xfmr_houses (glm_modifier,model, h, t, seg_loads, avgHouse, rgn):
    """For the full-order feeders, scan each service transformer to determine the number of houses it should have

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class name to scan
        seg_loads (dict): dictionary of downstream load (kva) served by each GridLAB-D link
        avgHouse (float): the average house load in kva
        rgn (int): the region number, 1..5
    """
    print ('Average House load', avgHouse, 'kVA. Region number:', rgn)
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
                    nhouse = int ((tkva / avgHouse) + 0.5) # round to nearest int
                    name = o
                    node = gld_strict_name(model[t][o]['to'])
                    if nhouse <= 0:
                        total_small += 1
                        total_small_kva += tkva
                        glm_modifier.defaults.small_nodes[node] = [tkva,phs]
                    else:
                        total_houses += nhouse
                        lg_v_sm = tkva / avgHouse - nhouse # >0 if we rounded down the number of houses
                        # let's get the income level for the dso_type and state
                        dsoIncomePct = getDsoIncomeLevelTable()
                        inc_lev = selectIncomeLevel(dsoIncomePct, np.random.uniform(0,1))
                        # let's get the vintage table for dso_type, state, and income level
                        dsoThermalPct = getDsoThermalTable(glm_modifier.defaults.income_level[inc_lev])
                        bldg, ti = selectResidentialBuilding (glm_modifier.defaults.rgnThermalPct[rgn-1], np.random.uniform (0, 1))
                        if bldg == 0:
                            total_sf += nhouse
                        elif bldg == 1:
                            total_apt += nhouse
                        else:
                            total_mh += nhouse
                        glm_modifier.defaults.house_nodes[node] = [nhouse, rgn, lg_v_sm, phs, bldg, ti]
    print (total_small, 'small loads totaling', '{:.2f}'.format (total_small_kva), 'kVA')
    print (total_houses, 'houses on', len(glm_modifier.defaults.house_nodes), 'transformers, [SF,APT,MH]=', total_sf, total_apt, total_mh)
    for i in range(6):
        glm_modifier.defaults.heating_bins[0][i] = round (total_sf * glm_modifier.defaults.bldgHeatingSetpoints[0][i][0] + 0.5)
        glm_modifier.defaults.heating_bins[1][i] = round (total_apt * glm_modifier.defaults.bldgHeatingSetpoints[1][i][0] + 0.5)
        glm_modifier.defaults.heating_bins[2][i] = round (total_mh * glm_modifier.defaults.bldgHeatingSetpoints[2][i][0] + 0.5)
        glm_modifier.defaults.cooling_bins[0][i] = round (total_sf * glm_modifier.defaults.bldgCoolingSetpoints[0][i][0] + 0.5)
        glm_modifier.defaults.cooling_bins[1][i] = round (total_apt * glm_modifier.defaults.bldgCoolingSetpoints[1][i][0] + 0.5)
        glm_modifier.defaults.cooling_bins[2][i] = round (total_mh * glm_modifier.defaults.bldgCoolingSetpoints[2][i][0] + 0.5)
    print ('cooling bins target', glm_modifier.defaults.cooling_bins)
    print ('heating bins target', glm_modifier.defaults.heating_bins)

#***************************************************************************************************
#***************************************************************************************************

def add_small_loads(glm_modifier, basenode, vnom):
    """Write loads that are too small for a house, onto a node

    Args:
      basenode (str): GridLAB-D node name
      op (file): open file to write to
      vnom (float): nominal line-to-neutral voltage at basenode
    """
    kva = float(glm_modifier.defaults.small_nodes[basenode][0])
    phs = glm_modifier.defaults.small_nodes[basenode][1]

    if 'A' in phs:
        vstart = str(vnom) + '+0.0j'
    elif 'B' in phs:
        vstart = format(-0.5 * vnom, '.2f') + format(-0.866025 * vnom, '.2f') + 'j'
    else:
        vstart = format(-0.5 * vnom, '.2f') + '+' + format(0.866025 * vnom, '.2f') + 'j'

    tpxname = basenode + '_tpx_1'
    mtrname = basenode + '_mtr_1'
    loadname = basenode + '_load_1'
    params = dict()
    name = basenode
    params["phases"] = phs
    params["nominal_voltage"] = str(vnom)
    params["voltage_1"] = vstart
    params["voltage_2"] = vstart
    glm_modifier.add_object("triplex_node", name, params)
    params2 = dict()
    name = tpxname
    params2["from"] = basenode
    params2["to"] = mtrname
    params2["phases"] = phs
    params2["length"] = "30"
    params2["configuration"] = glm_modifier.defaults.triplex_configurations[0][0]
    glm_modifier.add_object("triplex_line", name, params2)

    params3 = dict()
    params3["phases"] = phs
    params3["meter_power_consumption"] = "1+7j"
    add_tariff(glm_modifier)
    params3["nominal_voltage"] = str(vnom)
    params3["voltage_1"] = vstart
    params3["voltage_2"] = vstart
    glm_modifier.add_object("triplex_meter", mtrname, params3)
    if glm_modifier.defaults.metrics_interval > 0:
        params4 = dict()
        params4["parent"] = mtrname
        params4["interval"] = str(glm_modifier.defaults.metrics_interval)
        glm_modifier.add_object("metrics_collector", "", params4)
    params5 = dict()
    t_name = loadname
    params5["parent"] = mtrname
    params5["phases"] = phs
    params5["nominal_voltage"] = str(vnom)
    params5["voltage_1"] = vstart
    params5["voltage_2"] = vstart

    # waiting for the add comment method to be added to the modifier class
    # print ('  //', '{:.3f}'.format(kva), 'kva is less than 1/2 avg_house', file=op)

    params5["constant_power_12_real"] = "10.0"
    params5["constant_power_12_reac"] = "8.0"
    glm_modifier.add_object("triplex_load", t_name, params5)


#***************************************************************************************************
#***************************************************************************************************

def add_one_commercial_zone(glm_modifier, bldg):
  """Write one pre-configured commercial zone as a house

  Args:
      bldg: dictionary of GridLAB-D house and zipload attributes
      op (file): open file to write to
  """
  params = dict()
  name = bldg['zonename']
  params["parent"] = bldg['parent']
  params["groupid"] = bldg['groupid']
  params["motor_model"] = "BASIC"
  params["schedule_skew"] = '{:.0f}'.format(bldg['skew_value'])
  params["floor_area"] = '{:.0f}'.format(bldg['floor_area'])
  params["design_internal_gains"] = '{:.0f}'.format(bldg['int_gains'] * bldg['floor_area'] * 3.413)
  params["number_of_doors"] = '{:.0f}'.format(bldg['no_of_doors'])
  params["aspect_ratio"] = '{:.2f}'.format(bldg['aspect_ratio'])
  params["total_thermal_mass_per_floor_area"] = '{:1.2f}'.format(bldg['thermal_mass_per_floor_area'])
  params["interior_surface_heat_transfer_coeff"] = '{:1.2f}'.format(bldg['surface_heat_trans_coeff'])
  params["interior_exterior_wall_ratio"] = '{:.2f}'.format(bldg['interior_exterior_wall_ratio'])
  params["exterior_floor_fraction"] = '{:.3f}'.format(bldg['exterior_floor_fraction'])
  params["exterior_ceiling_fraction"] = '{:.3f}'.format(bldg['exterior_ceiling_fraction'])
  params["Rwall"] = str(bldg['Rwall'])
  params["Rroof"] = str(bldg['Rroof'])
  params["Rfloor"] = str(bldg['Rfloor'])
  params["Rdoors"] = str(bldg['Rdoors'])
  params["exterior_wall_fraction"] = '{:.2f}'.format(bldg['exterior_wall_fraction'])
  params["glazing_layers"] = '{:s}'.format(bldg['glazing_layers'])
  params["glass_type"] = '{:s}'.format(bldg['glass_type'])
  params["glazing_treatment"] = '{:s}'.format(bldg['glazing_treatment'])
  params["window_frame"] = '{:s}'.format(bldg['window_frame'])
  params["airchange_per_hour"] = '{:.2f}'.format(bldg['airchange_per_hour'])
  params["window_wall_ratio"] = '{:0.3f}'.format(bldg['window_wall_ratio'])
  params["heating_system_type"] = '{:s}'.format(bldg['heat_type'])
  params["auxiliary_system_type"] = '{:s}'.format(bldg['aux_type'])
  params["fan_type"] = '{:s}'.format(bldg['fan_type'])
  params["cooling_system_type"] = '{:s}'.format(bldg['cool_type'])
  params["air_temperature"] = '{:.2f}'.format(bldg['init_temp'])
  params["mass_temperature"] = '{:.2f}'.format(bldg['init_temp'])
  params["over_sizing_factor"] = '{:.1f}'.format(bldg['os_rand'])
  params["cooling_COP"] = '{:2.2f}'.format(bldg['COP_A'])
  params["cooling_setpoint"] = "80.0"
  params["heating_setpoint"] = "60.0"
  glm_modifier.add_object("house", name, params)

  params2 = dict()
  params2["schedule_skew"] = '{:.0f}'.format(bldg['skew_value'])
  params2["heatgain_fraction"] = "1.0"
  params2["power_fraction"] = '{:.2f}'.format(bldg['c_p_frac'])
  params2["impedance_fraction"] = 'impedance_fraction {:.2f}'.format(bldg['c_z_frac'])
  params2["current_fraction"] = '{:.2f}'.format(bldg['c_i_frac'])
  params2["power_pf"] = '{:.2f}'.format(bldg['c_p_pf'])
  params2["current_pf"] = '{:.2f}'.format(bldg['c_i_pf'])
  params2["impedance_pf"] = '{:.2f}'.format(bldg['c_z_pf'])
  #params2["base_power"] = '{:.2f}'.format(bldg['base_schedule'], bldg['adj_lights'])
  glm_modifier.add_object("ZIPload", "lights", params2)



  params3 = dict()
  params3["schedule_skew"] = '{:.0f}'.format(bldg['skew_value'])
  params3["heatgain_fraction"] = "1.0"
  params3["power_fraction"] = '{:.2f}'.format(bldg['c_p_frac'])
  params3["impedance_fraction"] = '{:.2f}'.format(bldg['c_z_frac'])
  params3["current_fraction"] = '{:.2f}'.format(bldg['c_i_frac'])
  params3["power_pf"] = '{:.2f}'.format(bldg['c_p_pf'])
  params3["current_pf"] = '{:.2f}'.format(bldg['c_i_pf'])
  params3["impedance_pf"] = '{:.2f}'.format(bldg['c_z_pf'])
  #params3["base_power"] = '{:.2f}'.format(bldg['base_schedule'], bldg['adj_plugs'])
  glm_modifier.add_object("ZIPload", "plug loads", params3)

  params4 = dict()
  params4["schedule_skew"] = '{:.0f}'.format(bldg['skew_value'])
  params4["heatgain_fraction"] = "1.0"
  params4["power_fraction"] = "0"
  params4["impedance_fraction"] = "0"
  params4["current_fraction"] = "0"
  params4["power_pf"] = "1"
  #params4["base_power"] = '{:.2f}'.format(bldg['base_schedule'], bldg['adj_gas'])
  glm_modifier.add_object("ZIPload", "gas waterheater", params4)



  params5 = dict()
  params5["schedule_skew"] = '{:.0f}'.format(bldg['skew_value'])
  params5["heatgain_fraction"] = "0.0"
  params5["power_fraction"] = '{:.2f}'.format(bldg['c_p_frac'])
  params5["impedance_fraction"] = '{:.2f}'.format(bldg['c_z_frac'])
  params5["current_fraction"] = '{:.2f}'.format(bldg['c_i_frac'])
  params5["power_pf"] = '{:.2f}'.format(bldg['c_p_pf'])
  params5["current_pf"] = '{:.2f}'.format(bldg['c_i_pf'])
  params5["impedance_pf"] = '{:.2f}'.format(bldg['c_z_pf'])
  #params5["base_power"] = '{:s}_exterior*{:.2f};'.format(bldg['base_schedule'], bldg['adj_ext'])
  glm_modifier.add_object("ZIPload", "exterior lights", params5)


  params6 = dict()
  params6["schedule_skew"] = '{:.0f}'.format(bldg['skew_value'])
  params6["heatgain_fraction"] = "1.0"
  params6["power_fraction"] = "0"
  params6["impedance_fraction"] = "0"
  params6["current_fraction"] = "0"
  params6["power_pf"] = "1"
  #params6["base_power"] = '{:s}_occupancy*{:.2f}'.format(bldg['base_schedule'], bldg['adj_occ'])
  glm_modifier.add_object("ZIPload", "occupancy", params6)

  if glm_modifier.defaults.metrics_interval > 0:
    params7 = dict()
    params7["interval"] = str(glm_modifier.defaults.metrics_interval)
    glm_modifier.add_object("ZIPload", "occupancy", params7)

#***************************************************************************************************
#***************************************************************************************************

def add_commercial_loads(glm_modifier,rgn, key):
  """Put commercial building zones and ZIP loads into the model

  Args:
      rgn (int): region 1..5 where the building is located
      key (str): GridLAB-D load name that is being replaced
      op (file): open file to write to
  """
  mtr = glm_modifier.defaults.comm_loads[key][0]
  comm_type = glm_modifier.defaults.comm_loads[key][1]
  nz = int(glm_modifier.defaults.comm_loads[key][2])
  kva = float(glm_modifier.defaults.comm_loads[key][3])
  nphs = int(glm_modifier.defaults.comm_loads[key][4])
  phases = glm_modifier.defaults.comm_loads[key][5]
  vln = float(glm_modifier.defaults.comm_loads[key][6])
  loadnum = int(glm_modifier.defaults.comm_loads[key][7])

  bldg = {}
  bldg['parent'] = key
  bldg['mtr'] = mtr
  bldg['groupid'] = comm_type + '_' + str(loadnum)
# waiting for the add comment method to be added to the model_GLM class
#  print ('// load', key, 'mtr', bldg['mtr'], 'type', comm_type, 'nz', nz, 'kva', '{:.3f}'.format(kva),
#         'nphs', nphs, 'phases', phases, 'vln', '{:.3f}'.format(vln), file=op)

  bldg['fan_type'] = 'ONE_SPEED'
  bldg['heat_type'] = 'GAS'
  bldg['cool_type'] = 'ELECTRIC'
  bldg['aux_type'] = 'NONE'
  bldg['no_of_stories'] = 1
  bldg['surface_heat_trans_coeff'] = 0.59
  bldg['oversize'] = glm_modifier.defaults.over_sizing_factor[rgn-1]
  bldg['glazing_layers'] = 'TWO'
  bldg['glass_type'] = 'GLASS'
  bldg['glazing_treatment'] = 'LOW_S'
  bldg['window_frame'] = 'NONE'
  bldg['c_z_frac'] = glm_modifier.defaults.c_z_frac
  bldg['c_i_frac'] = glm_modifier.defaults.c_i_frac
  bldg['c_p_frac'] = 1.0 - glm_modifier.defaults.c_z_frac - glm_modifier.defaults.c_i_frac

  bldg['c_z_pf'] = glm_modifier.defaults.c_z_pf
  bldg['c_i_pf'] = glm_modifier.defaults.c_i_pf
  bldg['c_p_pf'] = glm_modifier.defaults.c_p_pf

  if comm_type == 'OFFICE':
    bldg['ceiling_height'] = 13.
    bldg['airchange_per_hour'] = 0.69
    bldg['Rroof'] = 19.
    bldg['Rwall'] = 18.3
    bldg['Rfloor'] = 46.
    bldg['Rdoors'] = 3.
    bldg['int_gains'] = 3.24  # W/sf
    bldg['thermal_mass_per_floor_area'] = 1 # TODO
    bldg['exterior_ceiling_fraction'] = 1 # TODO
    bldg['base_schedule'] = 'office'
    num_offices = int(round(nz/15))  # each with 3 floors of 5 zones
    for jjj in range(num_offices):
      floor_area_choose = 40000. * (0.5 * np.random.random() + 0.5)
      for floor in range(1, 4):
        bldg['skew_value'] = randomize_commercial_skew()
        total_depth = math.sqrt(floor_area_choose / (3. * 1.5))
        total_width = 1.5 * total_depth
        if floor == 3:
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

          if floor > 1:
            bldg['exterior_floor_fraction'] = 0
          else:
            bldg['exterior_floor_fraction'] = w / (2. * (w + d)) / (floor_area / (floor_area_choose / 3.))

          bldg['thermal_mass_per_floor_area'] = 3.9 * (0.5 + 1. * np.random.random())
          bldg['interior_exterior_wall_ratio'] = floor_area / (bldg['ceiling_height'] * 2. * (w + d)) - 1. \
            + bldg['window_wall_ratio'] * bldg['exterior_wall_fraction']
          bldg['no_of_doors'] = 0.1  # will round to zero, presumably the exterior doors are treated like windows

          bldg['init_temp'] = 68. + 4. * np.random.random()
          bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
          bldg['COP_A'] = glm_modifier.defaults.cooling_COP * (0.8 + 0.4 * np.random.random())

          bldg['adj_lights'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.  # randomize 10# then convert W/sf -> kW
          bldg['adj_plugs'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
          bldg['adj_gas'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
          bldg['adj_ext'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
          bldg['adj_occ'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.

          bldg['zonename'] = gld_strict_name (key + '_bldg_' + str(jjj+1) + '_floor_' + str(floor) + '_zone_' + str(zone))
          add_one_commercial_zone (glm_modifier, bldg)

  elif comm_type == 'BIGBOX':
    bldg['ceiling_height'] = 14.
    bldg['airchange_per_hour'] = 1.5
    bldg['Rroof'] = 19.
    bldg['Rwall'] = 18.3
    bldg['Rfloor'] = 46.
    bldg['Rdoors'] = 3.
    bldg['int_gains'] = 3.6  # W/sf
    bldg['thermal_mass_per_floor_area'] = 1 # TODO
    bldg['exterior_ceiling_fraction'] = 1 # TODO
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
      total_depth = math.sqrt(floor_area_choose / bldg['aspect_ratio'])
      total_width = bldg['aspect_ratio'] * total_depth
      d = total_width / 3.
      w = total_depth / 2.

      for zone in range(1,7):
        if zone == 2 or zone == 5:
          bldg['exterior_wall_fraction'] = d / (2. * (d + w))
          bldg['exterior_floor_fraction'] = (0. + d) / (2. * (total_width + total_depth)) / (floor_area / floor_area_choose)
        else:
          bldg['exterior_wall_fraction'] = 0.5
          bldg['exterior_floor_fraction'] = (w + d) / (2. * (total_width + total_depth)) / (floor_area / floor_area_choose)
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

        bldg['interior_exterior_wall_ratio'] = (floor_area + bldg['no_of_doors'] * 20.) \
          / (bldg['ceiling_height'] * 2. * (w + d)) - 1. + bldg['window_wall_ratio'] * bldg['exterior_wall_fraction']
        bldg['init_temp'] = 68. + 4. * np.random.random()
        bldg['os_rand'] = bldg['oversize'] * (0.8 + 0.4 * np.random.random())
        bldg['COP_A'] = glm_modifier.defaults.cooling_COP * (0.8 + 0.4 * np.random.random())

        bldg['adj_lights'] = 1.2 * (0.9 + 0.1 * np.random.random()) * floor_area / 1000.  # randomize 10# then convert W/sf -> kW
        bldg['adj_plugs'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
        bldg['adj_gas'] = (0.9 + 0.2 * np.random.random()) * floor_area / 1000.
        bldg['adj_ext'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.
        bldg['adj_occ'] = (0.9 + 0.1 * np.random.random()) * floor_area / 1000.

        bldg['zonename'] = gld_strict_name (key + '_bldg_' + str(jjj+1) + '_zone_' + str(zone))
        add_one_commercial_zone (glm_modifier, bldg)

  elif comm_type == 'STRIPMALL':
    bldg['ceiling_height'] = 12 # T)D)
    bldg['airchange_per_hour'] = 1.76
    bldg['Rroof'] = 19.
    bldg['Rwall'] = 18.3
    bldg['Rfloor'] = 40.
    bldg['Rdoors'] = 3.
    bldg['int_gains'] = 3.6  # W/sf
    bldg['exterior_ceiling_fraction'] = 1.
    bldg['base_schedule'] = 'stripmall'
    midzone = int (math.floor(nz / 2.) + 1.)
    for zone in range (1, nz+1):
      bldg['skew_value'] = randomize_commercial_skew(glm_modifier)
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
      bldg['COP_A'] = glm_modifier.defaults.cooling_COP * (0.8 + 0.4 * np.random.random())

      bldg['adj_lights'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
      bldg['adj_plugs'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
      bldg['adj_gas'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
      bldg['adj_ext'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.
      bldg['adj_occ'] = (0.8 + 0.4 * np.random.random()) * floor_area / 1000.

      bldg['zonename'] = gld_strict_name (key + '_zone_' + str(zone))
      add_one_commercial_zone (glm_modifier, bldg)

  params = dict()
  if comm_type == 'ZIPLOAD':
    phsva = 1000.0 * kva / nphs
    name = '{:s}'.format (key + '_streetlights')
    params["parent"] = '{:s};'.format (mtr)
    params["groupid"] = "STREETLIGHTS"
    params["nominal_voltage"] = '{:2f}'.format(vln)
    params["phases"] = '{:s}'.format (phases)
    for phs in ['A', 'B', 'C']:
      if phs in phases:
          params["impedance_fraction_" + phs] = '{:f};'.format (glm_modifier.defaults.c_z_frac)
          params["current_fraction_" + phs] = '{:f}'.format (glm_modifier.defaults.c_i_frac)
          params["power_fraction_" + phs] = '{:f}'.format (bldg['c_p_frac'])
          params["impedance_pf_" + phs] = '{:f}'.format (glm_modifier.defaults.c_z_pf)
          params["current_pf_" + phs] = '{:f}'.format (glm_modifier.defaults.c_i_pf)
          params["power_pf_" + phs] = '{:f}'.format (glm_modifier.defaults.c_p_pf)
          params["base_power_" + phs] = '{:.2f}'.format (glm_modifier.defaults.light_scalar_comm * phsva)
    glm_modifier.add_object("load", "street lights", params)
  else:
    name = '{:s}'.format (key)
    params["parent"] = '{:s};'.format (mtr)
    params["groupid"] = '{:s}'.format (comm_type)
    params["nominal_voltage"] = '{:2f}'.format(vln)
    params["phases"] = '{:s}'.format (phases)
    glm_modifier.add_object("load", "accumulate zone", params)


#***************************************************************************************************
#***************************************************************************************************

def add_houses(glm_modifier, basenode, vnom, bIgnoreThermostatSchedule=True, bWriteService=True, bTriplex=True,
               setpoint_offset=1.0, fg_recs_dataset=None):
    """Put houses, along with solar panels and batteries, onto a node

    Args:
        basenode (str): GridLAB-D node name
        op (file): open file to write to
        vnom (float): nominal line-to-neutral voltage at basenode
    """

    meter_class = 'triplex_meter'
    node_class = 'triplex_node'
    if bTriplex == False:
        meter_class = 'meter'
        node_class = 'node'

    if fg_recs_dataset is None:
        nhouse = int(glm_modifier.defaults.house_nodes[basenode][0])
    else:
        housing_type, year_made_range = fg_recs_dataset.get_house_type_vintage(glm_modifier.defaults.recs_state,
                                                                               glm_modifier.defaults.recs_income_level,
                                                                               glm_modifier.defaults.recs_housing_density)
        SQFTRANGE = fg_recs_dataset.get_parameter_sample(glm_modifier.defaults.recs_state,
                                                         glm_modifier.defaults.recs_income_level,
                                                         glm_modifier.defaults.recs_housing_density,
                                                         housing_type[0], year_made_range[0], "SQFTRANGE")
        nhouse = fg_recs_dataset.calc_building_count(glm_modifier.defaults.recs_state,
                                                     glm_modifier.defaults.recs_income_level,
                                                     glm_modifier.defaults.recs_housing_density,
                                                     housing_type[0], year_made_range[0])

    rgn = int(glm_modifier.defaults.house_nodes[basenode][1])
    lg_v_sm = float(glm_modifier.defaults.house_nodes[basenode][2])
    phs = glm_modifier.defaults.house_nodes[basenode][3]
    bldg = glm_modifier.defaults.house_nodes[basenode][4]
    ti = glm_modifier.defaults.house_nodes[basenode][5]
    inc_lev = glm_modifier.defaults.house_nodes[basenode][6]
    # rgnTable = glm_modifier.defaults.rgnThermalPct[rgn-1]


    if 'A' in phs:
        vstart = str(vnom) + '+0.0j'
    elif 'B' in phs:
        vstart = format(-0.5 * vnom, '.2f') + format(-0.866025 * vnom, '.2f') + 'j'
    else:
        vstart = format(-0.5 * vnom, '.2f') + '+' + format(0.866025 * vnom, '.2f') + 'j'

    if glm_modifier.defaults.forERCOT == "True":
        phs = phs + 'S'
        tpxname = gld_strict_name(basenode + '_tpx')
        mtrname = gld_strict_name(basenode + '_mtr')
    else:
        params = dict()
        t_name = basenode
        params["phases"] = phs
        params["nominal_voltage"] = str(vnom)
        params["voltage_1"] = vstart
        params["voltage_2"] = vstart
        glm_modifier.add_object("triplex_node", t_name, params)
    for i in range(nhouse):
        if (glm_modifier.defaults.forERCOT == "False") and (bWriteService == True):

            tpxname = gld_strict_name(basenode + '_tpx_' + str(i + 1))
            mtrname = gld_strict_name(basenode + '_mtr_' + str(i + 1))
            params2 = dict()
            name = tpxname
            params2["from"] = basenode
            params2["to"] = mtrname
            params2["phases"] = phs
            params2["length"] = "30"
            params2["configuration"] = glm_modifier.defaults.name_prefix + \
                                       list(glm_modifier.defaults.triplex_configurations.keys())[0]
            glm_modifier.add_object("triplex_line", name, params2)

            params3 = dict()
            params3[""] = str
            params3["phases"] = phs
            params3["meter_power_consumption"] = "1+7j"
            add_tariff(params3)
            params3["nominal_voltage"] = str(vnom)
            params3["voltage_1"] = vstart
            params3["voltage_2"] = vstart
            glm_modifier.add_object("triplex_meter", mtrname, params3)

            if glm_modifier.defaults.metrics_interval > 0 and "meter" in glm_modifier.defaults.metrics:
                params4 = dict()
                params4["parent"] = mtrname
                params4["interval"] = str(glm_modifier.defaults.metrics_interval)
                glm_modifier.add_object("metrics_collector", "", params4)
        hsename = gld_strict_name(basenode + '_hse_' + str(i + 1))
        whname = gld_strict_name(basenode + '_wh_' + str(i + 1))
        solname = gld_strict_name(basenode + '_sol_' + str(i + 1))
        batname = gld_strict_name(basenode + '_bat_' + str(i + 1))
        evname = gld_strict_name(basenode + '_ev_' + str(i + 1))
        sol_i_name = gld_strict_name(basenode + '_isol_' + str(i + 1))
        bat_i_name = gld_strict_name(basenode + '_ibat_' + str(i + 1))
        sol_m_name = gld_strict_name(basenode + '_msol_' + str(i + 1))
        bat_m_name = gld_strict_name(basenode + '_mbat_' + str(i + 1))
        if glm_modifier.defaults.forERCOT == "True":
            hse_m_name = mtrname
            hse_m_name = gld_strict_name(basenode + '_mhse_' + str(i + 1))
            params4 = dict()
            t_name = hse_m_name
            params4["parent"] = mtrname
            params4["phases"] = phs
            params4["nominal_voltage"] = str(vnom)
            glm_modifier.add_object("triplex_meter", t_name, params4)
    else:
        hse_m_name = gld_strict_name(basenode + '_mhse_' + str(i + 1))
        params5 = dict()
        t_name = hse_m_name
        params5["parent"] = mtrname
        params5["phases"] = phs
        params5["nominal_voltage"] = str(vnom)
        glm_modifier.add_object("triplex_meter", t_name, params5)

    # ************* Floor area, ceiling height and stories *************************
    fa_array = {}  # distribution array for floor area min, max, mean, standard deviation
    stories = 1
    ceiling_height = 8
    vint = glm_modifier.defaults.vint_type[ti]
    income = glm_modifier.defaults.income_level[inc_lev]


    if bldg == 0:  # SF
        fa_bldg = 'single_family_detached'  # then pick single_Family_detached values for floor_area
        if np.random.uniform(0, 1) > \
                glm_modifier.defaults.res_bldg_metadata['num_stories'][glm_modifier.defaults.state][
                    glm_modifier.defaults.res_dso_type][income][fa_bldg][vint][
                    'one_story']:
            stories = 2  # all SF homes which are not single story are 2 stories
        if np.random.uniform(0, 1) <= \
                glm_modifier.defaults.res_bldg_metadata['high_ceilings'][glm_modifier.defaults.state][
                    glm_modifier.defaults.res_dso_type][income][fa_bldg][vint]:
            ceiling_height = 10  # all SF homes that have high ceilings are 10 ft
        ceiling_height += np.random.randint(0, 2)
    elif bldg == 1:  # apartments
        fa_bldg = 'apartment_2_4_units'  # then pick apartment_2_4_units for floor area
    elif bldg == 2:  # mh
        fa_bldg = 'mobile_home'
    else:
        raise ValueError("Wrong building type chosen !")



    vint = glm_modifier.defaults.vint_type[ti]
    # creating distribution array for floor_area
    for ind in ['min', 'max', 'mean', 'standard_deviation']:
        fa_array[ind] = glm_modifier.defaults.res_bldg_metadata['floor_area'][glm_modifier.defaults.state][
            glm_modifier.defaults.res_dso_type][income][fa_bldg][ind]
        # next_ti = ti
        # while not fa_array[ind]:  # if value is null/None, check the next vintage bin
        #     next_ti += 1
        #     fa_array[ind] = res_bldg_metadata['floor_area'][ind][fa_bldg][vint_type[next_ti]]
    # print(i)
    # print(nhouse)
    floor_area = random_norm_trunc(fa_array)  # truncated normal distribution
    floor_area = (1 + lg_v_sm) * floor_area  # adjustment depends on whether nhouses rounded up or down
    fa_rand = np.random.uniform(0, 1)
    if floor_area > 6000:  # TODO: do we need this condition ? it was originally 4000
        floor_area = 5800 + fa_rand * 200
    elif floor_area < 300:
        floor_area = 300 + fa_rand * 100
    floor_area = (1 + lg_v_sm) * floor_area  # adjustment depends on whether nhouses rounded up or down

    fa_rand = np.random.uniform(0, 1)
    if floor_area > 6000:  # TODO: do we need this condition ? it was originally 4000
        floor_area = 5800 + fa_rand * 200
    elif floor_area < 300:
        floor_area = 300 + fa_rand * 100

    scalar1 = 324.9 / 8907 * floor_area ** 0.442
    scalar2 = 0.6 + 0.4 * np.random.uniform(0, 1)
    scalar3 = 0.6 + 0.4 * np.random.uniform(0, 1)
    resp_scalar = scalar1 * scalar2
    unresp_scalar = scalar1 * scalar3

    skew_value = randomize_residential_skew()

    #  *************** Aspect ratio, ewf, ecf, eff, wwr ****************************
    if bldg == 0:  # SF homes
        dist_array = glm_modifier.defaults.res_bldg_metadata['aspect_ratio']['single_family']  # min, max, mean, std
        aspect_ratio = random_norm_trunc(dist_array)
        # Exterior wall and ceiling and floor fraction
        # A normal single family house has all walls exterior, has a ceiling and a floor
        ewf = 1  # exterior wall fraction
        ecf = 1  # exterior ceiling fraction
        eff = 1  # exterior floor fraction
        wwr = (
            glm_modifier.defaults.res_bldg_metadata['window_wall_ratio']['single_family']['mean'])  # window wall ratio
    elif bldg == 1:  # APT
        dist_array = glm_modifier.defaults.res_bldg_metadata['aspect_ratio']['apartments']  # min, max, mean, std
        aspect_ratio = random_norm_trunc(dist_array)
        wwr = (glm_modifier.defaults.res_bldg_metadata['window_wall_ratio']['apartments']['mean'])  # window wall ratio
        # Two type of apts assumed:
        #       1. small apt: 8 units with 4 units on each level: total 2 levels
        #       2. large apt: 16 units with 8 units on each level: total 2 levels
        # Let's decide if this unit belongs to a small apt (8 units) or large (16 units)
        small_apt_pct = glm_modifier.defaults.res_bldg_metadata['housing_type'][glm_modifier.defaults.state][
            glm_modifier.defaults.res_dso_type][income]['apartment_2_4_units']
        large_apt_pct = glm_modifier.defaults.res_bldg_metadata['housing_type'][glm_modifier.defaults.state][
            glm_modifier.defaults.res_dso_type][income]['apartment_5_units']
        if np.random.uniform(0, 1) < small_apt_pct / (small_apt_pct + large_apt_pct):  # 2-level small apt (8 units)
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
        wwr = (glm_modifier.defaults.res_bldg_metadata['window_wall_ratio']['mobile_home']['mean'])  # window wall ratio
        # sw_pct = res_bldg_metadata['mobile_home_single_wide'][state][res_dso_type][income]  # single wide percentage for given vintage bin
        # next_ti = ti
        # while not sw_pct:  # if the value is null or 'None', check the next vintage bin
        #     next_ti += 1
        #     sw_pct = res_bldg_metadata['mobile_home_single_wide'][vint_type[next_ti]]
        if floor_area <= 1080:  # Single wide
            aspect_ratio = random_norm_trunc(
                glm_modifier.defaults.res_bldg_metadata['aspect_ratio']['mobile_home_single_wide'])
        else:  # double wide
            aspect_ratio = random_norm_trunc(
                glm_modifier.defaults.res_bldg_metadata['aspect_ratio']['mobile_home_double_wide'])
        # A normal MH has all walls exterior, has a ceiling and a floor
        ewf = 1  # exterior wall fraction
        ecf = 1  # exterior ceiling fraction
        eff = 1  # exterior floor fraction

    # oversize = rgnOversizeFactor[rgn-1] * (0.8 + 0.4 * np.random.uniform(0,1))
    # data from https://collaborate.pnl.gov/projects/Transactive/Shared%20Documents/DSO+T/Setup%20Assumptions%205.3/Residential%20HVAC.xlsx
    oversize = random_norm_trunc(
        glm_modifier.defaults.res_bldg_metadata['hvac_oversize'])  # hvac_oversize factor
    wetc = random_norm_trunc(
        glm_modifier.defaults.res_bldg_metadata['window_shading'])  # window_exterior_transmission_coefficient

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
    h_COP = c_COP = np.random.choice(glm_modifier.defaults.cop_lookup[ti]) * (
            0.9 + np.random.uniform(0, 1) * 0.2)  # +- 10% of mean value
    # h_COP = c_COP = tiProps[10] + np.random.uniform(0, 1) * (tiProps[9] - tiProps[10])

    params6 = dict()
    name = hsename
    params6["parent"] = hse_m_name
    params6["groupid"] = glm_modifier.defaults.bldgTypeName[bldg]

    # params6["thermal_integrity_level"] = glm_modifier.defaults.tiName[ti]
    # params6["thermal_integrity_level"] = glm_modifier.defaults.thermal_integrity_level[ti]

    params6["schedule_skew"] = '{:.0f}'.format(skew_value)
    params6["floor_area"] = '{:.0f}'.format(floor_area)
    params6["number_of_stories"] = str(stories)
    params6["ceiling_height"] = str(ceiling_height)
    params6["over_sizing_factor"] = '{:.1f}'.format(oversize)
    params6["Rroof"] = '{:.2f}'.format(Rroof)
    params6["Rwall"] = '{:.2f}'.format(Rwall)
    params6["Rfloor"] = '{:.2f}'.format(Rfloor)
    params6["glazing_layers"] = str(glazing_layers)
    params6["glass_type"] = str(glass_type)
    params6["glazing_treatment"] = str(glazing_treatment)
    params6["window_frame"] = str(window_frame)
    params6["Rdoors"] = '{:.2f}'.format(Rdoor)
    params6["airchange_per_hour"] = '{:.2f}'.format(airchange)
    params6["cooling_COP"] = '{:.1f}'.format(c_COP)
    params6["air_temperature"] = '{:.2f}'.format(init_temp)
    params6["mass_temperature"] = '{:.2f}'.format(init_temp)
    params6["total_thermal_mass_per_floor_area"] = '{:.3f}'.format(mass_floor)
    params6["mass_solar_gain_fraction"] = '{}'.format(mass_solar_gain_frac)
    params6["mass_internal_gain_fraction"] = '{}'.format(mass_int_gain_frac)
    params6["aspect_ratio"] = '{:.2f}'.format(aspect_ratio)
    params6["exterior_wall_fraction"] = '{:.2f}'.format(ewf)
    params6["exterior_floor_fraction"] = '{:.2f}'.format(eff)
    params6["exterior_ceiling_fraction"] = '{:.2f}'.format(ecf)
    params6["window_exterior_transmission_coefficient"] = '{:.2f}'.format(wetc)
    params6["window_wall_ratio"] = '{:.2f}'.format(wwr)
    params6["breaker_amps"] = "1000"
    params6["hvac_breaker_rating"] = "1000"
    heat_rand = np.random.uniform(0, 1)
    cool_rand = np.random.uniform(0, 1)
    house_fuel_type = 'electric'
    heat_pump_prob = glm_modifier.defaults.res_bldg_metadata['space_heating_type'][glm_modifier.defaults.state][
                         glm_modifier.defaults.res_dso_type][income][fa_bldg][vint][
                         'gas_heating'] + \
                     glm_modifier.defaults.res_bldg_metadata['space_heating_type'][glm_modifier.defaults.state][
                         glm_modifier.defaults.res_dso_type][income][fa_bldg][vint]['heat_pump']
    # Get the air conditioning percentage for homes that don't have heat pumps
    electric_cooling_percentage = \
        glm_modifier.defaults.res_bldg_metadata['air_conditioning'][glm_modifier.defaults.state][
            glm_modifier.defaults.res_dso_type][income][fa_bldg]

    if heat_rand <= glm_modifier.defaults.res_bldg_metadata['space_heating_type'][glm_modifier.defaults.state][
        glm_modifier.defaults.res_dso_type][income][fa_bldg][vint]['gas_heating']:
        house_fuel_type = 'gas'
        params6["heating_system_type"] = "GAS"
        if cool_rand <= electric_cooling_percentage:
            params6["cooling_system_type"] = "ELECTRIC"
        else:
            params6["cooling_system_type"] = "NONE"
    elif heat_rand <= glm_modifier.defaults.rgnPenGasHeat[rgn - 1] + glm_modifier.defaults.rgnPenHeatPump[rgn - 1]:
        params6["heating_system_type"] = "HEAT_PUMP"
        params6["heating_COP"] = '{:.1f}'.format(h_COP)
        params6["cooling_system_type"] = "ELECTRIC"
        params6["auxiliary_strategy"] = "DEADBAND"
        params6["auxiliary_system_type"] = "ELECTRIC"
        params6["motor_model"] = "BASIC"
        params6["motor_efficiency"] = "AVERAGE"
    # TODO: check with Rob if following large home condition is needed or not:
    # elif floor_area * ceiling_height > 12000.0:  # electric heat not allowed on large homes
    #     params6["heating_system_type"] =  "GAS"
    #     if cool_rand <= electric_cooling_percentage:
    #         params6["cooling_system_type"] = "ELECTRIC"
    #     else:
    #         params6["cooling_system_type"] = "NONE"
    else:
        params6["heating_system_type"] = "RESISTANCE"
        if cool_rand <= glm_modifier.defaults.electric_cooling_percentage:
            params6["cooling_system_type"] = "ELECTRIC"
            params6["motor_model"] = "BASIC"
            params6["motor_efficiency"] = "GOOD"
        else:
            params6["cooling_system_type"] = "NONE"

    # default heating and cooling setpoints are 70 and 75 degrees in GridLAB-D
    # we need more separation to assure no overlaps during transactive simulations
    params6["cooling_setpoint"] = "80.0"
    params6["heating_setpoint"] = "60.0"
    glm_modifier.add_object("house", params6["house"], params6)

    # heatgain fraction, Zpf, Ipf, Ppf, Z, I, P
    params7 = dict()
    params7["schedule_skew"] = '{:.0f}'.format(skew_value)
    params7["base_power"] = 'responsive_loads*' + '{:.2f}'.format(resp_scalar)
    params7["heatgain_fraction"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['heatgain_fraction'])
    params7["impedance_pf"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['impedance_pf'])
    params7["current_pf"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['current_pf'])
    params7["power_pf"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['power_pf'])
    params7["impedance_fraction"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['impedance_fraction'])
    params7["current_fraction"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['current_fraction'])
    params7["power_fraction"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['power_fraction'])
    glm_modifier.add_object("ZIPload", "responsive", params7)

    params8 = dict()
    params8["schedule_skew"] = '{:.0f}'.format(skew_value)
    params8["base_power"] = 'unresponsive_loads*' + '{:.2f}'.format(unresp_scalar)
    params8["heatgain_fraction"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['heatgain_fraction'])
    params8["impedance_pf"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['impedance_pf'])
    params8["current_pf"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['current_pf'])
    params8["power_pf"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['power_pf'])
    params8["impedance_fkraction"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['impedance_fraction'])
    params8["current_fraction"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['current_fraction'])
    params8["power_fraction"] = '{:.2f}'.format(glm_modifier.defaults.ZIPload_parameters[0]['power_fraction'])
    glm_modifier.add_object("ZIPload", "unresponsive", params8)

    # if np.random.uniform (0, 1) <= glm_modifier.defaults.water_heater_percentage:
    # Determine if house has matching heating types for space and water
    if np.random.uniform(0, 1) <= \
            glm_modifier.defaults.res_bldg_metadata['water_heating_type'][glm_modifier.defaults.state][
                glm_modifier.defaults.res_dso_type][income][fa_bldg][vint]:
        wh_fuel_type = house_fuel_type
    elif house_fuel_type == 'gas':
        wh_fuel_type = 'electric'
    elif house_fuel_type == 'electric':
        wh_fuel_type = 'gas'
    if wh_fuel_type == 'electric':  # if the water heater fuel type is electric, install wh
        heat_element = 3.0 + 0.5 * np.random.randint(1, 6);  # numpy randint (lo, hi) returns lo..(hi-1)
        tank_set = 110 + 16 * np.random.uniform(0, 1);
        therm_dead = 4 + 4 * np.random.uniform(0, 1);
        tank_UA = 2 + 2 * np.random.uniform(0, 1);
        water_sch = np.ceil(glm_modifier.defaults.waterHeaterScheduleNumber * np.random.uniform(0, 1))
        water_var = 0.95 + np.random.uniform(0, 1) * 0.1  # +/-5% variability
        wh_demand_type = 'large_'

        # sizeIncr = np.random.randint (0,3)  # MATLAB randi(imax) returns 1..imax
        # sizeProb = np.random.uniform (0, 1);
        # if sizeProb <= glm_modifier.defaults.rgnWHSize[rgn-1][0]:
        #    wh_size = 20 + sizeIncr * 5
        #    wh_demand_type = 'small_'
        # elif sizeProb <= (glm_modifier.defaults.rgnWHSize[rgn-1][0] + glm_modifier.defaults.rgnWHSize[rgn-1][1]):
        #    wh_size = 30 + sizeIncr * 10
        #    if floor_area < 2000.0:
        #        wh_demand_type = 'small_'
        # else:
        #    if floor_area < 2000.0:
        #       wh_size = 30 + sizeIncr * 10
        #   else:
        #       wh_size = 50 + sizeIncr * 10
        # new wh size implementation
        wh_data = glm_modifier.defaults.res_bldg_metadata['water_heater_tank_size']
        if floor_area <= wh_data['floor_area']['1_2_people']['floor_area_max']:
            size_array = range(wh_data['tank_size']['1_2_people']['min'],
                               wh_data['tank_size']['1_2_people']['max'] + 1, 5)
            wh_demand_type = 'small_'
        elif floor_area <= wh_data['floor_area']['2_3_people']['floor_area_max']:
            size_array = range(wh_data['tank_size']['2_3_people']['min'],
                               wh_data['tank_size']['2_3_people']['max'] + 1, 5)
            wh_demand_type = 'small_'
        elif floor_area <= wh_data['floor_area']['3_4_people']['floor_area_max']:
            size_array = range(wh_data['tank_size']['3_4_people']['min'],
                               wh_data['tank_size']['3_4_people']['max'] + 1, 10)
        else:
            size_array = range(wh_data['tank_size']['5_plus_people']['min'],
                               wh_data['tank_size']['5_plus_people']['max'] + 1, 10)
        wh_size = np.random.choice(size_array)
    wh_demand_str = wh_demand_type + '{:.0f}'.format(water_sch) + '*' + '{:.2f}'.format(water_var)
    wh_skew_value = 3 * glm_modifier.defaults.residential_skew_std * np.random.randn()
    if wh_skew_value < -6 * glm_modifier.defaults.residential_skew_max:
        wh_skew_value = -6 * glm_modifier.defaults.residential_skew_max
    elif wh_skew_value > 6 * glm_modifier.defaults.residential_skew_max:
        wh_skew_value = 6 * glm_modifier.defaults.residential_skew_max
    params9 = dict()
    name = whname
    params9["schedule_skew"] = '{:.0f}'.format(wh_skew_value)
    params9["heating_element_capacity"] = '{:.1f}'.format(heat_element)
    params9["thermostat_deadband"] = '{:.1f}'.format(therm_dead)
    params9["location"] = "INSIDE"
    params9["tank_diameter"] = "1.5"
    params9["tank_UA"] = '{:.1f}'.format(tank_UA)
    params9["water_demand"] = wh_demand_str
    params9["tank_volume"] = '{:.0f}'.format(wh_size)
    #          if np.random.uniform (0, 1) <= glm_modifier.defaults.water_heater_participation:
    params9["waterheater_model"] = "MULTILAYER"
    params9["discrete_step_size"] = "60.0"
    params9["lower_tank_setpoint"] = '{:.1f}'.format(tank_set - 5.0)
    params9["upper_tank_setpoint"] = '{:.1f}'.format(tank_set + 5.0)
    params9["T_mixing_valve"] = '{:.1f}'.format(tank_set)
    #          else:
    #              params9["tank_setpoint"] = '{:.1f}'.format(tank_set)
    glm_modifier.add_object("waterheater", whname, params9)

    if glm_modifier.defaults.metrics_interval > 0:
        params10 = dict()
        params10["parent"] = whname
        params10["interval"] = str(glm_modifier.defaults.metrics_interval)
        glm_modifier.add_object("metrics_collector", "", params10)

    if glm_modifier.defaults.metrics_interval > 0:
        params11 = dict()
        params11["parent"] = whname
        params11["interval"] = str(glm_modifier.defaults.metrics_interval)
        glm_modifier.add_object("metrics_collector", "", params11)


# if PV is allowed, then only single-family houses can buy it, and only the single-family houses with PV will also consider storage
# if PV is not allowed, then any single-family house may consider storage (if allowed)
# apartments and mobile homes may always consider storage, but not PV
# bConsiderStorage = True
# Solar percentage should be defined here only from RECS data based on income level
# solar_percentage = res_bldg_metadata['solar_pv'][state][dso_type][income][fa_bldg]
# Calculate the solar, storage, and ev percentage based on the income level
    il_percentage = glm_modifier.defaults.res_bldg_metadata['income_level'][glm_modifier.defaults.state][
        glm_modifier.defaults.res_dso_type][income]

    if fg_recs_dataset is not None:
        solar_percentage_il = fg_recs_dataset.calc_solar_percentage(glm_modifier.defaults.recs_state,
                                                                    glm_modifier.defaults.recs_income_level,
                                                                        glm_modifier.defaults.recs_housing_density)
    else:
        solar_percentage_il = (glm_modifier.defaults.solar_percentage *
                        glm_modifier.defaults.res_bldg_metadata['solar_percentage'][income]) / il_percentage


    storage_percentage_il = (glm_modifier.defaults.storage_percentage *
        glm_modifier.defaults.res_bldg_metadata['battery_percentage'][income]) / il_percentage
    ev_percentage_il = (glm_modifier.defaults.ev_percentage * glm_modifier.defaults.res_bldg_metadata['ev_percentage'][
        income]) / il_percentage
    if bldg == 0:  # Single-family homes
        if solar_percentage_il > 0.0:
            pass
            # bConsiderStorage = False
        if np.random.uniform(0, 1) <= solar_percentage_il:  # some single-family houses have PV
            # bConsiderStorage = True
            # This is legacy code method to find solar rating
            # panel_area = 0.1 * floor_area
            # if panel_area < 162:
            #     panel_area = 162
            # elif panel_area > 270:
            #     panel_area = 270
            # inverter_undersizing = 1.0
            # array_efficiency = 0.2
            # rated_insolation = 1000.0
            # inv_power = inverter_undersizing * (panel_area / 10.7642) * rated_insolation * array_efficiency
            # this results in solar ranging from 3 to 5 kW
            # new method directly proportional to sq. ft.
            # typical PV panel is 350 Watts and avg home has 5kW installed.
            # If we assume 2500 sq. ft as avg area of a single family house, we can say:
            # one 350 W panel for every 175 sq. ft.
            num_panel = np.floor(floor_area / 175)
            inverter_undersizing = 1.0
            inv_power = num_panel * 350 * inverter_undersizing
            pv_scaling_factor = inv_power / glm_modifier.defaults.pv_rating_MW
            if glm_modifier.defaults.case_type['pv']:
                glm_modifier.defaults.solar_count += 1
                glm_modifier.defaults.solar_kw += 0.001 * inv_power
                params12 = dict()
                t_name = sol_m_name
                params12["parent"] = mtrname
                params12["phases"] = phs
                params12["nominal_voltage"] = str(vnom)
                glm_modifier.add_object("triplex_meter", t_name, params12)

                params13 = dict()
                t_name = sol_i_name
                params13["phases"] = phs
                params13["groupid"] = "sol_inverter"
                params13["generator_status"] = "ONLINE"
                params13["inverter_type"] = "FOUR_QUADRANT"
                params13["inverter_efficiency"] = "1"
                params13["rated_power"] = '{:.0f}'.format(inv_power)
                params13["generator_mode"] = glm_modifier.defaults.solar_inv_mode
                params13["four_quadrant_control_mode"] = glm_modifier.defaults.solar_inv_mode
                params13["P_Out"] = 'P_out_inj.value * {}'.format(pv_scaling_factor)
                if 'no_file' not in glm_modifier.defaults.solar_Q_player:
                    params13["Q_Out"] = "Q_out_inj.value * 0.0"
                else:
                    params13["Q_Out"] = "0"
                # write_solar_inv_settings(op)  # don't want volt/var control
                # No need of solar object
                # print('    object solar {', file=op)
                # print('      name', solname + ';', file=op)
                # print('      panel_type SINGLE_CRYSTAL_SILICON;', file=op)
                # print('      efficiency', '{:.2f}'.format(array_efficiency) + ';', file=op)
                # print('      area', '{:.2f}'.format(panel_area) + ';', file=op)
                # print('    };', file=op)
                # Instead of solar object, write a fake V_in and I_in sufficient high so
                # that it doesn't limit the player output
                params13["V_In"] = "10000000"
                params13["I_In"] = "10000000"
                glm_modifier.add_object("inverter", sol_i_name, params13)
            if glm_modifier.defaults.metrics_interval > 0:
                params15 = dict()
                params15["interval"] = str(glm_modifier.defaults.metrics_interval)
                params15["parent"] = sol_i_name
                glm_modifier.add_object("metrics_collector", "", params15)

    if np.random.uniform(0, 1) <= storage_percentage_il:
        battery_capacity = get_dist(glm_modifier.defaults.batt_metadata['capacity(kWh)']['mean'],
            glm_modifier.defaults.batt_metadata['capacity(kWh)'][
                                           'deviation_range_per']) * 1000
        max_charge_rate = get_dist(glm_modifier.defaults.batt_metadata['rated_charging_power(kW)']['mean'],
            glm_modifier.defaults.batt_metadata['rated_charging_power(kW)']['deviation_range_per']) * 1000
        max_discharge_rate = max_charge_rate
        inverter_efficiency = glm_modifier.defaults.batt_metadata['inv_efficiency(per)'] / 100
        charging_loss = get_dist(glm_modifier.defaults.batt_metadata['rated_charging_loss(per)']['mean'],
            glm_modifier.defaults.batt_metadata['rated_charging_loss(per)']['deviation_range_per']) / 100
        discharging_loss = charging_loss
        round_trip_efficiency = charging_loss * discharging_loss
        rated_power = max(max_charge_rate, max_discharge_rate)

        if glm_modifier.defaults.case_type['bt']:
            glm_modifier.defaults.battery_count += 1
            params16 = dict()
            params16["parent"] = mtrname
            params16["phases"] = phs
            params16["nominal_voltage"] = str(vnom)
            glm_modifier.add_object("triplex_meter", bat_m_name, params16)

            params17 = dict()
            params17["phases"] = phs
            params17["groupid"] = "batt_inverter"
            params17["generator_status"] = "ONLINE"
            params17["generator_mode"] = "CONSTANT_PQ"
            params17["inverter_type"] = "FOUR_QUADRANT"
            params17["four_quadrant_control_mode"] = glm_modifier.defaults.storage_inv_mode
            params17["charge_lockout_time"] = 1
            params17["discharge_lockout_time"] = 1
            params17["rated_power"] = rated_power
            params17["max_charge_rate"] = max_charge_rate
            params17["max_discharge_rate"] = max_discharge_rate
            params17["sense_object"] = mtrname
            params17["inverter_efficiency"] = inverter_efficiency
            params17["power_factor"] = 1.0
            glm_modifier.add_object("inverter", bat_i_name, params17)

            params18 = dict()
            params18["use_internal_battery_model"] = "true"
            params18[""] = ""
            params18["nominal_voltage"] = 480
            params18["battery_capacity"] = battery_capacity
            params18["round_trip_efficiency"] = round_trip_efficiency
            params18["state_of_charge"] = 0.50
            glm_modifier.add_object("battery", batname, params18)

            if glm_modifier.defaults.metrics_interval > 0 and "inverter" in glm_modifier.defaults.metrics:
                params19 = dict()
                params19["parent"] = batname
                params19["interval"] = glm_modifier.defaults.metrics_interval
                glm_modifier.add_object("metrics_collector", "", params19)

    if np.random.uniform(0, 1) <= ev_percentage_il:
        # first lets select an ev model:
        ev_name = selectEVmodel(glm_modifier.defaults.ev_metadata['sale_probability'], np.random.uniform(0, 1))
        ev_range = glm_modifier.defaults.ev_metadata['Range (miles)'][ev_name]
        ev_mileage = glm_modifier.defaults.ev_metadata['Miles per kWh'][ev_name]
        ev_charge_eff = glm_modifier.defaults.ev_metadata['charging efficiency']
        # check if level 1 charger is used or level 2
        if np.random.uniform(0, 1) <= glm_modifier.defaults.ev_metadata['Level_1_usage']:
            ev_max_charge = glm_modifier.defaults.ev_metadata['Level_1 max power (kW)']
            volt_conf = 'IS110'  # for level 1 charger, 110 V is good
        else:
            ev_max_charge = glm_modifier.defaults.ev_metadata['Level_2 max power (kW)'][ev_name]
            volt_conf = 'IS220'  # for level 2 charger, 220 V is must

        # now, let's map a random driving schedule with this vehicle ensuring daily miles
        # doesn't exceed the vehicle range and home duration is enough to charge the vehicle
        drive_sch = match_driving_schedule(ev_range, ev_mileage, ev_max_charge)
        # ['daily_miles','home_arr_time','home_duration','work_arr_time','work_duration']

        # Should be able to turn off ev entirely using ev_percentage, definitely in debugging
        if glm_modifier.defaults.case_type['pv']:  # evs are populated when its pvCase i.e. high renewable case
            # few sanity checks
            if drive_sch['daily_miles'] > ev_range:
                raise UserWarning('daily travel miles for EV can not be more than range of the vehicle!')
            if not is_hhmm_valid(drive_sch['home_arr_time']) or not is_hhmm_valid(
                drive_sch['home_leave_time']) or not is_hhmm_valid(drive_sch['work_arr_time']):
                raise UserWarning('invalid HHMM format of driving time!')
            if drive_sch['home_duration'] > 24 * 3600 or drive_sch['home_duration'] < 0 or \
                drive_sch['work_duration'] > 24 * 3600 or drive_sch['work_duration'] < 0:
                raise UserWarning('invalid home or work duration for ev!')
            if not is_drive_time_valid(drive_sch):
                raise UserWarning('home and work arrival time are not consistent with durations!')

            glm_modifier.defaults.ev_count += 1
            params20 = dict()
            params20["parent"] = hsename
            params20["configuration"] = volt_conf
            params20["breaker_amps"] = 1000
            params20["battery_SOC"] = 100.0
            params20["travel_distance"] = drive_sch['daily_miles']
            params20["arrival_at_work"] = drive_sch['work_arr_time']
            params20["duration_at_work"] = drive_sch['work_duration']
            params20["arrival_at_home"] = drive_sch['home_arr_time']
            params20["duration_at_home"] = '{}; // (secs)'.format(drive_sch['home_duration'])
            params20["work_charging_available"] = "FALSE"
            params20["maximum_charge_rate"] = ev_max_charge * 1000
            params20["mileage_efficiency"] = ev_mileage
            params20["mileage_classification"] = ev_range
            params20["charging_efficiency"] = ev_charge_eff
            glm_modifier.add_object("evcharger_det", evname, params20)

            if glm_modifier.defaults.metrics_interval > 0:
                params21 = dict()
                params21["parent"] = evname
                params21["interval"] = glm_modifier.defaults.metrics_interval
                glm_modifier.add_object("metrics_collector", "", params21)


#***************************************************************************************************
#***************************************************************************************************

def add_substation(glm_modifier, name, phs, vnom, vll):
    """Write the substation swing node, transformer, metrics collector and fncs_msg object

    Args:
        op (file): an open GridLAB-D input file
        name (str): node name of the primary (not transmission) substation bus
        phs (str): primary phasing in the substation
        vnom (float): not used
        vll (float): feeder primary line-to-line voltage
    """
    # if this feeder will be combined with others, need USE_FNCS to appear first as a marker for the substation
    if len(glm_modifier.defaults.case_name) > 0:
        if glm_modifier.defaults.message_broker == "fncs_msg":
            def_params = dict()
            t_name = "gld" + glm_modifier.defaults.substation_name
            def_params["parent"] = "network_node"
            def_params["configure"] = glm_modifier.defaults.case_name + '_gridlabd.txt'
            def_params["option"] = "transport:hostname localhost, port " + str(glm_modifier.defaults.port)
            def_params["aggregate_subscriptions"] = "true"
            def_params["aggregate_publications"] = "true"
            glm_modifier.add_object("fncs_msg",t_name,def_params)
        if glm_modifier.defaults.message_broker == "helics_msg":
            def_params = dict()
            t_name = "gld" + glm_modifier.defaults.substation_name
            def_params["configure"] = glm_modifier.defaults.case_name + '.json'
            glm_modifier.add_object("helics_msg",t_name,def_params)

    params3 = dict()
    name = 'substation_xfmr_config'
    params3["connect_type"] = 'WYE_WYE'
    params3["install_type"] = 'PADMOUNT'
    params3["primary_voltage"] = '{:.2f}'.format(glm_modifier.defaults.transmissionVoltage)
    params3["secondary_voltage"] = '{:.2f}'.format(vll)
    params3["power_rating"] = '{:.2f}'.format(glm_modifier.defaults.transmissionXfmrMVAbase * 1000.0)
    params3["resistance"] = '{:.2f}'.format(0.01 * glm_modifier.defaults.transmissionXfmrRpct)
    params3["reactance"] = '{:.2f}'.format(0.01 * glm_modifier.defaults.transmissionXfmrXpct)
    params3["shunt_resistance"] = '{:.2f}'.format(100.0 / glm_modifier.defaults.transmissionXfmrNLLpct)
    params3["shunt_reactance"] = '{:.2f}'.format(100.0 / glm_modifier.defaults.transmissionXfmrImagpct)
    glm_modifier.add_object("transformer_configuration", name, params3)

    params4 = dict()
    name = "substation_transformer"
    params4["from"] = "network_node"
    params4["to"] = name
    params4["phases"] = phs
    params4["configuration"] = "substation_xfmr_config"
    glm_modifier.add_object("transformer", name, params4)
    vsrcln = glm_modifier.defaults.transmissionVoltage / math.sqrt(3.0)

    params5 = dict()
    name = 'network_node'
    params5["groupid"] = glm_modifier.defaults.base_feeder_name
    params5["bustype"] = 'SWING'
    params5["nominal_voltage"] = '{:.2f}'.format(vsrcln)
    params5["positive_sequence_voltage"] = '{:.2f}'.format(vsrcln)
    params5["base_power"] = '{:.2f}'.format(glm_modifier.defaults.transmissionXfmrMVAbase * 1000000.0)
    params5["power_convergence_value"] = "100.0"
    params5["phases"] = phs
    glm_modifier.add_object("substation", 'network_node', params5)

    if glm_modifier.defaults.metrics_interval > 0:
        params6 = dict()
        params6["parent"] = 'network_node'
        params6["interval"] = str(glm_modifier.defaults.metrics_interval)
        glm_modifier.add_object("metrics_collector", "", params6)
        # debug
        params7 = dict()
        params7["parent"] = name
        params7["property"] = "distribution_power_A"
        params7["file"] = "sub_power.csv"
        params7["interval"] = "300"
        glm_modifier.add_object("recorder", name, params7)

# ***************************************************************************************************
# ***************************************************************************************************

# if triplex load, node or meter, the nominal voltage is 120
#   if the name or parent attribute is found in secmtrnode, we look up the nominal voltage there
#   otherwise, the nominal voltage is vprim
# secmtrnode[mtr_node] = [kva_total, phases, vnom]
#   the transformer phasing was not changed, and the transformers were up-sized to the largest phase kva
#   therefore, it should not be necessary to look up kva_total, but phases might have changed N==>S
# if the phasing did change N==>S, we have to prepend triplex_ to the class, write power_1 and voltage_1
# when writing commercial buildings, if load_class is present and == C, skip the instance


def add_voltage_class(glm_modifier,model, h, t, vprim, vll, secmtrnode):
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
                    add_substation(glm_modifier, name, phs, vnom, vll)
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
                parent = model[t][o]['parent']
                if parent in secmtrnode:
                    vnom = secmtrnode[parent][2]
                    phs = secmtrnode[parent][1]
            if str.find(phs, 'S') >= 0:
                bHaveS = True
            else:
                bHaveS = False
            if bHaveS == True and bHadS == False:
                prefix = 'triplex_'
            params = dict()
            if len(parent) > 0:
                params["parent"] = parent
            name = name
            if 'groupid' in model[t][o]:
                params["groupid"] = model[t][o]['groupid']
            if 'bustype' in model[t][o]:  # already moved the SWING bus behind substation transformer
                if model[t][o]['bustype'] != 'SWING':
                    params["bustype"] = model[t][o]['bustype']
            params["phases"] = phs
            params["nominal_voltage"] = str(vnom)
            if 'load_class' in model[t][o]:
                params["load_class"] = model[t][o]['load_class']
            if 'constant_power_A' in model[t][o]:
                if bHaveS == True:
                    params["power_1"] = model[t][o]['constant_power_A']
                else:
                    params["constant_power_A"] = model[t][o]['constant_power_A']
            if 'constant_power_B' in model[t][o]:
                if bHaveS == True:
                    params["power_1"] = model[t][o]['constant_power_B']
                else:
                    params["constant_power_B"] = model[t][o]['constant_power_B']
            if 'constant_power_C' in model[t][o]:
                if bHaveS == True:
                    params["power_1"] = model[t][o]['constant_power_C']
                else:
                    params["constant_power_C"] = model[t][o]['constant_power_C']
            if 'power_1' in model[t][o]:
                params["power_1"] = model[t][o]['power_1']
            if 'power_2' in model[t][o]:
                params["power_2"] = model[t][o]['power_2']
            if 'power_12' in model[t][o]:
                params["power_12"] = model[t][o]['power_12']
            vstarta = str(vnom) + '+0.0j'
            vstartb = format(-0.5 * vnom, '.2f') + format(-0.866025 * vnom, '.2f') + 'j'
            vstartc = format(-0.5 * vnom, '.2f') + '+' + format(0.866025 * vnom, '.2f') + 'j'
            if 'voltage_A' in model[t][o]:
                if bHaveS == True:
                    params["voltage_1"] = vstarta
                    params["voltage_2"] = vstarta
                else:
                    params["voltage_A"] = vstarta
            if 'voltage_B' in model[t][o]:
                if bHaveS == True:
                    params["voltage_1"] = vstartb
                    params["voltage_2"] = vstartb
                else:
                    params["voltage_B"] = vstartb
            if 'voltage_C' in model[t][o]:
                if bHaveS == True:
                    params["voltage_1"] = vstartc
                    params["voltage_2"] = vstartc
                else:
                    params["voltage_C"] = vstartc
            if 'power_1' in model[t][o]:
                params["power_1"] = model[t][o]['power_1']
            if 'power_2' in model[t][o]:
                params["power_2"] = model[t][o]['power_2']
            if 'voltage_1' in model[t][o]:
                if str.find(phs, 'A') >= 0:
                    params["voltage_1"] = vstarta
                    params["voltage_2"] = vstarta
                if str.find(phs, 'B') >= 0:
                    params["voltage_1"] = vstartb
                    params["voltage_2"] = vstartb
                if str.find(phs, 'C') >= 0:
                    params["voltage_1"] = vstartc
                    params["voltage_2"] = vstartc
            if name in extra_billing_meters:
                add_tariff(glm_modifier, params)
                if glm_modifier.defaults.metrics_interval > 0:
                    params2 = dict()
                    params2["interval"] = str(glm_modifier.defaults.metrics_interval)
                    glm_modifier.add_object("metrics_interval", name, params2)
            glm_modifier.add_object(prefix + t, name, params)

#***************************************************************************************************
#***************************************************************************************************

def add_config_class (glm_modifier, model, h, t):
    """Write a GridLAB-D configuration (i.e. not a link or node) class

    Args:
        model (dict): the parsed GridLAB-D model
        h (dict): the object ID hash
        t (str): the GridLAB-D class
        op (file): an open GridLAB-D input file
    """
    if t in model:
        for o in model[t]:
            params =dict()
            params[""] = str
            name = o
            for p in model[t][o]:
                if ':' in model[t][o][p]:
                    params[p] = h[model[t][o][p]]
                else:
                    params[p] = model[t][o][p]
            glm_modifier.add_object(t, o, params)


# ***************************************************************************************************
# ***************************************************************************************************

def add_xfmr_config(glm_modifier,key, phs, kvat, vnom, vsec, install_type, vprimll, vprimln):
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
    params = dict()
    name = glm_modifier.defaults.name_prefix + key
    params["power_rating"] = format(kvat, '.2f')
    kvaphase = kvat
    if 'XF2' in key:
        kvaphase /= 2.0
    if 'XF3' in key:
        kvaphase /= 3.0
    if 'A' in phs:
        params["powerA_rating"] = format(kvaphase, '.2f')
    else:
        params["powerA_rating"] = "0.0"
    if 'B' in phs:
        params["powerB_rating"] = format(kvaphase, '.2f')
    else:
        params["powerB_rating"] = "0.0"
    if 'C' in phs:
        params["powerC_rating"] = format(kvaphase, '.2f')
    else:
        params["powerC_rating"] = "0.0"
    params["install_type"] = install_type
    if 'S' in phs:
        row = Find1PhaseXfmr(glm_modifier, kvat)
        params["connect_type"] = "SINGLE_PHASE_CENTER_TAPPED"
        params["primary_voltage"] = str(vprimln)
        params["secondary_voltage"] = format(vsec, '.1f')
        params["resistance"] = format(row[1] * 0.5, '.5f')
        params["resistance1"] = format(row[1], '.5f')
        params["resistance2"] = format(row[1], '.5f')
        params["reactance"] = format(row[2] * 0.8, '.5f')
        params["reactance1"] = format(row[2] * 0.4, '.5f')
        params["reactance2"] = format(row[2] * 0.4, '.5f')
        params["shunt_resistance"] = format(1.0 / row[3], '.2f')
        params["shunt_reactance"] = format(1.0 / row[4], '.2f')
    else:
        row = Find3PhaseXfmr(glm_modifier, kvat)
        params["connect_type"] = "WYE_WYE"
        params["primary_voltage"] = str(vprimll)
        params["secondary_voltage"] = format(vsec, '.1f')
        params["resistance"] = format(row[1], '.5f')
        params["reactance"] = format(row[2], '.5f')
        params["shunt_resistance"] = format(1.0 / row[3], '.2f')
        params["shunt_reactance"] = format(1.0 / row[4], '.2f')
    glm_modifier.add_object("transformer_configuration", name, params)

# ***************************************************************************************************
# ***************************************************************************************************

def ProcessTaxonomyFeeder(glm_modifier, outname, rootname, vll, vln, avghouse, avgcommercial, fg_recs_dataset=None):
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
    glm_modifier.defaults.solar_count = 0
    glm_modifier.defaults.solar_kw = 0
    glm_modifier.defaults.battery_count = 0
    glm_modifier.defaults.ev_count = 0

    glm_modifier.defaults.base_feeder_name = gld_strict_name(rootname)

#    fname = glm_modifier.defaults.glmpath + rootname + '.glm'
    fname = glm_modifier.model.in_file
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
    print('using', glm_modifier.defaults.solar_percentage, 'percent solar and', glm_modifier.defaults.storage_percentage, 'percent storage penetration')
    # if glm_modifier.defaults.electric_cooling_percentage <= 0.0:
    #     glm_modifier.defaults.electric_cooling_percentage = glm_modifier.defaults.rgnPenElecCool[rgn - 1]
    #     print('using regional default', glm_modifier.defaults.electric_cooling_percentage,
    #           'air conditioning penetration')
    # else:
    #     print('using', glm_modifier.defaults.electric_cooling_percentage,
    #           'air conditioning penetration from JSON config')
    # if glm_modifier.defaults.water_heater_percentage <= 0.0:
    #     glm_modifier.defaults.water_heater_percentage = glm_modifier.defaults.rgnPenElecWH[rgn - 1]
    #     print('using regional default', glm_modifier.defaults.water_heater_percentage, 'water heater penetration')
    # else:
    #     print('using', glm_modifier.defaults.water_heater_percentage, 'water heater penetration from JSON config')
    pathstring = os.path.curdir
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


        op = open(glm_modifier.defaults.work_path + outname + '.glm', 'w')

        #print('###### Writing to', glm_modifier.defaults.work_path + outname + '.glm')
        print('Writing to', outname + '.glm')
        octr = 0;
        model = {}
        h = {}  # OID hash
        itr = iter(lines)
        for line in itr:
            if re.search('object', line):
                line, octr = obj(glm_modifier,None, model, line, itr, h, octr)
            else:  # should be the pre-amble, need to replace timestamp and stoptime
                if 'timestamp' in line or 'starttime' in line:
                    glm_modifier.model.module_entities['clock'].starttime.value = glm_modifier.defaults.starttime
                elif 'stoptime' in line:
                    glm_modifier.model.module_entities['clock'].stoptime.value = glm_modifier.defaults.endtime
                elif 'timezone' in line:
                    #print('  timezone ' + timezone + ';', file=op)
                    glm_modifier.model.module_entities['clock'].timezone.value = glm_modifier.defaults.timezone
#                elif 'module powerflow' in line:
#                    print('module powerflow{', file=op)
#                    print('  lu_solver \"KLU\";', file=op)
#                else:
#                    print(line, file=op)

        # apply the nameing prefix if necessary
        if len(glm_modifier.defaults.name_prefix) > 0:
            for t in model:
                for o in model[t]:
                    elem = model[t][o]
                    for tok in ['name', 'parent', 'from', 'to', 'configuration', 'spacing',
                                'conductor_1', 'conductor_2', 'conductor_N',
                                'conductor_A', 'conductor_B', 'conductor_C']:
                        if tok in elem:
                            elem[tok] = glm_modifier.defaults.name_prefix + elem[tok]

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
                if n1 == glm_modifier.defaults.Eplus_Bus:
                    kva += glm_modifier.defaults.Eplus_kVA
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
        dummy_params = dict()
        t_module = dict()
        # preparatory items for TESP
        glm_modifier.add_module("climate", dummy_params)
        glm_modifier.add_module("generators", dummy_params)
        glm_modifier.add_module("connection", dummy_params)
        t_module["implicit_enduses"] = "NONE"
        mod_params = dict()
        mod_params["implicit_enduses"] = "NONE"
        glm_modifier.add_module("residential",mod_params)


        glm_modifier.model.include_lines.append('#include "${TESPDIR}/data/schedules/appliance_schedules.glm"')
        glm_modifier.model.include_lines.append('#include "${TESPDIR}/data/schedules/water_and_setpoint_schedule_v5.glm"')
        glm_modifier.model.include_lines.append('#include "${TESPDIR}/data/schedules/commercial_schedules.glm"')


        glm_modifier.model.set_lines.append('#set minimum_timestep=' + str(glm_modifier.defaults.timestep))
        glm_modifier.model.set_lines.append('#set relax_naming_rules=1')
        glm_modifier.model.set_lines.append('#set warn=0')



        if glm_modifier.defaults.metrics_interval > 0:
            params = dict()
            params["interval"] = str(glm_modifier.defaults.metrics_interval)
            params["interim"] = "43200"
            if glm_modifier.defaults.forERCOT == "True":
                params["filename"] = outname + '_metrics.json'
            else:
                params["filename"] = '${METRICS_FILE}'
            glm_modifier.add_object("metrics_collector_writer","",params)


        params2 = dict()
        name = "localWeather"
        params2["name"] = str(glm_modifier.defaults.weather_name)
        params2["interpolate"] = "QUADRATIC"
        params2["latitude"] = str(glm_modifier.defaults.latitude)
        params2["longitude"] = str(glm_modifier.defaults.longitude)
        params2["tz_meridian"] = '{0:.2f};'.format(15 * glm_modifier.defaults.time_zone_offset)
        glm_modifier.add_object("climate", name, params2)


        if glm_modifier.defaults.solar_percentage > 0.0:
            #Waiting for the add comment method to be added to the modify class
#            print('// default IEEE 1547-2018 settings for Category B', file=op)
            glm_modifier.model.define_lines.append('#define INV_VBASE=240.0')
            glm_modifier.model.define_lines.append('#define INV_V1=0.92')
            glm_modifier.model.define_lines.append('#define INV_V2=0.98')
            glm_modifier.model.define_lines.append('#define INV_V3=1.02')
            glm_modifier.model.define_lines.append('#define INV_V4=1.08')
            glm_modifier.model.define_lines.append('#define INV_Q1=0.44')
            glm_modifier.model.define_lines.append('#define INV_Q2=0.00')
            glm_modifier.model.define_lines.append('#define INV_Q3=0.00')
            glm_modifier.model.define_lines.append('#define INV_Q4=-0.44')
            glm_modifier.model.define_lines.append('#define INV_VIN=200.0')
            glm_modifier.model.define_lines.append('#define INV_IIN=32.5')
            glm_modifier.model.define_lines.append('#define INV_VVLOCKOUT=300.0')
            glm_modifier.model.define_lines.append('#define INV_VW_V1=1.05 // 1.05833')
            glm_modifier.model.define_lines.append('#define INV_VW_V2=1.10')
            glm_modifier.model.define_lines.append('#define INV_VW_P1=1.0')
            glm_modifier.model.define_lines.append('#define INV_VW_P2=0.0')
        # write the optional volt_dump and curr_dump for validation

        if glm_modifier.defaults.WANT_VI_DUMP == "True":
            params3 = dict()
            params3["parent"] = name
            params3["filename"] = 'Voltage_Dump_' + outname + '.csv'
            params3["mode"] = 'polar'
            glm_modifier.add_object("voltdump", name, params3)
            params4 = dict()
            params4[""] = str
            params4["parent"] = name
            params4["filename"] = 'Current_Dump_' + outname + '.csv'
            params4["mode"] = 'polar'
            glm_modifier.add_object("currdump", name, params4)


        #waiting for the add comment method to be added to the modify class
#        print('// solar inverter mode on this feeder', file=op)
        glm_modifier.model.define_lines.append('#define ' + glm_modifier.defaults.name_prefix + 'INVERTER_MODE=' + glm_modifier.defaults.solar_inv_mode)

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
                kvat = Find3PhaseXfmrKva(glm_modifier, seg_kva)
            else:
                kvat = Find1PhaseXfmrKva(glm_modifier, seg_kva)
            if 'S' in seg_phs:
                vnom = 120.0
                vsec = 120.0
            else:
                if 'N' not in seg_phs:
                    seg_phs += 'N'
                if kvat > glm_modifier.defaults.max208kva:
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

            model[t][o]['configuration'] = glm_modifier.defaults.name_prefix + key
            model[t][o]['phases'] = seg_phs
            if key not in xfused:
                xfused[key] = [seg_phs, kvat, vnom, vsec, install_type]

        for key in xfused:
            add_xfmr_config(glm_modifier, key, xfused[key][0], xfused[key][1], xfused[key][2], xfused[key][3],
                              xfused[key][4], vll, vln)

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
                model[t][o]['current_limit'] = str(FindFuseLimit(glm_modifier, amps))

        add_local_triplex_configurations(glm_modifier)
        add_config_class(glm_modifier, model, h, 'regulator_configuration')
        add_config_class(glm_modifier, model, h, 'overhead_line_conductor')
        add_config_class(glm_modifier, model, h, 'line_spacing')
        add_config_class(glm_modifier, model, h, 'line_configuration')
        add_config_class(glm_modifier, model, h, 'triplex_line_conductor')
        add_config_class(glm_modifier, model, h, 'triplex_line_configuration')
        add_config_class(glm_modifier, model, h, 'underground_line_conductor')

        add_link_class(glm_modifier, model, h, 'fuse', seg_loads)
        add_link_class(glm_modifier, model, h, 'switch', seg_loads)
        add_link_class(glm_modifier, model, h, 'recloser', seg_loads)
        add_link_class(glm_modifier, model, h, 'sectionalizer', seg_loads)

        add_link_class(glm_modifier, model, h, 'overhead_line', seg_loads)
        add_link_class(glm_modifier, model, h, 'underground_line', seg_loads)
        add_link_class(glm_modifier, model, h, 'series_reactor', seg_loads)

        add_link_class(glm_modifier, model, h, 'regulator', seg_loads, want_metrics=True)
        add_link_class(glm_modifier, model, h, 'transformer', seg_loads)
        add_link_class(glm_modifier, model, h, 'capacitor', seg_loads, want_metrics=True)

        if glm_modifier.defaults.forERCOT == "True":
            replace_commercial_loads(glm_modifier, model, h, 'load', 0.001 * avgcommercial)
            #            connect_ercot_commercial (op)
            identify_ercot_houses(glm_modifier, model, h, 'load', 0.001 * avghouse, rgn)

            #connect_ercot_houses(model, h, op, vln, 120.0)
            add_ercot_houses(glm_modifier, model, h, vln,120.0)

            for key in glm_modifier.defaults.house_nodes:
                add_houses(glm_modifier,key, 120.0)
            for key in glm_modifier.defaults.small_nodes:
                add_ercot_small_loads(glm_modifier, key, vln)
            for key in glm_modifier.defaults.comm_loads:
                add_commercial_loads(glm_modifier, rgn, key)
        else:
            replace_commercial_loads(model, h, 'load', 0.001 * avgcommercial)
            identify_xfmr_houses(model, h, 'transformer', seg_loads, 0.001 * avghouse, rgn)
            for key in glm_modifier.defaults.house_nodes:
                add_houses(glm_modifier, key, 120.0)
            for key in glm_modifier.defaults.small_nodes:
                add_small_loads(glm_modifier, key, 120.0)
            for key in glm_modifier.defaults.comm_loads:
                #add_commercial_loads(glm_modifier, rgn, key)
                bldg_definition = comm_FG.define_comm_loads(glm_modifier.defaults.comm_loads[key][1], glm_modifier.defaults.comm_loads[key][2],
                                                    glm_modifier.defaults.dso_type, glm_modifier.defaults.ashrae_zone, glm_modifier.defaults.comm_bldg_metadata)
                comm_FG.create_comm_zones(bldg_definition, glm_modifier.defaults.comm_loads, key, op, glm_modifier.defaults.batt_metadata,
                                  glm_modifier.defaults.storage_percentage, glm_modifier.defaults.ev_metadata, glm_modifier.defaults.ev_percentage,
                                  glm_modifier.defaults.solar_percentage, glm_modifier.defaults.pv_rating_MW, glm_modifier.defaults.solar_Q_player,
                                  glm_modifier.defaults.case_type, glm_modifier.defaults.metrics, glm_modifier.defaults.metrics_interval, None)

        add_voltage_class(glm_modifier, model, h, 'node', vln, vll, secnode)
        add_voltage_class(glm_modifier, model, h, 'meter', vln, vll, secnode)
        if glm_modifier.defaults.forERCOT == "False":
            add_voltage_class(glm_modifier, model, h, 'load', vln, vll, secnode)
        if len(glm_modifier.defaults.Eplus_Bus) > 0 and glm_modifier.defaults.Eplus_Volts > 0.0 and \
                glm_modifier.defaults.Eplus_kVA > 0.0:
            #Waiting for the add comment method to be added to the modify class
#            print('////////// EnergyPlus large-building load ///////////////', file=op)
            row = Find3PhaseXfmr(glm_modifier.defaults.Eplus_kVA)
            actual_kva = row[0]
            watts_per_phase = 1000.0 * actual_kva / 3.0
            Eplus_vln = glm_modifier.defaults.Eplus_Volts / math.sqrt(3.0)
            vstarta = format(Eplus_vln, '.2f') + '+0.0j'
            vstartb = format(-0.5 * Eplus_vln, '.2f') + format(-0.866025 * Eplus_vln, '.2f') + 'j'
            vstartc = format(-0.5 * Eplus_vln, '.2f') + '+' + format(0.866025 * Eplus_vln, '.2f') + 'j'


            params5 = dict()
            name = glm_modifier.defaults.name_prefix + 'Eplus_transformer_configuration'
            params5["connect_type"] = "WYE_WYE"
            params5["install_type"] = "PADMOUNT"
            params5["power_rating"] = str(actual_kva)
            params5["primary_voltage"] = str(vll)
            params5["secondary_voltage"] = format(glm_modifier.defaults.Eplus_Volts, '.1f')
            params5["resistance"] = format(row[1], '.5f')
            params5["reactance"] = format(row[2], '.5f')
            params5["shunt_resistance"] = format(1.0 / row[3], '.2f')
            params5["shunt_reactance"] = format(1.0 / row[4], '.2f')
            glm_modifier.add_object("transformer_configuration", name, params5)

            params6 = dict()
            name = glm_modifier.defaults.name_prefix + 'Eplus_transformer'
            params6["phases"] = "ABCN"
            params6["from"] = glm_modifier.defaults.name_prefix + glm_modifier.defaults.Eplus_Bus
            params6["to"] = glm_modifier.defaults.name_prefix + 'Eplus_meter'
            params6["configuration"] = glm_modifier.defaults.name_prefix + 'Eplus_transformer_configuration'
            glm_modifier.add_object("transformer", name, params6)


            params7 = dict()
            t_name = glm_modifier.defaults.name_prefix + 'Eplus_meter'
            params7["phases"] = "ABCN"
            params7["meter_power_consumption"] = "1+15j"
            params7["nominal_voltage"] = '{:.4f}'.format(Eplus_vln)
            params7["voltage_A"] = vstarta
            params7["voltage_B"] = vstartb
            params7["voltage_C"] = vstartc
            add_tariff(glm_modifier, params7)
            glm_modifier.add_object("meter", t_name, params7)



            if glm_modifier.defaults.metrics_interval > 0:
                params8 = dict()
                params8["parent"] = t_name
                params8["interval"] = str(glm_modifier.defaults.metrics_interval)
                glm_modifier.add_object("metrics_collector", "", params8)


            params9 = dict()
            name = glm_modifier.defaults.name_prefix + 'Eplus_load;'
            params9["parent"] = glm_modifier.defaults.name_prefix + 'Eplus_meter'
            params9["phases"] = "ABCN"
            params9["nominal_voltage"] = '{:.4f}'.format(Eplus_vln)
            params9["voltage_A"] = vstarta
            params9["voltage_B"] = vstartb
            params9["voltage_C"] = vstartc
            params9["constant_power_A"] = '{:.1f}'.format(watts_per_phase)
            params9["constant_power_B"] = '{:.1f}'.format(watts_per_phase)
            params9["constant_power_C"] = '{:.1f}'.format(watts_per_phase)
            glm_modifier.add_object("load", name, params9)

        print('cooling bins unused', glm_modifier.defaults.cooling_bins)
        print('heating bins unused', glm_modifier.defaults.heating_bins)
        print(glm_modifier.defaults.solar_count, 'pv totaling', '{:.1f}'.format(glm_modifier.defaults.solar_kw), 'kw with',
              glm_modifier.defaults.battery_count, 'batteries')

        op.close()

# ***************************************************************************************************
# ***************************************************************************************************

def add_node_houses(glm_modifier, node, region, xfkva, phs, nh=None, loadkw=None, house_avg_kw=None, secondary_ft=None,
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
    glm_modifier.defaults.house_nodes = {}
    if not random_seed:
        np.random.seed(0)
    bTriplex = False
    if 'S' in phs:
        bTriplex = True
    glm_modifier.defaults.storage_percentage = storage_fraction
    glm_modifier.defaults.solar_percentage = solar_fraction
    glm_modifier.defaults.electric_cooling_percentage = electric_cooling_fraction
    lg_v_sm = 0.0
    vnom = 120.0
    if node_metrics_interval is not None:
        glm_modifier.defaults.metrics_interval = node_metrics_interval
    else:
        glm_modifier.defaults.metrics_interval = 0
    if nh is not None:
        nhouse = nh
    else:
        nhouse = int((loadkw / house_avg_kw) + 0.5)
        if nhouse > 0:
            lg_v_sm = loadkw / house_avg_kw - nhouse  # >0 if we rounded down the number of houses
    bldg, ti = selectResidentialBuilding(glm_modifier.defaults.rgnThermalPct[region - 1],
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
        if (glm_modifier.defaults.solar_percentage > 0.0) or (glm_modifier.defaults.storage_percentage) > 0.0:
            if bTriplex:
                # waiting for the add comment method to be added to the modifier class
                #print('// inverter base voltage for volt-var functions, on triplex circuit', file=fp)
                glm_modifier.model.define_lines.append("#define INV_VBASE=240.0")
            else:
                # waiting for the add comment method to be added to the modifier class
                #print('// inverter base voltage for volt-var functions, on 208-V three-phase circuit', file=fp)
                glm_modifier.model.define_lines.append("#define INV_VBASE=208.0")

        params = dict()
        name = '{:s}_xfmr'.format(node)
        params["phases"] = '{:s};'.format(phs)
        params["from"] = '{:s}'.format(node)
        params["to"] = '{:s}'.format(xfmr_meter)
        params["configuration"] = '{:s}'.format(xfkey)
        glm_modifier.add_object("transformer", name, params)

        if secondary_ft is not None:
            params2 = dict()
            name = '{:s}'.format(xfmr_meter)
            params2["phases"] = '{:s}'.format(phs)
            params2["nominal_voltage"] = '{:.2f};'.format(vnom)
            glm_modifier.add_object('{:s} {{'.format(meter_class), name, params2)
            params3 = dict()
            name = '{:s}_secondary;'.format(node)
            params3["phases"] = '{:s};'.format(phs)
            params3["from"] = '{:s};'.format(xfmr_meter)
            params3["to"] = '{:s}_mtr'.format(node)
            params3["length"] = '{:.1f};'.format(secondary_ft)
            params3["configuration"] = '{:s}'.format(linekey)
            glm_modifier.add_object('{:s} {{'.format(line_class), name, params3)
        params4 = dict()
        name = '{:s}_mtr;'.format(node)
        params4["phases"] = '{:s};'.format(phs)
        params4["nominal_voltage"] = '{:.2f}'.format(vnom)
        add_tariff(glm_modifier, params4)
        glm_modifier.add_object('{:s} {{'.format(meter_class), name, params4)
        if glm_modifier.defaults.metrics_interval > 0:
            params5 = dict()
            params5["parent"] = name
            params5["interval"] = str(glm_modifier.defaults.metrics_interval)
        glm_modifier.add_object('{:s} {{'.format(meter_class), name, params5)
        # write all the houses on that meter
        glm_modifier.defaults.house_nodes[node] = [nhouse, region, lg_v_sm, phs, bldg, ti]
        add_houses(glm_modifier, node, vnom, bIgnoreThermostatSchedule=False, bWriteService=False, bTriplex=bTriplex,
                     setpoint_offset=1.0)
    else:
        print('// Zero houses at {:s} phases {:s}'.format(node, phs))
        #waiting for the add comment methods to be added to modifier class
        #print('// Zero houses at {:s} phases {:s}'.format(node, phs), file=fp)


# ***************************************************************************************************
# ***************************************************************************************************

def populate_feeder(glm_modifier, configfile=None, config=None, taxconfig=None, fgconfig=None, fg_recs_data=None):
    """Wrapper function that processes one feeder. One or two keyword arguments must be supplied.

    Args:
        configfile (str): JSON file name for the feeder population data, mutually exclusive with config
        config (dict): dictionary of feeder population data already read in, mutually exclusive with configfile
        taxconfig (dict): dictionary of custom taxonomy data for ERCOT processing
        targetdir (str): directory to receive the output files, defaults to ./CaseName
    """

    if configfile is not None:
        checkResidentialBuildingTable()
    # we want the same pseudo-random variables each time, for repeatability
    np.random.seed(0)

    if config is None:
        lp = open(configfile).read()
        config = json.loads(lp)

    rootname = config['BackboneFiles']['TaxonomyChoice']
    tespdir = os.path.expandvars(os.path.expanduser(config['SimulationConfig']['SourceDirectory']))
    glm_modifier.defaults.glmpath = tespdir + '/feeders/'
    glm_modifier.defaults.supportpath = ''  # tespdir + '/schedules'
    glm_modifier.defaults.weatherpath = ''  # tespdir + '/weather'
    if 'NamePrefix' in config['BackboneFiles']:
        glm_modifier.defaults.name_prefix = config['BackboneFiles']['NamePrefix']
    work_path = './' + config['SimulationConfig']['CaseName'] + '/'

    if 'WorkingDirectory' in config['SimulationConfig']:
        work_path = config['SimulationConfig']['WorkingDirectory'] + '/'

    if 'OutputPath' in config['SimulationConfig']:
        work_path = config['SimulationConfig']['OutputPath'] + '/'

    substation_name = config['SimulationConfig']['Substation']
    glm_modifier.defaults.timezone = config['SimulationConfig']['TimeZone']

    glm_modifier.defaults.starttime = config['SimulationConfig']['StartTime']
    glm_modifier.defaults.endtime = config['SimulationConfig']['EndTime']
    glm_modifier.defaults.port = config['SimulationConfig']['port']
    glm_modifier.defaults.timestep = int(config['FeederGenerator']['MinimumStep'])
    glm_modifier.defaults.metrics = config['FeederGenerator']['Metrics']
    glm_modifier.defaults.metrics_type = config['FeederGenerator']['MetricsType']
    glm_modifier.defaults.metrics_interval = int(config['FeederGenerator']['MetricsInterval'])
    glm_modifier.defaults.metrics_interim = int(config['FeederGenerator']['MetricsInterim'])
    # glm_modifier.defaults.electric_cooling_percentage = 0.01 * float(config['FeederGenerator']['ElectricCoolingPercentage'])
    # glm_modifier.defaults.water_heater_percentage = 0.01 * float(config['FeederGenerator']['WaterHeaterPercentage'])
    # glm_modifier.defaults.water_heater_participation = 0.01 * float(config['FeederGenerator']['WaterHeaterParticipation'])
    glm_modifier.defaults.solar_percentage = 0.01 * float(config['FeederGenerator']['SolarPercentage'])
    glm_modifier.defaults.storage_percentage = 0.01 * float(config['FeederGenerator']['StoragePercentage'])
    glm_modifier.defaults.ev_percentage = 0.01 * float(config['FeederGenerator']['EVPercentage'])
    glm_modifier.defaults.solar_inv_mode = config['FeederGenerator']['SolarInverterMode']
    glm_modifier.defaults.storage_inv_mode = config['FeederGenerator']['StorageInverterMode']
    glm_modifier.defaults.weather_file = config['WeatherPrep']['DataSource']
    glm_modifier.defaults.bill_mode = config['FeederGenerator']['BillingMode']
    glm_modifier.defaults.kwh_price = float(config['FeederGenerator']['Price'])
    glm_modifier.defaults.monthly_fee = float(config['FeederGenerator']['MonthlyFee'])
    glm_modifier.defaults.tier1_energy = float(config['FeederGenerator']['Tier1Energy'])
    glm_modifier.defaults.tier1_price = float(config['FeederGenerator']['Tier1Price'])
    glm_modifier.defaults.tier2_energy = float(config['FeederGenerator']['Tier2Energy'])
    glm_modifier.defaults.tier2_price = float(config['FeederGenerator']['Tier2Price'])
    glm_modifier.defaults.tier3_energy = float(config['FeederGenerator']['Tier3Energy'])
    glm_modifier.defaults.tier3_price = float(config['FeederGenerator']['Tier3Price'])
    glm_modifier.defaults.Eplus_Bus = config['EplusConfiguration']['EnergyPlusBus']
    glm_modifier.defaults.Eplus_Volts = float(config['EplusConfiguration']['EnergyPlusServiceV'])
    glm_modifier.defaults.Eplus_kVA = float(config['EplusConfiguration']['EnergyPlusXfmrKva'])
    glm_modifier.defaults.transmissionXfmrMVAbase = float(config['PYPOWERConfiguration']['TransformerBase'])
    glm_modifier.defaults.transmissionVoltage = 1000.0 * float(config['PYPOWERConfiguration']['TransmissionVoltage'])
    glm_modifier.defaults.weather_name = config['WeatherPrep']['Name']
    glm_modifier.defaults.latitude = float(config['WeatherPrep']['Latitude'])
    glm_modifier.defaults.longitude = float(config['WeatherPrep']['Longitude'])
    glm_modifier.defaults.time_zone_offset = float(config['WeatherPrep']['TimeZoneOffset'])
    glm_modifier.defaults.state = config['SimulationConfig']['state']
    glm_modifier.defaults.dso_type = config['SimulationConfig']['DSO_type']
    glm_modifier.defaults.income_level = config['SimulationConfig'][
        'income_level']  # Should be a list of income levels for the DSO being tested
    glm_modifier.defaults.gld_scaling_factor = config['SimulationConfig']['scaling_factor']
    glm_modifier.defaults.pv_rating_MW = config['SimulationConfig']['rooftop_pv_rating_MW']
    glm_modifier.defaults.res_bldg_metadata = config['BuildingPrep']['ResBldgMetaData']
    glm_modifier.defaults.batt_metadata = config['BuildingPrep']['BattMetaData']
    glm_modifier.defaults.ev_metadata = config['BuildingPrep']['EvModelMetaData']
    glm_modifier.defaults.driving_data_file = config['BuildingPrep']['EvDrivingDataFile']
    glm_modifier.defaults.ev_driving_metadata = process_nhts_data(
        config['BuildingPrep']['MetaDataPath'] + glm_modifier.defaults.driving_data_file)
    glm_modifier.defaults.ev_reserved_soc = config['AgentPrep']['EV']['EVReserveHi']
    glm_modifier.defaults.solar_path = config['BuildingPrep']['SolarDataPath']
    glm_modifier.defaults.solar_P_player = config['BuildingPrep']['SolarPPlayerFile']
    glm_modifier.defaults.solar_Q_player = config['BuildingPrep']['SolarQPlayerFile']
    glm_modifier.defaults.ashrae_zone = config['BuildingPrep']['ASHRAEZone']  # TODO: use this later
    glm_modifier.defaults.comm_bldg_metadata = config['BuildingPrep']['CommBldgMetaData']
    glm_modifier.defaults.comm_bldgs_pop = config['BuildingPrep']['CommBldgPopulation']
    glm_modifier.defaults.case_type = config['SimulationConfig']['caseType']

    # -------- create cop lookup table by vintage bin-----------
    # (Laurentiu MArinovici 11/18/2019) moving the cop_lookup inside this function as it requires
    # residential building metadata
    cop_mat = glm_modifier.defaults.driving_data_fileres_bldg_metadata['COP_average']
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
    glm_modifier.defaults.house_nodes = {}
    glm_modifier.defaults.small_nodes = {}
    glm_modifier.defaults.comm_loads = {}

    if taxconfig is not None:
        print('called with a custom taxonomy configuration')
        forERCOT = True

        if rootname in taxconfig['backbone_feeders']:
            taxrow = taxconfig['backbone_feeders'][rootname]
            vll = taxrow['vll']
            vln = taxrow['vln']
            avg_house = taxrow['avg_house']
            avg_comm = taxrow['avg_comm']
            glm_modifier.defaults.case_name = config['SimulationConfig']['CaseName']
            work_path = taxconfig['work_path']
            print('Driving data casename:', glm_modifier.defaults.driving_data_filecase_name, 'rootname:', rootname, 'VLL:', vll, 'VLN:', vln, 'House load:', avg_house, 'Commercial load:', avg_comm, 'Driving data feeders path', glm_modifier.defaults.driving_data_filefeeders_path, 'Default work path:', glm_modifier.defaults.work_path)
            ProcessTaxonomyFeeder(glm_modifier.defaults.case_name, rootname, vll, vln, avg_house, avg_comm)
        else:
            print(rootname, 'not found in taxconfig backbone_feeders')
    else:
        glm_modifier.defaults.forERCOT = config['SimulationConfig']['simplifiedFeeders']
        print('using the built-in taxonomy')
        print(rootname, 'to', work_path, 'using', glm_modifier.defaults.weather_file)
        print('times', glm_modifier.model.module_entities['clock'].starttime.value, glm_modifier.model.module_entities['clock'].stoptime.value)
        print('steps', glm_modifier.defaults.timestep, glm_modifier.defaults.metrics_interval)
        # print('hvac', electric_cooling_percentage)
        print('pv', glm_modifier.defaults.solar_percentage, glm_modifier.defaults.solar_inv_mode)
        print('storage', glm_modifier.defaults.storage_percentage, glm_modifier.defaults.storage_inv_mode)
        print('billing', glm_modifier.defaults.kwh_price, glm_modifier.defaults.monthly_fee)
        for c in glm_modifier.defaults.taxchoice:
            if c[0] in rootname:
                glm_modifier.defaults.case_name = config['SimulationConfig']['CaseName']
                ProcessTaxonomyFeeder(glm_modifier.defaults.case_name, rootname, c[1], c[2], c[3], c[4])


#                quit()

# ***************************************************************************************************
# ***************************************************************************************************

def populate_all_feeders(glm_modifier, outpath):
    """Wrapper function that batch processes all taxonomy feeders in the 
    casefiles table (see source file)
    """
    print('Root Name, VLL, VLN, Avg House, Avg Commercial:')
    print(glm_modifier.defaults.casefiles)
    fg_recs_dataset = None
    if glm_modifier.defaults.use_recs_data == "true":
        fg_recs_dataset = recs.recs_data_set(glm_modifier.defaults.recs_data_file)
    if sys.platform == 'win32':
        batname = 'run_all.bat'
    else:
        batname = 'run_all.sh'
    op = open(outpath + batname, 'w')
    file_name_string = glm_modifier.defaults.casefiles[0][0]
    print(file_name_string)
    print('gridlabd -D WANT_VI_DUMP=1 -D METRICS_FILE=' + file_name_string + '.json', file_name_string + '.glm', file=op)
    op.close()
    outname = glm_modifier.defaults.casefiles[0][0]
    glm_modifier.defaults.work_path = outpath
    ProcessTaxonomyFeeder(glm_modifier,outname,glm_modifier.defaults.casefiles[0][0],
                          glm_modifier.defaults.casefiles[0][1],
                          glm_modifier.defaults.casefiles[0][2],
                          glm_modifier.defaults.casefiles[0][3],
                          glm_modifier.defaults.casefiles[0][4], fg_recs_dataset)

# ***************************************************************************************************
# ***************************************************************************************************
# def selectRECSBuildingTypeVintage(rcs_dataset, state, income_lvl, pop_density):
#     type_df, vint_df = rcs_dataset.get_house_type_vintage("Washington","Low","U" )
#     tdt, tdv = rcs_dataset.sample_type_vintage(type_df, vint_df)
#     return tdt, tdv

if __name__ == "__main__":
    test_modifier = initialize_glm_modifier("../../../../data/feeders/R1-12.47-1.glm")
    populate_all_feeders(test_modifier, "../../../../data/feeders/R1-12.47-1.glm")
    test_modifier.write_model("test.glm")





