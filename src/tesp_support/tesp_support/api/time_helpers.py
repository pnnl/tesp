# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: time_helpers.py
""" Utility time functions for use within tesp_support, including new agents.
"""

import numpy as np


def get_secs_from_hhmm(time):
    """ Convert HHMM to seconds

    Args:
        time (float): HHMM
    Returns:
        int: seconds
    """
    return np.floor(time / 100) * 3600 + (time % 100) * 60


def get_hhmm_from_secs(time):
    """ Convert seconds to HHMM

    Args:
        time (int): seconds
    Returns:
        int: HHMM
    """
    time = 60 * round(time / 60)
    ret = int(np.floor(time / 3600) * 100 + np.round((time % 3600) / 60))
    if ret == 2400:
        return 0
    return ret


def subtract_hhmm_secs(hhmm, secs):
    """ Subtract hhmm time - secs duration

    Args:
        hhmm (float): HHMM format time
        secs (int): seconds
    Returns:
        arrival time in HHMM
    """
    arr_secs = get_secs_from_hhmm(hhmm) - secs
    if arr_secs < 0:
        arr_secs = arr_secs + 24 * 3600
    return get_hhmm_from_secs(arr_secs)


def add_hhmm_secs(hhmm, secs):
    """ Add hhmm time + seconds duration

    Args:
        hhmm (float): HHMM
        secs (int): seconds
    Returns:
        hhmm+secs in hhmm format
    """
    add_secs = get_secs_from_hhmm(hhmm) + secs
    if add_secs > 24 * 3600:
        add_secs = add_secs - 24 * 3600
    return get_hhmm_from_secs(add_secs)


def get_duration(arrival, leave):
    """ Convert arrival and leaving time to duration

    Args:
        arrival (float): in HHMM format
        leave (float): in HHMM format
    Returns:
        int: duration in seconds
    """
    arr_secs = np.floor(arrival / 100) * 3600 + (arrival % 100) * 60
    leave_secs = np.floor(leave / 100) * 3600 + (leave % 100) * 60
    if leave > arrival:
        return leave_secs - arr_secs
    else:
        return (leave_secs - arr_secs) + 24 * 3600


def is_hhmm_valid(time):
    """ Check if HHMM is a valid number

    Args:
        time (float): HHMM format
    Returns:
        bool: true if valid or false if not
    """
    hr = np.floor(time / 100)
    mn = time % 100
    if hr > 23 or hr < 0 or mn < 0 or mn > 59 or type(mn) != int:
        return False
    return True


def get_dist(mean, var):
    """ Get a random number from a distribution given mean and %variability

    Args:
        mean (float): mean of distribution
        var (float): % variability
    Returns:
        float: one random entry from distribution
    """
    dev = (1 - var / 100) + np.random.uniform(0, 1) * var / 100 * 2
    return mean * dev
