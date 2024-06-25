import os

import numpy as np
import pandas as pd
import json


def time_of_use_price_profile(tou_params, step_size, save_path=None):
    """_summary_

    Args:
        tou_params (_type_): _description_
        step_size (_type_): _description_
        save_path (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
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
        pd.date_range(start="2016-01-01", end="2016-12-31 23:59:00", freq=step_size)
    )

    # Initialize the time-of-use price profile for each DSO
    tou_profile = pd.DataFrame(
        data={
            "Timestamp": timestamp,
            "DSO_1": np.zeros(len(timestamp)),
            "DSO_2": np.zeros(len(timestamp)),
            "DSO_3": np.zeros(len(timestamp)),
            "DSO_4": np.zeros(len(timestamp)),
            "DSO_5": np.zeros(len(timestamp)),
            "DSO_6": np.zeros(len(timestamp)),
            "DSO_7": np.zeros(len(timestamp)),
            "DSO_8": np.zeros(len(timestamp)),
        }
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
        tou_profile.to_csv(os.path.join(save_path, "time_of_use_price_profile.csv"))

    # Return the time-of-use price profile
    return tou_profile


def main():
    # Create or load time-of-use parameters
    #method = "create"
    method = "load"
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
            "price": 0.1,
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
            "price": 0.1,
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
        tou_params = {
            "DSO_1": single_dso_params,
            "DSO_2": single_dso_params,
            "DSO_3": single_dso_params,
            "DSO_4": single_dso_params,
            "DSO_5": single_dso_params,
            "DSO_6": single_dso_params,
            "DSO_7": single_dso_params,
            "DSO_8": single_dso_params,
        }
    elif method == "load":
        with open("time_of_use_parameters.json", "r") as fp:
            tou_params = json.load(fp)
    else:
        raise ValueError(
            f"{method} is not a viable method for specifying a time-of-use profile. "
            + "Please try again."
        )

if __name__ == "__main__":
    main()
    
    # Specify the step size between each time stamp in the time-of-use price profile
    #step_size = "5min"
    step_size = "1h"

    # Specify the path to which the price profile should be saved, if desired
    #save_path = None
    save_path = "../../../../examples/analysis/dsot/data"

    # Create the time-of-use price profile
    tou_profile = time_of_use_price_profile(tou_params, step_size, save_path)