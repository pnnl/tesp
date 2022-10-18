# Copyright (C) 2019 Battelle Memorial Institute
# file: case_merge.py
"""Combines GridLAB-D and agent files to run a multi-feeder TESP simulation

Public Functions:
    :merge_glm: combines GridLAB-D input files
    :merge_glm_dict: combines GridLAB-D metadata files
    :merge_agent_dict: combines the substation agent configuration files
    :merge_substation_yaml: combines the substation agent FNCS publish/subscribe files
    :merge_fncs_config: combines GridLAB-D FNCS publish/subscribe files
"""
import sys
import json
import tesp_support.helpers as helpers
from os import path

# import colorama

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'

def merge_glm(target, sources, xfmva):
    """Combines GridLAB-D input files into "target". The source files must already exist.

    Args:
        target (str): the path to the target GLM file, including the name of the file
        sources (list): list of feeder names in the target directory to merge
    """
    print ('combining', sources, 'glm files into', target)
    workdir = path.split(path.dirname(target))[0]
    op = open (target, 'w')
    inFirstFile = True
    firstHeadNode = ''
    finishedFirstSubstation = False
# configuration, spacing and conductor names are not unique between feeders
    for fdr in sources:
        with open (workdir + '/' + fdr + '/' + fdr + '.glm') as ip:
            numEndif = 0
            inSubstation = False
            inConfig = False
            thisHeadNode = ''
            for line in ip:
                if numEndif >= 1 or inFirstFile == True:
                    canWrite = True
                    if 'filename Voltage_Dump' in line:
                        line = '  filename Voltage_Dump_' + path.splitext(path.basename(target))[0] + '.csv;'
                    if 'filename Current_Dump' in line:
                        line = '  filename Current_Dump_' + path.splitext(path.basename(target))[0] + '.csv;'
                    if ('object ' in line) and (('configuration' in line) or ('conductor' in line) or ('spacing' in line)):
                        inConfig = True
                    if (inConfig == True) and (inSubstation == False):
                        if ' name ' in line:
                            toks = line.split()
                            name = toks[1][:-1]
                            line = '  name ' + fdr + '_' + name + ';'
                            inConfig = False
                    if inSubstation == False:
                        if (' spacing ' in line) or (' configuration ') in line or \
                            ('  conductor_1' in line) or ('  conductor_2' in line) or \
                            ('  conductor_A' in line) or ('  conductor_B' in line) or \
                            ('  conductor_C' in line) or ('  conductor_N' in line):
                            toks = line.split()
                            name = toks[1][:-1]
                            line = '  ' + toks[0] + ' ' + fdr + '_' + name + ';'
                    if '#ifdef USE_FNCS' in line:
                        inSubstation = True
                        helics_flag = bool(False)
                    if '#ifdef USE_HELICS' in line:
                        inSubstation = True
                        helics_flag = bool(True)
                    if inSubstation == True: 
                        if ' configure ' in line:
                            if helics_flag:
                                line = '  configure ' + path.splitext(path.basename(target))[0] + '_HELICS_Config.json;'
                            else:
                                line = '  configure ' + path.splitext(path.basename(target))[0] + '_FNCS_Config.txt;'
                        elif ' power_rating ' in line:
                            line = '  power_rating {:.2f};'.format (xfmva * 1e3)
                        elif ' base_power ' in line:
                            line = '  base_power {:.2f};'.format (xfmva * 1e6)
                        elif ' to ' in line:
                            toks = line.split()
                            thisHeadNode = toks[1][:-1]
                            if len(firstHeadNode) < 1:
                                firstHeadNode = thisHeadNode
                    if (inSubstation == True) and ('object node' in line):
                        inSubstation = False
                        inConfig = False
                        if finishedFirstSubstation == True:
                            print ('object switch {', file=op)
                            print ('  name tie_' + fdr + ';', file=op)
                            print ('  phases ABCN;', file=op)
                            print ('  from ' + firstHeadNode + ';', file=op)
                            print ('  to ' + thisHeadNode + ';', file=op)
                            print ('  status CLOSED;', file=op)
                            print ('}', file=op)
                        finishedFirstSubstation = True
                    if (inSubstation == True) and (finishedFirstSubstation == True):
                        canWrite = False
                    if canWrite == True:
                        print (line.rstrip(), file=op)
                if '#endif' in line:
                    numEndif += 1
        inFirstFile = False 
    op.close()

