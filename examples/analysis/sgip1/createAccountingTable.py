# @Author: Allison Campbell <camp426>
# @Date:   2021-04-09T10:37:55-07:00
# @Email:  allison.m.campbell@pnnl.gov
# @Last modified by:   camp426
# @Last modified time: 2021-10-25T17:26:54-07:00



import json
import os
import numpy as np
import pandas as pd
# the process_* modules have been copied to
# this user's local dir for testing
import process_pypower as pp
import process_gld as gp
import process_agents as pa
# import process_eplus as ep
# import process_inv as pi
# import process_houses as ph

# need to also test using
# import tesp_support.process_pypower as pp
# import tesp_support.process_gld as gp
# import tesp_support.process_eplus as ep

accounting_table = \
pd.DataFrame(['Wholesale electricity purchases for test feeder (MWh/d)',
              'Wholesale electricity purchase cost for test feeder ($/day)',
              'Total wholesale generation revenue ($/day)',
              'Transmission and Distribution Losses (% of MWh generated)',
              'Average PV energy transacted (kWh/day)',
              'Average PV energy revenue ($/day)',
              'Average ES energy transacted (kWh/day)',
              'Average ES energy net revenue',
              'Total CO2 emissions (MT/day)',
              'Total SOx emissions (kg/day)',
              'Total NOx emissions (kg/day)'],columns=['Metric Description'])
base_dir = '/Users/camp426/TESP Virtual Machine'

