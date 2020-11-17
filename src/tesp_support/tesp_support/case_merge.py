# Copyright (C) 2019 Battelle Memorial Institute
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
import sys
import json
import tesp_support.helpers as helpers

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
  print ('combining', sources, 'glm files into', target)
  workdir = './' + target + '/'
  op = open (workdir + target + '.glm', 'w')
  inFirstFile = True
  firstHeadNode = ''
  finishedFirstSubstation = False
  for fdr in sources:
    with open (workdir + fdr + '.glm') as ip:
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
        if inSubstation == True: 
          if '  configure' in line:
            if inHELICS == False:
              line = '  configure ' + target + '_FNCS_Config.txt;'
          elif '  power_rating' in line:
            line = '  power_rating {:.2f};'.format (xfmva * 1e3)
          elif '  base_power' in line:
            line = '  base_power {:.2f};'.format (xfmva * 1e6)
          elif '  to ' in line:
            toks = line.split()
            thisHeadNode = toks[1][:-1]
            if len(firstHeadNode) < 1:
              firstHeadNode = thisHeadNode
        if inHELICS == True:
          if 'configure' in line:
            line = '  configure ' + target + '_HELICS_gld_msg.json;'
            inHELICS = False
        if (inSubstation == True) and ('object node' in line):
          inSubstation = False
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
        if (inPreamble == True) and (inFirstFile == False):
          canWrite = False
        if canWrite == True:
          print (line.rstrip(), file=op)
        if '#endif' in line:
          if '&&&' in line:
            if 'end of common section for combining TESP cases' in line:
              inPreamble = False
    inFirstFile = False 
  op.close()

def key_present (val, ary):
  tok = val['key']
  for msg in ary:
    if tok == msg['key']:
      return True
  return False

def merge_gld_msg (target, sources):
  print ('combining', sources, 'HELICS GridLAB-D json files into', target)
  workdir = './' + target + '/'
  dict = {"name":"gld1", "period":1, "subscriptions":[], "publications":[]}
  subs = []
  pubs = []
  for fdr in sources:
    lp = open (workdir + fdr + '_HELICS_gld_msg.json').read()
    cfg = json.loads(lp)
    dict["name"] = cfg["name"]
    dict["period"] = cfg["period"]
    for pub in cfg["publications"]:
      if not key_present (pub, pubs):
        pubs.append (pub)
    for sub in cfg["subscriptions"]:
      if not key_present (sub, subs):
        subs.append (sub)
  dict["publications"] = pubs
  dict["subscriptions"] = subs
  dp = open (workdir + target + '_HELICS_gld_msg.json', 'w')
  json.dump (dict, dp, ensure_ascii=False, indent=2)
  dp.close()

def merge_substation_msg (target, sources):
  print ('combining', sources, 'HELICS Substation json files into', target)
  workdir = './' + target + '/'
  dict = {"name":"gld1", "period":1, "subscriptions":[], "publications":[]}
  subs = []
  pubs = []
  for fdr in sources:
    lp = open (workdir + fdr + '_HELICS_substation.json').read()
    cfg = json.loads(lp)
    dict["name"] = cfg["name"]
    dict["period"] = cfg["period"]
    for pub in cfg["publications"]:
      if not key_present (pub, pubs):
        pubs.append (pub)
    for sub in cfg["subscriptions"]:
      if not key_present (sub, subs):
        subs.append (sub)
  dict["publications"] = pubs
  dict["subscriptions"] = subs
  dp = open (workdir + target + '_HELICS_substation.json', 'w')
  json.dump (dict, dp, ensure_ascii=False, indent=2)
  dp.close()

