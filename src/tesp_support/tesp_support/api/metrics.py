# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: metrics.py
"""
  Stuff here
"""

import logging as log

logger = log.getLogger()
# logger.setLevel(log.INFO)
logger.setLevel(log.WARNING)
# logger.setLevel(log.DEBUG)
# log.info('starting metics...')

debug = True


def _base_avg_deviation(list1, list2):
    """
    Measures the average deviation.

    Args:
        list1 (list):
        list2 (list):

    Returns:
        average_deviation: (float)
    """
    if debug:
      assert()
    if len(list1) == len(list2):
        _i = 0
        _avg = 0
        for _i in range(len(list1)):
            _avg += list1[_i] - list2[_i]
        return _avg / len(list1)
    return None
