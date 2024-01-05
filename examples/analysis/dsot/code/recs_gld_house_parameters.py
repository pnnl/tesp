import json
import pandas as pd
import numpy as np
import math
import warnings
import os

def bin_size_check(sample_data,recs_data,state,housing_dens,inc_lev,binsize,climate_zone,income_str):
    og_bin_size = len(sample_data)
    print('Bin Size',inc_lev," ",og_bin_size)
    # Define Census Regions in case sample size is too small for state
    census_rgn = {
        'Pacific':['WA','OR','CA','HI','AK'],'Mountain':['ID','MT','WY','NV','UT','CO','AZ','NM'],
        'West North Central':['ND','MN','SD','NE','IA','KS','MO'],'West South Central':['OK','AR','TX','LA'],
        'East North Central':['WI','MI','IL','IN','OH'],'East South Central':['KY','TN','MS','AL'],
        'South Atlantic':['WV','MD','DC','DE','VA','NC','SC','GA','FL'],'Middle Atlantic':['NY','PA','NJ'],
        'New England':['ME','VT','NH','MA','CT','RI']
    }
    # Check if bin size is less than threshold.
    # If it is, use census region, then climate zone, and then finally widen income level input if needed.
    if og_bin_size<binsize:
        print(state, housing_dens, inc_lev)
        rgn = [key for key, value in census_rgn.items() if state in value][0]
        if housing_dens=='No_DSO_Type':
            rgn_bin_size = len(recs_data.loc[
                ((recs_data['DIVISION']==rgn) & 
                (recs_data[income_str]==inc_lev))
            ])
            if climate_zone == None:
                cz_bin_size = 0
            else:
                cz_bin_size = len(recs_data.loc[
                    ((recs_data['IECC_climate_code']==climate_zone) & 
                    (recs_data[income_str]==inc_lev))
                ])
            if inc_lev=='Low':
                il_bin_size = len(recs_data.loc[
                    ((recs_data['state_postal']==state) & 
                    (recs_data[income_str].isin(['Low','Middle'])))
                ])
            elif inc_lev=='Middle':
                il_bin_size = len(recs_data.loc[
                    ((recs_data['state_postal']==state) & 
                    (recs_data[income_str].isin(['Low','Middle','Upper'])))
                ])
            elif inc_lev=='Upper':
                il_bin_size = len(recs_data.loc[
                    ((recs_data['state_postal']==state) & 
                    (recs_data[income_str].isin(['Middle','Upper'])))
                ])
            max_bin = max(rgn_bin_size,cz_bin_size,il_bin_size)
            # if cz_bin_size<rgn_bin_size: use_cz=False
            if rgn_bin_size>binsize or rgn_bin_size==max_bin:
                sample_data = recs_data.loc[
                    ((recs_data['DIVISION']==rgn) & 
                    (recs_data[income_str]==inc_lev))
                ]
                warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Using census region to generate distributions with bin size {rgn_bin_size}.',UserWarning)
                # print(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {bin_size_thres}. Using census region to generate distributions with bin size {rgn_bin_size}.')
            elif cz_bin_size>binsize or cz_bin_size==max_bin:
                sample_data = recs_data.loc[
                    ((recs_data['IECC_climate_code']==climate_zone) & 
                    (recs_data[income_str]==inc_lev))
                ]
                warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Using climate zone to generate distributions with bin size {cz_bin_size}.')
            elif il_bin_size==max_bin:
                if inc_lev=='Low':
                    sample_data = recs_data.loc[
                        ((recs_data['state_postal']==state) & 
                        (recs_data[income_str].isin(['Low','Middle'])))
                    ]
                    warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Widening income level selection to generate distributions with bin size {il_bin_size}.')
                elif inc_lev=='Middle':
                    sample_data = recs_data.loc[
                        ((recs_data['state_postal']==state) & 
                        (recs_data[income_str].isin(['Low','Middle','Upper'])))
                    ]
                    warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Widening income level selection to generate distributions with bin size {il_bin_size}.')
                elif inc_lev=='Upper':
                    sample_data = recs_data.loc[
                        ((recs_data['state_postal']==state) & 
                        (recs_data[income_str].isin(['Middle','Upper'])))
                    ]
                    warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Widening income level selection to generate distributions with bin size {il_bin_size}.')
        else:
            rgn_bin_size = len(recs_data.loc[
                ((recs_data['DIVISION']==rgn) & 
                (recs_data['UATYP10']==housing_dens) & 
                (recs_data[income_str]==inc_lev))
            ])
            if climate_zone == None:
                cz_bin_size = 0
            else:
                cz_bin_size = len(recs_data.loc[
                    ((recs_data['IECC_climate_code']==climate_zone) & 
                    (recs_data['UATYP10']==housing_dens) & 
                    (recs_data[income_str]==inc_lev))
                ])
            if inc_lev=='Low':
                il_bin_size = len(recs_data.loc[
                    ((recs_data['state_postal']==state) & 
                    (recs_data['UATYP10']==housing_dens) & 
                    (recs_data[income_str].isin(['Low','Middle'])))
                ])
            elif inc_lev=='Middle':
                il_bin_size = len(recs_data.loc[
                    ((recs_data['state_postal']==state) & 
                    (recs_data['UATYP10']==housing_dens) & 
                    (recs_data[income_str].isin(['Low','Middle','Upper'])))
                ])
            elif inc_lev=='Upper':
                il_bin_size = len(recs_data.loc[
                    ((recs_data['state_postal']==state) & 
                    (recs_data['UATYP10']==housing_dens) & 
                    (recs_data[income_str].isin(['Middle','Upper'])))
                ])
            max_bin = max(rgn_bin_size,cz_bin_size,il_bin_size)
            # if cz_bin_size<rgn_bin_size: use_cz=False
            if rgn_bin_size>binsize or rgn_bin_size==max_bin:
                sample_data = recs_data.loc[
                    ((recs_data['DIVISION']==rgn) & 
                    (recs_data['UATYP10']==housing_dens) & 
                    (recs_data[income_str]==inc_lev))
                ]
                warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Using census region to generate distributions with bin size {rgn_bin_size}.',UserWarning)
                # print(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {bin_size_thres}. Using census region to generate distributions with bin size {rgn_bin_size}.')
            elif cz_bin_size>binsize or cz_bin_size==max_bin:
                sample_data = recs_data.loc[
                    ((recs_data['IECC_climate_code']==climate_zone) & 
                    (recs_data['UATYP10']==housing_dens) & 
                    (recs_data[income_str]==inc_lev))
                ]
                warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Using climate zone to generate distributions with bin size {cz_bin_size}.')
            elif il_bin_size==max_bin:
                if inc_lev=='Low':
                    sample_data = recs_data.loc[
                        ((recs_data['state_postal']==state) & 
                        (recs_data['UATYP10']==housing_dens) & 
                        (recs_data[income_str].isin(['Low','Middle'])))
                    ]
                    warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Widening income level selection to generate distributions with bin size {il_bin_size}.')
                elif inc_lev=='Middle':
                    sample_data = recs_data.loc[
                        ((recs_data['state_postal']==state) & 
                        (recs_data['UATYP10']==housing_dens) & 
                        (recs_data[income_str].isin(['Low','Middle','Upper'])))
                    ]
                    warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Widening income level selection to generate distributions with bin size {il_bin_size}.')
                elif inc_lev=='Upper':
                    sample_data = recs_data.loc[
                        ((recs_data['state_postal']==state) & 
                        (recs_data['UATYP10']==housing_dens) & 
                        (recs_data[income_str].isin(['Middle','Upper'])))
                    ]
                    warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {binsize}. Widening income level selection to generate distributions with bin size {il_bin_size}.')

    if len(sample_data)<binsize:
        print(f'WARNING: Bin size={len(sample_data)}. Bin size less than bin size threshold of {binsize}. No expansion methods meet bin size threshold.')
    total = sample_data['NWEIGHT'].sum() # Get total population for final sample after bin size check/adjustments
    return sample_data, total

