# Copyright (C) 2019-2022 Battelle Memorial Institute
# file: case_merge.py
"""Combines GridLAB-D and agent files to run a multi-feeder TESP simulation

Public Functions:
    :merge_glm: combines GridLAB-D input files
    :merge_glm_dict: combines GridLAB-D metadata files
    :merge_agent_dict: combines the substation agent configuration files
    :merge_substation_yaml: combines the substation agent FNCS publish/subscribe files
    :merge_fncs_config: combines GridLAB-D FNCS publish/subscribe files
    :merge_gld_msg: combines GridLAB-D HELICS publish/subscribe configurations
    :merge_substation_msg: combines the substation agent HELICS publish/subscribe configurations
"""
import json
import sys

from .helpers import gld_strict_name

if sys.platform == 'win32':
    pycall = 'python'
else:
    pycall = 'python3'


def merge_glm(target, sources, xfmva):
    """Combines GridLAB-D input files into target/target.glm. The source files must already exist.
  
    Args:
        target (str): the directory and root case name
        sources (list): list of feeder names in the target directory to merge
    """
    print('combining', sources, 'glm files into', target)
    workdir = './' + target + '/'
    op = open(workdir + target + '.glm', 'w')
    inFirstFile = True
    firstHeadNode = ''
    finishedFirstSubstation = False
    for fdr in sources:
        with open(workdir + fdr + '.glm') as ip:
            inPreamble = True
            inSubstation = False
            inHELICS = False
            thisHeadNode = ''
            for line in ip:
                canWrite = True
                if 'filename Voltage_Dump' in line:
                    line = '  filename Voltage_Dump_' + target + '.csv;'
                if 'filename Current_Dump' in line:
                    line = '  filename Current_Dump_' + target + '.csv;'
                if '#ifdef USE_FNCS' in line:
                    inSubstation = True
                if 'object helics_msg' in line:
                    inHELICS = True
                if inSubstation:
                    if '  configure' in line:
                        if not inHELICS:
                            line = '  configure ' + target + '_gridlabd.txt;'
                    elif '  power_rating' in line:
                        line = '  power_rating {:.2f};'.format(xfmva * 1e3)
                    elif '  base_power' in line:
                        line = '  base_power {:.2f};'.format(xfmva * 1e6)
                    elif '  to ' in line:
                        toks = line.split()
                        thisHeadNode = toks[1][:-1]
                        if len(firstHeadNode) < 1:
                            firstHeadNode = thisHeadNode
                if inHELICS:
                    if 'configure' in line:
                        line = '  configure ' + target + '_gridlabd.json;'
                        inHELICS = False
                if inSubstation and ('object node' in line):
                    inSubstation = False
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
                if inPreamble and not inFirstFile:
                    canWrite = False
                if canWrite:
                    print(line.rstrip(), file=op)
                if '#endif' in line:
                    if '&&&' in line:
                        if 'end of common section for combining TESP cases' in line:
                            inPreamble = False
        inFirstFile = False
    op.close()


def key_present(val, ary):
    tok = val['key']
    for msg in ary:
        if tok == msg['key']:
            return True
    return False


def merge_gld_msg(target, sources):
    print('combining', sources, 'HELICS GridLAB-D json files into', target)
    workdir = './' + target + '/'
    diction = {"name": "gld_1", "period": 1, "subscriptions": [], "publications": []}
    subs = []
    pubs = []
    for fdr in sources:
        lp = open(workdir + fdr + '_gridlabd.json').read()
        cfg = json.loads(lp)
        diction["name"] = cfg["name"]
        diction["period"] = cfg["period"]
        for pub in cfg["publications"]:
            if not key_present(pub, pubs):
                pubs.append(pub)
        for sub in cfg["subscriptions"]:
            if not key_present(sub, subs):
                subs.append(sub)
    diction["publications"] = pubs
    diction["subscriptions"] = subs
    dp = open(workdir + target + '_gridlabd.json', 'w')
    json.dump(diction, dp, ensure_ascii=False, indent=2)
    dp.close()


def merge_substation_msg(target, sources):
    print('combining', sources, 'HELICS Substation json files into', target)
    workdir = './' + target + '/'
    diction = {"name": "gld_1", "period": 1, "subscriptions": [], "publications": []}
    subs = []
    pubs = []
    for fdr in sources:
        lp = open(workdir + fdr + '_substation.json').read()
        cfg = json.loads(lp)
        diction["name"] = cfg["name"]
        diction["period"] = cfg["period"]
        for pub in cfg["publications"]:
            if not key_present(pub, pubs):
                pubs.append(pub)
        for sub in cfg["subscriptions"]:
            if not key_present(sub, subs):
                subs.append(sub)
    diction["publications"] = pubs
    diction["subscriptions"] = subs
    dp = open(workdir + target + '_substation.json', 'w')
    json.dump(diction, dp, ensure_ascii=False, indent=2)
    dp.close()


