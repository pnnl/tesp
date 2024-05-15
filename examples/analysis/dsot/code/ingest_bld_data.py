import pandas as pd
import os 
import shutil

def main(YYYY_MM_DD:str, end_time:str, path:str, weather_loc:str, weather_header:str, file_name:str, extract:bool, mapping:bool):

    excel_file_path = path + weather_loc + '/' + file_name
    print(f"Loading the main excel file = {file_name}")
    workbook = pd.read_excel(excel_file_path, header=None,sheet_name=None,engine='openpyxl')

    if mapping:
        mappings2 = {}
        mappings = {}
        folder_names = []
        print("Obtaining the mappings of building names and dummy building names...")
        for sheet_name in workbook.items():
            folder_names.append(sheet_name[0])

            actual_names = list(workbook[sheet_name[0]].iloc[2, 1:])
            bldg_nos = list(workbook[sheet_name[0]].iloc[0,1:])
            mapping_names = [f"bld_{col_index+1}" for col_index in range(len(actual_names))]
            tempdict = dict(zip(mapping_names, actual_names))
            mappings[sheet_name[0]] = tempdict

            tempdict2 = dict(zip(mapping_names,bldg_nos))
            mappings2[sheet_name[0]] = tempdict2

    if extract:
        mappings2 = {}
        mappings = {}
        folder_names = []
        print("Extracting the information the excel file into separate player csv files...")
        for sheet_name in workbook.items():
            folder_names.append(sheet_name[0])
            directory_path = path+weather_header+'/'+sheet_name[0]
            deleting(directory_path)
            os.makedirs(directory_path)
            df = pd.read_excel(excel_file_path, header=None, sheet_name=sheet_name[0], skiprows=3)
            df_original = pd.read_excel(excel_file_path, header=None,sheet_name=sheet_name[0])
            tempdict = dict()
            tempdict2 = dict()
            print(f"{sheet_name[0]}: folder created, working on generation bldg player csvs in current site folder.")
            for col_index in range(1, len(df.columns)):
                tempdict[f"bld_{col_index}"] = df_original.iloc[2, col_index]
                tempdict2[f"bld_{col_index}"] = df_original.iloc[0, col_index]
                column_data = df.iloc[:, col_index]
                csv_file_path = os.path.join(directory_path, f"bld_{col_index}.csv")
                column_data.to_csv(csv_file_path, index=False)
                df2 = pd.read_csv(csv_file_path)
                df2.columns = ['Power']
                df2["Power"] = (df2["Power"] * 1000 )/0.95  # convert kws to va
                df2['Timestamp'] = datetime(YYYY_MM_DD)
                df2 = df2[['Timestamp', 'Power']] # int(YYYY_MM_DD.split("-")[-1])
                df2 = df2[(df2.Timestamp.dt.day.isin(list(range(int(YYYY_MM_DD.split("-")[-1]),
                                                                int(end_time.split("-")[-1])+1)))) &
                          (df2.Timestamp.dt.month.isin(list(range(int(YYYY_MM_DD.split("-")[-2]),
                                                                  int(end_time.split("-")[-2])+1))))]
                df2.to_csv(csv_file_path, index=False, header=False)
            mappings[sheet_name[0]] = tempdict
            mappings2[sheet_name[0]] = tempdict2
        print("Creating the csv files for small, medium, large installations")
    return folder_names, mappings, mappings2

def deleting(directory_path):
    if os.path.exists(directory_path):
        shutil.rmtree(directory_path)
    else:
         return None
    
def datetime(YYYY_MM_DD:str):
    data_range = pd.date_range(YYYY_MM_DD.split("-")[0]+"-01-01", periods=8760, freq='H')
    return data_range

if __name__ == '__main__':
    """ -provide the absolute timestamp start day.This is supported by gld player.  
        -provide the path to the directory where file.xlsx is located
    """
    folder_names, mappings = main('2018-11-29', "C:\\Users\\gudd172\\Downloads\\testcode\\")