import json
import pandas as pd
import numpy as np
import warnings
import os

def get_residential_metadata(recs_data_file,dsot_metadata_file,output_file,sample={'state':[],'housing_density':[],'income_level':[]},bin_size_thres=100,climate_zone=''):
    # Read RECS data file
    recs = pd.read_csv(recs_data_file)
    # Make sure income level is in the right order
    sample['income_level'].sort()
    # Read DSOT_residential_parameters_metadata.json
    with open(dsot_metadata_file) as json_file:
        dsot_metadata = json.load(json_file)
    # Define RECS codebook
    # Define Census Regions in case sample size is too small for state
    census_rgn = {
        'Pacific':['WA','OR','CA','HI','AK'],'Mountain':['ID','MT','WY','NV','UT','CO','AZ','NM'],
        'West North Central':['ND','MN','SD','NE','IA','KS','MO'],'West South Central':['OK','AR','TX','LA'],
        'East North Central':['WI','MI','IL','IN','OH'],'East South Central':['KY','TN','MS','AL'],
        'South Atlantic':['WV','MD','DC','DE','VA','NC','SC','GA','FL'],'Middle Atlantic':['NY','PA','NJ'],
        'New England':['ME','VT','NH','MA','CT','RI']
    }
    # Define variable strings
    house_type_str = 'TYPEHUQ'
    vintage_str = 'YEARMADERANGE'
    n_stories_str = 'STORIES'
    ac_str = 'AIRCOND'
    sh_fuel_str = 'FUELHEAT'
    sh_equip_str = 'EQUIPM'
    wh_fuel_str = 'FUELH2O'
    hiceiling_str = 'HIGHCEIL'
    n_occ_str = 'NHSLDMEM'

    income_level_dict = {}
    housing_density_dict = {'C':'Suburban','R':'Rural','U':'Urban'}
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
    # Water heater tank size dictionary
    wh_size = {1:'30_or_less',2:'31-49',3:'50_or_more',4:'tankless'}
    wh_size_range = {'30_or_less':{'min':25,'max':30},'31-49':{'min':31,'max':49},'50_or_more':{'min':50,'max':75}}
    
    # Define probability distribtutions based on RECS data
    # Sample data based on inputted state, housing density, and income level
    metadata = {
        'income_level':{},'housing_type':{},'housing_vintage':{},'num_stories':{},'air_conditioning':{},
        'space_heating_type':{},'water_heating_type':{},'high_ceilings':{},'num_occupants':{}
    }
    for st in sample['state']:
        for key in metadata: metadata[key].update({st:{}})
        for hd in sample['housing_density']:
            hd_str = housing_density_dict[hd]
            for key in metadata: metadata[key][st].update({hd_str:{}})
            # Get total for specific state/density for all income levels
            # Used to generate income level distribution
            total_st_hd = recs.loc[
                ((recs['state_postal']==st) & 
                 (recs['UATYP10']==hd) & 
                 (recs['Income_cat'].isin(sample['income_level']))),'NWEIGHT'
            ].sum()
            for il in sample['income_level']:
                for key in metadata: metadata[key][st][hd_str].update({il:{}})
                # Get sample dataframe for triple
                sample_df = recs.loc[
                    ((recs['state_postal']==st) & 
                     (recs['UATYP10']==hd) & 
                     (recs['Income_cat']==il))
                ]
                total_triple = sample_df['NWEIGHT'].sum() # Get total population for triple
                metadata['income_level'][st][hd_str][il] = round(total_triple/total_st_hd,4)
                og_bin_size = len(sample_df)
                # Check if bin size is less than threshold.
                # If it is, use census region, then climate zone, and then finally widen income level input if needed.
                if og_bin_size<bin_size_thres:
                    print(st, hd, il)
                    rgn = [key for key, value in census_rgn.items() if st in value][0]
                    rgn_bin_size = len(recs.loc[
                        ((recs['DIVISION']==rgn) & 
                        (recs['UATYP10']==hd) & 
                        (recs['Income_cat']==il))
                    ])
                    cz_bin_size = len(recs.loc[
                        ((recs['IECC_climate_code']==climate_zone) & 
                        (recs['UATYP10']==hd) & 
                        (recs['Income_cat']==il))
                    ])
                    if il=='Low':
                        il_bin_size = len(recs.loc[
                            ((recs['state_postal']==st) & 
                            (recs['UATYP10']==hd) & 
                            (recs['Income_cat'].isin(['Low','Middle'])))
                        ])
                    elif il=='Middle':
                        il_bin_size = len(recs.loc[
                            ((recs['state_postal']==st) & 
                            (recs['UATYP10']==hd) & 
                            (recs['Income_cat'].isin(['Low','Middle','Upper'])))
                        ])
                    elif il=='Upper':
                        il_bin_size = len(recs.loc[
                            ((recs['state_postal']==st) & 
                            (recs['UATYP10']==hd) & 
                            (recs['Income_cat'].isin(['Middle','Upper'])))
                        ])
                    max_bin = max(rgn_bin_size,cz_bin_size,il_bin_size)
                    # if cz_bin_size<rgn_bin_size: use_cz=False
                    if rgn_bin_size>bin_size_thres or rgn_bin_size==max_bin:
                        sample_df = recs.loc[
                            ((recs['DIVISION']==rgn) & 
                            (recs['UATYP10']==hd) & 
                            (recs['Income_cat']==il))
                        ]
                        warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {bin_size_thres}. Using census region to generate distributions with bin size {rgn_bin_size}.',UserWarning)
                        # print(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {bin_size_thres}. Using census region to generate distributions with bin size {rgn_bin_size}.')
                    elif cz_bin_size>bin_size_thres or cz_bin_size==max_bin:
                        sample_df = recs.loc[
                            ((recs['IECC_climate_code']==climate_zone) & 
                            (recs['UATYP10']==hd) & 
                            (recs['Income_cat']==il))
                        ]
                        warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {bin_size_thres}. Using climate zone to generate distributions with bin size {cz_bin_size}.')
                    elif il_bin_size==max_bin:
                        if il=='Low':
                            sample_df = recs.loc[
                                ((recs['state_postal']==st) & 
                                (recs['UATYP10']==hd) & 
                                (recs['Income_cat'].isin(['Low','Middle'])))
                            ]
                            warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {bin_size_thres}. Widening income level selection to generate distributions with bin size {il_bin_size}.')
                        elif il=='Middle':
                            sample_df = recs.loc[
                                ((recs['state_postal']==st) & 
                                (recs['UATYP10']==hd) & 
                                (recs['Income_cat'].isin(['Low','Middle','Upper'])))
                            ]
                            warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {bin_size_thres}. Widening income level selection to generate distributions with bin size {il_bin_size}.')
                        elif il=='Upper':
                            sample_df = recs.loc[
                                ((recs['state_postal']==st) & 
                                (recs['UATYP10']==hd) & 
                                (recs['Income_cat'].isin(['Middle','Upper'])))
                            ]
                            warnings.warn(f'WARNING: Bin size={og_bin_size}. Bin size less than bin size threshold of {bin_size_thres}. Widening income level selection to generate distributions with bin size {il_bin_size}.')
                if len(sample_df)<bin_size_thres:
                    print(f'WARNING: Bin size={len(sample_df)}. Bin size less than bin size threshold of {bin_size_thres}. No expansion methods meet bin size threshold.')
                total = sample_df['NWEIGHT'].sum() # Get total population for final sample after bin size check/adjustments


                # Define probability distribution for housing_type
                total_dict = {}
                # Get house type distribution for triple
                for k, h in housing_type_dict.items():
                    metadata['housing_type'][st][hd_str][il][h]=round(sample_df.loc[(sample_df[house_type_str]==k),'NWEIGHT'].sum()/total,4)
                # print(metadata['housing_type'])
                # Get vintage by house type
                for k, h in housing_type_dict.items():
                    metadata['housing_vintage'][st][hd_str][il][h] = {}
                    total_dict[h] = {}
                    for p, y in housing_vintage_dict.items():
                        total_dict[h][y] = sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p)),'NWEIGHT'].sum()
                        if total_dict[h][y]==0:
                            total_dict[h][y]=1
                        metadata['housing_vintage'][st][hd_str][il][h][y]=round(total_dict[h][y]/total,4)

                # Get number of stories by house type and vintage
                for k, h in housing_type_dict.items():
                    metadata['num_stories'][st][hd_str][il][h]={}
                    for p, y in housing_vintage_dict.items():
                        metadata['num_stories'][st][hd_str][il][h][y]={}
                        for n, s in num_stories_dict.items():
                            metadata['num_stories'][st][hd_str][il][h][y][s]=round(sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p) & (sample_df[n_stories_str]==n)),'NWEIGHT'].sum()/total_dict[h][y],4)

                # Get distribution for air condition by house type and vintage
                for k, h in housing_type_dict.items():
                    metadata['air_conditioning'][st][hd_str][il][h]={}
                    for p, y in housing_vintage_dict.items():
                        metadata['air_conditioning'][st][hd_str][il][h][y]=round(sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p) & (sample_df[ac_str]==1)),'NWEIGHT'].sum()/total_dict[h][y],4)

                # Get distribution for gas heating by house type and vintage
                for k, h in housing_type_dict.items():
                    metadata['space_heating_type'][st][hd_str][il][h]={}
                    for p, y in housing_vintage_dict.items():
                        metadata['space_heating_type'][st][hd_str][il][h][y]={}
                        # Gas heating defined as all heating that is not electric
                        metadata['space_heating_type'][st][hd_str][il][h][y]['gas_heating']=round(sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p) & (sample_df[sh_fuel_str].isin([1,2,3,7,99,-2]))),'NWEIGHT'].sum()/total_dict[h][y],4)
                        metadata['space_heating_type'][st][hd_str][il][h][y]['heat_pump']=round(sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p) & (sample_df[sh_equip_str].isin([4,13]))),'NWEIGHT'].sum()/total_dict[h][y],4)
                        metadata['space_heating_type'][st][hd_str][il][h][y]['resistance']=round(sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p) & (sample_df[sh_fuel_str]==5) & (~sample_df[sh_equip_str].isin([4,13]))),'NWEIGHT'].sum()/total_dict[h][y],4)
                
                # Get distribution for if water heating matches space heating
                for k, h in housing_type_dict.items():
                    metadata['water_heating_type'][st][hd_str][il][h]={}
                    for p, y in housing_vintage_dict.items():
                        metadata['water_heating_type'][st][hd_str][il][h][y]={}
                        both_gas = sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p) & (sample_df[sh_fuel_str].isin([1,2,3,7,99,-2])) & (sample_df[wh_fuel_str].isin([1,2,3,7,8,99,-2]))),'NWEIGHT'].sum()
                        both_electric = sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p) & (sample_df[sh_fuel_str]==5) & (sample_df[wh_fuel_str]==5)),'NWEIGHT'].sum()
                        metadata['water_heating_type'][st][hd_str][il][h][y]=round((both_gas+both_electric)/total_dict[h][y],4)
                
                # Get distribution for high ceilings by house type and vintage
                for k, h in housing_type_dict.items():
                    metadata['high_ceilings'][st][hd_str][il][h]={}
                    for p, y in housing_vintage_dict.items():
                        metadata['high_ceilings'][st][hd_str][il][h][y]=round(sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p) & (sample_df[hiceiling_str]==1)),'NWEIGHT'].sum()/total_dict[h][y],4)

                # Get distribution for number of occupants by house type and vintage
                for k, h in housing_type_dict.items():
                    metadata['num_occupants'][st][hd_str][il][h]={}
                    for p, y in housing_vintage_dict.items():
                        metadata['num_occupants'][st][hd_str][il][h][y]={}
                        for o in range(1,max_num_occupants+1):
                            metadata['num_occupants'][st][hd_str][il][h][y][o]=round(sample_df.loc[((sample_df[house_type_str]==k) & (sample_df[vintage_str]==p) & (sample_df[n_occ_str]==o)),'NWEIGHT'].sum()/total_dict[h][y],4)
                
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

    # Add distributions from DSO+T
    metadata['floor_area'] = dsot_metadata['floor_area']
    metadata['aspect_ratio'] = dsot_metadata['aspect_ratio']
    metadata['mobile_home_single_wide'] = dsot_metadata['mobile_home_single_wide']
    metadata['window_wall_ratio'] = dsot_metadata['window_wall_ratio']
    metadata['water_heater_tank_size'] = dsot_metadata['water_heater_tank_size']
    metadata['hvac_oversize'] = dsot_metadata['hvac_oversize']
    metadata['window_shading'] = dsot_metadata['window_shading']
    metadata['COP_average'] = dsot_metadata['COP_average']
    metadata['GLD_residential_house_classes'] = dsot_metadata['GLD_residential_house_classes']

    with open(output_file,'w') as outfile:
        json.dump(metadata,outfile,indent=4)

if __name__ == "__main__":
    get_residential_metadata('RECSwIncomeLvl.csv','DSOT_residential_metadata.json','residential_metadata.json',{'state':['WA'],'housing_density':['R','U'],'income_level':['Middle','Upper','Low']},bin_size_thres=100,climate_zone='4C')