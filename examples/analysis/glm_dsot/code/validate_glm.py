import os
import pandas as pd
import json
import shutil
from tesp_support.api.modify_GLM import GLMModifier, GLMModel
import tesp_support.dsot.glm_dictionary as gd

def read_glm(data_path, caseName):
    """Read in the substation .glms written from a prepare_case_dsot.py that 
    did not use GLMModifier, then write out an equivalent .glm using the new
    GLMModifier. Then create a glm_dict for each substation. 

    Args:
        data_path (str): the data path
        caseName (str): the name of the case folder
    """
    glm = GLMModifier()
    for dso_key in range(1,9):
        in_file_glm = os.path.abspath(caseName + '/Substation_' + str(dso_key) + '/Substation_' + str(dso_key) + '.glm')
        i_glm, success = glm.read_model(os.path.join(data_path, in_file_glm))
        glm.del_object('helics_msg', f"gldSubstation_{dso_key}") # FNCS run
        #glm.del_object('fncs_msg', f"gldSubstation_{dso_key}") # HELICS run
        glm.write_model(os.path.join(data_path, in_file_glm))
        if not success:
            exit()
        gd.glm_diction(caseName, "Substation_" + str(dso_key))
        shutil.move(f'{caseName}/Substation_{dso_key}/Substation_{dso_key}_glm_dict.json',
                        f'{caseName}/DSO_{dso_key}/Substation_{dso_key}_glm_dict.json')
        
        
def read_feeder_glm(data_path, caseName, feeder_name):
    """Read in a particular feeder .glms written from a prepare_case_dsot.py that 
    did not use GLMModifier, then write out an equivalent .glm using the new
    GLMModifier. Then create a glm_dict for each substation. 

    Args:
        data_path (str): the data path
        caseName (str): the name of the case folder
        feeder_name (str): the particular feeder name
    """
    glm = GLMModifier()
    in_file_glm = os.path.abspath(caseName + '/' + feeder_name + '/' + feeder_name + '.glm')
    i_glm, success = glm.read_model(os.path.join(data_path, in_file_glm))
    glm.write_model(os.path.join(data_path, in_file_glm))
    if not success:
        exit()
    gd.glm_diction(caseName, feeder_name)
    try:
        shutil.move(f'{caseName}/{feeder_name}/{feeder_name}_glm_dict.json',
                        f'{caseName}/DSO_1/{feeder_name}_glm_dict.json')
    except:
        shutil.move(f'{caseName}/{feeder_name}/{feeder_name}_glm_dict.json',
                        f'{caseName}/copperplate_feeder/{feeder_name}_glm_dict.json')
    glm.model.plot_model()

