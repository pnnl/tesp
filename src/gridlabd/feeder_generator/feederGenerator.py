import sys;
import re;
import os.path;
import networkx as nx;
import numpy as np;
from math import sqrt; 

# we want the same pseudo-random variables each time, for repeatability
np.random.seed (0)

glmpath = 'Input_feeders/'
outpath = './'

max208kva = 100.0
xfmrMargin = 1.20
fuseMargin = 2.50

starttime = '2013-07-01 00:00:00'
endtime = '2013-07-03 00:00:00'
timestep = 15
metrics_interval = 300
use_fncs = True
use_houses = True
use_Eplus = True
Eplus_Bus = ''
Eplus_Volts = 480.0
Eplus_kVA = 150.0
electric_cooling_penetration = 0.9
electric_cooling_participation = 0.8
solar_penetration = 0.0
storage_penetration = 0.0
solar_inv_mode = 'CONSTANT_PF'
storage_inv_mode = 'LOAD_FOLLOWING'
weather_file = 'AZ-Tucson_International_Ap.tmy3'

rgnName = ['West Coast', 'North Central/Northeast', 'Southwest', 'Southeast Central', 'Southeast Coast']
rgnTimeZone = ['PST+8PDT', 'EST+5EDT', 'MST+7MDT', 'CST+6CDT', 'EST+5EDT']
rgnWeather = ['CA-San_francisco','OH-Cleveland','AZ-Phoenix','TN-Nashville','FL-Miami']
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
rgnThermalPct = [[[0.0805,0.0724,0.1090,0.0867,0.1384,0.1264,0.1297],  # Region 1, SF
                  [0.0356,0.1223,0.0256,0.0000,0.0000,0.0000,0.0000],  #           Apt
                  [0.0000,0.0554,0.0181,0.0000,0.0000,0.0000,0.0000]], #           MH
                 [[0.1574,0.0702,0.1290,0.0971,0.0941,0.0744,0.1532],
                  [0.0481,0.0887,0.0303,0.0000,0.0000,0.0000,0.0000],
                  [0.0000,0.0372,0.0202,0.0000,0.0000,0.0000,0.0000]],
                 [[0.0448,0.0252,0.0883,0.0843,0.1185,0.1315,0.2411],
                  [0.0198,0.1159,0.0478,0.0000,0.0000,0.0000,0.0000],
                  [0.0000,0.0524,0.0302,0.0000,0.0000,0.0000,0.0000]],
                 [[0.0526,0.0337,0.0806,0.0827,0.1081,0.1249,0.2539],
                  [0.0217,0.1091,0.0502,0.0000,0.0000,0.0000,0.0000],
                  [0.0000,0.0491,0.0333,0.0000,0.0000,0.0000,0.0000]],
                 [[0.0526,0.0337,0.0806,0.0827,0.1081,0.1249,0.2539],
                  [0.0217,0.1091,0.0502,0.0000,0.0000,0.0000,0.0000],
                  [0.0000,0.0491,0.0333,0.0000,0.0000,0.0000,0.0000]]]

rgnFloorArea = [[2209,820,1054], # single family, apartment, mobile home
                [2951,798,1035],
                [2370,764,1093],
                [2655,901,1069],
                [2655,901,1069]]

rgnOneStory = [0.6887,0.5210,0.7745,0.7043,0.7043]

rgnPenGasHeat =  [0.7051,0.8927,0.6723,0.4425,0.4425]
rgnPenHeatPump = [0.0321,0.0177,0.0559,0.1983,0.1983]
rgnPenResHeat =  [0.2628,0.0896,0.2718,0.3592,0.3592]
rgnPenElecCool = [0.4348,0.7528,0.5259,0.9673,0.9673]
rgnOversizeFactor = [0.1,0.2,0.2,0.3,0.3]

# index 0 is region (minus one)
# index 1 is SF, Apt, MH
# index 2 is Nighttime Ratio, NightTimeAvgDiff,HighBinValue,LowBinValue
rgnCoolingSetpoint = [[[0.098,0.96,69,65],  # Region 1, SF
                       [0.155,0.49,69,65],  #           Apt
                       [0.138,0.97,69,65]], #           MH
                      [[0.140,0.96,70,70],
                       [0.207,0.49,70,70],
                       [0.172,0.97,70,70]],
                      [[0.166,0.96,73,71],
                       [0.103,0.49,73,71],
                       [0.172,0.97,73,71]],
                      [[0.306,0.96,76,74],
                       [0.310,0.49,76,74],
                       [0.276,0.97,76,74]],
                      [[0.206,0.96,79,77],
                       [0.155,0.49,79,77],
                       [0.138,0.97,79,77]]]

