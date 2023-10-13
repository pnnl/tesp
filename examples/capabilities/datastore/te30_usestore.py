# Copyright (C) 2023 Battelle Memorial Institute
# file: te30_usestore.py
""" 
Takes existing datastore made by running the te30 example and processes the results. This
demonstrates the prototype datastore capability in TESP.
"""


import tesp_support.api.store as store
import os
import pprint
import matplotlib.pyplot as plt
from datetime import datetime as dt
import pandas as pd

# Setting up pretty printing, mostly for debugging.
pp = pprint.PrettyPrinter(indent=4)


def process_results(case_name):
    """
    Opens up datastore (.zip) and metadata (.json) to process results

    Assumes te30_store.zip and te30_store.json have been copied from ../te30 folder to
    the same folder as this script (examples/capabilities/datastore).
    """
    start_date_1 = "2013-07-01 00:00"
    end_date_1 = "2013-07-02 00:00"

    # Depending on how your unzip tools work, unzipping the data store may
    # create another folder and put all the zipped files into it. If so,
    # we need to change our working directory to that folder.
    if os.path.exists(case_name):
        os.chdir(case_name)

    # Define the data store
    te30_store = store.Store(case_name)

    # List all the files in the store for inspection; particularly useful if
    # you're new to the dataset
    print(f"Schemas in data store:")
    for item in te30_store.get_schema():
        print(f"\t{item}")

    # Get weather data (CSV)
    # "weather" is the name of the data store schema for "weather.csv
    weather_schema = te30_store.get_schema("weather")

    # Inspect the available tables and data
    print(f"Weather tables {pp.pformat(weather_schema.tables)}")
    print(f"Weather columns {pp.pformat(weather_schema.columns)}")
    # The "solar_flux" column is what we're looking for.

    # For better or worse, the single table of data inside weather.csv is
    # also named "weather".
    weather_data = weather_schema.get_series_data("weather", start_date_1, end_date_1)

    # Checking data type for timestamp and convert if necessary
    weather_time = weather_data["timestamp"]
    if isinstance(weather_time.iloc[0], str):
        # For some reason, Pandas is not a happy camper with the timezone information
        # cutting it out since it is not relevant for this example
        weather_time = weather_time.str[:-4]
        weather_time = pd.to_datetime(weather_time, format="%Y-%m-%d %H:%M:%S")
    # And convert the data as strings to numeric values
    if isinstance(weather_data["solar_flux"].iloc[0], str):
        solar_data = pd.to_numeric(weather_data["solar_flux"])

    # As a convenience, make a new dataframe with only the data I need
    weather_data = pd.concat([weather_time.T, solar_data], axis=1)
    weather_data = weather_data.set_index("timestamp")

    # Get rooftop solar production data (HDF5)
    inverter_schema = te30_store.get_schema("inverter_TE_ChallengeH_metrics")

    print(f"Inverter tables {pp.pformat(inverter_schema.tables)}")
    print(f"inverter columns {pp.pformat(inverter_schema.columns)}")
    # For silly reasons, GridLAB-D stores each day of data in its own table
    # called "index1", "index2", etc.

    inverter_data = inverter_schema.get_series_data("index1", start_date_1, end_date_1)
    # Just going to be looking at data from a single house
    houseA11_inv = inverter_data.loc[(inverter_data["name"] == b"inv_F1_house_A11")]
    inverter_time = houseA11_inv["date"]
    if isinstance(inverter_time.iloc[0], str):
        inverter_time = inverter_time.str[:-4]
        inverter_time = pd.to_datetime(inverter_time, format="%Y-%m-%d %H:%M:%S")
    inverter_data = pd.concat([inverter_time.T, houseA11_inv["real_power_avg"]], axis=1)
    inverter_data = inverter_data.set_index("date")

    # Plot the resulting data
    fig = plt.figure()
    ax1 = fig.add_subplot()
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Inverter Power (W)")
    ax1.plot(inverter_data["real_power_avg"], label="Inverter Power", color="blue")
    ax2 = ax1.twinx()
    ax2.set_ylabel("Solar Flux (W/ft^2)")
    ax2.plot(weather_data["solar_flux"], label="Solar Flux", color="orange")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc=2)
    fig.autofmt_xdate(rotation=45)
    plt.show()


if __name__ == "__main__":
    process_results("te30_store")
