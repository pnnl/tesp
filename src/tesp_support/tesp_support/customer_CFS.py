# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: customer_CFS.py

"""
@author: yint392
"""
# individual customer

import json
import os

from .dso_helper_functions import returnDictSum


# This function calculates ...
# inputs: customer_name, paths
# outputs:


def customer_CFS(GLD_metadata,
                 metadata_path,
                 customer,
                 customer_bill):
    with open(os.path.join(metadata_path, 'metadata-general.json')) as json_file:
        metadata_gen = json.load(json_file)
    metadata_general = metadata_gen["general"]

    # #TO-DO
    # Commercial_buildings = ['medium_small_office', 'warehouse_storage', 'big_box', 'strip_mall', 'education',
    #                         'food_service', 'food_sales', 'lodging', 'low_occupancy']
    # Residential_buildings = ['SINGLE_FAMILY', 'MULTI_FAMILY', 'MOBILE_HOME']
    # Large_commercial_buildings = ['large_office', 'healthcare_inpatient']

    # rate_class
    Building_type = GLD_metadata['billingmeters'][customer]['building_type']

    # cust_participating = True
    # hvac_participating = True
    # wh_participating = True
    # batt_participating = True
    # ev_participating = True
    # pv_participating = True

    cust_participating = GLD_metadata['billingmeters'][customer]['cust_participating']
    hvac_participating = GLD_metadata['billingmeters'][customer]['hvac_participating']
    wh_participating = GLD_metadata['billingmeters'][customer]['wh_participating']
    batt_participating = GLD_metadata['billingmeters'][customer]['batt_participating']
    ev_participating = GLD_metadata['billingmeters'][customer]['ev_participating']
    pv_participating = GLD_metadata['billingmeters'][customer]['pv_participating']

    if Building_type == 'UNKNOWN':
        return
    else:
        Customer_class = GLD_metadata['billingmeters'][customer]['tariff_class']

        # # not 100% sure
        # for Commercial_building in Commercial_buildings:
        #     if Commercial_building in Building_type:
        #         Customer_class = 'commercial'
        #
        # for Residential_building in Residential_buildings:
        #     if Residential_building in Building_type:
        #         Customer_class = 'residential'
        #
        # for Large_commercial_building in Large_commercial_buildings:
        #     if Large_commercial_building in Building_type:
        #         Customer_class = 'large_commercial'

        metadata_thermostat = metadata_general['thermostat']
        metadata_water_heater = metadata_general['water_heater']
        metadata_battery = metadata_general['battery']
        metadata_V1G = metadata_general['V1G']
        metadata_V2G = metadata_general['V2G']
        metadata_PV = metadata_general['PV']

        if Customer_class == 'residential':
            ACCF_WaterHeater = metadata_general['ACCF'][Customer_class]['smart_water_heater_marginal'][Building_type.lower()]
            ACCF_V1G = metadata_general['ACCF'][Customer_class]['smart_EV_charger_marginal'][Building_type.lower()]
            ACCF_V2G = metadata_general['ACCF'][Customer_class]['smart_EV_inverter_marginal'][Building_type.lower()]
        else:
            ACCF_WaterHeater = 0
            ACCF_V1G = 0
            ACCF_V2G = 0
        ACCF_Battery = metadata_general['ACCF'][Customer_class]['battery_total'][Building_type.lower()]
        ACCF_PV = metadata_general['ACCF'][Customer_class]['PV_total'][Building_type.lower()]

        Average_Hourly_Labor_Cost_maintenance_repair = metadata_general['labor']['maintenance_repair']['average_hourly_labor_cost']
        Average_Hourly_Labor_Cost_plumber = metadata_general['labor']['plumber']['average_hourly_labor_cost']
        Average_Hourly_Labor_Cost_electrician = metadata_general['labor']['electrician']['average_hourly_labor_cost']

        Rated_Battery_Size = GLD_metadata['billingmeters'][customer]['battery_capacity']
        Rated_System_Size = GLD_metadata['billingmeters'][customer]['pv_capacity']

        Participant = 1 if wh_participating else 0
        WaterHeater = Participant * ACCF_WaterHeater * \
        (metadata_water_heater['controller_purchase_price'] + metadata_water_heater['mixing_valve_purchase_price'] +
         metadata_water_heater['mixing_valve_installation_time_hrs']*Average_Hourly_Labor_Cost_plumber)

        battery_present = 1 if Rated_Battery_Size > 0 else 0
        Participant = 1 if batt_participating else 0
        Battery = Participant * ACCF_Battery * \
                  ((metadata_battery['installed_system_first_costs'] * Rated_Battery_Size) + \
        metadata_battery['fixed_O&M_costs'] * battery_present + metadata_battery['variable_O&M_costs'] * Rated_Battery_Size)

        Participant = 1 if ev_participating else 0
        V1G = Participant * ACCF_V1G * \
              (metadata_V1G['marginal_purchase_price'] + metadata_V1G['marginal_installation_time'] *
               Average_Hourly_Labor_Cost_electrician + metadata_V1G['marginal_installation_capital'])

        V2G = Participant * ACCF_V2G * \
              (metadata_V2G['marginal_purchase_price'] + metadata_V2G['marginal_installation_time'] *
               Average_Hourly_Labor_Cost_electrician + metadata_V2G['marginal_installation_capital'])

        Participant = 1 if pv_participating else 0
        if Customer_class == 'residential':
            if Rated_System_Size < 2:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['<2']
            elif Rated_System_Size < 3:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['2-3']
            elif Rated_System_Size < 4:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['3-4']
            elif Rated_System_Size < 5:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['4-5']
            elif Rated_System_Size < 6:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['5-6']
            elif Rated_System_Size < 7:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['6-7']
            elif Rated_System_Size < 8:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['7-8']
            elif Rated_System_Size < 9:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['8-9']
            elif Rated_System_Size < 10:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['9-10']
            elif Rated_System_Size < 11:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['10-11']
            elif Rated_System_Size < 12:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['11-12']
            else:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['>12']
        elif Customer_class == 'commercial':
            if Rated_System_Size < 10:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['<10']
            elif Rated_System_Size < 20:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['10-20']
            elif Rated_System_Size < 50:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['20-50']
            elif Rated_System_Size < 100:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['50-100']
            elif Rated_System_Size < 250:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['100-250']
            elif Rated_System_Size < 500:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['250-500']
            elif Rated_System_Size < 1000:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['500-1000']
            else:
                installed_price_per_kW = metadata_PV['installed_price_per_kW'][Customer_class]['>1000']

        PV_present = 1 if Rated_System_Size > 0 else 0
        PV = Participant * ACCF_PV * ((installed_price_per_kW * Rated_System_Size) +
                                      (PV_present * metadata_PV['operating_expenses'][Customer_class]))

        if Customer_class == 'commercial':
            UnitaryHVAC = 0

            ACCF_comHVAC = metadata_general['ACCF'][Customer_class]['smart_large_HVAC_marginal'][Building_type.lower()]

            Participant = 1 if hvac_participating else 0
            Number_of_Zones = GLD_metadata['billingmeters'][customer]['sqft'] / 2500
            LgHVAC = Participant * ACCF_comHVAC * (metadata_thermostat['marginal_purchase_price'] * Number_of_Zones)

        elif Customer_class == 'residential':
            LgHVAC = 0
            Number_of_Zones = 1

            ACCF_thermostat = metadata_general['ACCF'][Customer_class]['smart_thermostat_marginal'][Building_type.lower()]
            Participant = 1 if hvac_participating else 0
            UnitaryHVAC = Participant * Number_of_Zones * ACCF_thermostat * \
                          (metadata_thermostat['marginal_purchase_price'] +
                           metadata_thermostat['marginal_installation_time_hrs'] *
                           Average_Hourly_Labor_Cost_maintenance_repair +
                           metadata_thermostat['marginal_installation_capital'])

        Bills = customer_bill['BillsFix']['TotalFix'] + customer_bill['BillsTransactive']['TotalDyn']
        # fed_corporate_income_tax = metadata['general']['fed_corporate_income_tax']
        # state_income_tax = metadata['general']['state_income_tax']
        # Depreciation = 0 # Please retain this field in the Cusomter CFS but assign it a value of Zero for the DSO+T analsysis
        # Deductions = Bills * metadata_general['tax_bill_deduction'][Customer_class][Building_type.lower()]

        IncomeAllocation = Bills

        ElectricityExpense = Bills * metadata_general['tax_bill_deduction'][Customer_class][Building_type.lower()]

        TaxCredits = 0

        Customer_Cash_Flows_dict = {
            'Customer_name': customer,
            'Scenario': 'TBD',  # 'Moderate Renewables Scenario'
            'Case': 'TBD',  # 'Batteries Case' 'Flexible Loads Case'
            'Customer_class': Customer_class,
            'Building_type': Building_type,
            'DER_Type': 'TBD',
            'participating': cust_participating,

            # Bills coming from Hayden
            'Bills': customer_bill,

            'Capital': {
                'Investment': {
                    'UnitaryHVAC': UnitaryHVAC,
                    'WaterHeater': WaterHeater,
                    'LgHVAC': LgHVAC,
                    'Battery': Battery,
                    'V1G': V1G,
                    'V2G': V2G
                },
                'PV': PV
            },
            'Revenues': {
                'IncomeAllocation': IncomeAllocation,
                # 'Incentives': 0, # customer_metadata['incentive_for_DER_participation'],
                'PerformancePayments': 0,
                'DSOShare': 0  # customer_metadata['DSO_rebate']
            },
            'Taxes': {
                # 'Depreciation': Depreciation,
                # 'Deductions': Deductions,
                'ElectricityExpense': ElectricityExpense,
                'TaxCredits': TaxCredits
            },
            'NetEnergyCost': 0,
            'EnergyPurchased': 0,
            'EffectiveCostEnergy': 0
        }

        Investment = UnitaryHVAC + WaterHeater + LgHVAC + Battery + V1G + V2G
        Capital = Investment + PV
        Expenses = Bills  # ?
        Revenues = 0  # Incentives + DSOShare

        PurchasesFix = returnDictSum(customer_bill['BillsFix']['PurchasesFix'])
        EnergyFix = customer_bill['BillsFix']['PurchasesFix']['EnergyFix']
        DemandCharges = customer_bill['BillsFix']['PurchasesFix']['DemandCharges']
        ConnChargesFix = customer_bill['BillsFix']['ConnChargesFix']

        BillsFix = customer_bill['BillsFix']['TotalFix']

        PurchasesDyn = returnDictSum(customer_bill['BillsTransactive']['PurchasesDyn'])
        DAEnergy = customer_bill['BillsTransactive']['PurchasesDyn']['DAEnergy']
        RTEnergy = customer_bill['BillsTransactive']['PurchasesDyn']['RTEnergy']
        DistCharges = customer_bill['BillsTransactive']['DistCharges']
        ConnChargesDyn = customer_bill['BillsTransactive']['ConnChargesDyn']

        BillsTransactive = customer_bill['BillsTransactive']['TotalDyn']

        Bills = BillsFix + BillsTransactive

        Taxes = ElectricityExpense - TaxCredits

        NetEnergyCost = Capital + Expenses + Taxes - Revenues

        FixedEnergy = BillsFix
        # EnergyPurchased = FixedEnergy + DAEnergy + RTEnergy
        EnergyPurchased = customer_bill['EnergyQuantity']
        EffectiveCostEnergy = NetEnergyCost / EnergyPurchased

        Customer_Cash_Flows_csv = {
            'Bills': Bills,
            'BillsFix': BillsFix,
            'EnergyFix': EnergyFix,
            'DemandCharges': DemandCharges,
            'ConnChargesFix': ConnChargesFix,
            'BillsTransactive': BillsTransactive,
            'DAEnergy': DAEnergy,
            'RTEnergy': RTEnergy,
            'DistCharges': DistCharges,
            'ConnChargesDyn': ConnChargesDyn,
            'Capital': Capital,
            'Investment': Investment,
            'UnitaryHVAC': UnitaryHVAC,
            'WaterHeater': WaterHeater,
            'LgHVAC': LgHVAC,
            'Battery': Battery,
            'V1G': V1G,
            'V2G': V2G,
            'PV': PV,
            'Revenues': 0,
            'IncomeAllocation': IncomeAllocation,
            'PerformancePayments': 0,
            'DSOShare': 0,
            'Taxes': 0,
            'ElectricityExpense': ElectricityExpense,
            'TaxCredits': 0,
            'NetEnergyCost': NetEnergyCost,
            'EnergyPurchased': EnergyPurchased,
            'BlendedRate': customer_bill['BlendedRate'],
            'EffectiveCostEnergy': EffectiveCostEnergy
        }

        return Customer_Cash_Flows_dict, Customer_Cash_Flows_csv


if __name__ == '__main__':
    '''
    dso_paths = ['D:/DSOT/20160807_5d_lean_batt_acd8c80b/DSO_1',
                 'D:/DSOT/20160807_5d_lean_batt_acd8c80b/DSO_2',
                 'D:/DSOT/20160807_5d_lean_batt_acd8c80b/DSO_3']

    dso_paths = ['D:/DSOT/Base_858c4e40/2016_02/DSO_1',
                 'D:/DSOT/Base_858c4e40/2016_02/DSO_2',
                 'D:/DSOT/Base_858c4e40/2016_02/DSO_3']

    base_case = 'D:/DSOT/Base_858c4e40/2016_02'

    # meta_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/metadata'
    meta_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/tesp-private/examples/analysis/dsot/data'

    path_to_write = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/test_save_files'
    save_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/test_save_files'
    '''

    Customer_Cash_Flows_dict, Customer_Cash_Flows_csv = customer_CFS(GLD_metadata,
                                                                     metadata_path,
                                                                     customer,
                                                                     customer_bill)