def get_residential_metadata(metadata,sample_data,state,hsdens_str,inc_lev,total):
    # Define RECS codebook
    # Define variable strings
    house_type_str = 'TYPEHUQ'
    vintage_str = 'YEARMADERANGE'
    n_stories_str = 'STORIES'
    flr_area_str = 'TOTSQFT_EN'
    ac_str = 'AIRCOND'
    sh_fuel_str = 'FUELHEAT'
    sh_equip_str = 'EQUIPM'
    wh_fuel_str = 'FUELH2O'
    hiceiling_str = 'HIGHCEIL'
    n_occ_str = 'NHSLDMEM'
    solar_str = 'SOLAR'
    ev_str = 'EVCHRGHOME' # Using EV is charged at home. There is another value that just indicates if they own an EV.
    therm_str = 'TYPETHERM'

    housing_type_dict = {
        1:'mobile_home',2:'single_family_detached',3:'single_family_attached',4:'apartment_2_4_units',5:'apartment_5_units'
    }
    housing_vintage_dict = {
        1:'pre_1950',2:'1950-1959',3:'1960-1969',4:'1970-1979',5:'1980-1989',6:'1990-1999',7:'2000-2009',8:'2010-2015',9:'2016-2020'
    }
    num_stories_dict = {
        1:'one_story',2:'two_story',3:'three_story',4:'four_or_more_story',5:'split_level',-2:'not_applicable'
    }
    air_conditioning_dict = {
        1:'yes',0:'no'
    }
    # Use FUELHEAT
    heating_fuel_dict = {
        5:'electricity',1:'natural_gas',2:'propane',3:'fuel_oil',7:'wood',99:'other',-2:'not_applicable'
    }
    # Use EQUIPM and FUELHEAT
    electric_heating_type_dict = {
        5:'wall_baseboard_heaters',10:'portable_elec_heaters',4:'central_heat_pump',13:'mini_split',
        3:'central_furnace'
    }
    # Number of occupants
    max_num_occupants = 7
    # Solar PV
    solar_pv_dict = {
        1:'yes',0:'no',-2:'not_applicable'
    }
    # EV
    ev_dict = {
        1:'yes',0:'no',-2:'not_applicable'
    }
    # Water heater tank size dictionary
    wh_size = {1:'30_or_less',2:'31-49',3:'50_or_more',4:'tankless'}
    wh_size_range = {'30_or_less':{'min':25,'max':30},'31-49':{'min':31,'max':49},'50_or_more':{'min':50,'max':75}}
    
    
    # Define probability distribution for housing_type
    total_dict = {}
    # Get house type distribution for triple
    for k, h in housing_type_dict.items():
        metadata['housing_type'][state][hsdens_str][inc_lev][h]=round(sample_data.loc[(sample_data[house_type_str]==k),'NWEIGHT'].sum()/total,4)
    # print(metadata['housing_type'])
    # Get vintage by house type
    for k, h in housing_type_dict.items():
        metadata['housing_vintage'][state][hsdens_str][inc_lev][h] = {}
        total_dict[h] = {}
        for p, y in housing_vintage_dict.items():
            total_dict[h][y] = sample_data.loc[((sample_data[house_type_str]==k) & (sample_data[vintage_str]==p)),'NWEIGHT'].sum()
            if total_dict[h][y]==0:
                total_dict[h][y]=1
            metadata['housing_vintage'][state][hsdens_str][inc_lev][h][y]=round(total_dict[h][y]/total,4)

    # Get number of stories by house type and vintage
    for k, h in housing_type_dict.items():
        metadata['num_stories'][state][hsdens_str][inc_lev][h]={}
        for p, y in housing_vintage_dict.items():
            metadata['num_stories'][state][hsdens_str][inc_lev][h][y]={}
            for n, s in num_stories_dict.items():
                metadata['num_stories'][state][hsdens_str][inc_lev][h][y][s]=round(sample_data.loc[((sample_data[house_type_str]==k) & 
                                                                                                    (sample_data[vintage_str]==p) & 
                                                                                                    (sample_data[n_stories_str]==n)),
                                                                                                    'NWEIGHT'].sum()/total_dict[h][y],4)

    # Get floor_area distribution by house type and vintage
    for k, h in housing_type_dict.items():
        metadata['floor_area'][state][hsdens_str][inc_lev][h]={}
        # for p, y in housing_vintage_dict.items():
        values = sample_data.loc[(sample_data[house_type_str]==k),flr_area_str].values
        weighting = sample_data.loc[(sample_data[house_type_str]==k),'NWEIGHT'].values
        if values.size == 0:
            metadata['floor_area'][state][hsdens_str][inc_lev][h]['mean'] = None
            metadata['floor_area'][state][hsdens_str][inc_lev][h]['max'] = None
            metadata['floor_area'][state][hsdens_str][inc_lev][h]['min'] = None
            metadata['floor_area'][state][hsdens_str][inc_lev][h]['standard_deviation'] = None
        else:
            avg = np.average(values,weights=weighting)
            std_dev = math.sqrt(np.average((values-avg)**2,weights=weighting))
            metadata['floor_area'][state][hsdens_str][inc_lev][h]['mean'] = round(avg,4)
            metadata['floor_area'][state][hsdens_str][inc_lev][h]['max'] = float(np.max(values))
            metadata['floor_area'][state][hsdens_str][inc_lev][h]['min'] = float(np.min(values))
            metadata['floor_area'][state][hsdens_str][inc_lev][h]['standard_deviation'] = round(std_dev,4)

    # Get single wide mobile home by income level
    # for p, y in housing_vintage_dict.items():
    #     metadata['mobile_home_single_wide'][st][hd_str][il][y] = round(sample_df.loc[((sample_df[house_type_str]==1) & (sample_df[vintage_str]==p) & (sample_df[flr_area_str]<=1080)),'NWEIGHT'].sum()/total_dict['mobile_home'][y],4)
    # metadata['mobile_home_single_wide'][state][hsdens_str][inc_lev] = round(sample_data.loc[((sample_data[house_type_str]==1) & 
    #                                                                                          (sample_data[flr_area_str]<=1080)),
    #                                                                                          'NWEIGHT'].sum()/sum(total_dict['mobile_home'].values()),4)

    # Get distribution for air conditioning for homes with gas or resistance heating by house type and vintage
    for k, h in housing_type_dict.items():
        total_gas_res_homes = sample_data.loc[((sample_data[house_type_str]==k) & 
                                                (~sample_data[sh_equip_str].isin([4,13]))),
                                                'NWEIGHT'].sum()
        metadata['air_conditioning'][state][hsdens_str][inc_lev][h]=round(sample_data.loc[((sample_data[house_type_str]==k) &  
                                                                                           (sample_data[ac_str]==1) &
                                                                                           (~sample_data[sh_equip_str].isin([4,13]))),
                                                                                           'NWEIGHT'].sum()/total_gas_res_homes,4)

    # Get distribution for gas heating by house type and vintage
    for k, h in housing_type_dict.items():
        metadata['space_heating_type'][state][hsdens_str][inc_lev][h]={}
        for p, y in housing_vintage_dict.items():
            metadata['space_heating_type'][state][hsdens_str][inc_lev][h][y]={}
            # Gas heating defined as all heating that is not electric
            metadata['space_heating_type'][state][hsdens_str][inc_lev][h][y]['gas_heating']=round(sample_data.loc[((sample_data[house_type_str]==k) & 
                                                                                                                   (sample_data[vintage_str]==p) & 
                                                                                                                   (sample_data[sh_fuel_str].isin([1,2,3,7,99,-2]))),
                                                                                                                   'NWEIGHT'].sum()/total_dict[h][y],4)
            metadata['space_heating_type'][state][hsdens_str][inc_lev][h][y]['heat_pump']=round(sample_data.loc[((sample_data[house_type_str]==k) & 
                                                                                                                 (sample_data[vintage_str]==p) & 
                                                                                                                 (sample_data[sh_equip_str].isin([4,13]))),
                                                                                                                 'NWEIGHT'].sum()/total_dict[h][y],4)
            metadata['space_heating_type'][state][hsdens_str][inc_lev][h][y]['resistance']=round(sample_data.loc[((sample_data[house_type_str]==k) & 
                                                                                                                  (sample_data[vintage_str]==p) & 
                                                                                                                  (sample_data[sh_fuel_str].isin([5,10])) & 
                                                                                                                  (~sample_data[sh_equip_str].isin([4,13]))),
                                                                                                                  'NWEIGHT'].sum()/total_dict[h][y],4)
    
    # Get distribution for if water heating matches space heating
    for k, h in housing_type_dict.items():
        metadata['water_heating_type'][state][hsdens_str][inc_lev][h]={}
        for p, y in housing_vintage_dict.items():
            metadata['water_heating_type'][state][hsdens_str][inc_lev][h][y]={}
            both_gas = sample_data.loc[((sample_data[house_type_str]==k) & 
                                        (sample_data[vintage_str]==p) & 
                                        (sample_data[sh_fuel_str].isin([1,2,3,7,99,-2])) & 
                                        (sample_data[wh_fuel_str].isin([1,2,3,7,8,99,-2]))),'NWEIGHT'].sum()
            both_electric = sample_data.loc[((sample_data[house_type_str]==k) & 
                                             (sample_data[vintage_str]==p) & 
                                             (sample_data[sh_fuel_str]==5) & 
                                             (sample_data[wh_fuel_str]==5)),'NWEIGHT'].sum()
            metadata['water_heating_type'][state][hsdens_str][inc_lev][h][y]=round((both_gas+both_electric)/total_dict[h][y],4)
    
    # Get distribution for high ceilings by house type and vintage
    for k, h in housing_type_dict.items():
        metadata['high_ceilings'][state][hsdens_str][inc_lev][h]={}
        for p, y in housing_vintage_dict.items():
            metadata['high_ceilings'][state][hsdens_str][inc_lev][h][y]=round(sample_data.loc[((sample_data[house_type_str]==k) & 
                                                                                               (sample_data[vintage_str]==p) & 
                                                                                               (sample_data[hiceiling_str]==1)),'NWEIGHT'].sum()/total_dict[h][y],4)

    # Get distribution for number of occupants by house type and vintage
    # Not being used in feeder generator
    for k, h in housing_type_dict.items():
        metadata['num_occupants'][state][hsdens_str][inc_lev][h]={}
        for p, y in housing_vintage_dict.items():
            metadata['num_occupants'][state][hsdens_str][inc_lev][h][y]={}
            for o in range(1,max_num_occupants+1):
                metadata['num_occupants'][state][hsdens_str][inc_lev][h][y][o]=round(sample_data.loc[((sample_data[house_type_str]==k) & 
                                                                                                      (sample_data[vintage_str]==p) & 
                                                                                                      (sample_data[n_occ_str]==o)),'NWEIGHT'].sum()/total_dict[h][y],4)
    
    # Get distribution for Solar PV by house type
    for k, h in housing_type_dict.items():
        metadata['solar_pv'][state][hsdens_str][inc_lev][h]=round(sample_data.loc[((sample_data[house_type_str]==k) & 
                                                                                   (sample_data[solar_str]==1)),'NWEIGHT'].sum()/sum(total_dict[h].values()),4)
    # Get distribution for EV by house type
    for k, h in housing_type_dict.items():
        metadata['ev'][state][hsdens_str][inc_lev][h]=round(sample_data.loc[((sample_data[house_type_str]==k) & 
                                                                             (sample_data[ev_str]==1)),'NWEIGHT'].sum()/sum(total_dict[h].values()),4)
        
    metadata['programmable_thermostat'][state][hsdens_str][inc_lev] = round(sample_data.loc[((sample_data[therm_str].isin([2,3]))),'NWEIGHT'].sum()/total,4)

    # metadata['water_heater_tank_size']={}
    # for k, h in housing_type_dict.items():
    #     metadata['tank_size_dist'][h]={}
    #     for p, y in housing_vintage_dict.items():
    #         metadata['tank_size_dist'][h][y]={}
    #         for t, w in wh_size.items():
    #             metadata['tank_size_dist'][h][y][w]=round(sample_df.loc[((sample_df['TYPEHUQ']==k) & (sample_df['YEARMADERANGE']==p) & (sample_df['WHEATSIZ']==t)),'NWEIGHT'].sum()/total,4)
    # metadata['water_heater_tank_size']['tank_size'] = wh_size_range
    
    # test_key = 'num_occupants'
    # metadata_df = pd.DataFrame.from_dict({(i,j):metadata[test_key][i][j]
    #                                     for i in metadata[test_key].keys()
    #                                     for j in metadata[test_key][i].keys()},
    #                                     orient='index')

    # print(metadata_df)
    # print(metadata_df.values.sum())
    return metadata,total_dict

