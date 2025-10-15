# Copyright (c) 2019-2025 Battelle Memorial Institute
# file: generate_case.py
""" Utility function to split a year run to monthly runs. This is DSO+T specific helper functions
"""

import pyjson5
import sys
import os

import prepare_case_glm_dsot as prep_case


def generate_case(caseName, port, pv=None, bt=None, fl=None, ev=None):

    config_file = str('../data/' + caseName + '.json5')
    with open(config_file, 'r', encoding='utf-8') as json5_file:
        ppc = pyjson5.load(json5_file)
    split_case = ppc['split_case']
    caseStartYear = ppc['caseStartYear']
    caseEndYear = ppc['caseEndYear']

    if split_case:
        while True:
            for i in range(4, 5):
                # (exclusive, inclusive)
                directory_name = str(caseStartYear) + "_" + '{0:0>2}'.format(i+1)
                ppc['caseName'] = node + "_" + directory_name
                ppc['port'] = int(port + i)

                year = caseStartYear
                month = '{0:0>2}'.format(i)
                daytime = "-29 00:00:00"
                if i == 0:
                    daytime = "-01 00:00:00"
                    month = '01'
                ppc['StartTime'] = str(year) + "-" + month + daytime

                year = caseStartYear
                month = '{0:0>2}'.format(i+2)
                daytime = "-01 00:00:00"
                if i == 11:
                    daytime = "-30 00:00:00"
                    month = '12'
                ppc['EndTime'] = str(year) + "-" + month + daytime

                config_dump = pyjson5.dumps(ppc, indent=2)
                out_file = os.path.join("../data/", "generate_config_dump.json5")
                with open(out_file, 'w', encoding='utf-8') as file:
                    file.write(config_dump)
                prep_case.prepare_case(int(node), "generate_config_dump", pv=pv, bt=bt, fl=fl, ev=ev)

            if caseStartYear == caseEndYear:
                break
            caseStartYear += 1

if __name__ == "__main__":
    if len(sys.argv) > 6:
        generate_case(int(sys.argv[1]), sys.argv[2], pv=int(sys.argv[3]), bt=int(sys.argv[4]), fl=int(sys.argv[5]), ev=int(sys.argv[6]))
    else:
        node = "8"
        # node = "200"

        # generate_case(node + "_system_case_config", 5570, pv=0, bt=0, fl=0, ev=0)
        # generate_case(node + "_system_case_config", 5570, pv=0, bt=1, fl=0, ev=0)
        # generate_case(node + "_system_case_config", 5570, pv=0, bt=0, fl=1, ev=0)
        # generate_case(node + "_hi_system_case_config", 5570, pv=1, bt=0, fl=0, ev=0)
        # generate_case(node + "_hi_system_case_config", 5570, pv=1, bt=1, fl=0, ev=1)
        # generate_case(node + "_hi_system_case_config", 5570, pv=1, bt=0, fl=1, ev=1)
        generate_case("rates_config", 5570, pv=1, bt=1, fl=1, ev=1)
