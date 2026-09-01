# Copyright (c) 2019-2025 Battelle Memorial Institute
# file: generate_case.py
""" Utility function to split a year run to monthly runs. This is DSO+T specific helper functions
"""

import os
import sys

import prepare_case_glm_dsot as prep_case
import pyjson5


def generate_case(caseName, start, finish):
    config_file = str('../data/' + caseName + '.json5')
    with open(config_file, 'r', encoding='utf-8') as json5_file:
        ppc = pyjson5.load(json5_file)
    split_case = ppc['split_case']
    caseStartYear = ppc['caseStartYear']
    caseEndYear = ppc['caseEndYear']
    case_rate = ppc['rate']
    port = ppc['port']
    if len(case_rate) > 0:
        case_rate_and_node = str(ppc['nodes']) + "_" + case_rate + "_"
    else:
        case_rate_and_node = str(ppc['nodes']) + "_"

    if split_case:
        while True:
            for i in range(start, finish):
                # (exclusive, inclusive)
                directory_name = str(caseStartYear) + "_" + f'{i+1:0>2}'
                ppc['caseName'] = case_rate_and_node + directory_name
                ppc['port'] = int(port + i)

                year = caseStartYear
                month = f'{i:0>2}'
                daytime = "-29 00:00:00"
                if i == 0:
                    daytime = "-01 00:00:00"
                    month = '01'
                ppc['StartTime'] = str(year) + "-" + month + daytime

                year = caseStartYear
                month = f'{i+2:0>2}'
                daytime = "-01 00:00:00"
                if i == 11:
                    daytime = "-30 00:00:00"
                    month = '12'
                ppc['EndTime'] = str(year) + "-" + month + daytime

                config_dump = pyjson5.dumps(ppc, indent=2)
                out_file = os.path.join("../data/", "generate_config_dump.json5")
                with open(out_file, 'w', encoding='utf-8') as file:
                    file.write(config_dump)
                prep_case.prepare_case("generate_config_dump")

            if caseStartYear == caseEndYear:
                break
            caseStartYear += 1

if __name__ == "__main__":
    # Either define your simulation time here or from the console, ex:
    # `python3 generate_case.py 3 5`
    start = 3 # Month to start (Exclusive)
    finish = 4 # Month to end (Inclusive)

    if len(sys.argv) > 1:
        generate_case("rates_config", int(sys.argv[1]), int(sys.argv[2]))
    else:
        generate_case("rates_config", start, finish)
