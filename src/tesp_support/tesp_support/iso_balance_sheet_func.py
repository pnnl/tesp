# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: iso_balance_sheet_func.py
"""
@author: yint392
"""
import os
# import pandas as pd
import json

# This function calculates ...

# inputs: paths
# outputs: ISO balance sheet

def iso_balance_sheet_annual(meta_path, path_to_write, write_to_txt = False, write_to_JSON = False):

    with open(os.path.join(meta_path, 'DSOT_ISO_metadata.json')) as json_file:
        ISO_metadata = json.load(json_file)

#    PerMWTransacted?
    HrsPerYear = 8760
    
    Maintenance = ISO_metadata['Maintenance']['fixed_cost'] + \
                  (ISO_metadata['Maintenance']['variable_cost'] * PerMWTransacted)

    Labor = (ISO_metadata['Labor']['hourly_rate']*HrsPerYear) * \
            (1+(1-ISO_metadata['Labor']['salary_percentage_of_compensation']))*\
            (ISO_metadata['Labor']['number_of_customers']/ISO_metadata['Labor']['customers_per_FTE'])

    FacilitiesMortgage = ((ISO_metadata['facility_mortgage']['interest_rate'] *
                           ISO_metadata['facility_mortgage']['loan_balance']) +
                          ISO_metadata['facility_mortgage']['taxes'] +
                          ISO_metadata['facility_mortgage']['insurance'])/12

    # Subcontracts = 
    
    HardwareSoftware = ISO_metadata['hardware_and_software']['fixed_costs'] + \
                       (ISO_metadata['hardware_and_software']['variable_costs']*PerMWTransacted)
    
#    Revenue = (0.555*megawatt-hour of metered load)*1.03 # megawatt hour of adjusted metered load comes from simulation
    # TDH: megawatt-hour-of-metered-load is PD from the bus data times the simulation step size (15 seconds = 15/3600 hrs) for an amount of energy.
    
    ISO_balance_sheet = {
           'Expenses': {
                   'Maintenance': Maintenance, 
                   'Labor': Labor, 
                   'FacilitiesMortgage': FacilitiesMortgage, 
                   'Subcontracts': 0, 
                   'HardwareSoftware': HardwareSoftware
            }, 
           'Revenue': 0
    }
           
    if write_to_txt:
        os.chdir(path_to_write)
        f = open('ISO_balance_sheet.txt', 'w')
        f.write(str(json.dumps(ISO_balance_sheet, indent=4, sort_keys=False)))
        f.close()
    
    if write_to_JSON:
        os.chdir(path_to_write)
        with open('ISO_balance_sheet.json', 'w') as f:
            json.dumps(ISO_balance_sheet, f)

    return ISO_balance_sheet

if __name__ == '__main__':
    json_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/metadata'
    path_to_write = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/'
    
    ISO_balance_sheet = iso_balance_sheet_annual(json_path, path_to_write, write_to_txt=False, write_to_JSON=False)












