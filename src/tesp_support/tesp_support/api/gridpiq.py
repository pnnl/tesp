#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019-2023 Battelle Memorial Institute
"""
Created on Mon Jan 23 14:05:08 2023

This script attempts to demonstrate the grid PIQ for new TESP API.

@author: d3j331 - Mitch Pelton
"""

import json

from tesp_support.api.store import entities_path
from tesp_support.api.entity import assign_defaults


# Identified avert regions
# https://www.epa.gov/avert/avert-tutorial-getting-started-identify-your-avert-regions

class GridPIQ:
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
        self.config = assign_defaults(self, entities_path + 'grid_PIQ.json')

    def reset_dispatch_data(self):
        self.Zeros = []
        self.Total = []
        for kind in self.choices:
            gen = self.__getattribute__(kind)
            gen = []

    def set_dispatch_data(self, kind, idx, data):
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
        if count > 0:
            for kind in self.choices:
                gen = self.__getattribute__(kind)
                gen /= count

    def set_max_load(self, data):
        if data > self.max_load:
            self.max_load = data

    def set_datetime(self, start_datetime, end_datetime):
        """

        Args:
            start_datetime:
            end_datetime:

        Returns:

        """
        self.tech[0]['parameters']['post_project_load']['start_date'] = start_datetime
        self.tech[0]['parameters']['post_project_load']['end_date'] = end_datetime
        self.context['parameters']['pre_project_load']['start_date'] = start_datetime
        self.context['parameters']['pre_project_load']['end_date'] = end_datetime
        self.context['parameters']['dispatch_data']['start_date'] = start_datetime
        self.context['parameters']['dispatch_data']['end_date'] = end_datetime
        gbl = self.__getattribute__('global')
        gbl['parameters']['analysis_start_date']['data'] = start_datetime
        gbl['parameters']['analysis_end_date']['data'] = end_datetime

    def write_json(self):
        """

        """
        for kind in self.choices:
            gen = self.__getattribute__(kind)
            if kind == 'NaturalGas':
                self.context['parameters']['dispatch_data']['data']['Natural Gas'] = gen
            else:
                self.context['parameters']['dispatch_data']['data'][kind] = gen
            for ii in range(len(gen)):
                if ii == len(self.Total):
                    self.Zeros.append(0)
                    self.Total.append(gen[ii])
                else:
                    self.Total[ii] += gen[ii]

        self.context['parameters']['pre_project_load']['data'] = self.Zeros
        self.context['parameters']['pre_project_max_load']['data'] = 0

        self.tech[0]['parameters']['post_project_load']['data'] = self.Total
        self.tech[0]['parameters']['post_project_max_load']['data'] = self.max_load

        dictionary = {
            "tech": [self.tech[0]],
            "impacts": self.impacts,
            "context": self.context,
            "global": self.__getattribute__('global')
        }
        with open("sample.json", "w") as outfile:
            json.dump(dictionary, outfile, indent=2)


def test():
    start_date = "2016-01-04 00:00"
    end_date = "2016-01-04 23:00"
    choices = ["Nuclear", "Wind", "Coal", "Solar", "NaturalGas", "Petroleum"]
    percent = [0.10, 0.10, 0.40, 0.0, 0.30, 0.10]
    data = [
        44549.86877, 45016.21691, 47017.04049, 45582.91460, 46028.10423, 46489.12242, 46846.10710, 46890.73556,
        46086.56812, 44254.71294, 42134.03615, 40375.42948, 39034.53516, 38206.21089, 37822.15485, 37919.82094,
        38486.89171, 39637.39861, 41622.17184, 43177.01046, 43815.28902, 44178.21888, 42964.65054, 42026.75463
    ]

    pq = GridPIQ()
    pq.set_datetime(start_date, end_date)
    for i in range(len(choices)):
        for j in range(len(data)):
            pq.set_dispatch_data(choices[i], j, data[j]*percent[i])
    pq.set_max_load(55678.4353)
    pq.write_json()


if __name__ == '__main__':
    test()