rgnHeatingSetpoint = [[[0.141,0.80,63,59],  # Region 1, SF
                       [0.085,0.20,63,59],  #           Apt
                       [0.129,0.88,63,59]], #           MH
                      [[0.204,0.80,66,64],
                       [0.132,0.20,66,64],
                       [0.177,0.88,66,64]],
                      [[0.231,0.80,69,67],
                       [0.147,0.20,69,67],
                       [0.161,0.88,69,67]],
                      [[0.163,0.80,70,70],
                       [0.279,0.20,70,70],
                       [0.274,0.88,70,70]],
                      [[0.120,0.80,73,71],
                       [0.109,0.20,73,71],
                       [0.081,0.88,73,71]]]

rgnPenPoolPump = [0.0904,0.0591,0.0818,0.0657,0.0657]

rgnPenElecWH = [0.7455,0.7485,0.6520,0.3572,0.3572]
# index 0 is the region (minus one)
# index 0 is <=30 gal, 31-49 gal, >= 50gal
rgnWHSize = [[0.0000,0.3333,0.6667],
             [0.1459,0.5836,0.2706],
             [0.2072,0.5135,0.2793],
             [0.2259,0.5267,0.2475],
             [0.2259,0.5267,0.2475]]

coolingScheduleNumber = 8
heatingScheduleNumber = 6
waterHeaterScheduleNumber = 6

# Index 0 is the level (minus one)
# Rceiling, Rwall, Rfloor, WindowLayers, WindowGlass,Glazing,WindowFrame,Rdoor,AirInfil,COPhi,COPlo
singleFamilyProperties = [[16.0, 10.0, 10.0, 1, 1, 1, 1,   3,  .75, 2.8, 2.4],
                          [19.0, 11.0, 12.0, 2, 1, 1, 1,   3,  .75, 3.0, 2.5],
                          [19.0, 14.0, 16.0, 2, 1, 1, 1,   3,   .5, 3.2, 2.6],
                          [30.0, 17.0, 19.0, 2, 1, 1, 2,   3,   .5, 3.4, 2.8],
                          [34.0, 19.0, 20.0, 2, 1, 1, 2,   3,   .5, 3.6, 3.0],
                          [36.0, 22.0, 22.0, 2, 2, 1, 2,   5, 0.25, 3.8, 3.0],
                          [48.0, 28.0, 30.0, 3, 2, 2, 4,  11, 0.25, 4.0, 3.0]]

apartmentProperties = [[13.4, 11.7,  9.4, 1, 1, 1, 1, 2.2, .75, 2.8,  1.9],
                       [20.3, 11.7, 12.7, 2, 1, 2, 2, 2.7, 0.25, 3.0, 2.0],
                       [28.7, 14.3, 12.7, 2, 2, 3, 4, 6.3, .125, 3.2, 2.1]]

mobileHomeproperties = [[   0,    0,    0, 0, 0, 0, 0,   0,   0,   0,   0],
                        [13.4,  9.2, 11.7, 1, 1, 1, 1, 2.2, .75, 2.8, 1.9],
                        [24.1, 11.7, 18.1, 2, 2, 1, 2,   3, .75, 3.5, 2.2]]

# kva, %r, %x, %nll, %imag
three_phase = [[30,1.90,1.77,0.79,4.43],
               [45,1.75,2.12,0.70,3.94],
               [75,1.60,2.42,0.63,3.24],
               [112.5,1.45,2.85,0.59,2.99],
               [150,1.30,3.25,0.54,2.75],
               [225,1.30,3.52,0.50,2.50],
               [300,1.30,4.83,0.46,2.25],
               [500,1.10,4.88,0.45,2.26],
               [750,0.97,5.11,0.44,1.89],
               [1000,0.85,5.69,0.43,1.65],
               [1500,0.78,5.70,0.39,1.51],
               [2000,0.72,5.70,0.36,1.39],
               [2500,0.70,5.71,0.35,1.36],
               [3750,0.62,5.72,0.31,1.20],
               [5000,0.55,5.72,0.28,1.07],
               [7500,0.55,5.72,0.28,1.07],
               [10000,0.55,5.72,0.28,1.07]]