def get_RECS_jsons(recs_data_file,dsot_metadata_file,output_file_resmeta,output_file_hvacsp,sample={'state':[],'housing_density':[],'income_level':[]},bin_size_thres=100,climate_zone=''):
    # Read RECS data file
    recs = pd.read_csv(recs_data_file)
    # Use the right income level data from RECS
    inc_str = 'Income_cat2'
    # Make sure income level is in the right order
    order = {key: i for i, key in enumerate(['Low','Moderate','Middle','Upper'])}
    sample['income_level'] = sorted(sample['income_level'],key=lambda d: order[d])
    # Read DSOT_residential_parameters_metadata.json
    with open(dsot_metadata_file) as json_file:
        dsot_metadata = json.load(json_file)

    # RECS Codebook for housing density
    housing_density_dict = {'C':'Suburban','R':'Rural','U':'Urban','No_DSO_Type':'No_DSO_Type'}

    # Define probability distribtutions based on RECS data
    # Sample data based on inputted state, housing density, and income level
    res_metadata = {
        'income_level':{},'housing_type':{},'housing_vintage':{},'num_stories':{},'floor_area':{}, 
        'mobile_home_single_wide':{},'air_conditioning':{},'space_heating_type':{},
        'water_heating_type':{},'high_ceilings':{},'num_occupants':{},'solar_pv':{},'ev':{},
        'programmable_thermostat':{}
    }
    hvac_setpoints = {
        'programmable_thermostat':{},'telework':{}, 'num_days_telework':{},'occ_cool':{},
        'unocc_cool':{},'night_cool':{},'occ_heat':{},'unocc_heat':{},'night_heat':{}
    }

    for st in sample['state']:
        for key in res_metadata: res_metadata[key].update({st:{}}) # Add new state keys to the metadata dictionary
        for key in hvac_setpoints: hvac_setpoints[key].update({st:{}})
        for hd in sample['housing_density']:
            hd_str = housing_density_dict[hd]
            for key in res_metadata: res_metadata[key][st].update({hd_str:{}}) # Add new housing density keys to the metadata dictionary
            for key in hvac_setpoints: hvac_setpoints[key][st].update({hd_str:{}})
            # Get total for specific state/density for all income levels
            # Used to generate income level distribution
            if hd=='No_DSO_Type':
                total_st_hd = recs.loc[
                    ((recs['state_postal']==st) & 
                    (recs[inc_str].isin(sample['income_level']))),'NWEIGHT'
                ].sum()
            else:
                total_st_hd = recs.loc[
                    ((recs['state_postal']==st) & 
                    (recs['UATYP10']==hd) & 
                    (recs[inc_str].isin(sample['income_level']))),'NWEIGHT'
                ].sum()

            for il in sample['income_level']:
                for key in res_metadata: res_metadata[key][st][hd_str].update({il:{}}) # Add new income level keys to the metadata dictionary
                # for key in hvac_setpoints: hvac_setpoints[key][st][hd_str].update({il:[]})
                # Get sample dataframe for triple
                if hd=='No_DSO_Type':
                    sample_df = recs.loc[
                        ((recs['state_postal']==st) & 
                        (recs[inc_str]==il))
                    ]
                else:
                    sample_df = recs.loc[
                        ((recs['state_postal']==st) & 
                        (recs['UATYP10']==hd) & 
                        (recs[inc_str]==il))
                    ]
                total_triple = sample_df['NWEIGHT'].sum() # Get total population for triple
                res_metadata['income_level'][st][hd_str][il] = round(total_triple/total_st_hd,4)
                # Check if bin size is less than threshold.
                # If it is, use census region, then climate zone, and then finally widen income level input if needed.
                sample_df, total = bin_size_check(sample_df,recs,st,hd,il,bin_size_thres,climate_zone,inc_str)

                res_metadata, total_dict = get_residential_metadata(res_metadata,sample_df,st,hd_str,il,total)
                hvac_setpoints = get_hvac_setpoints(hvac_setpoints,sample_df,st,hd_str,il,total)
    # Add distributions from DSO+T
    # metadata['floor_area'] = dsot_metadata['floor_area']
    res_metadata['aspect_ratio'] = dsot_metadata['aspect_ratio']
    # metadata['mobile_home_single_wide'] = dsot_metadata['mobile_home_single_wide']
    res_metadata['window_wall_ratio'] = dsot_metadata['window_wall_ratio']
    res_metadata['water_heater_tank_size'] = dsot_metadata['water_heater_tank_size']
    res_metadata['hvac_oversize'] = dsot_metadata['hvac_oversize']
    res_metadata['window_shading'] = dsot_metadata['window_shading']
    res_metadata['COP_average'] = dsot_metadata['COP_average']
    res_metadata['COP_average']['2016'] = 3.9359
    res_metadata['COP_average']['2017'] = 3.9359
    res_metadata['COP_average']['2018'] = 3.9359
    res_metadata['COP_average']['2019'] = 3.9359
    res_metadata['COP_average']['2020'] = 3.2956
    res_metadata['GLD_residential_house_classes'] = dsot_metadata['GLD_residential_house_classes']
    # Add income level dependent solar, storage, and ev percentages
    res_metadata['solar_percentage'] = {}
    res_metadata['solar_percentage']['Low'] = 0.21
    res_metadata['solar_percentage']['Middle'] = 0.21
    res_metadata['solar_percentage']['Upper'] = 0.58
    res_metadata['battery_percentage'] = {}
    res_metadata['battery_percentage']['Low'] = 0.21
    res_metadata['battery_percentage']['Middle'] = 0.21
    res_metadata['battery_percentage']['Upper'] = 0.58
    res_metadata['ev_percentage'] = {}
    res_metadata['ev_percentage']['Low'] = 0.24
    res_metadata['ev_percentage']['Middle'] = 0.42
    res_metadata['ev_percentage']['Upper'] = 0.33

    with open(output_file_resmeta,'w') as outfile:
        json.dump(res_metadata,outfile,indent=4)
    with open(output_file_hvacsp,'w') as outfile:
        json.dump(hvac_setpoints,outfile,indent=4)

