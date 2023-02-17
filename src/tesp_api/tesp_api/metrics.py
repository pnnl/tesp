# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: metrics.py
"""
  Stuff here
"""


class avg_deviation:
    """
    Measures the average deviation using the actual measurement(s) vs the set point(s).

    Input lengths must be the same

    """

    @staticmethod
    def _base_avg_deviation(self, list1, list2):
        """
        Measures the average deviation.

        Args:
            list1 (list):
            list2 (list):

        Returns:
            average_deviation: (float)
        """

        if len(list1) == len(list2):
            _avg = 0
            for _i in range(len(list1)):
                _avg += list1[_i] - list2[_i]
            return _avg / len(list1)
        return None

    def _avg_deviation(self, input1, input2):
        """
        find out type

        Args:
            input1 (list):  list
            input2 (any):  float or list

        Returns:
            average_deviation: (float)

        """
        return

    def _avg_deviation(self, start_date, end_date, input1, input2):
        """

        Args:
            start_date:
            end_date:
            input1:
            input2:

        Returns:
            average_deviation: (float)

        """
        return
