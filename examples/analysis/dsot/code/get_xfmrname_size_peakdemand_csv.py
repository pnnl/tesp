import pandas as pd
import os

if __name__ == '__main__':


    # load xfmrm name and size csv file (obtained mid script evaluation from EV mapping function).
    xfmr_name_size_df = pd.read_csv("xfrmr_name_size.csv")

    main_names = ['AZ_Tucson']  # , 'WA_Tacoma', 'AL_Dothan', 'IA_Johnston', 'LA_Alexandria', 'AK_Anchorage', 'MT_Greatfalls']
    sizes = ["Large"]
    custom_suffix = "jul14_runs"  # "jul9_runs"
    folder_count = 17
    concat_df = pd.DataFrame()
    for xol in main_names:
        for xoli in sizes:
            half_name = f"{xol}_{xoli}_{custom_suffix}"
            for k_li in range(folder_count):
                folder_name = f"{half_name}_{k_li+1}_fl"

                print(f"------------------------------------------------")
                print(f"------------------------------------------------")
                print(f"------------------------------------------------")
                print(f"Processing ----> {folder_name}")
                print(f"------------------------------------------------")
                print(f"------------------------------------------------")
                print(f"------------------------------------------------")

                curr_dir = os.getcwd()
                base_case = f"{curr_dir}/" + folder_name
                basedir = f"{base_case}/Substation_1/comm_xfrmr_load_inVA.csv"

                xfrmr_load_subfolder_df = pd.read_csv(basedir)
                xfrmr_load_subfolder_df_max = xfrmr_load_subfolder_df.max().reset_index().rename(columns={0:"peak_value"})
                xfrmr_load_subfolder_df_max = xfrmr_load_subfolder_df_max[xfrmr_load_subfolder_df_max["index"] != ("# "
                                                                                                                 "timestamp")]
                xfrmr_load_subfolder_df_max["peak_value"] = xfrmr_load_subfolder_df_max["peak_value"]/1000

                concat_df = pd.concat([concat_df, xfrmr_load_subfolder_df_max])
    concat_df = concat_df.rename(columns={"index":"Name"})
    final_df_needed = xfmr_name_size_df.merge(concat_df, on='Name', how='left')
    k = 1