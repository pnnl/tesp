# Copyright (C) 2022-2023 Battelle Memorial Institute
# file: recs_api.py

import pandas as pd
import sqlite3 as sqlite
import duckdb as dkdb
import random

pd.options.mode.chained_assignment = None

# *******************************************************************************************************************
# *******************************************************************************************************************

"""Function reads into a pandas dataframe an Excel or SQLite file containing RECS data. Upon success the function returns
    the dataframe containing the data. The function detects if the file path is for an Excel file or a SQLite file and uses
    the appropriate method of reading the data into a dataframe.


Args:
	file_name (str): the name and path of the file to be read in.
Returns:
	dataframe: containing the RECS data read from the input file. If there is a problem reading the file, the function 
	returns None.
"""


def get_recs_data(file_name):
    try:
        t_recs_df = pd.read_excel(file_name, sheet_name=0, header=0)
        return t_recs_df
    except:
        try:
            con = sqlite.connect(file_name)
            t_recs_df = pd.read_sql_query("SELECT * from RECSwIncomeLvl", con)
            return t_recs_df
        except:
            return None


# *******************************************************************************************************************
# *******************************************************************************************************************

"""Class is used to access and process a file which contains RECS data.
    """

class recs_data_set:
    #*******************************************************************************************************************
    #*******************************************************************************************************************

    """Function creates and initializes a new recs_data_set class object
Args:
	file_name (str): the name and path of the file to be read in.
    Returns:
	    dataframe: containing the RECS data read from the input file. If there is a problem reading the file, the
	    function returns None.
    """
    def __init__(self, file_name):
        self.recs_data = get_recs_data(file_name)

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    """Function queries a list of unique date built ranges contained in the dataset
    Args:
        none
    Returns:
    	dataframe: contains the list of unique date built ranges
    """
    def get_year_made_ranges(self):
        xlrd = self.recs_data
        sql_query = "SELECT DISTINCT(YEARMADERANGE) FROM xlrd ORDER BY YEARMADERANGE ASC"
        year_made_ranges = dkdb.query(sql_query).to_df()
        return year_made_ranges

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    """Function calculates the sum of nweight values based upon the arguments entered as parameters to the function
    Args:
    	st_name (string): name of the state the summed weights for a building type are to be calculated
    	income_level (string): income category that summed weights are to be calculate "Low","Middle", "Moderate",
    	 or "Upper"
    	population_density (string): population density category to be used in the summed weights ("C" = suburban,
    	 "R" = rural, "U" = urban)
    	housing_type (int): housing type category to be used in the summed weights 1 = Mobile Home, 
    	2 = Single Family Detatched,3 = Single Family Attached, 4 = Apartment 2-4, 5 = Apartment 5 or more 
    Returns:
    	dataframe: containing the calculated summation value
    """
    def calc_building_weight(self, st_name, income_level, population_density, housing_type):
        xlrd = self.recs_data
        sql_query = "SELECT SUM(nweight) FROM xlrd WHERE state_name='" + st_name + "'" + " AND typehuq=" + str(
            housing_type) + " AND Income_cat='" + income_level + "'" + " AND UATYP10='" + population_density + "'"
        nweight = dkdb.query(sql_query).to_df()
        return nweight

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def is_base_param_valid(self, param_name, param_type):
        if param_type == "state_name":
            params = self.get_state_names()
            param_id = "state_name"
        elif param_type == "income_cat":
            params = self.get_income_levels()
            param_id = "Income_cat"
        elif param_type == "housing_density":
            params = self.get_density_levels()
            param_id = "UATYP10"
        else:
            print("Invalid parameter type entered")
            return False
        for param in params[param_id]:
            if param_name == param:
                return True
        return False

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def is_base_param_list_valid(self, param_names, param_type):
        if param_type == "state_name":
            params = self.get_state_names()
            param_id = "state_name"
        elif param_type == "income_cat":
            params = self.get_income_levels()
            param_id = "Income_cat"
        elif param_type == "housing_density":
            params = self.get_density_levels()
            param_id = "UATYP10"
        else:
            print("Invalid parameter type entered")
            return False
        in_check = False
        for param in param_names:
            for param_name in params[param_id]:
                if param == param_name:
                    in_check = True
            if not in_check:
                return in_check
            else:
                in_check = False
        return True

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def check_base_param(self, param_name, param_type):
        param_list = []
        if str(type(param_name)) == "<class 'str'>":
            if self.is_base_param_valid(param_name, param_type):
                param_list.append(param_name)
            else:
                print("Invalid param name entered")
                return None
        elif str(type(param_name)) == "<class 'list'>":
            if self.is_base_param_list_valid(param_name, param_type):
                param_list = param_name
            else:
                print("Invalid " + param_type + " list entered")
                return None
        else:
            print("Invalid parameter type entered")
            return None
        return param_list

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def calc_parameter_distribution(self, st_name, income_level, population_density):
        xlrd = self.recs_data
        sql_query = "SELECT state_name, Income_cat, UATYP10, SUM(nweight) as 'summed_nweight',COUNT(nweight) as 'count' FROM xlrd WHERE state_name='" + st_name + "'" + " AND Income_cat='" + income_level + "'" + " AND UATYP10='" + population_density + "' GROUP BY state_name, Income_cat, UATYP10"
        nweight = dkdb.query(sql_query).to_df()
        return nweight

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def calculate_key_parameter_percentages(self, key_parameter_df):
        sql_query = "SELECT  SUM(summed_nweight) as 'total_nweight' FROM key_parameter_df"
        total_weight_df = dkdb.query(sql_query).to_df()
        total_weight = total_weight_df['total_nweight'][0]
        sql_query = "SELECT summed_nweight/" + str(total_weight) + " as 'percentage' FROM key_parameter_df"
        percentage_df = dkdb.query(sql_query).to_df()
        # frames = [key_parameter_df, percentage_df]
        # calculated_percents_df = pd.concat(frames)
        # return calculated_percents_df
        return percentage_df

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def get_all_params_list(self, param_type):
        param_list = []
        if param_type == "state_name":
            param_df = self.get_state_names()
        elif param_type == "income_cat":
            param_df = self.get_income_levels()
        elif param_type == "housing_density":
            param_df = self.get_density_levels()
        else:
            return None
        if param_type == "income_cat":
            param_id = "Income_cat"
        elif param_type == "housing_density":
            param_id = "UATYP10"
        else:
            param_id = param_type
        for param in param_df[param_id]:
            param_list.append(param)
        return param_list

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def build_key_parameter_distributions(self, state, income_level, housing_density):
        distribution_df = pd.DataFrame()
        if state == "all":
            state_lst = self.get_all_params_list("state_name")
        else:
            state_lst = self.check_base_param(state, "state_name")
        if income_level == "all":
            income_lst = self.get_all_params_list("income_cat")
        else:
            income_lst = self.check_base_param(income_level, "income_cat")
        if housing_density == "all":
            density_lst = self.get_all_params_list("housing_density")
        else:
            density_lst = self.check_base_param(housing_density, "housing_density")

        if state_lst is None or income_lst is None or density_lst is None:
            return None
        for state_name in state_lst:
            for income_lvl in income_lst:
                for density in density_lst:
                    temp_df = self.calc_parameter_distribution(state_name, income_lvl, density)
                    frames = [distribution_df, temp_df]
                    distribution_df = pd.concat(frames)
        percentage_df = self.calculate_key_parameter_percentages(distribution_df)
        distribution_df["percentage"] = 0.0
        #        distribution_df.iloc[0,4] = 53.65
        i = 0
        for percentage in percentage_df['percentage']:
            distribution_df.iloc[i, 5] = percentage
            i += 1
        return distribution_df

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def sample_type_vintage(self, distribution_df, num_samples):
        indices = []
        sampled_weights = []
        sampled_types = []
        sampled_vintages = []
        i = 0
        for row in distribution_df.iterrows():
            i += 1
            indices.append(i)
            print(row)
            sampled_weights.append(row[1]['percentage'])
        sampled_indices = random.choices(indices, weights=sampled_weights, k=num_samples)
        for index in sampled_indices:
            sampled_types.append(distribution_df.iloc[index].loc['TYPEHUQ'])
            sampled_vintages.append(distribution_df.iloc[index].loc['YEARMADERANGE'])
        return sampled_types, sampled_vintages

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def get_house_type_vintage(self, state, income_level, housing_density):
        distribution_df = pd.DataFrame()
        housing_lst = ["1", "2", "3", "4", "5"]
        vintage_lst = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        income_search_string = self.get_parameter_search_string(income_level, "Income_cat")
        density_search_string = self.get_parameter_search_string(housing_density, "UATYP10")
        xlrd = self.recs_data
        for house_type in housing_lst:
            for vintage_type in vintage_lst:
                sql_query = "SELECT state_name, Income_cat, UATYP10, TYPEHUQ, YEARMADERANGE, SUM(nweight) as 'summed_nweight',COUNT(nweight) as 'count' FROM xlrd WHERE state_name='" + state + "'" + " AND " + income_search_string + " AND " + density_search_string + " AND TYPEHUQ='" + house_type + "' AND YEARMADERANGE='" + vintage_type + "' GROUP BY state_name, Income_cat, UATYP10, TYPEHUQ, YEARMADERANGE"
                house_vintage_df = dkdb.query(sql_query).to_df()
                frames = [distribution_df, house_vintage_df]
                distribution_df = pd.concat(frames)
        percentage_df = self.calculate_key_parameter_percentages(distribution_df)
        distribution_df["percentage"] = 0.0
        distribution_df['indice'] = 0
        i = 0
        for percentage in percentage_df['percentage']:
            distribution_df['percentage'].iloc[i] = percentage
            distribution_df['indice'].iloc[i] = i
            i += 1
        housing_sampled_lst, vintage_sampled_lst = self.sample_type_vintage(distribution_df,1)
        return housing_sampled_lst, vintage_sampled_lst

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def get_parameter_search_string(self, parameter_string, parameter_name):
        param_list = parameter_string.split('&')
        if len(param_list) == 1:
            return parameter_name + "='" + parameter_string + "'"
        else:
            search_string = " ("
            i = 0
            for param_string in param_list:
                search_string += parameter_name + "='" + param_string + "' "
                if i < len(param_list) - 1:
                    search_string += "OR "
                else:
                    search_string += ") "
                i += 1
            return search_string

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def sample_parameter_distribution(self, distribution_df, num_samples, parameter_name):
        indices = []
        sampled_weights = []
        sampled_values = []
        i = 0
        for row in distribution_df.iterrows():
            i += 1
            indices.append(i)
            print(row)
            sampled_weights.append(row[1]['percentage'])
        sampled_indices = random.choices(indices, weights=sampled_weights, k=num_samples)
        for index in sampled_indices:
            sampled_values.append(distribution_df.iloc[index].loc[parameter_name])
        return sampled_values

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    def get_parameter_sample(self, state_name, income_level, housing_density, parameter_name):
        xlrd = self.recs_data
        sql_query = "SELECT state_name, Income_cat, UATYP10," + parameter_name + ", SUM(nweight) as 'summed_nweight',COUNT(nweight) as 'count' FROM xlrd WHERE state_name='" + state_name + "'" + " AND " + self.get_parameter_search_string(
            income_level, "Income_cat") + " AND " + self.get_parameter_search_string(housing_density,
                                                                                     "UATYP10") + " GROUP BY state_name, Income_cat, UATYP10, " + parameter_name
        distribution_df = dkdb.query(sql_query).to_df()
        percentage_df = self.calculate_key_parameter_percentages(distribution_df)
        distribution_df["percentage"] = 0.0
        i = 0
        for percentage in percentage_df['percentage']:
            distribution_df['percentage'].iloc[i] = percentage
            i += 1
        sampled_values = self.sample_parameter_distribution(distribution_df, 1, parameter_name)
        return sampled_values

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    """Function calculates the sum of nweight values based upon the arguments entered as parameters to the function
    Args:
    	st_name (string): name of the state the summed weights for a building type are to be calculated
    	income_level (string): income category that summed weights are to be calculate "Low","Middle", "Moderate",
    	 or "Upper"
    	population_density (string): population density category to be used in the summed weights ("C" = suburban,
    	 "R" = rural, "U" = urban)
    Returns:
    	dataframe: containing the calculated summation value
    """
    def calc_total_building_weight(self, st_name, income_level, population_density):
        xlrd = self.recs_data
        sql_query = "SELECT SUM(nweight) FROM xlrd WHERE state_name='" + st_name + "'" + " AND Income_cat='" + income_level + "'" + " AND UATYP10='" + population_density + "'"
        total_weight = dkdb.query(sql_query).to_df()
        return total_weight

    #*******************************************************************************************************************
    #*******************************************************************************************************************
    def calc_solar_percentage(self, st_name, income_lvl, pop_density):
        xlrd = self.recs_data
        sql_query = "SELECT COUNT(SOLAR) FROM xlrd WHERE state_name='" + st_name + "'" + " AND Income_cat='" + income_lvl + "'" + " AND UATYP10='" + pop_density + "'"
        total_cnt = dkdb.query(sql_query).fetchall()
        sql_query2 = "SELECT COUNT(SOLAR) FROM xlrd WHERE state_name='" + st_name + "'" + " AND Income_cat='" + income_lvl + "'" + " AND UATYP10='" + pop_density + "' AND SOLAR=1"
        yes_cnt = dkdb.query(sql_query2).fetchall()
        return yes_cnt[0][0] / total_cnt[0][0]

    #*******************************************************************************************************************
    #*******************************************************************************************************************
    """Function calculates the sum of nweight values based upon the arguments entered as parameters to the function
    Args:
    	st_name (string): name of the state the summed weights for a building type are to be calculated
    	income_level (string): income category that summed weights are to be calculate "Low","Middle", "Moderate",
    	    or "Upper"
    	population_density (string): population density category to be used in the summed weights ("C" = suburban,
    	    "R" = rural, "U" = urban)
    	housing_type (int): housing type category to be used in the summed weights 1 = Mobile Home, 
    	    2 = Single Family Detatched,3 = Single Family Attached, 4 = Apartment 2-4, 5 = Apartment 5 or more
    	year_made_range (int): the category of date range during which the housing was built 1 = Before 1950, 
    	    2 = 1950-1959, 3 = 1960-1969, 4 = 1970-1979, 5 = 1980-1989, 6 = 1990-1999, 7 = 2000-2009, 8 = 2010-2015, 
    	    9 = 2016-2020

    Returns:
    	dataframe: containing the calculated summation value
    """
    def calc_building_age(self, st_name, income_level, population_density, housing_type, year_made_range):
        xlrd = self.recs_data
        sql_query = "SELECT SUM(nweight) FROM xlrd WHERE state_name='" + st_name + "'" + " AND typehuq=" + str(
            housing_type) + " AND Income_cat='" + income_level + "'" + " AND UATYP10='" + population_density + "' AND YEARMADERANGE =" + str(
            year_made_range)
        total_age_weight = dkdb.query(sql_query).to_df()
        return total_age_weight

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    """Function calculates the sum of nweight values based upon the arguments entered as parameters to the function
    Args:
    	st_name (string): name of the state the summed weights for a building type are to be calculated
    	income_level (string): income category that summed weights are to be calculate "Low","Middle", "Moderate",
    	    or "Upper"
    	population_density (string): population density category to be used in the summed weights ("C" = suburban,
    	    "R" = rural, "U" = urban)
    	housing_type (int): housing type category to be used in the summed weights 1 = Mobile Home, 
    	    2 = Single Family Detatched,3 = Single Family Attached, 4 = Apartment 2-4, 5 = Apartment 5 or more
    	year_made_range (int): the category of date range during which the housing was built 1 = Before 1950, 
    	    2 = 1950-1959, 3 = 1960-1969, 4 = 1970-1979, 5 = 1980-1989, 6 = 1990-1999, 7 = 2000-2009, 8 = 2010-2015, 
    	    9 = 2016-2020
        sqft_range (int): the square footage category of a house 1 = 1 Less than 600 square feet, 
    	    2 = 2 600 to 799 square feet, 3 = 3 800 to 999 square feet, 4 = 4 1,000 to 1,499 square feet, 
    	    5 = 5 1,500 to 1,999 square feet, 6 = 6 2,000 to 2,499 square feet, 7 = 7 2,500 to 2,999 square feet,
    	    8 = 8 3,000 square feet or more
    Returns:
    	dataframe: containing the calculated summation value
    """
    def calc_building_count(self, st_name, income_level, population_density, housing_type, year_made_range, sqft_range):
        xlrd = self.recs_data
        sql_query = "SELECT SUM(nweight), COUNT(nweight) FROM xlrd WHERE state_name='" + st_name + "'" + " AND typehuq=" + str(
            housing_type) + " AND Income_cat='" + income_level + "'" + " AND UATYP10='" + population_density + "' AND YEARMADERANGE =" + str(
            year_made_range) + " AND SQFTRANGE =" + str(sqft_range)
        total_building_count = dkdb.query(sql_query).to_df()
        return total_building_count

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    """Function queries a list of unique state names contained in the dataset
    Args:
        none
    Returns:
    	dataframe: containing the calculated summation value
    """
    def get_state_names(self):
        xlrd = self.recs_data
        sql_query = "SELECT DISTINCT(state_name) FROM xlrd ORDER BY state_name ASC"
        state_names = dkdb.query(sql_query).to_df()
        return state_names

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    """Function queries a list of unique income categories contained in the dataset
    Args:
        none
    Returns:
    	dataframe: contains the list of unique income categories
    """
    def get_income_levels(self):
        xlrd = self.recs_data
        sql_query = "SELECT DISTINCT(Income_cat) FROM xlrd ORDER BY Income_cat ASC"
        income_levels = dkdb.query(sql_query).to_df()
        return income_levels

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    """Function queries a list of unique population density categories contained in the dataset
    Args:
        none
    Returns:
    	dataframe: contains the list of unique population density categories
    """
    def get_density_levels(self):
        xlrd = self.recs_data
        sql_query = "SELECT DISTINCT(UATYP10) FROM xlrd ORDER BY UATYP10 ASC"
        density_levels = dkdb.query(sql_query).to_df()
        return density_levels

    #*******************************************************************************************************************
    #*******************************************************************************************************************

    """Function queries a list of unique building type categories contained in the dataset
    Args:
        none
    Returns:
    	dataframe: contains the list of unique building type categories
    """
    def get_building_types(self):
        xlrd = self.recs_data
        sql_query = "SELECT DISTINCT(TYPEHUQ) FROM xlrd ORDER BY TYPEHUQ ASC"
        building_types = dkdb.query(sql_query).to_df()
        return building_types

    def run_test(self):
#        house_vintage_df, house_type_df = self.get_house_type_vintage("California", "Middle&Moderate", "U")
#        dist_df = self.get_parameter_distribution('California', 'Middle&Moderate', 'U', 2, 5, 'ROOFTYPE')
        solar_percent = self.calc_solar_percentage("California", "Upper", "U")
        print(solar_percent)

#***************************************************************************************************
#***************************************************************************************************

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    recs_ds = recs_data_set("datafiles/TESP_RECS.db")
    recs_ds.run_test()