def get_hvac_setpoints(metadata,sample_data,state,hsdens_str,inc_lev,total):
    '''
    Get the thermostat setpoint probability distributions from RECS data.
    '''
    therm_str = 'TYPETHERM'
    tw_str = 'TELLWORK'
    num_tw_str = 'TELLDAYS'
    occ_cool_str = 'TEMPHOMEAC'
    unocc_cool_str = 'TEMPGONEAC'
    night_cool_str = 'TEMPNITEAC'
    occ_heat_str = 'TEMPHOME'
    unocc_heat_str = 'TEMPGONE'
    night_heat_str = 'TEMPNITE'
    sp_rng = np.arange(50,91)
    sp_rng = np.insert(sp_rng,0,-2)
    tw_days_rng = np.arange(8)
    tw_days_rng = np.insert(tw_days_rng,0,-2)
    # print('setpoint range',sp_rng)
    metadata['programmable_thermostat'][state][hsdens_str][inc_lev] = round(sample_data.loc[((sample_data[therm_str].isin([2,3]))),'NWEIGHT'].sum()/total,4)
    metadata['telework'][state][hsdens_str][inc_lev] = round(sample_data.loc[((sample_data[tw_str]==1)),'NWEIGHT'].sum()/total,4)
    metadata['num_days_telework'][state][hsdens_str][inc_lev] = {}
    for d in tw_days_rng:
        metadata['num_days_telework'][state][hsdens_str][inc_lev][str(d)] = round(sample_data.loc[((sample_data[num_tw_str]==d)),'NWEIGHT'].sum()/total,4)
    metadata['occ_cool'][state][hsdens_str][inc_lev] = [['Temperature','Percentage']]
    metadata['occ_heat'][state][hsdens_str][inc_lev] = [['Temperature','Percentage']]
    metadata['unocc_cool'][state][hsdens_str][inc_lev] = [['Not home daytime temperature']]
    metadata['unocc_heat'][state][hsdens_str][inc_lev] = [['Not home daytime temperature']]
    metadata['night_cool'][state][hsdens_str][inc_lev] = [['Nighttime temperature']]
    metadata['night_heat'][state][hsdens_str][inc_lev] = [['Nighttime temperature']]
    clm = 1
    clm_cool = 1
    clm_heat = 1
    # Only want houses with AC for the cooling setpoint distributions
    total_c = sample_data.loc[((sample_data['AIRCOND']==1)),'NWEIGHT'].sum()
    # Get occupied setpoint distribution first
    for sp_idx, sp in enumerate(sp_rng):
        total_o_cool = sample_data.loc[((sample_data[occ_cool_str]==sp) & 
                                        (sample_data['AIRCOND']==1)),
                                        'NWEIGHT'].sum() # Get total houses that have this occupied setpoint
        total_o_heat = sample_data.loc[((sample_data[occ_heat_str]==sp)),'NWEIGHT'].sum()
        percentage_cool = round(100*total_o_cool/total_c,2)
        percentage_heat = round(100*total_o_heat/total,2)
        metadata['occ_cool'][state][hsdens_str][inc_lev].append([str(sp),str(percentage_cool)])
        metadata['occ_heat'][state][hsdens_str][inc_lev].append([str(sp),str(percentage_heat)])
        metadata['unocc_cool'][state][hsdens_str][inc_lev][0].append('HOME DAY TEMPERATURE '+str(sp))
        metadata['unocc_heat'][state][hsdens_str][inc_lev][0].append('HOME DAY TEMPERATURE '+str(sp))
        
        row = 1
        # Get unoccupied setpoint based on occupied setpoint
        for spu_idx, spu in enumerate(sp_rng):
            if sp_idx == 0:
                metadata['unocc_cool'][state][hsdens_str][inc_lev].append([str(spu)])
                metadata['unocc_heat'][state][hsdens_str][inc_lev].append([str(spu)])

            total_o_u_cool = sample_data.loc[((sample_data[occ_cool_str]==sp) & 
                                              (sample_data[unocc_cool_str]==spu) & 
                                              (sample_data['AIRCOND']==1)),'NWEIGHT'].sum()
            total_o_u_heat = sample_data.loc[((sample_data[occ_heat_str]==sp) & (sample_data[unocc_heat_str]==spu)),'NWEIGHT'].sum()
            if total_o_cool==0 or total_o_u_cool==0:
                metadata['unocc_cool'][state][hsdens_str][inc_lev][spu_idx+1].append('0')
            else:
                metadata['unocc_cool'][state][hsdens_str][inc_lev][spu_idx+1].append(str(round(100*total_o_u_cool/total_o_cool,2)))
                metadata['night_cool'][state][hsdens_str][inc_lev][0].append('HOME AND GONE PAIR '+str(sp)+'&'+str(spu))
                # Get nightime setpoint based on occupied and unoccupied setpoint
                for spn_idx, spn in enumerate(sp_rng):
                    if clm_cool == 1:
                        metadata['night_cool'][state][hsdens_str][inc_lev].append([str(spn)])
                    total_o_u_n_cool = sample_data.loc[((sample_data[occ_cool_str]==sp) & 
                                                        (sample_data[unocc_cool_str]==spu) & 
                                                        (sample_data[night_cool_str]==spn) & 
                                                        (sample_data['AIRCOND']==1)),
                                                        'NWEIGHT'].sum()
                    metadata['night_cool'][state][hsdens_str][inc_lev][spn_idx+1].append(str(round(100*total_o_u_n_cool/total_o_u_cool,2)))
                clm_cool +=1
            if total_o_heat==0 or total_o_u_heat==0:
                metadata['unocc_heat'][state][hsdens_str][inc_lev][spu_idx+1].append('0')
            else:
                metadata['unocc_heat'][state][hsdens_str][inc_lev][spu_idx+1].append(str(round(100*total_o_u_heat/total_o_heat,2)))
                metadata['night_heat'][state][hsdens_str][inc_lev][0].append('HOME AND GONE PAIR '+str(sp)+'&'+str(spu))
                for spn_idx, spn in enumerate(sp_rng):
                    if clm_heat == 1:
                        metadata['night_heat'][state][hsdens_str][inc_lev].append([str(spn)])
                    total_o_u_n_heat = sample_data.loc[
                        ((sample_data[occ_heat_str]==sp) & 
                        (sample_data[unocc_heat_str]==spu) & 
                        (sample_data[night_heat_str]==spn)),'NWEIGHT'
                    ].sum()
                    metadata['night_heat'][state][hsdens_str][inc_lev][spn_idx+1].append(str(round(100*total_o_u_n_heat/total_o_u_heat,2)))
                clm_heat +=1
            row += 1
        
        # print(metadata['unocc_cool'][state][hsdens_str][inc_lev])
        # metadata['unocc_cool'][state][hsdens_str][inc_lev]
    return metadata

if __name__ == "__main__":
    get_RECS_jsons(
        '../../../../data/feeders/RECSwIncomeLvl.csv',
        '../data/DSOT_residential_metadata.json',
        '../data/RECS_residential_metadata.json',
        '../data/hvac_setpt_RECS.json',
        {'state':['TX'],'housing_density':['No_DSO_Type'],'income_level':['Middle','Upper','Low']},
        bin_size_thres=100,climate_zone=None)