import os

import numpy as np
import pandas as pd
import json

node = 8
dso_name = []
for idx in range(1,node+1):
    dso_name.append(f'DSO_{idx}')

def time_of_use_price_profile(tou_params, step_size, dso_name, save_path=None):
    """Creates a price profile that corresponds to parameters of a specified 
   time-of-use rate.

   Args:
       tou_params (dict): A dictionary of relevant time-of-use rate parameters for 
        each DSO. Includes time-of-use rate periods, off-peak price, scaling between 
        off-peak price and specified time-of-use period, and seasonal membership for 
        each month.
       step_size (str): A string indicating the size of each time step in a format 
        recognizable by pandas (e.g., "1h" corresponds to time steps of one hour, 
        "5min" corresponds to time steps of five minutes).
       dso_name (str): A string specifying the DSO's name.
       save_path (str): A string specifying the directory to which the created 
        time-of-use price profile should be saved. If no price profile should be saved, 
        provide None. Defaults to not saving the created price profile.

   Reutrns:
       tou_profile (pandas.DataFrame): A DataFrame specifying the price profile for 
       each DSO in time steps of size `step_size`.
    """
    # Create mapping of month numbers to month abbreviations
    month_num_to_abbrev = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }

    # Initialize the time stamp
    timestamp = pd.Series(
        pd.date_range(start="2015-12-29", end="2016-12-31 23:59:00", freq=step_size)
    )

    # Initialize the time-of-use price profile for each DSO
    tou_profile = pd.DataFrame(
        data={"Timestamp": timestamp,
              **{dso_name[idx]: np.zeros(len(timestamp)) for idx in range(len(dso_name))}}
    )
    tou_profile.set_index("Timestamp", inplace=True)

    # Create the time-of-use price profile for each DSO
    for d in tou_profile.columns:
        for t in timestamp:
            for p in tou_params[d][month_num_to_abbrev[t.month]]["periods"]:
                for h in range(
                    len(
                        tou_params[d][month_num_to_abbrev[t.month]]["periods"][p][
                            "hour_start"
                        ]
                    )
                ):
                    if t.hour in range(
                        tou_params[d][month_num_to_abbrev[t.month]]["periods"][p][
                            "hour_start"
                        ][h],
                        tou_params[d][month_num_to_abbrev[t.month]]["periods"][p][
                            "hour_end"
                        ][h],
                    ):
                        tou_profile.loc[t, d] = (
                            tou_params[d][month_num_to_abbrev[t.month]]["price"]
                            * tou_params[d][month_num_to_abbrev[t.month]]["periods"][p][
                                "ratio"
                            ]
                        )

    # Save the file, if desired
    if save_path is not None:
        tou_profile.to_csv(os.path.join(save_path, "time_of_use_price_profile.csv"), header=None)

    # Return the time-of-use price profile
    return tou_profile


def main(dso_name, method):
    # Create or load time-of-use parameters
    # Specify the path to which the price profile should be saved, if desired
    #save_path = None
    save_path = "../../../../examples/analysis/dsot/data"

    if method == "create":
        # Specify the rate parameters for winter months
        winter_dict = {
            "periods": {
                "off-peak": {
                    "hour_start": [0, 9, 20],
                    "hour_end": [6, 17, 24],
                    "ratio": 1,
                },
                "peak": {
                    "hour_start": [6, 17],
                    "hour_end": [9, 20],
                    "ratio": 3,
                },
            },
            "price": 0.07,
            "season": "winter",
        }

        # Specify the rate parameters for summer months
        summer_dict = {
            "periods": {
                "off-peak": {
                    "hour_start": [0, 22],
                    "hour_end": [16, 24],
                    "ratio": 1,
                },
                "peak": {
                    "hour_start": [16],
                    "hour_end": [22],
                    "ratio": 3,
                },
            },
            "price": 0.07,
            "season": "summer",
        }

        # Create the rate structure for one DSO by assigning winter and summer months
        single_dso_params = {
            "Jan": winter_dict,
            "Feb": winter_dict,
            "Mar": winter_dict,
            "Apr": winter_dict,
            "May": summer_dict,
            "Jun": summer_dict,
            "Jul": summer_dict,
            "Aug": summer_dict,
            "Sep": summer_dict,
            "Oct": summer_dict,
            "Nov": winter_dict,
            "Dec": winter_dict,
        }

        # Create the time-of-use rate structure for each DSO
        tou_params = {}
        for name in dso_name:
            tou_params[name] = single_dso_params

    elif method == "load":
        with open(os.path.join(save_path, "time_of_use_price_profile.csv"),"r") as fp:
            tou_params = json.load(fp)
    else:
        raise ValueError(
            f"{method} is not a viable method for specifying a time-of-use profile. "
            + "Please try again."
        )
    
    # Specify the step size between each time stamp in the time-of-use price profile
    step_size = "5min"
    #step_size = "1h"


    # Create the time-of-use price profile
    tou_profile = time_of_use_price_profile(tou_params, step_size, dso_name, save_path)

if __name__ == "__main__":
    # method = "create" or "load" time-of-use parameters
    main(dso_name, "create")
    