# kva, %r, %x, %nll, %imag
single_phase = [[5,2.10,1.53,0.90,3.38],
                [10,1.90,1.30,0.68,2.92],
                [15,1.70,1.47,0.60,2.53],
                [25,1.60,1.51,0.52,1.93],
                [37.5,1.45,1.65,0.47,1.74],
                [50,1.30,1.77,0.45,1.54],
                [75,1.25,1.69,0.42,1.49],
                [100,1.20,2.19,0.40,1.45],
                [167,1.15,2.77,0.38,1.66],
                [250,1.10,3.85,0.36,1.81],
                [333,1.00,4.90,0.34,1.97],
                [500,1.00,4.90,0.29,1.98]]

def parse_kva(arg):
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

    return sqrt (p*p + q*q)

# leave off intermediate fuse sizes 8, 12, 20, 30, 50, 80, 140
# leave off 6, 10, 15, 25 from the smallest sizes, too easily blown
standard_fuses = [40, 65, 100, 200]
standard_reclosers = [280, 400, 560, 630, 800]
standard_breakers = [600, 1200, 2000]

def FindFuseLimit (amps):
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
    kva *= xfmrMargin
    for row in single_phase:
        if row[0] >= kva:
            return row[0]
    return 0.0

def Find3PhaseXfmrKva (kva):
    kva *= xfmrMargin
    for row in three_phase:
        if row[0] >= kva:
            return row[0]
    return 0.0

def Find1PhaseXfmr (kva):
    for row in single_phase:
        if row[0] >= kva:
            return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
    return 0,0,0,0,0

def Find3PhaseXfmr (kva):
    for row in three_phase:
        if row[0] >= kva:
            return row[0], 0.01 * row[1], 0.01 * row[2], 0.01 * row[3], 0.01 * row[4]
    return 0,0,0,0,0

# Root Name, VLL, VLN, Avg House, Avg Commercial
#casefiles = [['R1-12.47-1',12470.0, 7200.0, 4000.0, 20000.0],
#             ['R1-12.47-2',12470.0, 7200.0, 4500.0, 30000.0],
#             ['R1-12.47-3',12470.0, 7200.0, 8000.0, 15000.0],
#             ['R1-12.47-4',12470.0, 7200.0, 4000.0, 15000.0],
#             ['R1-25.00-1',24900.0,14400.0, 6000.0, 25000.0],
#             ['R2-12.47-1',12470.0, 7200.0, 7000.0, 20000.0],
#             ['R2-12.47-2',12470.0, 7200.0,15000.0, 25000.0],
#             ['R2-12.47-3',12470.0, 7200.0, 5000.0, 30000.0],
#             ['R2-25.00-1',24900.0,14400.0, 6000.0, 15000.0],
#             ['R2-35.00-1',34500.0,19920.0,15000.0, 30000.0],
#             ['R3-12.47-1',12470.0, 7200.0,12000.0, 40000.0],
#             ['R3-12.47-2',12470.0, 7200.0,14000.0, 30000.0],
#             ['R3-12.47-3',12470.0, 7200.0, 7000.0, 15000.0],
#             ['R4-12.47-1',13800.0, 7970.0, 9000.0, 30000.0],
#             ['R4-12.47-2',12470.0, 7200.0, 6000.0, 20000.0],
#             ['R4-25.00-1',24900.0,14400.0, 6000.0, 20000.0],
#             ['R5-12.47-1',13800.0, 7970.0, 6500.0, 20000.0],
#             ['R5-12.47-2',12470.0, 7200.0, 4500.0, 15000.0],
#             ['R5-12.47-3',13800.0, 7970.0, 4000.0, 15000.0],
#             ['R5-12.47-4',12470.0, 7200.0, 6000.0, 30000.0],
#             ['R5-12.47-5',12470.0, 7200.0, 4500.0, 25000.0],
#             ['R5-25.00-1',22900.0,13200.0, 3000.0, 20000.0],
#             ['R5-35.00-1',34500.0,19920.0, 6000.0, 25000.0],
#             ['GC-12.47-1',12470.0, 7200.0, 8000.0, 13000.0]]
#casefiles = [['new_R2-12.47-2',12470.0, 7200.0,15000.0, 25000.0]]
casefiles = [['new_R1-12.47-1',12470.0, 7200.0, 4000.0, 20000.0]]

