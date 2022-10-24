# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: gen_map.py
import json

import xlrd

'''
0: "bus id -bus number",
1: "Pg -real power output (MW)",
2: "Qg -reactive power output (MVAr)",
3: "Qmax -maximum reactive power output (MVAr)",
4: "Qmin -minimum reactive power output (MVAr)",
5: "Vg -voltage magnitude set point (p.u.)",
6: "mBase -total MVA base of machine, defaults to baseMVA",
7: "status -machine status > 0 = machine in-service, machine status ≤ 0 = machine out-of-service",
8: "Pmax -maximum real power output (MW)",
9: "Pmin -minimum real power output (MW)",
10:"PC1* -lower real power output of PQ capability curve (MW)",
11:"PC2* -upper real power output of PQ capability curve (MW)",
12:"QC1MIN* -minimum reactive power output at PC1 (MVAr)",
13:"QC1MAX* -maximum reactive power output at PC1 (MVAr)",
14:"QC2MIN* -minimum reactive power output at PC2 (MVAr)",
15:"QC2MAX* -maximum reactive power output at PC2 (MVAr)",
16:"RAMP AGC* -ramp rate for load following/AGC (MW/min)",
17:"RAMP 10* -ramp rate for 10 minute reserves (MW)",
18:"RAMP 30* -ramp rate for 30 minute reserves (MW)",
19:"RAMP Q* -ramp rate for reactive power (2 sec timescale) (MVAr/min)",
20:"APF* -area participation factor",
21:"Minimum uptime (hours)",
22:"Minimum downtime (hours)",
23:"Gen id",
24:"Gen type",

"gencost": "An array for each generator cost [2, startup, shutdown, 3, c2, c1, c0]"
'''

pctramprate = {'wind': 0.05,
               'nuclear': 0.003162,
               'coal': 0.03312,
               'gas': 0.5}

minuptime = {'wind': 0,  # 10.214
             'nuclear': 168,
             'coal': 146.85,
             'gas': 4.62}

mindowntime = {'wind': 0,  # 6.596
               'nuclear': 168,
               'coal': 45.49,
               'gas': 3.2}

# from PJM data #k$
startupcost = {'wind': 6.87,
               'nuclear': 2.17,
               'coal': 9.56,
               'gas': 8.98}

# ========   INPUT SETTINGS  ========================
data_path = '../../../examples/analysis/dsot/data/'
case_path = '../../../examples/analysis/dsot/code/'
# case_path = '../../../examples/capabilities/ercot/case8/dsostub/'
# case_path = '../../../examples/capabilities/ercot/case8/'

high_renew_wind_scaling = 2.00


# case_file = 'ercot_8'
# ========   END INPUT SETTINGS  ========================


