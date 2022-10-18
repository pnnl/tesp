# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: generator_balance_sheet_func.py
"""
@author: yint392
"""

import os
import json


# This function calculates ...
# inputs: generator type and paths
# outputs: generator balance sheet for a specific type

def generator_balance_sheet_annual(generator_num, gen_type, meta_path, system_path, path_to_write,
                                   write_to_txt=False, write_to_JSON=False):
    # reading meta_path
    with open(os.path.join(meta_path, 'DSOT_generator_metadata.json')) as json_file:
        generator_metadata = json.load(json_file)

    with open(os.path.join(system_path, 'system_case_config.json')) as json_file:
        system_case_config = json.load(json_file)

    MW_Rated = system_case_config['gen'][generator_num][
        [i for i, x in enumerate(system_case_config['metadata']['gen']) if 'Pmax' in x][0]]
    # MW_Rated = system_case_config['gen'][0][[i for i, x in enumerate(system_case_config['metadata']['gen']) if 'Pmax' in x][0]]

    FixedMaintenance = generator_metadata['fixed_maintenance']['fixed_cost'][gen_type] + (
                generator_metadata['fixed_maintenance']['per_MW_cost'][gen_type] * MW_Rated)

    FixedLabor = generator_metadata['fixed_labor']['fixed_cost'][gen_type] + (
                generator_metadata['fixed_labor']['per_MW_cost'][gen_type] * MW_Rated)

    DebtService = generator_metadata['debt_service']['capital_investment'][gen_type] * \
                  generator_metadata['debt_service']['interest_rate'][gen_type]

    VariableMaintenance = generator_metadata['variable_maintenance']['fixed_cost'][gen_type] + (
                generator_metadata['variable_maintenance']['per_MW_cost'][gen_type] * MW_Rated)

    VariableLabor = generator_metadata['variable_labor']['fixed_cost'][gen_type] + (
                generator_metadata['variable_labor']['per_MW_cost'][gen_type] * MW_Rated)

    # MarketSales = SumOverTime(LMP * EnergyOutput) ?
    # LMP 
    # EnergyOutput amount of energy produced by the generator

    #    Fuel = Energy_Output * Heat_Rate(c1 coefficient)
    #    Heat_Rate = system_case_config['gencost'][generator_num][-3:]
    #    Heat_Rate = system_case_config['gencost'][0][-3:]

    # Fuel = SumOverTime(MarginalCostCurve(OutputPower)) ?
    # OutputPower same as EnergyOutput

    Deductions = generator_metadata['taxes']['deductions']
    Depreciation = generator_metadata['taxes']['depreciation']
    TaxedProfit = generator_metadata['taxes']['taxable_profit']

    Generator_balance_sheet = {
        'Type': gen_type,
        'CapitalCosts': {
            'Fixed': {
                'FixedMaintenance': FixedMaintenance,
                'FixedLabor': FixedLabor,
                'DebtService': DebtService
            },
            'Variable': {
                'VariableMaintenance': VariableMaintenance,
                'VariableLabor': VariableLabor,
                'Fuel': 0
            },
            'Admin': 0,
            'Taxes': {
                'Deductions': Deductions,
                'Depreciation': Depreciation,
                'TaxedProfit': TaxedProfit
            },
            'Revenue': {
                'MarketSales': 0,
                'BilateralSales': 0,
                'CapacityPayments': 0
            }
        }
    }

    if write_to_txt:
        os.chdir(path_to_write)
        f = open('Generator_balance_sheet.txt', 'w')
        f.write(str(json.dumps(Generator_balance_sheet, indent=4, sort_keys=False)))
        f.close()

    if write_to_JSON:
        os.chdir(path_to_write)
        with open('Generator_balance_sheet.json', 'w') as f:
            json.dumps(Generator_balance_sheet, f)

    return Generator_balance_sheet


if __name__ == '__main__':
    generator_num = 0
    gen_type = 'nuclear'
    # gen_type = "nuclear", "coal_steam", "combine_cycle_NG","simple_cycle_NG", "wind", "solar", "NG_steam"
    json_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/metadata'
    path_to_write = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/'
    system_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/tesp-private/examples/dsot_v3'

    Generator_balance_sheet = generator_balance_sheet_annual(generator_num, gen_type, json_path, path_to_write,
                                                             write_to_txt=False, write_to_JSON=False)
