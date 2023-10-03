
import json

import tesp_support.api.store as fle


def dsot_store(case_name):
    my_store = fle.Store('dsot_store')

    my_file = my_store.add_path("../", "DSOT Directory")
    # case
    sub = my_file.set_includeDir("code/" + case_name, True)

    # We need to load in the master metadata (*system_case_config.json)
    # case_file = "../code/" + case_name + "/generate_case_config.json"
    # with open(case_file, 'r', encoding='utf-8') as json_file:
    #     sys_config = json.load(json_file)
    #     start_time = sys_config['StartTime']
    #     end_time = sys_config['EndTime']
    #     tso_config = sys_config['DSO']
    #     for i in range(len(tso_config)):
    #         name = tso_config[i][1] + 'metrics_billing_meter.h5'
    #         my_file = my_store.add_file(name, tso_config[i][1], "billing for " + tso_config[i][1])
    #         tables = my_file.get_tables()
    #         if len(tables) > 1:
    #             columns = my_file.get_columns(tables[1])
    #             my_file.set_date_bycol(tables[1], 'date')

    # schedules
    sub = my_file.set_includeDir("data/schedule_df", True)
    # solar
    sub = my_file.set_includeDir("data/8-node data/DAT formatted files", True)
    # data
    sub = my_file.set_includeDir("data", False)
    # outages files
    my_file.set_includeFile(sub, "planned_outages.csv")
    my_file.set_includeFile(sub, "unplanned_outages.csv")
    # player files
    my_file.set_includeFile(sub, "mod_renew*")
    my_file.set_includeFile(sub, "2016_ERCOT_5min_Load_Data_Revised.csv")
    my_file.set_includeFile(sub, "2016_ERCOT_Hourly_Load_Data_Revised.csv")
    my_file.set_includeFile(sub, "8_const_industry_p.csv")
    # metadat file generating case
    my_file.set_includeFile(sub, "default_case_config.json")
    my_file.set_includeFile(sub, "8-metadata-lean.json")
    my_file.set_includeFile(sub, "hvac_setpt.json")
    my_file.set_includeFile(sub, "8_DSO_quadratic_curves.json")
    my_file.set_includeFile(sub, "DSOT_commercial_metadata.json")
    my_file.set_includeFile(sub, "DSOT_residential_metadata.json")
    my_file.set_includeFile(sub, "DSOT_battery_metadata.json")
    my_file.set_includeFile(sub, "DSOT_ev_model_metadata.json")
    my_file.set_includeFile(sub, "DSOT_ev_driving_metadata.csv")
    my_file.set_includeFile(sub, "8_schedule_server_metadata.json")

    # "solarPPlayerFile": "5_minute_dist_power.csv"
    # "solarAgentForecastFile": "8-node_dist_hourly_forecast_power.csv"
    # "solarDataPath": "../../../data/solar_data/solar_pv_power_profiles/"
    # "dataPath": "../data"
    # "WeatherDataSourcePath": "../data/8-node data/DAT formatted files/"

    my_store.write()
    my_store.zip()


def little_post():
    pass


if __name__ == "__main__":
    dsot_store("lean_aug_8")