def merge_glm_dict(target, sources, xfmva):
    """Combines GridLAB-D metadata files into "target". The source files must already exist.

    The output JSON won't have a top-level base_feeder attribute. Instead,
    the base_feeder from each source file will become a feeder key in the
    output JSON feeders dictionary, and then every child object on that feeder 
    will have its feeder_id, originally network_node, changed to match the base_feeder.

    Args:
        target (str): the path to the target JSON file, including the name of the file
        sources (list): list of feeder names in the target directory to merge
    """
    print ('combining', sources, 'GridLAB-D json files into', target)
    dict = {'bulkpower_bus' : 'TBD', \
            'FNCS' : '', \
            'HELICS': '', \
            'transformer_MVA' : xfmva, \
            'feeders' : {}, \
            'billingmeters' : {}, \
            'houses' : {}, \
            'inverters' : {}, \
            'capacitors' : {}, \
            'regulators' : {}, \
            'climate': {}}
    workdir = path.split(path.dirname(target))[0]
    for fdr in sources:
        lp = open (path.dirname(target) + '/' + fdr + '_glm_dict.json').read()
        cfg = json.loads(lp)
        fdr_id = helpers.gld_strict_name (cfg['base_feeder'])
        if sources.index(fdr) == 0:
            dict['bulkpower_bus'] = cfg['bulkpower_bus']
            dict['FNCS'] = cfg['FNCS']
            dict['HELICS'] = cfg['HELICS']
            dict['climate'] = cfg['climate']
        dict['feeders'][fdr_id] = {'house_count':cfg['feeders']['network_node']['house_count'], \
                                   'inverter_count':cfg['feeders']['network_node']['inverter_count']}
        for key in ['billingmeters', 'houses', 'inverters', 'capacitors', 'regulators']:
            for obj in cfg[key]:
                if 'feeder_id' in cfg[key][obj]:
                    cfg[key][obj]['feeder_id'] = fdr_id
            #for x in cfg[key].keys():
            #    if x in dict[key].keys():
            #        print(colorama.Fore.RED + colorama.Back.CYAN + x + colorama.Style.RESET_ALL)
            dict[key].update(cfg[key])
            #print(colorama.Fore.YELLOW + colorama.Back.RED + "{0} -->> current {1}, total -->> {2}".format(key, len(cfg[key]), len(dict[key])) + colorama.Style.RESET_ALL)
    op = open (target, 'w')
    print (json.dumps(dict), file=op)
    op.close()

def merge_agent_dict(target, sources):
    """Combines the substation agent configuration files into "target". The source files must already exist.

    Args:
        target (str): the path to the target JSON file, including the name of the file
        sources (list): list of feeder names in the target directory to merge
    """
    print ('combining', sources, 'agent json files into', target)
    dict = {'markets':{}, 'hvacs':{}, 'batteries':{}, 'water_heaters':{}, 'size':{}, 'generators':{}, 'site_agent':{}, 'StartTime':"", 'EndTime':"", 'LogLevel':""}
    workdir = path.split(path.dirname(target))[0]
    for fdr in sources:
        lp = open (path.dirname(target) + '/' + fdr + '_agent_dict.json').read()
        cfg = json.loads(lp)
        for key in cfg.keys():
            if key in ["StartTime", "EndTime", "LogLevel", "size", "solver", "Metrics", "MetricsType", "MetricsInterval"]:
                dict[key] = cfg[key]
            else:
                dict[key].update(cfg[key])
    op = open (target, 'w')
    print (json.dumps(dict), file=op)
    op.close()

def merge_substation_yaml(target, sources):
    """Combines GridLAB-D input files into "target". The source files must already exist.

    Args:
        target (str): the path to the target YAML file, including the name of the file
        sources (list): list of feeder names in the target directory to merge
    """
    print ('combining', sources, 'yaml/json files into', target)
#    workdir = path.split(path.dirname(target))[0]
    op = open (target, 'w')
#    inFirstFile = True
    for fdr in sources:
        if 'json' in target:
            with open(path.dirname(target) + '/' + fdr + '.json') as ip:
                #            numListFalse = 0
                for line in ip:
                    print(line.rstrip(), file=op)
        elif 'yaml' in target:
            with open (path.dirname(target) + '/' + fdr + '.yaml') as ip:
    #            numListFalse = 0
                for line in ip:
                    print(line.rstrip(), file=op)
                    # if numListFalse >= 8 or inFirstFile == True:   # original was numListFalse >= 2, so we were getting duplicates in the YAML file for the substation
                    #     print (line.rstrip(), file=op)
                    # if 'list: false' in line:
                    #     numListFalse += 1
#        inFirstFile = False
    op.close()

def merge_fncs_config(target, dso, sources):
    """Combines GridLAB-D input files into "target". The source feeders must already exist.

    Args:
        target (str): the path to the target TXT file, including the name of the file
        sources (list): list of feeder names in the target directory to merge
    """
    print ('combining', sources, 'txt files into', target)
    workdir = path.split(path.dirname(target))[0]
    # extracting the climate name from one of the feeders, as all feeders under the same substation should be in the same climate zone
    dictFile = open(workdir + '/' + dso + '/' + sources[0] + '_glm_dict.json').read()
    gd = json.loads(dictFile)
#    substClimate = gd['climate']['name']
    op = open (target, 'w')
#    inFirstFile = True
    for fdr in sources:
        if len(gd['HELICS']) > 1:
            with open(workdir + '/' + fdr + '/' + fdr + '_HELICS_Config.json') as ip:
                #            numLocalWeather = 0
                for line in ip:
                    print(line.rstrip(), file=op)
        else:
            with open (workdir + '/' + fdr + '/' + fdr + '_FNCS_Config.txt') as ip:
    #            numLocalWeather = 0
                for line in ip:
                    print(line.rstrip(), file=op)
    #                if numLocalWeather >= 6 or inFirstFile == True:
    #                    print (line.rstrip(), file=op)
    #                if substClimate in line:
    #                    numLocalWeather += 1
    #        inFirstFile = False
    op.close()

