#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019-2023 Battelle Memorial Institute
"""
Created on Mon Jan 23 14:05:08 2023

This script attempts to demonstrate the grid PIQ for new TESP API.

@author: d3j331 - Mitch Pelton
"""

import json
import math
import os
import re
import numpy as np

import tesp_support.helpers
from store import entities_path
from entity import assign_defaults
from model import GLModel
from entity import Entity


# Identified avert regions
# https://www.epa.gov/avert/avert-tutorial-getting-started-identify-your-avert-regions

class gridPIQ:
    def __init__(self):
        self.config = assign_defaults(self, entities_path + 'grid_PIQ.json')

    def set_dispatch_data(self, data):
        return
    
    def set_datetime(self, start_datetime, end_datetime):
        self.tech[0].post_project_load.start_date = start_datetime
        self.tech[0].post_project_load.end_date = end_datetime
        self.context.parameters.pre_project_load.start_date = start_datetime
        self.context.parameters.pre_project_load.end_date = end_datetime
        self["global"].parameters.analysis_start_date.data = start_datetime
        self["global"].parameters.analysis_end_date.data = end_datetime

    def write_json(self):
        dictionary = {
            "tech": [self.tech[0]],
            "context": self.context,
            "global": self["global"]
        }
        with open("sample.json", "w") as outfile:
            json.dump(dictionary, outfile)