def merge_glm_dict(target, sources, xfmva):
    """Combines GridLAB-D metadata files into target/target.json. The source files must already exist.
  
    Each constituent feeder has a new ID constructed from the NamePrefix + original base_feeder,
    then every child object on that feeder will have its feeder_id, originally network_node, 
    changed to match the new one.
  
    Args:
        target (str): the directory and root case name
        sources (list): list of feeder names in the target directory to merge
        xfmva (int):
    """
    print('combining', sources, 'GridLAB-D json files into', target)
    diction = {'bulkpower_bus': 'TBD',
               'FedName': 'gld_1',
               'feeders': {},
               'transformer_MVA': xfmva,
               'billingmeters': {},
               'houses': {},
               'inverters': {},
               'capacitors': {},
               'regulators': {}}
    workdir = './' + target + '/'
    for fdr in sources:
        cp = open(fdr + '.json').read()
        comb_cfg = json.loads(cp)
        name_prefix = comb_cfg['BackboneFiles']['NamePrefix']

        lp = open(workdir + fdr + '_glm_dict.json').read()
        cfg = json.loads(lp)
        fdr_id = gld_strict_name(name_prefix + cfg['feeders']['network_node']['base_feeder'])
        print('created new feeder id', fdr_id, 'for', fdr)
        diction['feeders'][fdr_id] = {'house_count': cfg['feeders']['network_node']['house_count'],
                                      'inverter_count': cfg['feeders']['network_node']['inverter_count'],
                                      'base_feeder': cfg['feeders']['network_node']['base_feeder']}
        for key in ['billingmeters', 'houses', 'inverters', 'capacitors', 'regulators']:
            for obj in cfg[key]:
                if 'feeder_id' in cfg[key][obj]:
                    cfg[key][obj]['feeder_id'] = fdr_id
            diction[key].update(cfg[key])
    op = open(workdir + target + '_glm_dict.json', 'w')
    print(json.dumps(diction), file=op)
    op.close()


def merge_agent_dict(target, sources, xfmva):
    """Combines the substation agent configuration files into target/target.json. The source files must already exist.
  
    Args:
        target (str): the directory and root case name
        sources (list): list of feeder names in the target directory to merge
    """
    print('combining', sources, 'agent json files into', target)
    diction = {'markets': {},
               'controllers': {},
               'dt': 0.0,
               'GridLABD': ''}
    workdir = './' + target + '/'
    for fdr in sources:
        lp = open(workdir + fdr + '_agent_dict.json').read()
        cfg = json.loads(lp)
        if diction['dt'] <= 0.0:
            diction['dt'] = cfg['dt']
        if len(diction['GridLABD']) < 1:
            diction['GridLABD'] = cfg['GridLABD']
        for key in ['markets', 'controllers']:
            diction[key].update(cfg[key])
    for mkt in diction['markets']:
        diction['markets'][mkt]['max_capacity_reference_bid_quantity'] = xfmva * 1000.0 * (5.0 / 3.0)
    op = open(workdir + target + '_agent_dict.json', 'w')
    print(json.dumps(diction), file=op)
    op.close()


def merge_substation_yaml(target, sources):
    """Combines GridLAB-D input files into target/target.yaml. The source files must already exist.
  
    Args:
        target (str): the directory and root case name
        sources (list): list of feeder names in the target directory to merge
    """
    print('combining', sources, 'yaml files into', target)
    workdir = './' + target + '/'
    op = open(workdir + target + '_substation.yaml', 'w')
    inFirstFile = True
    for fdr in sources:
        with open(workdir + fdr + '_substation.yaml') as ip:
            numListFalse = 0
            for line in ip:
                if numListFalse >= 2 or inFirstFile:
                    print(line.rstrip(), file=op)
                if 'list: false' in line:
                    numListFalse += 1
        inFirstFile = False
    op.close()


def merge_fncs_config(target, sources):
    """Combines GridLAB-D input files into target/target.txt. The source feeders must already exist.
  
    Args:
        target (str): the directory and root case name
        sources (list): list of feeder names in the target directory to merge
    """
    print('combining', sources, 'txt files into', target)
    workdir = './' + target + '/'
    op = open(workdir + target + '_gridlabd.txt', 'w')
    inFirstFile = True
    for fdr in sources:
        with open(workdir + fdr + '_gridlabd.txt') as ip:
            numLocalWeather = 0
            for line in ip:
                if numLocalWeather >= 6 or inFirstFile:
                    print(line.rstrip(), file=op)
                if 'localWeather' in line:
                    numLocalWeather += 1
        inFirstFile = False
    op.close()