def prepare_network(node, node_col, high_renewables_case, zero_pmin=False, zero_index=False, on_ehv=True,
                    split_start_cost=False, high_ramp_rates=False, coal=True):
    if high_renewables_case:
        case_file = node + '_hi_system_case_config'
    else:
        case_file = node + '_system_case_config'

    book = xlrd.open_workbook(data_path + 'bus_generators.xlsx')
    if high_ramp_rates:
        sheet = book.sheet_by_name('Gen Info-high ramps')
    else:
        sheet = book.sheet_by_name('Gen Info')

    # os.rename(case_path + case_file + '.json', case_path + case_file + '_old.json')

    with open(case_path + case_file + '.json') as json_file:
        data = json.load(json_file)

        genCost = []
        genData = []
        genFuel = []
        if high_renewables_case:
            gentypes = ['solar', 'coal', 'gas', 'nuclear', 'wind', 'hydro']
        else:
            gentypes = ['coal', 'gas', 'nuclear', 'wind', 'hydro']
        if not coal:
            gentypes.remove('coal')

        for irow in range(1, sheet.nrows - 2):
            genidx = int(sheet.cell(irow, 0).value)
            if zero_index:
                busNo = int(sheet.cell(irow, node_col).value) - 1
            else:
                busNo = int(sheet.cell(irow, node_col).value)

            mvabase = sheet.cell(irow, 3).value
            if zero_pmin:  # Mode to set pmin to zero as part of debugging
                pmin = 0.0
            else:
                pmin = sheet.cell(irow, 4).value
            qmin = sheet.cell(irow, 5).value
            qmax = sheet.cell(irow, 6).value
            c2 = sheet.cell(irow, 7).value
            c1 = sheet.cell(irow, 8).value
            c0 = sheet.cell(irow, 9).value
            Gentype = sheet.cell(irow, 10).value
            RampRate = sheet.cell(irow, 11).value
            if split_start_cost:
                StartupCost = sheet.cell(irow, 12).value / 2
                ShutdownCost = sheet.cell(irow, 12).value / 2
            else:
                StartupCost = sheet.cell(irow, 12).value
                ShutdownCost = 0

            # For the 200 bus case determine if there is a high voltage bus that the generator should be connected to.
            # Solar and Wind are to remain on low-voltage buses:
            if node == '200' and on_ehv and "Wind" not in Gentype and "Solar" not in Gentype:  # 1 = 200 node case
                for branch in data['branch']:
                    if branch[0] == busNo and branch[1] > 200:
                        busNo = branch[1]
                        break
                    elif branch[1] == busNo and branch[0] > 200:
                        busNo = branch[1]
                        break

            # If high renewable case scale up the baseline wind capacities
            if high_renewables_case and "Wind" in Gentype:
                mvabase = high_renew_wind_scaling * mvabase

            if "Wind" in Gentype:
                fueltype = 'wind'
            elif "Nuclear" in Gentype:
                fueltype = 'nuclear'
            elif "Coal" in Gentype:
                fueltype = 'coal'
            elif "Gas" in Gentype:
                fueltype = 'gas'
            elif "Hydro" in Gentype:
                fueltype = 'hydro'
            elif "Solar" in Gentype:
                fueltype = 'solar'
            else:
                fueltype = 'other'

            if fueltype in gentypes:
                # gen_id[busNo] = gen_id[busNo] + 1
                genData.append([
                    busNo,
                    float(0),
                    float(0),
                    float(qmax),
                    float(qmin),
                    1.0,
                    float(mvabase),
                    1,
                    float(mvabase),
                    float(pmin),
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    float(RampRate),
                    0.0,
                    0.0,
                    0.0,
                    0.0
                ])
                genCost.append([
                    2,
                    float(StartupCost),
                    float(ShutdownCost),
                    3,
                    float(c2),
                    float(c1),
                    float(c0)
                ])
                genFuel.append([
                    fueltype,
                    Gentype,
                    genidx,
                    1
                ])

        # divide the generators into parts
        # testing on dividing first generator into 3
        '''
        oldQmax = genData[0][3]
        oldQmin = genData[0][4]
        oldPmax = genData[0][8]
        oldPmin = genData[0][9]

        newPmax = oldPmax/3.0
        newGenData = genData[0]
        newGenCost = genCost[0]
        newGenData[3] = oldQmax * newPmax/oldPmax
        newGenData[4] = oldQmin * newPmax/oldPmax
        newGenData[6] = newPmax
        newGenData[8] = newPmax
        newGenData[9] = oldPmin * newPmax/oldPmax
        data['gen'].pop(0)
        data['gencost'].pop(0)
        for j in range(3):
            data['gen'] = [newGenData] + data['gen']
            data['gencost'] = [newGenCost] + data['gencost']

        genData = data['gen']
        genCost = data['gencost']

        # assigning ramp rate based on fuel type
        for i in range(len(data['gen'])):
            # find the type of generation
            c2 = float(genCost[i][4])
            c1 = float(genCost[i][5])
            c0 = float(genCost[i][6])
            pmax = float(genData[i][8])
            # assign fuel types from the IA State default costs
            if c2 < 2e-5:  
                genfuel = 'wind'
            elif c2 < 0.0003:
                genfuel = 'nuclear'
            elif c1 < 25.0:
                genfuel = 'coal'
            else:
                genfuel = 'gas'
            # calculate ramprate based on fuel type
            ramprate = pctramprate[genfuel]*pmax
            minUpTime = math.ceil(minuptime[genfuel])
            minDownTime = math.ceil(mindowntime[genfuel])
            # update the original data variable
            data['gen'][i][16] = ramprate
            data['gen'][i].append(minUpTime)
            data['gen'][i].append(minDownTime)
        '''
        data['gen'] = genData
        data['gencost'] = genCost
        data['genfuel'] = genFuel
        print('Finished ' + case_file)

    json_file.close()
    # write it in the original data file
    with open(case_path + case_file + '.json', 'w') as outfile:
        json.dump(data, outfile, indent=2)
        outfile.close()


# ------- prepare_network(
#                 node,
#                 node_col,
#                 high_renewables_case,
#                 zero_pmin=False,
#                 zero_index=False,
#                 on_ehv=True,
#                 split_start_cost=False,
#                 high_ramp_rates=False,
#                 coal=True)


node = ['8', '200']
col = [2, 1]

for i in range(2):
    # ----- Use commands below to run with low ramp rates and defaults
    # prepare_network(node[i], col[i], True)
    # prepare_network(node[i], col[i], False)

    # ----- Use the commands below to turn off coal high renewables
    # prepare_network(node[i], col[i], True, False, False, True, False, False, False)
    # prepare_network(node[i], col[i], False, False, False, True, False, False, False)

    # ----- Use commands below to run with high ramp rates
    prepare_network(node[i], col[i], True, False, False, True, False, True)
    prepare_network(node[i], col[i], False, False, False, True, False, True)

    # ----- Use commands below to run with start up costs split 50/50 between start up and shutdown
    # prepare_network(node[i], col[i], True, False, False, True, True)
    # prepare_network(node[i], col[i], False, False, False, True, True)
