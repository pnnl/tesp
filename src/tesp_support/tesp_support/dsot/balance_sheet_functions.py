# -*- coding: utf-8 -*-
# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: balance_sheet_functions.py
# @author: yint392
"""
"""

import json
import os


def too_balance_sheet_annual(meta_path, write_path, write_to_txt=False, write_to_JSON=False):
    """ This function calculates ...

    Args:
        meta_path:
        write_path:
        write_to_txt:
        write_to_JSON:
    Returns:
        dict:
    """
    with open(os.path.join(meta_path, 'DSOT_TOO_metadata.json')) as json_file:
        TOO_metadata = json.load(json_file)

    # MilesofLine = TOO_metadata['miles_of_line']['345_kV']
    # MilesofLine = TOO_metadata['miles_of_line']['138_KV']
    MilesofLine = TOO_metadata['miles_of_line']['total']

    FixedMaintenance = TOO_metadata['maintenance_cost']['fixed_cost']
    # FixedLabor = ?
    DebtService = TOO_metadata['debt_service']['interest_rate'] * TOO_metadata['debt_service']['loan_balance']

    VariableMaintenance = (TOO_metadata['maintenance_cost']['variable_cost']['345_kV'] +
                           TOO_metadata['maintenance_cost']['variable_cost']['138_KV']) * MilesofLine

    VariableLabor = ((TOO_metadata['labor_cost']['hourly_rate']['Rural'] +
                     TOO_metadata['labor_cost']['hourly_rate']['Suburban'] +
                     TOO_metadata['labor_cost']['hourly_rate']['Urban']) *
                     TOO_metadata['labor_cost']['annual_maintenance_hours_per_mile_of_line'] * MilesofLine)

    Admin = ((TOO_metadata['administration_costs']['hourly_rate']['Rural'] +
             TOO_metadata['administration_costs']['hourly_rate']['Suburban'] +
             TOO_metadata['administration_costs']['hourly_rate']['Urban']) *
             TOO_metadata['administration_costs']['admin_hours_per_mile_of_line'] * MilesofLine)

    Deductions = TOO_metadata['taxes']['deductions']
    Depreciation = TOO_metadata['taxes']['depreciation']
    TaxedProfit = TOO_metadata['taxes']['taxable_profit']
    Taxes = ((TaxedProfit - Depreciation - Deductions) / 12) / MilesofLine

    # Revenue = ? sumOverTime(Energy * a constant value)

    balance_sheet = {
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

    if write_to_txt:
        os.chdir(write_path)
        f = open('TOO_balance_sheet.txt', 'w')
        f.write(str(json.dumps(balance_sheet, indent=4, sort_keys=False)))
        f.close()

    if write_to_JSON:
        os.chdir(write_path)
        with open('TOO_balance_sheet.json', 'w') as f:
            print(json.dumps(balance_sheet), file=f)

    return balance_sheet


def iso_balance_sheet_annual(meta_path, write_path, write_to_txt=False, write_to_JSON=False):
    """ This function calculates ...

    Args:
        meta_path:
        write_path:
        write_to_txt:
        write_to_JSON:
    Returns:
        dict:
    """
    with open(os.path.join(meta_path, 'DSOT_ISO_metadata.json')) as json_file:
        ISO_metadata = json.load(json_file)

    #    PerMWTransacted?
    HrsPerYear = 8760

    Maintenance = (ISO_metadata['Maintenance']['fixed_cost'] +
                  (ISO_metadata['Maintenance']['variable_cost'] * PerMWTransacted))

    Labor = (ISO_metadata['Labor']['hourly_rate'] * HrsPerYear) * \
            (1 + (1 - ISO_metadata['Labor']['salary_percentage_of_compensation'])) * \
            (ISO_metadata['Labor']['number_of_customers'] / ISO_metadata['Labor']['customers_per_FTE'])

    FacilitiesMortgage = ((ISO_metadata['facility_mortgage']['interest_rate'] *
                           ISO_metadata['facility_mortgage']['loan_balance']) +
                          ISO_metadata['facility_mortgage']['taxes'] +
                          ISO_metadata['facility_mortgage']['insurance']) / 12

    # Subcontracts =

    HardwareSoftware = (ISO_metadata['hardware_and_software']['fixed_costs'] +
                       (ISO_metadata['hardware_and_software']['variable_costs'] * PerMWTransacted))

    # megawatt hour of adjusted metered load comes from simulation
    # Revenue = (0.555*megawatt-hour of metered load)*1.03
    # TDH: megawatt-hour-of-metered-load is PD from the bus data times the simulation step size
    # (15 seconds = 15/3600 hrs) for an amount of energy.

    balance_sheet = {
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
        os.chdir(write_path)
        f = open('ISO_balance_sheet.txt', 'w')
        f.write(str(json.dumps(balance_sheet, indent=4, sort_keys=False)))
        f.close()

    if write_to_JSON:
        os.chdir(write_path)
        with open('ISO_balance_sheet.json', 'w') as f:
            print(json.dumps(balance_sheet), file=f)

    return balance_sheet


def test_too():
    json_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/metadata'
    path_to_write = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/'

    TOO_balance_sheet = too_balance_sheet_annual(json_path, path_to_write, write_to_txt=False, write_to_JSON=False)


def test_iso():
    json_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/metadata'
    path_to_write = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/'

    ISO_balance_sheet = iso_balance_sheet_annual(json_path, path_to_write, write_to_txt=False, write_to_JSON=False)


