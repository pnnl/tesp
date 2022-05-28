# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: pprun.py
import pypower.api as pp

import tesp_support.tso_helpers as tso

ppc = tso.load_json_case('./Case1/ppcase.json')
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
tso.summarize_opf(res)

rpf = pp.runpf(ppc, ppopt_regular)
tso.summarize_opf(rpf[0])
