import subprocess
import os
import time

def run_sh(current_folder_name):
    os.chdir(current_folder_name)
    print(f"Running simulation in folder = {current_folder_name}")
    result = subprocess.Popen("./run.sh")
    os.chdir("../")

    return result

if __name__ == "__main__":
    start_time = time.time()
    # folder_name = "AZ_Tucson_Large_parallel_and_comm_overload_test2"
    # customsuffix = "feb12_runs"  # "test_timestamp_mismatch"  # "final_runs"  "fix_comm_tf_config_ratings"  # "parallel_and_comm_overload_test2"
    customsuffix = "jul14_runs"
    gridsize = "Large"
    # weather_folders = [f"AZ_Tucson_{gridsize}_{customsuffix}",
    #                    f"WA_Tacoma_{gridsize}_{customsuffix}",
    #                    f"AL_Dothan_{gridsize}_{customsuffix}",
    #                    f"IA_Johnston_{gridsize}_{customsuffix}",
    #                    f"LA_Alexandria_{gridsize}_{customsuffix}",
    #                    f"AK_Anchorage_{gridsize}_{customsuffix}",
    #                    f"MT_Greatfalls_{gridsize}_{customsuffix}"]
    weather_folders = [f"AZ_Tucson_{gridsize}_{customsuffix}"]
    # weather_folders = [f"AZ_Tucson_Large_{customsuffix}"]
    # folder_count_list = [10, 10, 10, 10, 10, 10, 10]
    # folder_count_list = [2, 2, 2, 2, 2, 2, 2]
    # folder_count_list = [17, 17, 17, 17, 17, 16, 16]
    folder_count_list = [17]
    batch_size = 10  # If the VM is good, you can make this equal to folder_count_list[i], the parallel sim code will
    # try to deploy all jobs successfully as long as VM can handle it (ports, helics etc etc if possible)

    # batch_size = 2
    # batch_size = 10

    for idx, folder_name in enumerate(weather_folders):
        print(f"Running weather scenario = {idx}/{len(weather_folders)}. Folder series = {folder_name}.")
        folder_count = folder_count_list[idx]
        run_sims = True
        i1 = 0
        folder_names_list = []
        while run_sims:
            processes = []

            for ik in range(batch_size):
                i1 = i1 + 1
                if i1 <= folder_count:
                    current_folder_name = f"{folder_name}_{i1}_fl"
                    folder_names_list.append(current_folder_name)
                    p = run_sh(current_folder_name)
                    processes.append(p)
                else:
                    run_sims = False
                    break

            exit_codes = [p.wait() for p in processes]

            if not all([x == 0 for x in exit_codes]):
                print(
                    f"Problem running the run.sh scripts from folders {exit_codes} and {folder_names_list}. Exiting...")
                exit()

    end_time = time.time()
    print(f"Total time taken = {((end_time - start_time)/60)/60} hours.")
