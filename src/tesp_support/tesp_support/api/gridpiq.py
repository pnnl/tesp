#!/usr/bin/env python3
# Copyright (C) 2022-2023 Battelle Memorial Institute
# file: gridpiq.py
# Created on 1/23/2023
# @author: d3j331 - Mitch Pelton
"""This script attempts to demonstrate the grid PIQ for new TESP API.
"""

import json
from datetime import datetime, timedelta

from .data import piq_entities_path
from .entity import assign_defaults


class GridPIQ:
    # Identified avert regions
    # https://www.epa.gov/avert/avert-tutorial-getting-started-identify-your-avert-regions

    def __init__(self):
        self.impacts = None
        self.context = {}
        self.tech = None
        self.max_load = 0
        self.Nuclear = []
        self.Wind = []
        self.Coal = []
        self.Solar = []
        self.NaturalGas = []
        self.Petroleum = []
        self.Zeros = []
        self.Total = []

        self.choices = {"Nuclear", "Wind", "Coal", "Solar", "NaturalGas", "Petroleum"}
        self.config = assign_defaults(self, piq_entities_path)

    def reset_dispatch_data(self):
        """

        """
        self.Zeros = []
        self.Total = []
        for kind in self.choices:
            gen = self.__getattribute__(kind)
            gen = []

    def set_dispatch_data(self, kind, idx, data):
        """

        Args:
            kind:
            idx:
            data:
        """
        # kind is one of "Nuclear", "Wind", "Coal", "Solar", "NaturalGas", "Petroleum"
        # or the lower case of it
        # idx starts at 0
        for choice in self.choices:
            if kind.lower() in choice.lower():
                gen = self.__getattribute__(choice)
                length = len(gen)
                if idx == length:
                    gen.append(data)
                elif idx > length:
                    while length < idx:
                        gen.append(0)
                        length += 1
                    gen.append(data)
                else:
                    gen[idx] += data
                break

    def avg_dispatch_data(self, count):
        """

        Args:
            count (int):
        """
        if count > 0:
            for kind in self.choices:
                gen = self.__getattribute__(kind)
                idx = len(gen) - 1
                if idx > -1:
                    gen[idx] = gen[idx] / count

    def set_max_load(self, data):
        """

        Args:
            data (float):
        """
        if data > self.max_load:
            self.max_load = data

    def set_datetime(self, start_datetime, end_datetime, s_offset, e_offset):
        """

        Args:
            start_datetime (str): the start date and time with the format '%Y-%m-%d %H:%M:%S'
            end_datetime (str): the end date and time with the format '%Y-%m-%d %H:%M:%S'
            s_offset (int): in hours
            e_offset (int): in hours
        """
        s = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S') + timedelta(hours=s_offset)
        e = datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S') + timedelta(hours=e_offset)
        start_ = f'{s:%Y-%m-%d %H:%M}'
        end_ = f'{e:%Y-%m-%d %H:%M}'

        self.tech[0]['parameters']['post_project_load']['start_date'] = start_
        self.tech[0]['parameters']['post_project_load']['end_date'] = end_
        self.context['parameters']['pre_project_load']['start_date'] = start_
        self.context['parameters']['pre_project_load']['end_date'] = end_
        self.context['parameters']['dispatch_data']['start_date'] = start_
        self.context['parameters']['dispatch_data']['end_date'] = end_
        gbl = self.__getattribute__('global')
        gbl['parameters']['analysis_start_date']['data'] = start_
        gbl['parameters']['analysis_end_date']['data'] = end_

    def toJson(self):
        """

        Returns:
            dict:
        """
        for kind in self.choices:
            gen = self.__getattribute__(kind)
            if len(gen) > 0:
                for ii in range(len(gen)):
                    if ii == len(self.Total):
                        self.Zeros.append(1)
                        self.Total.append(gen[ii])
                    else:
                        self.Total[ii] += gen[ii]
        for kind in self.choices:
            gen = self.__getattribute__(kind)
            if len(gen) > 0:
                for ii in range(len(gen)):
                    gen[ii] = gen[ii] / self.Total[ii]
                if kind == 'NaturalGas':
                    self.context['parameters']['dispatch_data']['data']['Natural Gas'] = gen
                else:
                    self.context['parameters']['dispatch_data']['data'][kind] = gen

        self.max_load = 0
        for ii in range(len(gen)):
            self.set_max_load(self.Total[ii])

        self.context['parameters']['pre_project_load']['data'] = self.Zeros
        self.context['parameters']['pre_project_max_load']['data'] = 1

        self.tech[0]['parameters']['post_project_load']['data'] = self.Total
        self.tech[0]['parameters']['post_project_max_load']['data'] = self.max_load

        dictionary = {
            "tech": [self.tech[0]],
            "impacts": self.impacts,
            "context": self.context,
            "global": self.__getattribute__('global')
        }
        return dictionary

    def write(self, filename):
        with open(filename, "w") as outfile:
            json.dump(self.toJson(), outfile, indent=2)


def _test():
    from .data import tesp_test

    start_date = "2016-01-03 00:00:00"
    end_date = "2016-01-05 00:00:00"
    choices = ["Nuclear", "Wind", "Coal", "Solar", "NaturalGas", "Petroleum"]
    percent = [0.10, 0.10, 0.40, 0.0, 0.30, 0.10]
    data = [
        44549.86877, 45016.21691, 47017.04049, 45582.91460, 46028.10423, 46489.12242, 46846.10710, 46890.73556,
        46086.56812, 44254.71294, 42134.03615, 40375.42948, 39034.53516, 38206.21089, 37822.15485, 37919.82094,
        38486.89171, 39637.39861, 41622.17184, 43177.01046, 43815.28902, 44178.21888, 42964.65054, 42026.75463
    ]

    pq = GridPIQ()
    pq.set_datetime(start_date, end_date, 24, -1)
    for j in range(len(data)):
        for i in range(len(choices)):
            if i != 3:
                pq.set_dispatch_data(choices[i], j, data[j]*percent[i])
                for k in range(8):
                    pq.set_dispatch_data(choices[i], j, data[j]*percent[i])
        pq.avg_dispatch_data(9)
    pq.set_max_load(55678.4353)
    pq.write(tesp_test + "api/gridPIQ.json")


if __name__ == '__main__':
    _test()
