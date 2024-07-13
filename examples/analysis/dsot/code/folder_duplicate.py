import os
import shutil


print(os.getcwd())
# file_name_dict = {'AZ_Tucson': 'Largesite_az.xlsx',
    #                   'WA_Tacoma': 'Largesite_wa.xlsx',
    #                   'AL_Dothan': 'Largesite_al.xlsx',
    #                   'IA_Johnston': 'Largesite_ia.xlsx',
    #                   'LA_Alexandria': 'Largesite_la.xlsx',
    #                   'AK_Anchorage': 'Largesite_ak.xlsx',
    #                   'MT_Greatfalls': 'Largesite_mt.xlsx'}
# suffix1 = 'AZ_Tucson_Medium_feb24_runs'
# suffix2 = 'AZ_Tucson_Medium_feb24_runs_uncontrolled'
# suffix3 = 'AZ_Tucson_Medium_feb24_runs_controlled'
suffix1 = 'WA_Tacoma_Medium_feb24_runs'
suffix2 = 'WA_Tacoma_Medium_feb24_runs_uncontrolled'
suffix3 = 'WA_Tacoma_Medium_feb24_runs_controlled'
main_names = ['AZ_Tucson']  #, 'WA_Tacoma', 'AL_Dothan', 'IA_Johnston', 'LA_Alexandria', 'AK_Anchorage', 'MT_Greatfalls']
sizes =  ["Large"] # ["Medium", "Small"]
for xol in main_names:
    for xoli in sizes:
        suffix1 = f"{xol}_{xoli}_feb12_runs"
        suffix2 = f"{xol}_{xoli}_jul9_runs"
        # suffix3 = f"{xol}_{xoli}_feb24_runs_controlled"
        folder_count = 17
        for k in range(folder_count):
            print(k+1)
            old_name = f"{suffix1}_{k+1}_fl"
            new_name1 = f"{suffix2}_{k+1}_fl"
            # new_name2 = f"{suffix3}_{k+1}_fl"
            shutil.copytree(old_name, new_name1)
            # shutil.copytree(old_name, new_name2)
            print(f"Finished {old_name} -----> {new_name1}")

