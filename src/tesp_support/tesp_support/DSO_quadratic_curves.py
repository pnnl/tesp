# -*- coding: utf-8 -*-

# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: DSO_quadratic_curves.py
"""Class that prepares the quadratic curves for DSO market

"""
import json
import logging as log

import numpy as np
import pandas as pd

logger = log.getLogger()


class DSO_LMPs_vs_Q:
    """This object creats the quadractive curves witht historical data from the base case
    
    Args:
        config_path (str): path to file directory
        file_name (str): name of the CSV file containing the historical DA LMP prices with associated quantities 
        
    Attributes:
        config_path (str): path to file directory
        df_dsos_lml_q (list od dataframes): list of lmps and associated quantity trou time
        lmps_names (list of str): list of lmps names
        q_lmps_names (list of str): list of quantities names
        
        degree (int): degree of curve to be fitted
            
        coeficients_weekday (array of arrays): 24 arrays of 3 for every DSO
        coeficients_weekend (array of arrays): 24 arrays of 3 for every DSO
    """

    def __init__(self, config_path='LMP_DATA', file_name='/Annual_DA_LMP_Load_data.csv'):
        """Initialize the object
        """
        self.config_path = config_path
        data_da = pd.read_csv(config_path + file_name, skiprows=0)  # Read data
        # Include data to self
        # Organize and remove outliers
        self.df_dsos_lml_q, self.lmps_names, self.q_lmps_names = self.organize_remuve_outliers(data_da)
        # Curve parameters
        self.degree = 2  # quadratic curve
        # Fitted curves
        self.coeficients_weekday = None
        self.coeficients_weekend = None

    def organize_remuve_outliers(self, data_da):
        """Orginize and remuve outliers from dataframe of multiple DSO
        
        Args:
            data_da (dataframe): contaings historical data from DA LMPs with associated quantities 
        
        Returns:
            df_dsos_lml_q (list of dataframes): every element of the list is a DSO with historical price and quantiti. The index is pandas datetime.
        """
        # Organize data
        data_da['Date/Time'] = pd.to_datetime(data_da[data_da.columns[0]], format='%Y-%m-%d %H:%M:%S')
        data_da = data_da.set_index('Date/Time')
        lmps = []
        q_lmps = []

        names = data_da.columns
        names = list(names)
        for n in names:
            if n.startswith('da_lmp'):
                lmps.append(n)
            if n.startswith('da_q'):
                q_lmps.append(n)

        df_dsos_lml_q = []
        for i in range(len(lmps)):
            raw = pd.DataFrame()
            raw['y'] = data_da[lmps[i]].values / 1000.0
            raw['x'] = data_da[q_lmps[i]].values * 1000.0
            raw.index = data_da.index
            df_dsos_lml_q.append(raw)

        # Remove outliers (Retail market has a maximum price of "1000.0". Thus after division is equal to "1".)
        for i in range(len(lmps)):
            df_dsos_lml_q[i] = df_dsos_lml_q[i][df_dsos_lml_q[i]['y'] <= 0.999]

        return df_dsos_lml_q, lmps, q_lmps

    def fit_model(self, i, p_time):
        """Fit a quadractive curve utilizing sklearn
        
        Args:
            i (int): DSO identifier 
            p_time (np array boolean): True for samples utilized in fiiting the quadractic curve 
        
        Returns:
            df_dsos_lml_q (array): [['1', 'x', 'x^2']] quadractic curve coeficients 
        """
        x = np.array(self.df_dsos_lml_q[i]['x'][p_time].values)
        y = np.array(self.df_dsos_lml_q[i]['y'][p_time].values)
        zz = np.polyfit(x, y, self.degree)
        df_dsos_lml_q = np.array([zz[2], zz[1], zz[0]])
        return df_dsos_lml_q

    def multiple_fit_calls(self):
        """Calls the fit model for each cenario
        
        The cenarios are hour of day and day type (i.e., weekday and weekends)
        
        Args:
            positive (bolean): True to force curve coefficients to be positive 
        """
        coeficients_weekday = list()
        coeficients_weekend = list()
        for i in range(len(self.lmps_names)):
            temp = self.df_dsos_lml_q[i].index.dayofweek <= 4
            coeficients_weekday.append(self.fit_model(i, temp))
            temp = self.df_dsos_lml_q[i].index.dayofweek >= 5
            coeficients_weekend.append(self.fit_model(i, temp))

        self.coeficients_weekday = coeficients_weekday
        self.coeficients_weekend = coeficients_weekend
        return coeficients_weekday, coeficients_weekend

    def c_to_DSO_m(self, DSO, C):
        """Convert coefficients to DSO market
        
        Args:
            DSO (int): DSO identifier  
            C (int): from 0 to 2 especifing the curve coeficient being taken  
        """
        curve_c_weekday = np.full((5, 24), self.coeficients_weekday[DSO][C])
        curve_c_weekend = np.full((2, 24), self.coeficients_weekend[DSO][C])

        curve_c = np.concatenate((curve_c_weekday, curve_c_weekend), axis=0)
        return curve_c

    def make_json_out(self):
        """Save the fitted curve to json
        """
        data = {}
        for DSO in range(len(self.lmps_names)):
            data[self.lmps_names[DSO]] = []
            data[self.lmps_names[DSO]].append({
                'curve_c': self.c_to_DSO_m(DSO, 0).tolist(),
                'curve_b': self.c_to_DSO_m(DSO, 1).tolist(),
                'curve_a': self.c_to_DSO_m(DSO, 2).tolist(),
            })

        # with open(self.config_path+'/DSO_quadratic_curves.json', 'w') as outfile:
        with open('DSO_quadratic_curves.json', 'w') as outfile:
            json.dump(data, outfile)