def is_node_class(s):
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
    '''
    Store an object in the model structure
    Inputs:
        parent: name of parent object (used for nested object defs)
        model: dictionary model structure
        line: glm line containing the object definition
        itr: iterator over the list of lines
        oidh: hash of object id's to object names
        octr: object counter
    '''
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
                oname = val
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
                    print ('  ' + p + ' ' + model[t][o][p] + ';', file=op)
            print('}', file=op)

# name, r, gmr, ampacity
triplex_conductors = [['triplex_4/0_aa', 0.48, 0.0158, 1000.0]]

# name, hot, neutral, thickness, diameter
triplex_configurations = [['tpx_config', 'triplex_4/0_aa', 'triplex_4/0_aa', 0.08, 0.522]]

def write_local_triplex_configurations (op):
  for row in triplex_conductors:
    print ('object triplex_line_conductor {', file=op)
    print (' name', row[0] + ';', file=op)
    print (' resistance', str(row[1]) + ';', file=op)
    print (' geometric_mean_radius', str(row[2]) + ';', file=op)
    print (' rating.summer.continuous', str(row[3]) + ';', file=op)
    print (' rating.summer.emergency', str(row[3]) + ';', file=op)
    print (' rating.winter.continuous', str(row[3]) + ';', file=op)
    print (' rating.winter.emergency', str(row[3]) + ';', file=op)
    print ('}', file=op)
  for row in triplex_configurations:
    print ('object triplex_line_configuration {', file=op)
    print (' name', row[0] + ';', file=op)
    print (' conductor_1', row[1] + ';', file=op)
    print (' conductor_2', row[1] + ';', file=op)
    print (' conductor_N', row[2] + ';', file=op)
    print (' insulation_thickness', str(row[3]) + ';', file=op)
    print (' diameter', str(row[4]) + ';', file=op)
    print ('}', file=op)

house_nodes = {}

def identify_houses (model, h, t, avgHouse, rgn):
    print ('Average House', avgHouse)
    total_houses = 0
    if t in model:
        for o in model[t]:
            if 'power_12' in model[t][o]:
                tkva = parse_kva (model[t][o]['power_12'])
                nhouse = int ((tkva / avgHouse) + 0.5)
                name = o
                if nhouse <= 0:
                    print (name, tkva, 'too small for a house')
                else:
                    total_houses += nhouse
                    house_nodes[name] = [nhouse,rgn]
    print (total_houses, 'houses at', len(house_nodes), 'nodes')

def write_houses(basename, op, phs, vnom, vstart):
    nhouse = int(house_nodes[basename][0])
    rgn = int(house_nodes[basename][0])
    for i in range(nhouse):
        tpxname = basename + '_tpx_' + str(i+1)
        mtrname = basename + '_mtr_' + str(i+1)
        hsename = basename + '_hse_' + str(i+1)
        print ('object triplex_line {', file=op)
        print ('  name', tpxname + ';', file=op)
        print ('  from', basename + ';', file=op)
        print ('  to', mtrname + ';', file=op)
        print ('  phases', phs + ';', file=op)
        print ('  length 30;', file=op)
        print ('  configuration', triplex_configurations[0][0] + ';', file=op)
        print ('}', file=op)
        print ('object triplex_meter {', file=op)
        print ('  name', mtrname + ';', file=op)
        print ('  phases', phs + ';', file=op)
        print ('  nominal_voltage ' + str(vnom) + ';', file=op)
        print ('  voltage_1 ' + vstart + ';', file=op)
        print ('  voltage_2 ' + vstart + ';', file=op)
        print ('}', file=op)
        print ('object house {', file=op)
        print ('  name', hsename + ';', file=op)
        print ('  parent', mtrname + ';', file=op)
        print ('  object ZIPload { // responsive', file=op)
        print ('    heatgain_fraction 0.9;', file=op)
        print ('  };', file=op)
        print ('  object ZIPload { // unresponsive', file=op)
        print ('    heatgain_fraction 0.9;', file=op)
        print ('  };', file=op)
        if np.random.uniform (0, 1) >= 0.1:
          print ('  object waterheater {', file=op)
          print ('    object metrics_collector {', file=op)
          print ('      interval', str(metrics_interval) + ';', file=op)
          print ('    };', file=op)
          print ('  };', file=op)
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
def write_voltage_class (model, h, t, op, vprim, secmtrnode):
    if t in model:
        for o in model[t]:
            name = o # model[t][o]['name']
            phs = model[t][o]['phases']
            vnom = vprim
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
            if str.find(phs,'S') >= 0:
                bHaveS = True
            else:
                bHaveS = False
            if bHaveS == True and bHadS == False:
                prefix = 'triplex_'
            vstarta = str(vnom) + '+0.0j'
            vstartb = format(-0.5*vnom,'.2f') + format(-0.866025*vnom,'.2f') + 'j'
            vstartc = format(-0.5*vnom,'.2f') + '+' + format(0.866025*vnom,'.2f') + 'j'
            if name in house_nodes:
                if 'A' in phs:
                    vstart = vstarta
                elif 'B' in phs:
                    vstart = vstartb
                else:
                    vstart = vstartc
                write_houses (name, op, phs, vnom, vstart)
            print('object ' + prefix + t + ' {', file=op)
            if len(parent) > 0:
                print('  parent ' + parent + ';', file=op)
            print('  name ' + name + ';', file=op)
            if 'bustype' in model[t][o]:
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
            print('}', file=op)

