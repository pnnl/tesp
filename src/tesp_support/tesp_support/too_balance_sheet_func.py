# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: too_balance_sheet_func.py
"""
@author: yint392
"""
import os
# import pandas as pd
import json

# This function calculates ...

# inputs: paths
# outputs: TOO balance sheet

def too_balance_sheet_annual(meta_path, path_to_write, write_to_txt = False, write_to_JSON = False):

    with open(os.path.join(meta_path, 'DSOT_TOO_metadata.json')) as json_file:
        TOO_metadata = json.load(json_file)
        
    MilesofLine = TOO_metadata['miles_of_line']['total'] #? TOO_metadata['miles_of_line']['345_kV'] TOO_metadata['miles_of_line']['138_KV']
    
    FixedMaintenance = TOO_metadata['maintenance_cost']['fixed_cost']
    # FixedLabor = ?
    DebtService = TOO_metadata['debt_service']['interest_rate']*TOO_metadata['debt_service']['loan_balance']
    
    VariableMaintenance = (TOO_metadata['maintenance_cost']['variable_cost']['345_kV'] +
                           TOO_metadata['maintenance_cost']['variable_cost']['138_KV'])*MilesofLine #?
    VariableLabor = (TOO_metadata['labor_cost']['hourly_rate']['Rural'] +
                     TOO_metadata['labor_cost']['hourly_rate']['Suburban'] +
                     TOO_metadata['labor_cost']['hourly_rate']['Urban'])\
                    *TOO_metadata['labor_cost']['annual_maintenance_hours_per_mile_of_line']*MilesofLine #?
    
    Admin = (TOO_metadata['adminstration_costs']['hourly_rate']['Rural'] +
             TOO_metadata['adminstration_costs']['hourly_rate']['Suburban'] +
             TOO_metadata['adminstration_costs']['hourly_rate']['Urban'])\
            *TOO_metadata['adminstration_costs']['admin_hours_per_mile_of_line']*MilesofLine
    
    
    Deductions = TOO_metadata['taxes']['deductions']
    Depreciation = TOO_metadata['taxes']['depreciation']
    TaxedProfit = TOO_metadata['taxes']['taxable_profit']
    Taxes = ((TaxedProfit-Depreciation-Deductions)/12)/MilesofLine
    
    # Revenue = ? sumOverTime(Energy * a constant value)
        
    TOO_balance_sheet = {
            'Scenario': 'TBD',  # 'Moderate Renewables Scenario' 'High Renewables Scenario'
            'Case': 'TBD',  # 'Batteries Case' 'Flexible Loads Case'
            'CapitalCosts': {
                    'Fixed': {
                            'FixedMaintenance': FixedMaintenance, 
                            'FixedLabor': 0,  # FixedLabor
                            'DebtService': DebtService
                    }, 
                    'Variable': {
                            'VariableMaintenance': VariableMaintenance, 
                            'VariableLabor': VariableLabor
                    }, 
                    'Admin': Admin, 
                    'Taxes': {
                            'Deductions': Deductions,
                            'Depreciation': Depreciation,
                            'TaxedProfit': TaxedProfit,
                            'Taxes': Taxes  # sum()
                    }, 
                    'Revenue': 0
            }
    }
    
    if write_to_txt == True:
        os.chdir(path_to_write)
        f = open('TOO_balance_sheet.txt', 'w')
        f.write(str(json.dumps(TOO_balance_sheet, indent=4, sort_keys=False)))
        f.close()
    
    if write_to_JSON == True:
        os.chdir(path_to_write)
        with open('TOO_balance_sheet.json', 'w') as f:
            json.dumps(TOO_balance_sheet, f)
                    
    return TOO_balance_sheet





if __name__ == '__main__':
    json_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/metadata'
    path_to_write = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/'
    
    TOO_balance_sheet = too_balance_sheet_annual(json_path, path_to_write, write_to_txt=False, write_to_JSON=False)