if __name__ == "__main__":
    obj = DSO_LMPs_vs_Q()
    obj.multiple_fit_calls()
    # obj.make_json_out()

    import matplotlib.pyplot as plt

    """ Configure plots
    """
    # plt.rcParams['figure.figsize'] = (6, 8)
    plt.rcParams['figure.dpi'] = 600
    SMALL_SIZE = 14
    MEDIUM_SIZE = 16
    BIGGER_SIZE = 16
    plt.rcParams["font.family"] = "Times New Roman"
    plt.rc('font', size=SMALL_SIZE)  # controls default text sizes
    plt.rc('axes', titlesize=SMALL_SIZE)  # fontsize of the axes title
    plt.rc('axes', labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
    plt.rc('xtick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc('ytick', labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc('legend', fontsize=SMALL_SIZE)  # legend fontsize
    plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

    """ Plot DSO2
    """


    def get_y(a, x):
        y = a[0] + a[1] * x + a[2] * x * x
        return y


    DSO = 1  # 1 corespond to 2
    temp = obj.df_dsos_lml_q[DSO].index.dayofweek <= 4
    x = obj.df_dsos_lml_q[DSO]['x'][temp]
    y = obj.df_dsos_lml_q[DSO]['y'][temp]
    a = obj.coeficients_weekday[DSO]
    xx = np.linspace(x.min(), x.max(), num=1000)

    fig, ax = plt.subplots()
    ax.plot(x, y, 'o', label='points')
    ax.plot(xx, get_y(a, xx), 'red', label='fited curve')
    ax.grid()
    ax.set(xlabel='quantity (KWh)', ylabel='price ($)', title='weekdays')
    fig.tight_layout()
    fig.legend(bbox_to_anchor=(0., 1.01, 1., .102), loc='lower left',
               ncol=2, mode="expand", borderaxespad=0.)
    fig.show()

    temp = obj.df_dsos_lml_q[DSO].index.dayofweek >= 5
    x = obj.df_dsos_lml_q[DSO]['x'][temp]
    y = obj.df_dsos_lml_q[DSO]['y'][temp]
    a = obj.coeficients_weekday[DSO]
    xx = np.linspace(x.min(), x.max(), num=1000)

    fig, ax = plt.subplots()
    ax.plot(x, y, 'o', label='points')
    ax.plot(xx, get_y(a, xx), 'red', label='fited curve')
    ax.grid()
    ax.set(xlabel='quantity (KWh)', ylabel='price ($)', title='weekends')
    fig.tight_layout()
    fig.legend(bbox_to_anchor=(0., 1.01, 1., .102), loc='lower left',
               ncol=2, mode="expand", borderaxespad=0.)
    fig.show()