def read_dict(caseName, level:str):    
    glm_dict_list = {}
    agent_dict_list = {}
    if level == "DSO":
        for dso_key in range(1,8):
            glm_dict_list[dso_key] = os.path.abspath(caseName + '/DSO_' + str(dso_key) + '/Substation_' + str(dso_key) + '_glm_dict.json')
    elif level == "feeder":
        glm_dict_list[1] = os.path.abspath(caseName + '/DSO_1' + '/feeder1' + '_glm_dict.json')
        dso_k = 1
    elif level == "copper":
        glm_dict_list[1] = os.path.abspath(caseName + '/copperplate_feeder' + '/copperplate_feeder' + '_glm_dict.json')
        dso_k = 1
    hse_df = pd.DataFrame()
    hvac_agent_df = pd.DataFrame()
    # Get house parameters from each DSO glm_dict
    for dso_k, f_str in glm_dict_list.items():
        with open(f_str) as f:
            glm_dict = json.load(f)
        res_df = pd.DataFrame.from_dict(glm_dict['houses'], orient='index')
        res_df = res_df.reset_index()
        res_df['DSO'] = dso_k # add a column for DSO number
        # com_df = pd.DataFrame.from_dict(glm_dict['houses'], orient='index')
        # com_df = com_df.reset_index()
        # com_df['DSO'] = dso_k # add a column for DSO number
        # Add columns to distinguish houses and each DER
        for inc in ['Low', 'Middle', 'Upper', '']:
            for k, v in {'house':inc, 'battery':'bat', 'solar':'sol', 'ev':'ev'}.items():
                for val in glm_dict['billingmeters'].values():
                    children = val['children']
                    if len([s for s in children if inc in s]) > 0:
                        if len([s for s in children if v in s]) > 0:
                            res_df.loc[res_df['index']==[s for s in children if inc in s][0],k] = 'Yes'
                        else:
                            res_df.loc[res_df['index']==[s for s in children if inc in s][0],k] = 'No'
        # for groupid in ['office', 'warehouse_storage', 'big_box', 'strip_mall', 'education', 'food_service', 'food_sales', 'lodging', 'healthcare_inpatient', 'low_occupancy']:
        #     for k, v in {'house':groupid, 'battery':'bat', 'solar':'sol', 'ev':'ev'}.items():
        #         for val in glm_dict['billingmeters'].values():
        #             children = val['children']
        #             if len([s for s in children if inc in s]) > 0:
        #                 if len([s for s in children if v in s]) > 0:
        #                     com_df.loc[com_df['index']==[s for s in children if inc in s][0],k] = 'Yes'
        #                 else:
        #                     com_df.loc[com_df['index']==[s for s in children if inc in s][0],k] = 'No'
        # Merge all DSO house parameters into one dataframe
        hse_df = pd.concat([hse_df,res_df],ignore_index=True)
        bldg_df = hse_df
    # Get HVAC agent data
    for dso_k, f_str in agent_dict_list.items():
        with open(f_str) as f:
            agent_dict = json.load(f)
        temp_df2 = pd.DataFrame.from_dict(agent_dict['hvacs'],orient='index')
        temp_df2 = temp_df2.reset_index()
        temp_df2['DSO'] = dso_k # add a column for DSO number
        hvac_agent_df = pd.concat([hvac_agent_df,temp_df2],ignore_index=True)
    # Save for later analysis
    hse_df.to_csv(os.path.abspath(caseName + '/' + 'house_parameters.csv'))
    #bldg_df.to_csv(os.path.abspath(caseName + '/' + 'bldg_parameters.csv'))
    hvac_agent_df.to_csv(os.path.abspath(caseName + '/' + 'hvac_agents.csv'))
    # Get totals
    low_hses = len(hse_df.loc[(hse_df['income_level']=='Low')])
    middle_hses = len(hse_df.loc[(hse_df['income_level']=='Middle')])
    upper_hses = len(hse_df.loc[(hse_df['income_level']=='Upper')])
    com_bldgs = len(hse_df.loc[(hse_df['income_level']=='')])
    # Excluding commercial and industrial buildings where income_level = None:
    tot_hses = low_hses + middle_hses + upper_hses
    sol_hses = len(hse_df.loc[(hse_df['house']=='Yes') & (hse_df['solar']=='Yes') & (hse_df['income_level'] !='')])
    sol_com = len(bldg_df.loc[(bldg_df['house']=='Yes') & (bldg_df['solar']=='Yes') & (hse_df['income_level'] =='')])
    ev_hses = len(hse_df.loc[(hse_df['house']=='Yes') & (hse_df['ev']=='Yes') & (hse_df['income_level'] !='')])
    ev_com = len(bldg_df.loc[(bldg_df['house']=='Yes') & (bldg_df['ev']=='Yes') & (hse_df['income_level'] =='')])
    bat_hses = len(hse_df.loc[(hse_df['house']=='Yes') & (hse_df['battery']=='Yes') & (hse_df['income_level'] !='')])
    bat_com = len(bldg_df.loc[(bldg_df['house']=='Yes') & (bldg_df['battery']=='Yes') & (hse_df['income_level'] =='')])
    elec_wh_hses = len(hse_df.loc[(hse_df['house']=='Yes') & (hse_df['wh_gallons']!=0) & (hse_df['income_level'] !='')])
    elec_sh_hses = len(hse_df.loc[(hse_df['house']=='Yes') & (hse_df['fuel_type']=='electric') & (hse_df['income_level'] !='')])
    print(f"=== RESIDENTIAL POPULATION SUMMARY for {caseName} ===")
    print(f"Number of residential homes {tot_hses}")
    print(f"=== Income (Percent of all homes) ===")
    print(f"=== Low: {round(100*low_hses/tot_hses,2)}%, Middle: {round(100*middle_hses/tot_hses,2)}%, Upper: {round(100*upper_hses/tot_hses,2)}%. ===")
    print(f"=== DERs (Percent of all homes) ===")
    print(f"=== Solar: {round(100*sol_hses/tot_hses,2)}%, EVs: {round(100*ev_hses/tot_hses,2)}%, Batteries: {round(100*bat_hses/tot_hses,2)}%. ===")
    print(f"=== Electric Water Heating/Space Heating (Percent of all homes) ===")
    print(f"=== Water Heating: {round(100*elec_wh_hses/tot_hses,2)}%, Space Heating: {round(100*elec_sh_hses/tot_hses,2)}%. ===")
    print(f"=== COMMERCIAL POPULATION SUMMARY for {caseName} ===")
    print(f"Number of commercial buildings: {com_bldgs}")
    print(f"=== DERs (Percent of all buildings) ===")
    print(f"=== Solar: {round(100*sol_com/com_bldgs,2)}%, EVs: {round(100*ev_com/com_bldgs,2)}%, Batteries: {round(100*bat_com/com_bldgs,2)}%. ===")

if __name__ == "__main__":
    #read_glm(".", "../archive/lean_aug_8_pv_bt_fl_ev")
    #read_glm(".", "gld_feeder_test_pv_bt_fl_ev")
    read_dict("../archive/lean_aug_8_pv_bt_fl_ev", "DSO")
    read_dict("gld_feeder_test_pv_bt_fl_ev", "DSO")
    #read_feeder_glm(".", "../archive/lean_aug_8_pv_bt_fl_ev", "feeder1")
    #read_feeder_glm(".", "gld_feeder_test_pv_bt_fl_ev", "feeder1")
    #read_dict("../archive/lean_aug_8_pv_bt_fl_ev", "feeder")
    #read_dict("gld_feeder_test_pv_bt_fl_ev", "feeder")
    #read_feeder_glm(".", "../archive/lean_aug_8_pv_bt_fl_ev", "copperplate_feeder")
    #read_feeder_glm(".", "gld_feeder_test_pv_bt_fl_ev", "copperplate_feeder")
    #read_dict("../archive/lean_aug_8_pv_bt_fl_ev", "copper")
    #read_dict("gld_feeder_test_pv_bt_fl_ev", "copper")