def calculate_metrics(dir,name):
    # Wholesale electricity purchases for test feeder (MWh/day)
    gld_dict = gp.read_gld_metrics(dir,name,dictname='')
    time_diff = (gld_dict['hrs'][1]-gld_dict['hrs'][0])
    n_daily_obs = 24/time_diff
    n_days = len(gld_dict['hrs'])/n_daily_obs
    substation_MWh = gld_dict['data_s'][:,:,gld_dict['idx_s']['SUB_POWER_IDX']]*time_diff/1e6
    # instantaneous load, with ampFactor
    pypower_dict = pp.read_pypower_metrics(dir,name)
    # find bus number for test feeder -- the bus
    bus_no = pypower_dict['keys_b'][0]
    aF = pypower_dict['dso_b'][bus_no]['ampFactor']
    substation_MWh = substation_MWh.reshape(int(n_days),int(n_daily_obs))*aF
    wholesale_purchases_MWh_d = substation_MWh.sum(axis=1)

    # Wholesale electricity purchase cost for test feeder ($/day)
    PD_idx = pypower_dict['idx_b']['PD_IDX']
    time_diff = (pypower_dict['hrs'][1]-pypower_dict['hrs'][0])
    n_daily_obs = 24/time_diff
    n_days = len(pypower_dict['hrs'][1:])/n_daily_obs
    wholesale_purchase_price = pypower_dict['data_b'][:,1:,pypower_dict['idx_b']['LMP_P_IDX']]
    # reshape into per day, and move from units of $/kWh to $/MWh
    wholesale_purchase_price = wholesale_purchase_price.reshape(int(n_days),int(n_daily_obs))*1e3
    # multiply the wholesale_purchase_price in each time interval
    # by the load on the bus 7 from GLD in that interval
    wholesale_purchases_cost_d = (substation_MWh*wholesale_purchase_price).sum(axis=1)

    # Total wholesale generation revenue ($/day)
    wholesale_generation_MWh = pypower_dict['data_g'][:,1:,pypower_dict['idx_g']['PGEN_IDX']]*time_diff
    wholesale_LMP_per_MWh = pypower_dict['data_g'][:,1:,pypower_dict['idx_g']['GENLMP_IDX']]*1e3
    total_generation_revenue = (wholesale_generation_MWh*wholesale_LMP_per_MWh).sum(axis=0)
    wholesale_revenue_d = total_generation_revenue.reshape(int(n_days),int(n_daily_obs)).sum(axis=1)

    TnD_losses = gld_dict['data_s'][:,:,gld_dict['idx_s']['SUB_LOSSES_IDX']]*time_diff/1e6
    TnD_losses = TnD_losses.reshape(int(n_days),int(n_daily_obs))*20
    # substation_MWh.sum(axis=1)
    TnD_loss_pct = TnD_losses.sum(axis=1)/(substation_MWh.sum(axis=1))

    if len(gld_dict['keys_i']) > 0:
        # Average PV energy transacted (kWh/day)
        ave_PV_kWh_d = (gld_dict['solar_kw'].reshape(int(n_days),int(n_daily_obs))*time_diff).mean(axis=1)
        # Average PV energy revenue ($/day)
        auction_dict = pa.read_agent_metrics(dir,name)
        ave_PV_revenue_d = ((auction_dict['data_a'][0,:,0]*gld_dict['solar_kw']).reshape(int(n_days),int(n_daily_obs))*time_diff).sum(axis=1)
        # Average ES energy transacted (kWh/day)
        ave_ES_kWh_d = (gld_dict['battery_kw'].reshape(int(n_days),int(n_daily_obs))*time_diff).mean(axis=1)
        # Average ES revenue transacted ($/day)
        ave_ES_revenue_d = ((auction_dict['data_a'][0,:,0]*gld_dict['battery_kw']).reshape(int(n_days),int(n_daily_obs))*time_diff).sum(axis=1)
    else:
        ave_PV_kWh_d = np.array([0,0])
        ave_PV_revenue_d = np.array([0,0])
        ave_ES_kWh_d = np.array([0,0])
        ave_ES_revenue_d = np.array([0,0])

    # step 1: overwrite generator dict with genfuel and gentype
    # Q. Huang et al., "Simulation-Based Valuation of Transactive Energy Systems,"
    # in IEEE Transactions on Power Systems, vol. 34, no. 5, pp. 4138-4147, Sept. 2019,
    # doi: 10.1109/TPWRS.2018.2838111.
    pypower_dict['generators']['1']['genfuel'] = 'hydro'
    pypower_dict['generators']['1']['gentype'] = 'hydro'
    pypower_dict['generators']['2']['genfuel'] = 'gas'
    pypower_dict['generators']['2']['gentype'] = 'combinedcycle'
    pypower_dict['generators']['3']['genfuel'] = 'gas'
    pypower_dict['generators']['3']['gentype'] = 'singlecycle'
    pypower_dict['generators']['4']['genfuel'] = 'gas'
    pypower_dict['generators']['4']['gentype'] = 'combinedcycle'

    # TODO The emission rate info could be specified in a JSON file
    # generation emission rate table (lb/MWh)
    # Combination of the tables 11.3 and 11. 5 in the last years' report
    # https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-20772.pdf
    # Table B.20
    # Table B.19
    # coal: 10.41 MBTU/MWh
    # natural gas (CC): 8.16 MBTU/MWh
    # natural gas (CT) ("petroleum"): 11 MBTU/MWh
    # maybe additional information here?
    # https://www.eia.gov/electricity/annual/html/epa_08_02.html
    #                         CO2                SOX        NOX
    # coal                   205.57*10.09     0.1*10.09     0.06*10.09
    # natural gas (CC)       117.08*7.67      0.001*7.67    0.0075*7.67
    # natural gas (CT)       117.08*11.37     0.001*11.37   0.0075*11.37

    gen_emission_rate = {'coal': [205.57 * 10.09, 0.1 * 10.09, 0.06 * 10.09],
                         'combinedcycle': [117.08 * 7.67, 0.001 * 7.67, 0.0075 * 7.67],
                         'singlecycle': [117.08 * 11.37, 0.001 * 11.37, 0.0075 * 11.37]}

    gen_emission_rate = pd.DataFrame(gen_emission_rate)
    gen_emission_rate.index = ['CO2','SOX','NOX']
    # step 2: get all the generator numbers for each technology type

    generators = pd.DataFrame(pypower_dict['generators']).T
    total_gen = np.zeros(shape=(len(gen_emission_rate.columns),(n_daily_obs*2).astype(int)), dtype=float)
    total_emissions = np.zeros(shape=(len(gen_emission_rate.index),(n_daily_obs*2).astype(int)), dtype=float)
    for gentype,i in zip(gen_emission_rate.columns,range(len(total_gen))):
        #print(gentype,i)
        gen_idx = generators[generators['gentype'] == gentype].index.astype(int).tolist()
        total_gen[i] = (pypower_dict['data_g'][gen_idx,1:,PD_idx]*time_diff).sum(axis=0)
        for ghgtype,j in zip(gen_emission_rate.index,range(len(total_emissions))):
            #print(ghgtype,j,gen_emission_rate.loc[ghgtype,gentype])
            total_emissions[j] = total_emissions[j] + total_gen[i]*gen_emission_rate.loc[ghgtype,gentype]


    # this is in units of lb/day
    final_emissions = total_emissions.reshape(3,int(n_days),int(n_daily_obs)).sum(axis=2)
    # convert CO2 to MT
    lb_to_MT = 0.000453592
    CO2_emissions_d = final_emissions[0]*lb_to_MT
    # convert SOx, NOx to kg
    lb_to_kg = 0.453592
    SOx_emissions_d = (final_emissions[1:]*lb_to_kg)[0]
    NOx_emissions_d = (final_emissions[1:]*lb_to_kg)[1]


    raw_table = \
    pd.DataFrame(np.array([wholesale_purchases_MWh_d,
            wholesale_purchases_cost_d,
            wholesale_revenue_d,
            TnD_loss_pct,
            ave_PV_kWh_d,
            ave_PV_revenue_d,
            ave_ES_kWh_d,
            ave_ES_revenue_d,
            CO2_emissions_d,
            SOx_emissions_d,
            NOx_emissions_d]),columns=[name+' Day 1',name+' Day 2'])
    return raw_table

