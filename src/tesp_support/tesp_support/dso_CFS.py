# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: dso_CFS.py
"""
@author: yint392
"""
# all CFSs should be annually
# but each folder is monthly data

import sys
import os
from os.path import dirname, abspath, join
import pandas as pd
import json
import seaborn as sns
from datetime import datetime, date, timedelta
import math
import h5py
import errno
import numpy as np
import tesp_support.dso_helper_functions as tesp


# This dso_CFS function calculates cash flow statement ...

# inputs:
# dso number

# path_to_write: path to write the balance sheet
# save_path: path to save some calculated values, especially the ones that take a long time

# outputs: DSO CFS and parts (as python dictionaries or .csv)

# 12 paths to 12 months
# under each month, the dso and substation paths should be the same





def dso_CFS(case_config,
            DSOmetadata,
            dso_num,
            DSO_peak_demand,
            DSO_base_case_peak_demand,
            DSO_Cash_Flows,
            DSO_Revenues_and_Energy_Sales,
            Market_Purchases,
            Market_Purchases_base_case):

    ### reading json data
    # with open(os.path.join(metadata_path, '8-node-metadata.json')) as json_file:
    #    metadata_8_node = json.load(json_file)

    metadata_8_node = DSOmetadata

    # with open(os.path.join(metadata_path, 'metadata-general.json')) as json_file:
    #     metadata_gen = json.load(json_file)

    metadata_gen = DSOmetadata

    ## assuming glm_dict is the same for different months?
    # with open(os.path.join(dso_path, [f for f in os.listdir(dso_path) if f.endswith('glm_dict.json')][0])) as json_file:  # should it be Substation_path?
    #     glm_dict = json.load(json_file)

    # with open(os.path.join(config_path, 'system_case_config.json')) as json_file:
    #     system_case_config = json.load(json_file)

    system_case_config = case_config

    TransactiveCaseFlag = system_case_config["caseType"]["bt"] or system_case_config["caseType"]["fl"]
    # placeholder for testing
    # TransactiveCaseFlag = 1

    dso_name = 'dso_' + str(dso_num)

    metadata_general = metadata_gen["general"]
    metadata_dso = metadata_8_node[dso_name.upper()]
    utility_type = metadata_dso["utility_type"]
    ACCF_distribution_infrastructure = metadata_general['ACCF']['grid_assets']['distribution_owner'][utility_type]['distribution_infrastructure']
    ACCF_controls_and_software = metadata_general['ACCF']['grid_assets']['distribution_owner'][utility_type]['controls_and_software']

    substation_costs = metadata_general['substation_costs']

    substation_new_cost_per_kVA = substation_costs['substation_new_cost_per_kVA'][utility_type]
    substation_upgrade_cost_per_kVA = substation_costs['substation_upgrade_cost_per_kVA'][utility_type]

    power_factor_peak = metadata_general['power_factor_peak']
    frac_exist_sub_built_new = substation_costs['frac_exist_sub_built_new']

    pddn_f = substation_costs['peak_demand_density_normalized']['fully-developed']
    pddn_u = substation_costs['peak_demand_density_normalized']['undeveloped']
    sasfd = substation_costs['service_area_share_fully_developed'][utility_type]
    years_greenfield = substation_costs['years_greenfield']

    GreenfieldGrowthLocalSub = ((pddn_f / pddn_u )**(1 / years_greenfield)) - 1

    CapacityMarginBrown = 1 - 1 / ((1+substation_costs['brownfield_growth_rate_dso_total'][utility_type]) **
                                   substation_costs['years_sub_design_life'])

    CapacityMarginGreen = 1 - ( (1 - CapacityMarginBrown)  *  pddn_u  /  pddn_f )

    PeakDemandDensityNormGreen = (pddn_f -  pddn_u ) / np.log( pddn_f / pddn_u )

    ShareGreenfield = ( substation_costs['greenfield_growth_rate_dso_total'][utility_type]  /  ( GreenfieldGrowthLocalSub * PeakDemandDensityNormGreen )  *
                        ((pddn_u * (1-sasfd)) + (pddn_f * sasfd))) / \
          (   1  +  ( substation_costs['greenfield_growth_rate_dso_total'][utility_type]  /  ( GreenfieldGrowthLocalSub * PeakDemandDensityNormGreen ) *
                      (pddn_u - PeakDemandDensityNormGreen)))

    ShareUndeveloped = 1  -  ShareGreenfield  -  sasfd

    if TransactiveCaseFlag:
        FracPeakDemandReduction = (DSO_base_case_peak_demand - DSO_peak_demand) / DSO_base_case_peak_demand
    else:
        FracPeakDemandReduction = 0

    SubFleetCapacityFactorBrown = (( 1 - CapacityMarginBrown )  -  ( 1 / (1- FracPeakDemandReduction) ) )  / \
                                  (np.log( 1 - FracPeakDemandReduction )  +  np.log( 1 - CapacityMarginBrown ))

    SubFleetCapacityFactorGreen = (   ( 1 - CapacityMarginBrown )  *  ( 1  - (pddn_u/ pddn_f)   ))      / \
                     (   ( 1 - FracPeakDemandReduction )  *   np.log( pddn_f / pddn_u )   )

    PeakDemandDensityTotal = (   pddn_u *  ShareUndeveloped   )  + \
    (   PeakDemandDensityNormGreen * ShareGreenfield   )  + (  pddn_f * sasfd  )

    SubExistCapacityDeveloped = DSO_base_case_peak_demand * pddn_f * sasfd /  \
                          ( SubFleetCapacityFactorBrown * power_factor_peak * PeakDemandDensityTotal )

    SubExistCapacityGreenfield = DSO_base_case_peak_demand * PeakDemandDensityNormGreen * ShareGreenfield /  \
                                 ( SubFleetCapacityFactorGreen * power_factor_peak * PeakDemandDensityTotal )
    SubExistCapacityUndeveloped = DSO_base_case_peak_demand * pddn_u * ShareUndeveloped / \
                   ( SubFleetCapacityFactorBrown * power_factor_peak * PeakDemandDensityTotal )

    NoSubstations = SubExistCapacityUndeveloped * power_factor_peak / substation_costs['substation_capacity_avg']['undeveloped'] + \
    SubExistCapacityGreenfield * power_factor_peak / substation_costs['substation_capacity_avg']['greenfield'] + \
    SubExistCapacityDeveloped * power_factor_peak / substation_costs['substation_capacity_avg']['fully-developed']

    SubConstructAnnualCapacity = ((max(0, substation_costs['brownfield_growth_rate_dso_total'][utility_type]) + 1/years_greenfield) * (pddn_f - pddn_u) *
                                  ShareGreenfield * (DSO_base_case_peak_demand / power_factor_peak )) / (PeakDemandDensityTotal * (1 - CapacityMarginBrown))

    SubUpAnnualCapacity = (max(0, substation_costs['brownfield_growth_rate_dso_total'][utility_type]) * SubExistCapacityUndeveloped ) + \
    (max(0, substation_costs['brownfield_growth_rate_dso_total'][utility_type]) * SubExistCapacityDeveloped )

    SubExistCostPerKva = (frac_exist_sub_built_new  *  substation_new_cost_per_kVA   +
                          (1 - frac_exist_sub_built_new)  *  substation_upgrade_cost_per_kVA)

    SubsExistCapitalCost = ( SubExistCapacityUndeveloped + SubExistCapacityGreenfield + SubExistCapacityDeveloped ) * \
                           SubExistCostPerKva * 1000 / 1000
    SubsAddedAnnualCapitalCost = (SubConstructAnnualCapacity * substation_new_cost_per_kVA + SubUpAnnualCapacity * substation_upgrade_cost_per_kVA) * 1000 / 1000

    Substations = (SubsExistCapitalCost + SubsAddedAnnualCapitalCost) * ACCF_distribution_infrastructure

    Feeders = metadata_general["feeder_capital_cost_per_MVA"][utility_type] * DSO_base_case_peak_demand / \
    power_factor_peak * ACCF_distribution_infrastructure * \
    (1 + substation_costs['greenfield_growth_rate_dso_total'][utility_type] +
      substation_costs['brownfield_growth_rate_dso_total'][utility_type]) / 1000

    number_of_customers = metadata_dso['number_of_customers']

    meter_cost = lambda type: metadata_8_node["general"]['meter_cost'][type] * number_of_customers * \
                              metadata_dso['RCI customer count mix'][type]

    Meters = (meter_cost('residential') + meter_cost('commercial')+ meter_cost('industrial')) * \
    ACCF_distribution_infrastructure * \
    (1 + substation_costs['greenfield_growth_rate_dso_total'][utility_type] +
     metadata_general['brownfield_growth_new_meters_frac'] *
     substation_costs['brownfield_growth_rate_dso_total'][utility_type]) / 1000


    MktHdw = (NoSubstations + 1) * \
    (metadata_general['market_operations']['hardware']['per_substation']
         +  (metadata_general['market_operations']['hardware']['per_customer'] * number_of_customers / 1000 / NoSubstations) ) * \
    ACCF_controls_and_software * TransactiveCaseFlag / 1000

    market_operations_software = metadata_general['market_operations']['software']

    MktSoft = (market_operations_software['constant'] +
    market_operations_software['per_customer'] * number_of_customers / 1000 +
    (market_operations_software['per_customer^1/2']  * (number_of_customers / 1000) ** (1/2)) +
    NoSubstations * market_operations_software['per_substation'] ) * \
    ACCF_controls_and_software * TransactiveCaseFlag / 1000


    AmiNetwork = metadata_general['AMI_DER_network'][utility_type] * number_of_customers * ACCF_controls_and_software / 1000
    DER_network_transactive_increase = metadata_general['DER_network_transactive_increase']
    DerNetwork = AmiNetwork * TransactiveCaseFlag * DER_network_transactive_increase

    Upfront_DA_Network_Capital_Costs = metadata_general['DA_network']['upfront_DA_network_capital_costs']
    # Annual_O_and_M_Costs = metadata_general['DA_network']['DA_network_O&M_costs']

    DaNetwork = Upfront_DA_Network_Capital_Costs * ACCF_controls_and_software * number_of_customers / 1000


    software = lambda type: (metadata_general['software'][type]['constant'] +
    number_of_customers * metadata_general['software'][type]['per_customer'] / 1000 +
    (number_of_customers * (metadata_general['software'][type]['per_customer^1/2']  / 1000) ** (1/2)) +
    (NoSubstations * metadata_general['software'][type]['per_substation']) ) * ACCF_controls_and_software / 1000

    DmsSoft = software('DMS_software')
    OmsSoft = software('OMS_software')
    CisSoft = software('CIS_software')
    BillingSoft = software('billing_software')

    # Calculate the change in capacity market price due to load reduction and then the total capacity payment
    CapacityPriceFactor = 1 - (metadata_general['generation_capacity_price_elast_factor'] *
                               (DSO_base_case_peak_demand - DSO_peak_demand) / DSO_base_case_peak_demand)
    PeakCapacity = metadata_general['generation_capacity_fee_per_kW'] * CapacityPriceFactor * DSO_peak_demand * \
                   metadata_general['generation_capacity_reserve'] * 1000 / 1000

    EnergyQuantityPurchased_base_case = Market_Purchases_base_case['WhEnergyPurchases']['WhDAPurchases']['WhDAEnergy'] + \
                                        Market_Purchases_base_case['WhEnergyPurchases']['WhRTPurchases']['WhRTEnergy'] + \
                                        Market_Purchases_base_case['WhEnergyPurchases']['WhBLPurchases']['WhBLEnergy']

    WhDAQPurchases = Market_Purchases['WhEnergyPurchases']['WhDAPurchases']['WhDAEnergy'] # Day-ahead energy volume
    WhRTQPurchases = Market_Purchases['WhEnergyPurchases']['WhRTPurchases']['WhRTEnergy'] # Real-time energy volume
    WhBLQPurchases = Market_Purchases['WhEnergyPurchases']['WhBLPurchases']['WhBLEnergy'] # Bilateral energy volume

    EnergyQuantityPurchased = WhDAQPurchases + WhRTQPurchases + WhBLQPurchases

    WhDAPurchases = Market_Purchases['WhEnergyPurchases']['WhDAPurchases']['WhDACosts'] # Day-ahead energy cost
    WhRTPurchases = Market_Purchases['WhEnergyPurchases']['WhRTPurchases']['WhRTCosts'] # Real-time energy cost
    WhBLPurchases = Market_Purchases['WhEnergyPurchases']['WhBLPurchases']['WhBLCosts'] # Bilateral energy cost

    EnergyPurchased = WhDAPurchases + WhRTPurchases + WhBLPurchases

    transmission_access_fee_per_MWh = metadata_general['transmission_access_fee_per_MWh']
    TransCharges = transmission_access_fee_per_MWh * EnergyQuantityPurchased_base_case  / 1000 + \
                   (DSO_peak_demand - DSO_base_case_peak_demand) * 1000 * metadata_general['transmission_capital_cost_per_kW']/1000 * \
                   metadata_general['ACCF']['grid_assets']['transmission_owner']['transmission_infrastructure'] * \
                   metadata_general['transmission_capital_benefit_factor']


    WhReserves = EnergyQuantityPurchased * \
                 ( ( system_case_config['reserveUp'] - metadata_general['reserve']['regulation_fraction'] ) *
                   ( metadata_general['reserve']['spinning_reserve_cost'] + metadata_general['reserve']['non_spinning_reserve_cost']) +
                   metadata_general['reserve']['regulation_fraction'] * metadata_general['reserve']['regulation_cost'] ) /1000

    # 0 for now
    WhLosses = Market_Purchases['OtherWholesale']['WhLosses']

    iso_energy_fee = metadata_general['iso_energy_fee']
    WhISO = iso_energy_fee * EnergyQuantityPurchased_base_case  / 1000




    RetailDAEnergy = tesp.returnDictSum(DSO_Revenues_and_Energy_Sales['RetailSales']['TransactiveSales']['RetailDAEnergy'])
    RetailRTEnergy = tesp.returnDictSum(DSO_Revenues_and_Energy_Sales['RetailSales']['TransactiveSales']['RetailRTEnergy'])
    TransactFees = metadata_general['dso_transaction_fee_per_KWh']  *  ( RetailDAEnergy + RetailRTEnergy ) /1000 * 1000



    EnergySold = DSO_Revenues_and_Energy_Sales['EnergySold']
    O_and_M_Materials  =  metadata_general['O&M_material_cost_per_kWh'] * EnergySold * 1000 / 1000


    # labor

    if TransactiveCaseFlag:
        MktOpsLev1Fte, MktOpsFte, MktOpsLev1Cost, MktOpsLeaderRatio, MktOpsLabor, MktOpsLeaderLevel = \
            tesp.labor_transactive('market_operations', metadata_general, metadata_dso, utility_type, NoSubstations, TransactiveCaseFlag)
        DerRecruiterLev1Fte, DerRecruiterFte, DerRecruiterLev1Cost, DerRecruiterLeaderRatio, AssetR_R, DerRecruiterLeaderLevel = \
            tesp.labor_transactive('DER_recruiter', metadata_general, metadata_dso, utility_type, NoSubstations, TransactiveCaseFlag)

        DerNetLev1Fte, DerNetFte, DerNetLev1Cost, DerNetLeaderRatio, CustNetworkLabor, DerNetworkLeaderLevel = \
            tesp.labor_network_admin_transactive('DER_network_labor_ratios',
                                                                              'network_admin_hourly_rate',
                                                                              metadata_general,
                                                                              metadata_dso, utility_type, NoSubstations,
                                                                              TransactiveCaseFlag)

        DerCyberLev1Fte, DerCyberFte, DerCyberLev1Cost, DerCyberLeaderRatio, CustCyberLabor, DerCyberLeaderLevel = \
            tesp.labor_network_admin_transactive('DER_cyber_labor_ratios',
                                                                              'cyber_analyst_hourly_rate',
                                                                              metadata_general,
                                                                              metadata_dso, utility_type, NoSubstations,
                                                                              TransactiveCaseFlag)
    else:
        MktOpsLev1Fte, MktOpsFte, MktOpsLev1Cost, MktOpsLeaderRatio, MktOpsLabor, MktOpsLeaderLevel = 0,0,0,0,0,0
        DerRecruiterLev1Fte, DerRecruiterFte, DerRecruiterLev1Cost, DerRecruiterLeaderRatio, AssetR_R, DerRecruiterLeaderLevel = 0,0,0,0,0,0
        DerNetLev1Fte, DerNetFte, DerNetLev1Cost, DerNetLeaderRatio, CustNetworkLabor, DerNetworkLeaderLevel = 0,0,0,0,0,0
        DerCyberLev1Fte, DerCyberFte, DerCyberLev1Cost, DerCyberLeaderRatio, CustCyberLabor, DerCyberLeaderLevel = 0,0,0,0,0,0

    CustomerServiceAgentLev1Fte, CustomerServiceAgentFte, CustomerServiceAgentLev1Cost, \
    CustomerServiceAgentLeaderRatio, CustomerServiceAgent, CustomerServiceAgentLeaderLevel = \
        tesp.labor('customer_service_agent', metadata_general, metadata_dso, utility_type, NoSubstations)

    LinemenLev1Fte, LinemenFte, LinemenLev1Cost, LinemenLeaderRatio, Linemen, LinemenLeaderLevel = \
        tesp.labor('linemen', metadata_general, metadata_dso, utility_type, NoSubstations)
    OperatorLev1Fte, OperatorFte, OperatorLev1Cost, OperatorLeaderRatio, Operators, OperatorLeaderLevel = \
        tesp.labor('operator', metadata_general, metadata_dso, utility_type, NoSubstations)
    PlanningLev1Fte, PlanningFte, PlanningLev1Cost ,PlanningLeaderRatio, Planning, PlanningLeaderLevel = \
        tesp.labor('planning', metadata_general, metadata_dso, utility_type, NoSubstations)

    MeteringLev1Fte, MeteringFte, MeteringLev1Cost, MeteringLeaderRatio, Metering, MeteringLeaderLevel = \
        tesp.labor('metering', metadata_general, metadata_dso, utility_type, NoSubstations)

    DmsNetLev1Fte, DmsNetFte, DmsNetLev1Cost ,DmsNetLeaderRatio, DmsNetworkLabor, DmsNetLeaderLevel = \
        tesp.labor_network_admin('DMS_network_labor_ratios', 'network_admin_hourly_rate',
                            metadata_general, metadata_dso, utility_type, NoSubstations)
    DmsCyberLev1Fte, DmsCyberFte, DmsCyberLev1Cost, DmsCyberLeaderRatio, DmsCyberLabor, DmsCyberLeaderLevel = \
        tesp.labor_network_admin('DMS_cyber_labor_ratios', 'cyber_analyst_hourly_rate',
              metadata_general, metadata_dso, utility_type, NoSubstations)

    BusinessNetworkTotalLabor = DmsNetworkLabor + DmsCyberLabor
    BusinessNetworkFte = DmsNetFte + DmsCyberFte

    LegalLev1Fte, LegalFte, LawyerLev1Cost, LawyerLeaderRatio, LegalLabor, LawyerLeaderLevel = \
        tesp.labor('corporate_lawyer', metadata_general, metadata_dso, utility_type, NoSubstations)

    HRLev1Fte, HRFte, HRLev1Cost, HRLeaderRatio, HRLabor, HRLeaderLevel = \
        tesp.labor('human_resources', metadata_general, metadata_dso, utility_type, NoSubstations)

    AccountingLev1Fte, AccountingFte, AccountingLev1Cost, AccountingLeaderRatio, AccountingLabor, AccountingLeaderLevel = \
        tesp.labor('accounting', metadata_general, metadata_dso, utility_type, NoSubstations)

    EconomicsLev1Fte, EconomicsFte, EconomicsLev1Cost, EconomicsLeaderRatio, EconomicsLabor, EconomicsLeaderLevel = \
        tesp.labor('economist', metadata_general, metadata_dso, utility_type, NoSubstations)



    BillingLev1Fte, BillingFte, BillingLev1Cost, BillingLeaderRatio, Billing, BillingLeaderLevel = \
        tesp.labor_increase('billing', metadata_general, metadata_dso, utility_type, NoSubstations, TransactiveCaseFlag)

    AmiCyberLev1Fte, AmiCyberFte, AmiCyberLev1Cost, AmiCyberLeaderRatio, AmiCyberLabor, AmiCyberLeaderLevel = \
        tesp.labor_network_admin_increase('AMI_cyber_labor_ratios', 'cyber_analyst_hourly_rate', metadata_general,
                                     metadata_dso, utility_type, NoSubstations, TransactiveCaseFlag)

    AmiNetLev1Fte, AmiNetFte, AmiNetLev1Cost, AmiNetLeaderRatio, AmiNetworkLabor, AmiNetworkLeaderLevel = \
        tesp.labor_network_admin_increase('AMI_network_labor_ratios', 'network_admin_hourly_rate', metadata_general,
                                     metadata_dso, utility_type, NoSubstations, TransactiveCaseFlag)




    AdminLev1Fte, AdminFte, AdminLev1Cost, AdminLeaderRatio, AdminLabor, AdminLeaderLevel = \
        tesp.labor('admin', metadata_general, metadata_dso, utility_type, NoSubstations)

    PRLev1Fte, PRFte, PRLev1Cost, PRLeaderRatio, PRLabor, PRLeaderLevel = \
        tesp.labor('public_relations', metadata_general, metadata_dso, utility_type, NoSubstations)


    team_salary_escalation_1 = metadata_general['labor']['team_salary_escalation_1']
    CroLevel = CustomerServiceAgentLeaderLevel
    CroCost = CustomerServiceAgentLeaderRatio * CustomerServiceAgentLev1Cost

    CooLevel = LinemenLeaderLevel
    CooCost = LinemenLeaderRatio * LinemenLev1Cost

    ChoLevel = HRLeaderLevel
    ChoCost = HRLeaderRatio * HRLev1Cost

    CloLevel = LawyerLeaderLevel
    CloCost = LawyerLeaderRatio * LawyerLev1Cost

    if (AmiNetFte + AmiCyberFte + DerNetFte + DerCyberFte + DmsNetFte + DmsCyberFte) <=5:
        CioLevel = 0
        CioCost = 0
    else:
        CioLevel = max(AmiNetworkLeaderLevel, AmiCyberLeaderLevel, DerNetworkLeaderLevel, DerCyberLeaderLevel,
                       DmsNetLeaderLevel, DmsCyberLeaderLevel ) +  1
        CioCost = max(AmiNetLeaderRatio * (team_salary_escalation_1**AmiNetworkLeaderLevel) * AmiNetLev1Cost,
                      AmiCyberLeaderRatio * (team_salary_escalation_1**AmiCyberLeaderLevel) * AmiCyberLev1Cost,
                      DerNetLeaderRatio * (team_salary_escalation_1**DerNetworkLeaderLevel) * DerNetLev1Cost,
                      DerCyberLeaderRatio * (team_salary_escalation_1**DerCyberLeaderLevel) * DerCyberLev1Cost,
                      DmsNetLeaderRatio * (team_salary_escalation_1**DmsNetLeaderLevel) * DmsNetLev1Cost,
                      DmsCyberLeaderRatio * (team_salary_escalation_1**DmsCyberLeaderLevel) * DmsCyberLev1Cost)

    if AccountingFte  +  EconomicsFte <= 5:
        CfoLevel = 0
        CfoCost = 0
    else:
        CfoLevel = max(AccountingLeaderLevel, EconomicsLeaderLevel) +  1
        CfoCost = max(AccountingLeaderRatio * (team_salary_escalation_1**AccountingLeaderLevel) * AccountingLev1Cost,
                      EconomicsLeaderRatio * (team_salary_escalation_1**EconomicsLeaderLevel) * EconomicsLev1Cost)

    CeoCost = max(CfoCost * (team_salary_escalation_1**CfoLevel),
                  CloCost * (team_salary_escalation_1**CloLevel),
                  ChoCost * (team_salary_escalation_1**ChoLevel),
                  CioCost * (team_salary_escalation_1**CioLevel),
                  CooCost * (team_salary_escalation_1**CooLevel),
                  CroCost * (team_salary_escalation_1**CroLevel))


    Admin = (CeoCost + CfoCost + CloCost + ChoCost + CioCost) / 1000 + LegalLabor + HRLabor + \
            AccountingLabor + EconomicsLabor + PRLabor + AdminLabor + BusinessNetworkTotalLabor

    CioLevel_bool = 1 if CioLevel > 0 else 0
    CfoLevel_bool = 1 if CfoLevel > 0 else 0

    linemen_sqft_employee = metadata_general['workspace_costs']['linemen_sqft_employee']
    office_sqft_employee = metadata_general['workspace_costs']['office_sqft_employee']
    industrial_workspace_costs = metadata_general['workspace_costs']['industrial_workspace_costs'][utility_type]
    office_workspace_costs = metadata_general['workspace_costs']['office_workspace_costs'][utility_type]
    Space = LinemenLev1Fte * linemen_sqft_employee * industrial_workspace_costs / 1000 + \
            (LinemenFte - LinemenLev1Fte +  MktOpsFte +  CustomerServiceAgentFte +  DerRecruiterFte +
             BillingFte +  AmiNetFte +  AmiCyberFte +  DerNetFte +  DerCyberFte +
             OperatorFte + PlanningFte + AdminFte + DmsNetFte + DmsCyberFte + BusinessNetworkFte + LegalFte +
             HRFte + AccountingFte + EconomicsFte + PRFte + 1 + CioLevel_bool + CfoLevel_bool) * \
            office_sqft_employee * office_workspace_costs / 1000


    DOtoMO = 0
    RSPtoMO = 0 #MktSoft + MktHdw + MktOpsLabor


    CapitalExpenses_dict = {
            'DistPlant': {
            'Substations': Substations,
            'Feeders': Feeders,
            'Meters': Meters
            },
            'InfoTech': {
            'MktSoftHdw': {'MktSoft': MktSoft,
                           'MktHdw': MktHdw
                           },
            'AMIDERNetwork': {
                'AmiNetwork': AmiNetwork,
                'DerNetwork': DerNetwork
            },
            'DaNetwork': DaNetwork,
            'DmsSoft': DmsSoft,
            'OmsSoft': OmsSoft,
            'CisSoft': CisSoft,
            'BillingSoft': BillingSoft
            }
        }

    MOtoDO = 0
    MOtoRSP = 0
    DOtoRSP = 0

    Revenues_dict = {
        'RetailSales': DSO_Cash_Flows['Revenues']['RetailSales'],

        'TransactFees': TransactFees,
        'TransTo': {'TransToMO': {
            'MOtoDO': MOtoDO,
            'MOtoRSP': MOtoRSP
        },
            'TransToDO': {
                'DOtoRSP': DOtoRSP
            }
        }
    }


    RSPtoDO = 0 #tesp.returnDictSum(Revenues_dict) - (MktSoft + MktHdw + MktOpsLabor)

    #Revenues = tesp.returnDictSum(Revenues_dict)
    #TaxesRevenues = Revenues * metadata_general['effective_income_tax_rate'][utility_type]


    # a separate function?
    OperatingExpenses_dict = {'PeakCapacity': PeakCapacity,
                     'TransCharges': TransCharges,
                     'WhEnergyPurchases': {
                         'WhDAPurchases': WhDAPurchases,
                         'WhRTPurchases': WhRTPurchases,
                         'WhBLPurchases': WhBLPurchases
                     },
                     'OtherWholesale': {
                         'WhReserves': WhReserves,
                         'WhLosses': WhLosses,
                         'WhISO': WhISO
                     },
                     'O&mMaterials': O_and_M_Materials,
                     'O&mLabor': {
                         'Linemen': Linemen,
                         'Operators': Operators,
                         'Planning': Planning,
                         'Metering': Metering
                     },
                     'MktOpsLabor': MktOpsLabor,
                     'AmiCustOps': {
                         'AmiOps': {
                             'AmiNetworkLabor': AmiNetworkLabor,
                             'AmiCyberLabor': AmiCyberLabor
                         },
                         'CustOps': {
                             'CustNetworkLabor': CustNetworkLabor,
                             'CustCyberLabor': CustCyberLabor
                         },
                         'DmsOps': {
                             'DmsNetworkLabor': DmsNetworkLabor,
                             'DmsCyberLabor': DmsCyberLabor
                         }
                     },
                     'RetailOps': {
                         'CustomerService': CustomerServiceAgent,
                         'AssetR&R': AssetR_R,
                         'Billing': Billing
                     },
                     'Admin': Admin,
                     'Space': Space,
                     'TransFrom': {
                         'TransFromDO':
                             {'DOtoMO': DOtoMO},
                         'TransFromRSP':
                             {'RSPtoMO': RSPtoMO,
                              'RSPtoDO': RSPtoDO}
                     }
                     }

    OperatingExpenses = tesp.returnDictSum(OperatingExpenses_dict)
    #TaxExpDeduct = Expenses * metadata_general['effective_income_tax_rate'][utility_type]
    #Taxes = TaxesRevenues + TaxExpDeduct

    NetIncome = tesp.returnDictSum(Revenues_dict) - \
                tesp.returnDictSum(CapitalExpenses_dict) - \
                tesp.returnDictSum(OperatingExpenses_dict)

    DSO_Cash_Flows_dict = {
        'CapitalExpenses': CapitalExpenses_dict,
        'OperatingExpenses': OperatingExpenses_dict,
        'Revenues': Revenues_dict,
        'NetIncome': NetIncome,
        'Balance': 0
        # 'Return on Equity': 0
    }

    DistPlant = Substations + Feeders + Meters

    MktSoftHdw =  MktSoft + MktHdw
    AmiDerNetwork = AmiNetwork + DerNetwork
    InfoTech = MktSoftHdw + AmiDerNetwork + DaNetwork + DmsSoft + OmsSoft + CisSoft + BillingSoft

    CapitalExpenses = DistPlant + InfoTech

    WhEnergyPurchases = WhDAPurchases + WhRTPurchases + WhBLPurchases
    OtherWholesale = WhReserves + WhLosses + WhISO
    O_M_Labor = Linemen + Operators + Planning + Metering

    AmiOps = AmiNetworkLabor + AmiCyberLabor
    CustOps = CustNetworkLabor + CustCyberLabor
    AmiCustOps = AmiOps + CustOps

    DmsOps = DmsNetworkLabor + DmsCyberLabor

    RetailOps = CustomerServiceAgent + AssetR_R + Billing

    TransFromDO = DOtoMO
    TransFromRSP = RSPtoMO + RSPtoDO
    TransFrom = TransFromDO + TransFromRSP

    TransToMO = MOtoDO + MOtoRSP
    TransToDO = DOtoRSP
    TransTo = TransToMO + TransToDO

    OperatingExpenses = PeakCapacity + TransCharges + WhEnergyPurchases + OtherWholesale + O_and_M_Materials + \
               O_M_Labor + MktOpsLabor + AmiCustOps + \
               DmsOps + RetailOps + Admin + Space #+ TransFrom


    FixedSales = tesp.returnDictSum(DSO_Cash_Flows['Revenues']['RetailSales']['FixedSales'])
    TransactiveSales = tesp.returnDictSum(DSO_Cash_Flows['Revenues']['RetailSales']['TransactiveSales'])
    RetailSales = FixedSales + TransactiveSales

    Revenues = RetailSales # + TransactFees +

    DSO_Cash_Flows_composite = {
        'CapitalExpenses': CapitalExpenses,
        'DistPlant': DistPlant,
        'Substations': Substations,
        'Feeders': Feeders,
        'Meters': Meters,
        'InfoTech': InfoTech,
        'MktSoftHdw': MktSoftHdw,
        'MktSoft': MktSoft,
        'MktHdw': MktHdw,
        'AmiDerNetwork': AmiDerNetwork,
        'AmiNetwork': AmiNetwork,
        'DerNetwork': DerNetwork,
        'DaNetwork': DaNetwork,
        'DmsSoft': DmsSoft,
        'OmsSoft': OmsSoft,
        'CisSoft': CisSoft,
        'BillingSoft': BillingSoft,
        'OperatingExpenses': OperatingExpenses,
        'PeakCapacity': PeakCapacity,
        'TransCharges': TransCharges,
        'WhEnergyPurchases': WhEnergyPurchases,
        'WhDAPurchases': WhDAPurchases,
        'WhRTPurchases': WhRTPurchases,
        'WhBLPurchases': WhBLPurchases,
        'OtherWholesale': OtherWholesale,
        'WhReserves': WhReserves,
        'WhLosses': WhLosses,
        'WhISO': WhISO,
        'O&mMaterials': O_and_M_Materials,
        'O&mLabor': O_M_Labor,
        'Linemen': Linemen,
        'Operators': Operators,
        'Planning': Planning,
        'Metering': Metering,
        'MktOpsLabor': MktOpsLabor,
        'AmiCustOps': AmiCustOps,
        'AmiOps': AmiOps,
        'AmiNetworkLabor': AmiNetworkLabor,
        'AmiCyberLabor': AmiCyberLabor,
        'CustOps': CustOps,
        'CustNetworkLabor': CustNetworkLabor,
        'CustCyberLabor': CustCyberLabor,
        'DmsOps': DmsOps,
        'DmsNetworkLabor': DmsNetworkLabor,
        'DmsCyberLabor': DmsCyberLabor,
        'RetailOps': RetailOps,
        'CustomerService': CustomerServiceAgent,
        'AssetR&R': AssetR_R,
        'Billing': Billing,
        'Admin': Admin,
        'AdminDO': 0,
        'AdminMO': 0,
        'AdminRSP': 0,
        'Space': Space,
        'SpaceDO': 0,
        'SpaceMO': 0,
        'SpaceRSP': 0,
        'TransFrom': TransFrom,
        'TransFromDO': TransFromDO,
        'DOtoMO': DOtoMO,
        'TransFromRSP': TransFromRSP,
        'RSPtoMO': RSPtoMO,
        'RSPtoDO': RSPtoDO,
        'Revenues': Revenues,
        'RetailSales': RetailSales,
        'FixedSales': FixedSales,
        'FixedEnergyCharges': DSO_Cash_Flows['Revenues']['RetailSales']['FixedSales']['FixedEnergyCharges'],
        'DemandCharges': DSO_Cash_Flows['Revenues']['RetailSales']['FixedSales']['DemandCharges'],
        'ConnectChargesFix': DSO_Cash_Flows['Revenues']['RetailSales']['FixedSales']['ConnectChargesFix'],
        'TransactiveSales': TransactiveSales,
        'RetailDACharges': DSO_Cash_Flows['Revenues']['RetailSales']['TransactiveSales']['RetailDACharges'],
        'RetailRTCharges': DSO_Cash_Flows['Revenues']['RetailSales']['TransactiveSales']['RetailRTCharges'],
        'DistCharges': DSO_Cash_Flows['Revenues']['RetailSales']['TransactiveSales']['DistCharges'],
        'ConnectChargesDyn': DSO_Cash_Flows['Revenues']['RetailSales']['TransactiveSales']['ConnectChargesDyn'],
        'TransactFees': TransactFees,
        'TransTo': TransTo,
        'TransToMO': TransToMO,
        'MOtoDO': MOtoDO,
        'MOtoRSP': MOtoRSP,
        'TransToDO': TransToDO,
        'DOtoRSP': DOtoRSP,
        'Balance': 0
    }

    # DSO_Cash_Flows_DO
    # DSO_Cash_Flows_MO
    # DSO_Cash_Flows_RSP

    DSO_Revenues_and_Energy_Sales = DSO_Cash_Flows['Revenues']['RetailSales']

    DSO_Wholesale_Energy_Purchase_Summary = {
        'PeakCapacity': PeakCapacity,
        'TransCharges': TransCharges,
        'WhEnergyPurchases': Market_Purchases['WhEnergyPurchases'],
        'OtherWholesale': {
            'WhReserves': WhReserves,
            'WhLosses': WhLosses
        },
        'EnergyPurchased': EnergyPurchased,
        'EffectiveCostWholesaleEnergy': 0 # (PeakCapacity + TransCharges + WhEnergyPurchases + OtherWholesale) / EnergyPurchased
    }


    return CapitalExpenses_dict, OperatingExpenses_dict, Revenues_dict, \
           DSO_Cash_Flows_dict, DSO_Wholesale_Energy_Purchase_Summary, DSO_Cash_Flows_composite





