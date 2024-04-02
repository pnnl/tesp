# -*- coding: utf-8 -*-
"""
Created on Wed Mar 27 10:52:51 2024

@author: rame388
"""

import os
import pandas as pd
import numpy as np

load_5min = pd.read_csv('2016_ERCOT_5min_load_data.csv', index_col=False)
load_5min.index = load_5min['Seconds']

# x = np.linspace(0, 2*np.pi, 10)
# y = np.sin(x)
# xvals = np.linspace(0, 2*np.pi, 50)
# yinterp = np.interp(xvals, x, y)

x = np.array(load_5min.index)
y1 = np.array(load_5min['Bus1'])
y2 = np.array(load_5min['Bus2'])
y3 = np.array(load_5min['Bus3'])
y4 = np.array(load_5min['Bus4'])
y5 = np.array(load_5min['Bus5'])
y6 = np.array(load_5min['Bus6'])
y7 = np.array(load_5min['Bus7'])
y8 = np.array(load_5min['Bus8'])
xvals = np.linspace(0, 32050500, 106835*5)
b1 = np.interp(xvals, x, y1)
b2 = np.interp(xvals, x, y2)
b3 = np.interp(xvals, x, y3)
b4 = np.interp(xvals, x, y4)
b5 = np.interp(xvals, x, y5)
b6 = np.interp(xvals, x, y6)
b7 = np.interp(xvals, x, y7)
b8 = np.interp(xvals, x, y8)

b1 = (b1 )/(np.max(b1))
b2 = (b2 )/(np.max(b2))
b3 = (b3 )/(np.max(b3))
b4 = (b4 )/(np.max(b4))
b5 = (b5 )/(np.max(b5))
b6 = (b6 )/(np.max(b6))
b7 = (b7 )/(np.max(b7))
b8 = (b8 )/(np.max(b8))

load_1min = pd.DataFrame({1:b1, 2:b2, 3:b3, 4:b4, 5:b5, 6:b6, 7:b7, 8:b8})
load_1min.to_csv("loadprofile_1min.csv", index=False, header=None)
