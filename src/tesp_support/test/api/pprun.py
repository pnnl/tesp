# Copyright (C) 2017-2023 Battelle Memorial Institute
# file: pprun.py
from os import path

import pypower.api as pp

import tesp_support.api.tso_helpers as th


dirpath = path.expandvars('$TESPDIR/examples/capabilities/pypower/')
ppc = th.load_json_case(dirpath + '/ppcase.json')
# print(ppc)

ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['opf_dc'])
ppopt_regular = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=ppc['pf_dc'])

print(ppc['UnitsOut'])
print(ppc['BranchesOut'])

for row in ppc['UnitsOut']:
    print('unit  ', row[0], 'off from', row[1], 'to', row[2], flush=True)
for row in ppc['BranchesOut']:
    print('branch', row[0], 'out from', row[1], 'to', row[2], flush=True)

res = pp.runopf(ppc, ppopt_market)
th.summarize_opf(res)

rpf = pp.runpf(ppc, ppopt_regular)
th.summarize_opf(rpf[0])