accounting_table_raw = pd.DataFrame()
accounting_table_delta = pd.DataFrame()
day_one = pd.DataFrame()
day_two = pd.DataFrame()
SGIP1_list = ['a','b','c','d','e']
for i in SGIP1_list:
    name = 'SGIP1'+i
    dir = base_dir+'/'+name
    print('**********\n\n\n')
    print('Starting Metrics Calculations for ',name)
    print('\n\n\n**********')
    raw_table = calculate_metrics(dir,name)
    accounting_table_raw = pd.concat([accounting_table_raw,raw_table],axis=1)
    delta = raw_table.copy()
    delta['SGIP1'+i+' Day 2'] = raw_table['SGIP1'+i+' Day 2'] - raw_table['SGIP1'+i+' Day 1']
    accounting_table_delta = pd.concat([accounting_table_delta,delta],axis=1)
    if i == 'a':
        day_one = accounting_table_raw['SGIP1'+i+' Day 1']
        day_two = accounting_table_raw['SGIP1'+i+' Day 2']
    elif i == 'b':
        delta = raw_table.copy()
        delta['SGIP1b diff SGIP1a Day 1'] = accounting_table_raw['SGIP1b Day 1'] - accounting_table_raw['SGIP1a Day 1']
        delta['SGIP1b diff SGIP1a Day 2'] = accounting_table_raw['SGIP1b Day 2'] - accounting_table_raw['SGIP1a Day 2']
        day_one = pd.concat([day_one,delta['SGIP1b diff SGIP1a Day 1']],axis=1)
        day_two = pd.concat([day_two,delta['SGIP1b diff SGIP1a Day 2']],axis=1)
    else:
        delta = raw_table.copy()
        delta['SGIP1'+i+' diff SGIP1b Day 1'] = accounting_table_raw['SGIP1'+i+' Day 1'] - accounting_table_raw['SGIP1b Day 1']
        delta['SGIP1'+i+' diff SGIP1b Day 2'] = accounting_table_raw['SGIP1'+i+' Day 2'] - accounting_table_raw['SGIP1b Day 2']
        day_one = pd.concat([day_one,delta['SGIP1'+i+' diff SGIP1b Day 1']],axis=1)
        day_two = pd.concat([day_two,delta['SGIP1'+i+' diff SGIP1b Day 2']],axis=1)

    # accounting_table = pd.concat([accounting_table,raw_table],axis=1)


day_one
day_two
accounting_table_delta

accounting_table_final = pd.concat([accounting_table,accounting_table_delta,day_one,day_two],axis=1)

accounting_table_final.to_csv(base_dir+'/SGIP1_accounting_table.csv',index=False)
