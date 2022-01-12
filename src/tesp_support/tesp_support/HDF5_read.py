# -*- coding: utf-8 -*-
# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: HDF5_read.py
"""
Created on Thu Jul 18 11:06:53 2019

@author: yint392
"""

import os
import pandas as pd



pd.set_option('display.max_columns', 50)


# change path
os.chdir('C:/Users/yint392/Documents/DSO/TE_test_different/dso_1')
os.chdir('C:/Users/yint392/Documents/DSO/TE_test_different/TE_Base_s1')

# get the HDF5 file names
hdf5filenames = [f for f in os.listdir('.') if f.endswith('.hdf5') and f.startswith('battery_agent')]
hdf5filenames = [f for f in os.listdir('.') if f.endswith('.hdf5') and f.startswith('dso_market')]
hdf5filenames = [f for f in os.listdir('.') if f.endswith('.hdf5') and f.startswith('retail_market')]

hdf5filenames = [f for f in os.listdir('.') if f.endswith('.h5') and f.startswith('billing_meter')]
hdf5filenames = [f for f in os.listdir('.') if f.endswith('.h5') and f.startswith('substation')]

# get the keys
filename = hdf5filenames[0]
store = pd.HDFStore(filename,'r')
list(store.keys())


# reading the data
test_df = pd.read_hdf(hdf5filenames[0], key='/metrics_df0', mode='r')
test_df = pd.read_hdf(hdf5filenames[0], key='/metrics_df1', mode='r')


test_df = pd.read_hdf(hdf5filenames[0], key='/Metadata', mode='r')
test_df = pd.read_hdf(hdf5filenames[0], key='/index1', mode='r')

# check the data
test_df.head()

# print column names
for col in test_df: 
    print(col) 

# print index names
test_df.index.values


########## also an example of querying and making simple calculation using pd.read_hdf, the "where" parameter works like a SQL query

test = pd.read_hdf('battery_agent_TE_Base_s1_3600_0_metrics.hdf5', where = "bid_four_point_da > 0.1",
                   key='/metrics_df0', columns=['uid', 'bid_four_point_da'], mode='r').groupby('uid')['bid_four_point_da'].mean()