if __name__ == '__main__':
    '''
    dso_numbers = [1]
    # dso_names = ['dso_1', 'dso_2', 'dso_3']

    # meta_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/metadata'
    meta_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/tesp-private/examples/analysis/dsot/data'

    dso_paths = ['D:\\DSOT\\Base_858c4e40\\2016_02\\DSO_1']
    Substation_paths = ['D:\\DSOT\\Base_858c4e40\\2016_02\\Substation_1']

    system_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/tesp-private/examples/dsot_v3'

    path_to_write = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/test_save_files'
    save_path = 'C:/Users/yint392/OneDrive - PNNL/Documents/DSO/test_save_files'

    # what is the Effective Cost of Energy?
    # dso_name = dso_names[0]
    dso_num = dso_numbers[0]
    # meta_path
    dso_path = dso_paths[0]
    Substation_path = Substation_paths[0]
    # system_path
    transactive = True
    # path_to_write
    # save_path
    '''
    CapitalExpenses_dict, OperatingExpenses_dict, Revenues_dict, \
    DSO_Cash_Flows_dict, DSO_Wholesale_Energy_Purchase_Summary, DSO_Cash_Flows_composite = \
        dso_CFS(config_path, DSOmetadata, dso_num, DSO_base_case_peak_demand,
                DSO_Cash_Flows, DSO_Revenues_and_Energy_Sales)