def merge_glm_dict(target, sources, xfmva):
  """Combines GridLAB-D metadata files into target/target.json. The source files must already exist.

  Each constituent feeder has a new ID constructed from the NamePrefix + original base_feeder,
  then every child object on that feeder will have its feeder_id, originally network_node, 
  changed to match the new one.

  Args:
      target (str): the directory and root case name
      sources (list): list of feeder names in the target directory to merge
  """
  print ('combining', sources, 'GridLAB-D json files into', target)
  dict = {'bulkpower_bus' : 'TBD', \
          'FedName' : 'gld1', \
          'transformer_MVA' : xfmva, \
          'feeders' : {}, \
          'billingmeters' : {}, \
          'houses' : {}, \
          'inverters' : {}, \
          'capacitors' : {}, \
          'regulators' : {}}
  workdir = './' + target + '/'
  for fdr in sources:
    cp = open (fdr + '.json').read()
    comb_cfg = json.loads(cp)
    name_prefix = comb_cfg['BackboneFiles']['NamePrefix']

    lp = open (workdir + fdr + '_glm_dict.json').read()
    cfg = json.loads(lp)
    fdr_id = helpers.gld_strict_name (name_prefix + cfg['feeders']['network_node']['base_feeder'])
    print ('created new feeder id', fdr_id, 'for', fdr)
    dict['feeders'][fdr_id] = {'house_count':cfg['feeders']['network_node']['house_count'], \
                               'inverter_count':cfg['feeders']['network_node']['inverter_count'], \
                               'base_feeder':cfg['feeders']['network_node']['base_feeder']}
    for key in ['billingmeters', 'houses', 'inverters', 'capacitors', 'regulators']:
      for obj in cfg[key]:
        if 'feeder_id' in cfg[key][obj]:
          cfg[key][obj]['feeder_id'] = fdr_id
      dict[key].update(cfg[key])
  op = open (workdir + target + '_glm_dict.json', 'w')
  print (json.dumps(dict), file=op)
  op.close()

def merge_agent_dict(target, sources, xfmva):
  """Combines the substation agent configuration files into target/target.json. The source files must already exist.

  Args:
      target (str): the directory and root case name
      sources (list): list of feeder names in the target directory to merge
  """
  print ('combining', sources, 'agent json files into', target)
  dict = {'markets':{},'controllers':{},'dt':0.0,'GridLABD':''}
  workdir = './' + target + '/'
  for fdr in sources:
    lp = open (workdir + fdr + '_agent_dict.json').read()
    cfg = json.loads(lp)
    if dict['dt'] <= 0.0:
      dict['dt'] = cfg['dt']
    if len(dict['GridLABD']) < 1:
      dict['GridLABD'] = cfg['GridLABD']
    for key in ['markets', 'controllers']:
      dict[key].update(cfg[key])
  for mkt in dict['markets']:
    dict['markets'][mkt]['max_capacity_reference_bid_quantity'] = xfmva * 1000.0 * (5.0 / 3.0)
  op = open (workdir + target + '_agent_dict.json', 'w')
  print (json.dumps(dict), file=op)
  op.close()

def merge_substation_yaml(target, sources):
  """Combines GridLAB-D input files into target/target.yaml. The source files must already exist.

  Args:
      target (str): the directory and root case name
      sources (list): list of feeder names in the target directory to merge
  """
  print ('combining', sources, 'yaml files into', target)
  workdir = './' + target + '/'
  op = open (workdir + target + '_substation.yaml', 'w')
  inFirstFile = True 
  for fdr in sources:
    with open (workdir + fdr + '_substation.yaml') as ip:
      numListFalse = 0
      for line in ip:
        if numListFalse >= 2 or inFirstFile == True:
          print (line.rstrip(), file=op)
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
  print ('combining', sources, 'txt files into', target)
  workdir = './' + target + '/'
  op = open (workdir + target + '_FNCS_Config.txt', 'w')
  inFirstFile = True 
  for fdr in sources:
    with open (workdir + fdr + '_FNCS_Config.txt') as ip:
      numLocalWeather = 0
      for line in ip:
        if numLocalWeather >= 6 or inFirstFile == True:
          print (line.rstrip(), file=op)
        if 'localWeather' in line:
          numLocalWeather += 1
    inFirstFile = False 
  op.close()

