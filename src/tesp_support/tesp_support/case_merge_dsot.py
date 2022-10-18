# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: case_merge.py
"""Combines GridLAB-D and agent files to run a multi-feeder TESP simulation

Public Functions:
    :merge_glm: combines GridLAB-D input files
    :merge_glm_dict: combines GridLAB-D metadata files
    :merge_agent_dict: combines the substation agent configuration files
    :merge_substation_yaml: combines the substation agent FNCS publish/subscribe files
    :merge_fncs_config: combines GridLAB-D FNCS publish/subscribe files
"""
import json
import sys
from os import path

from .helpers import gld_strict_name

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def merge_glm(target, sources, xfmva):
    """Combines GridLAB-D input files into "target". The source files must already exist.

    Args:
        target (str): the path to the target GLM file, including the name of the file
        sources (list): list of feeder names in the target directory to merge
        xfmva (int):
    """
    print('combining', sources, 'glm files into', target)
    workdir = path.split(path.dirname(target))[0]
    op = open(target, 'w')
    inFirstFile = True
    firstHeadNode = ''
    finishedFirstSubstation = False
    # configuration, spacing and conductor names are not unique between feeders
    for fdr in sources:
        with open(workdir + '/' + fdr + '/' + fdr + '.glm') as ip:
            numEndif = 0
            inSubstation = False
            inConfig = False
            thisHeadNode = ''
            for line in ip:
                if numEndif >= 1 or inFirstFile:
                    canWrite = True
                    if 'filename Voltage_Dump' in line:
                        line = '  filename Voltage_Dump_' + path.splitext(path.basename(target))[0] + '.csv;'
                    if 'filename Current_Dump' in line:
                        line = '  filename Current_Dump_' + path.splitext(path.basename(target))[0] + '.csv;'
                    if ('object ' in line) and (
                            ('configuration' in line) or ('conductor' in line) or ('spacing' in line)):
                        inConfig = True
                    if inConfig and not inSubstation:
                        if ' name ' in line:
                            toks = line.split()
                            name = toks[1][:-1]
                            line = '  name ' + fdr + '_' + name + ';'
                            inConfig = False
                    if not inSubstation:
                        if (' spacing ' in line) or (' configuration ' in line) or \
                                ('  conductor_1' in line) or ('  conductor_2' in line) or \
                                ('  conductor_A' in line) or ('  conductor_B' in line) or \
                                ('  conductor_C' in line) or ('  conductor_N' in line):
                            if 'IS220' in line or 'IS110' in line:
                                pass
                            else:
                                toks = line.split()
                                name = toks[1][:-1]
                                line = '  ' + toks[0] + ' ' + fdr + '_' + name + ';'
                    if '#ifdef USE_FNCS' in line:
                        inSubstation = True
                    if inSubstation:
                        if ' configure ' in line:
                            if '.txt' in line:
                                line = '  configure ' + path.splitext(path.basename(target))[0] + '_gridlabd.txt;'
                            else:
                                line = '  configure ' + path.splitext(path.basename(target))[0] + '.json;'
                        elif ' power_rating ' in line:
                            line = '  power_rating {:.2f};'.format(xfmva * 1e3)
                        elif ' base_power ' in line:
                            line = '  base_power {:.2f};'.format(xfmva * 1e6)
                        elif ' to ' in line:
                            toks = line.split()
                            thisHeadNode = toks[1][:-1]
                            if len(firstHeadNode) < 1:
                                firstHeadNode = thisHeadNode
                    if inSubstation and ('object node' in line):
                        inSubstation = False
                        inConfig = False
                        if finishedFirstSubstation:
                            print('object switch {', file=op)
                            print('  name tie_' + fdr + ';', file=op)
                            print('  phases ABCN;', file=op)
                            print('  from ' + firstHeadNode + ';', file=op)
                            print('  to ' + thisHeadNode + ';', file=op)
                            print('  status CLOSED;', file=op)
                            print('}', file=op)
                        finishedFirstSubstation = True
                    if inSubstation and finishedFirstSubstation:
                        canWrite = False
                    if canWrite:
                        print(line.rstrip(), file=op)
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
        xfmva (int):
    """
    print('combining', sources, 'GridLAB-D json files into', target)
    diction = {'bulkpower_bus': 'TBD',
               'message_name': '',
               'climate': {},
               'feeders': {},
               'transformer_MVA': xfmva,
               'billingmeters': {},
               'houses': {},
               'inverters': {},
               'capacitors': {},
               'regulators': {},
               'ev': {}}
    for fdr in sources:
        lp = open(path.dirname(target) + '/' + fdr + '_glm_dict.json').read()
        cfg = json.loads(lp)
        fdr_id = gld_strict_name(cfg['base_feeder'])
        if sources.index(fdr) == 0:
            diction['bulkpower_bus'] = cfg['bulkpower_bus']
            diction['message_name'] = cfg['message_name']
            diction['climate'] = cfg['climate']
        diction['feeders'][fdr_id] = {'house_count': cfg['feeders']['network_node']['house_count'],
                                      'inverter_count': cfg['feeders']['network_node']['inverter_count'],
                                      'ev_count': cfg['feeders']['network_node']['ev_count']}
        for key in ['billingmeters', 'houses', 'inverters', 'capacitors', 'regulators', 'ev']:
            for obj in cfg[key]:
                if 'feeder_id' in cfg[key][obj]:
                    cfg[key][obj]['feeder_id'] = fdr_id
            diction[key].update(cfg[key])
    op = open(target, 'w')
    print(json.dumps(diction), file=op)
    op.close()


def merge_agent_dict(target, sources):
    """Combines the substation agent configuration files into "target". The source files must already exist.

    Args:
        target (str): the path to the target JSON file, including the name of the file
        sources (list): list of feeder names in the target directory to merge
    """
    print('combining', sources, 'agent json files into', target)
    diction = {'markets': {},
               'hvacs': {},
               'batteries': {},
               'water_heaters': {},
               'ev': {},
               'pv': {},
               'site_agent': {},
               'StartTime': "",
               'EndTime': "",
               'LogLevel': ""}
    for fdr in sources:
        lp = open(path.dirname(target) + '/' + fdr + '_agent_dict.json').read()
        cfg = json.loads(lp)
        for key in cfg.keys():
            if key in ["StartTime", "EndTime", "LogLevel", "solver", "numCore", "priceSensLoad", "serverPort",
                       "Metrics", "MetricsType", "MetricsInterval"]:
                diction[key] = cfg[key]
            else:
                diction[key].update(cfg[key])
    op = open(target, 'w')
    print(json.dumps(diction), file=op)
    op.close()


def merge_substation_yaml(target, sources):
    """Combines GridLAB-D input files into "target". The source files must already exist.

    Args:
        target (str): the path to the target YAML file, including the name of the file
        sources (list): list of feeder names in the target directory to merge
    """
    print('combining', sources, 'yaml files into', target)
    op = open(target, 'w')
    for fdr in sources:
        with open(path.dirname(target) + '/' + fdr + '.yaml') as ip:
            for line in ip:
                print(line.rstrip(), file=op)
    op.close()


def merge_fncs_config(target, sources):
    """Combines GridLAB-D input files into "target". The source feeders must already exist.

    Args:
        target (str): the path to the target TXT file, including the name of the file
        sources (list): list of feeder names in the target directory to merge
    """
    print('combining', sources, 'txt files into', target)
    workdir = path.split(path.dirname(target))[0]
    op = open(target, 'w')
    for fdr in sources:
        with open(workdir + '/' + fdr + '/' + fdr + '_gridlabd.txt') as ip:
            for line in ip:
                print(line.rstrip(), file=op)
    op.close()