def write_xfmr_config (key, phs, kvat, vnom, vsec, install_type, vprimll, vprimln, op):
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
    for t in model:
        print(t+':')
        for o in model[t]:
            print('\t'+o+':')
            for p in model[t][o]:
                if ':' in model[t][o][p]:
                    print('\t\t'+p+'\t-->\t'+h[model[t][o][p]])
                else:
                    print('\t\t'+p+'\t-->\t'+model[t][o][p])

def parse_kva(cplx):
    toks = re.split('[\+j]',cplx)
    p = float(toks[0])
    q = float(toks[1])
    return 0.001 * sqrt(p*p + q*q)

def accumulate_load_kva(data):
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

if sys.platform == 'win32':
    batname = 'run_all.bat'
else:
    batname = 'run_all.sh'
op = open (batname, 'w')
for c in casefiles:
    print ('gridlabd -D WANT_VI_DUMP=1', c[0] + '.glm', file=op)
op.close()

for c in casefiles:
    fname = glmpath + c[0] + '.glm'
    print (fname)
    rgn = 0
    if 'R1' in c[0]:
        rgn = 1
    elif 'R2' in c[0]:
        rgn = 2
    elif 'R3' in c[0]:
        rgn = 3
    elif 'R4' in c[0]:
        rgn = 4
    elif 'R5' in c[0]:
        rgn = 5
    print ('region', rgn)
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

        op = open (outpath + c[0] + '.glm', 'w')
        octr = 0;
        model = {}
        h = {}		# OID hash
        itr = iter(lines)
        for line in itr:
            if re.search('object',line):
                line,octr = obj(None,model,line,itr,h,octr)
            else:
                print (line, file=op)

#        log_model (model, h)

        # construct a graph of the model, starting with known links
        G = nx.Graph()
        for t in model:
            if is_edge_class(t):
                for o in model[t]:
                    n1 = model[t][o]['from']
                    n2 = model[t][o]['to']
                    G.add_edge(n1,n2,eclass=t,ename=o,edata=model[t][o])

        # add the parent-child node links
        for t in model:
            if is_node_class(t):
                for o in model[t]:
                    if 'parent' in model[t][o]:
                        p = model[t][o]['parent']
                        G.add_edge(o,p,eclass='parent',ename=o,edata={})

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

        sub_graphs = nx.connected_component_subgraphs(G)
        seg_loads = {} # [name][kva, phases]
        total_kva = 0.0
#       for sg in sub_graphs:
#           print (sg.number_of_nodes())
#           if sg.number_of_nodes() < 10:
#               print(sg.nodes)
#               print(sg.edges)
        for n1, data in G.nodes(data=True):
            if 'ndata' in data:
                kva = accumulate_load_kva (data['ndata'])
                if kva > 0:
                    total_kva += kva
                    nodes = nx.shortest_path(G, n1, swing_node)
                    edges = zip(nodes[0:], nodes[1:])
#                    print (n1, '{:.2f}'.format(kva), 'kva on', data['ndata']['phases'])
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
#        for row in seg_loads:
#            print (' ', row, '{:.2f}'.format(seg_loads[row][0]), seg_loads[row][1])

# write the optional volt_dump and curr_dump for validation
        print ('#ifdef WANT_VI_DUMP', file=op)
        print ('object voltdump {', file=op)
        print ('  filename Voltage_Dump_' + c[0] + '.csv;', file=op)
        print ('  mode polar;', file=op)
        print ('}', file=op)
        print ('object currdump {', file=op)
        print ('  filename Current_Dump_' + c[0] + '.csv;', file=op)
        print ('  mode polar;', file=op)
        print ('}', file=op)
        print ('#endif', file=op)

# NEW STRATEGY - loop through transformer instances and assign a standard size based on the downstream load
#              - change the referenced transformer_configuration attributes
#              - write the standard transformer_configuration instances we actually need
        xfused = {} # ID, phases, total kva, vnom (LN), vsec, poletop/padmount
        secnode = {} # Node, st, phases, vnom                                                                  
        t = 'transformer'
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

            secnode[model[t][o]['to']] = [kvat, seg_phs, vnom]

            old_key = h[model[t][o]['configuration']]
            install_type = model['transformer_configuration'][old_key]['install_type']

            raw_key = 'XF' + str(nphs) + '_' + install_type + '_' + seg_phs + '_' + str(kvat)
            key = raw_key.replace('.', 'p')

            model[t][o]['configuration'] = key
            model[t][o]['phases'] = seg_phs
            if key not in xfused:
                xfused[key] = [seg_phs, kvat, vnom, vsec, install_type]

        for key in xfused:
#            print(key, xfused[key][0], xfused[key][1], xfused[key][2], xfused[key][3], xfused[key][4])
            write_xfmr_config (key, xfused[key][0], xfused[key][1], xfused[key][2], xfused[key][3], 
                               xfused[key][4], c[1], c[2], op)

        t = 'capacitor'
        if t in model:
            for o in model[t]:
                model[t][o]['nominal_voltage'] = str(int(c[2]))
                model[t][o]['cap_nominal_voltage'] = str(int(c[2]))

        t = 'fuse'
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
                    amps = 1000.0 * seg_kva / sqrt(3.0) / c[1]
                elif nphs == 2:
                    amps = 1000.0 * seg_kva / 2.0 / c[2]
                else:
                    amps = 1000.0 * seg_kva / c[2]
                model[t][o]['current_limit'] = str (FindFuseLimit (amps))

        write_local_triplex_configurations (op)

        write_config_class (model, h, 'regulator_configuration', op)
        write_config_class (model, h, 'overhead_line_conductor', op)
        write_config_class (model, h, 'line_spacing', op)
        write_config_class (model, h, 'line_configuration', op)
        write_config_class (model, h, 'triplex_line_conductor', op)
        write_config_class (model, h, 'triplex_line_configuration', op)
        write_config_class (model, h, 'underground_line_conductor', op)

        write_link_class (model, h, 'fuse', seg_loads, op)
        write_link_class (model, h, 'switch', seg_loads, op)
        write_link_class (model, h, 'recloser', seg_loads, op)
        write_link_class (model, h, 'sectionalizer', seg_loads, op)

        write_link_class (model, h, 'overhead_line', seg_loads, op)
        write_link_class (model, h, 'underground_line', seg_loads, op)
        write_link_class (model, h, 'triplex_line', seg_loads, op)
        write_link_class (model, h, 'series_reactor', seg_loads, op)

        write_link_class (model, h, 'regulator', seg_loads, op)
        write_link_class (model, h, 'transformer', seg_loads, op)
        write_link_class (model, h, 'capacitor', seg_loads, op)

        identify_houses (model, h, 'triplex_node', 0.001 * c[3], rgn)

        write_voltage_class (model, h, 'node', op, c[2], secnode)
        write_voltage_class (model, h, 'meter', op, c[2], secnode)
        write_voltage_class (model, h, 'load', op, c[2], secnode)
        write_voltage_class (model, h, 'triplex_node', op, c[2], secnode)
        write_voltage_class (model, h, 'triplex_meter', op, c[2], secnode)
        write_voltage_class (model, h, 'triplex_load', op, c[2], secnode)

        op.close()



