# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: Wh_Energy_Purchases.py
import os
import pandas as pd
import numpy as np
import datetime
import json

# ercot_path = 'C:\\Users\\mayh819\\PycharmProjects\\tesp-private\\tesp-private\\ercot\\case8\\dsostub'
# ercot_path = 'C:\\Users\\reev057\\PycharmProjects\\DSO+T\\Data\\GnT\\case1Apr'
data_path = '..\\..\\..\\examples\\analysis\\dsot\\data'

dso_num = 1
h1 = 5
h2 = 16
h3 = 20
place = 'Houston'        #place_names = ['CPS', 'North', 'South', 'West', 'Houston']

def load_hourly_data(dir_path, dso_num, simdata):
    """Utility to open hourly ERCOT csv file. The entire date range for the data (e.g. 1 year) is considered
    Arguments:
        ercot_path: directory path of ercot data
        dso_num: dso number (1-8)
        day_range (range): range of simulation days for data to be returned
    Returns:
        data_df : dataframe of ERCOT data for dso specified
        """
    if simdata:
        os.chdir(dir_path)
        data_df = pd.read_csv('Annual_DA_LMP_Load_data.csv')
        data_df.rename(columns={'Unnamed: 0': 'date_time'}, inplace=True)
        data_df.rename(columns={'time': 'date_time'}, inplace=True)
        data_df.rename(columns={'da_q' + '{}'.format(dso_num): 'Bus' + '{}'.format(dso_num)}, inplace=True)
        col = 'Bus' + '{}'.format(dso_num)
        data_df = data_df[[col, 'date_time']]
        data_df['date_time'] = pd.to_datetime(data_df['date_time'])
        start_time = datetime.datetime(2016, 1, 1)
        stop_time = datetime.datetime(2016, 12, 31)
        data_df = data_df.loc[data_df['date_time'] >= start_time]
        data_df = data_df.loc[data_df['date_time'] <= stop_time]
        print(data_df.head())
    else:
        os.chdir(dir_path)
        data_df = pd.read_csv('2016_ERCOT_Hourly_Load_Data.csv', index_col='Hour_End')
        data_df.reset_index(inplace=True)
        data_df.rename(columns={'Hour_End': 'date_time'}, inplace=True)
        col = 'Bus' + '{}'.format(dso_num)
        data_df = data_df[[col, 'date_time']]
        data_df['date_time'] = pd.to_datetime(data_df['date_time'])
        start_time = datetime.datetime(2016, 1, 1)
        stop_time = datetime.datetime(2016, 12, 31)
        data_df = data_df.loc[data_df['date_time'] >= start_time]
        data_df = data_df.loc[data_df['date_time'] <= stop_time]
        print(data_df.head())

    return data_df

def load_realtime_data(dir_path, dso_num, simdata):
    """Utility to open 5 min ERCOT csv file. The entire date range for the data (e.g. 1 year) is considered
    Arguments:
        dso_num: dso number (1-8)
    Returns:
        data_df : 15 min dataframe of ERCOT data for specified dso
        """
    if simdata:
        os.chdir(dir_path)
        data_df = pd.read_csv('Annual_RT_LMP_Load_data.csv')
        data_df.rename(columns={'Unnamed: 0': 'date_time'}, inplace=True)
        data_df.rename(columns={'time': 'date_time'}, inplace=True)
        data_df.rename(columns={'rt_q' + '{}'.format(dso_num): ' Bus' + '{}'.format(dso_num)}, inplace=True)
        col = ' Bus' + '{}'.format(dso_num)
        data_df = data_df[[col, 'date_time']]
        data_df['date_time'] = pd.to_datetime(data_df['date_time'])
        start_time = datetime.datetime(2016, 1, 1)
        stop_time = datetime.datetime(2016, 12, 31)
        data_df = data_df.loc[data_df['date_time'] >= start_time]
        data_df = data_df.loc[data_df['date_time'] <= stop_time]
        print(data_df.head())
    else:
        # os.chdir(dir_path)
        data_df = pd.read_csv('2016_ERCOT_5min_Load_Data.csv')
        date_rng = pd.date_range(start='1/1/2016 01:00:00', periods=len(data_df), freq='5min')
        data_df['date_time'] = pd.to_datetime(date_rng)
        col = ' Bus' + '{}'.format(dso_num)
        data_df = data_df[[col, 'date_time']]
        data_df = data_df.set_index(['date_time'])
        data_df = data_df.groupby(pd.Grouper(freq='15T')).mean()
        data_df.reset_index(inplace=True)
        print(data_df.head())

    return data_df


def load_price_data(dir_path, market_type, dso_num, simdata):
    if simdata:
        os.chdir(dir_path)
        col = 'Bus' + '{}'.format(dso_num) + ' $_mwh'
        if market_type == 'DA':
            prices_data = pd.read_csv('Annual_DA_LMP_Load_data.csv')
            prices_data.rename(columns={'da_lmp' + '{}'.format(dso_num): col}, inplace=True)
        else:
            prices_data = pd.read_csv('Annual_RT_LMP_Load_data.csv')
            prices_data.rename(columns={' LMP' + '{}'.format(dso_num): col}, inplace=True)
        prices_data.rename(columns={'Unnamed: 0': 'date_time'}, inplace=True)
        prices_data.rename(columns={'time': 'date_time'}, inplace=True)
        prices_data.rename(columns={'da_lmp' + '{}'.format(dso_num): col}, inplace=True)

        prices_data = prices_data[[col, 'date_time']]
        prices_data['date_time'] = pd.to_datetime(prices_data['date_time'])
        start_time = datetime.datetime(2016, 1, 1)
        stop_time = datetime.datetime(2016, 12, 31)
        prices_data = prices_data.loc[prices_data['date_time'] >= start_time]
        prices_data = prices_data.loc[prices_data['date_time'] <= stop_time]
    else:
        if market_type == 'DA':
            prices_data = pd.read_excel('DAM_2016.xlsx', sheet_name=place)
            date_rng = pd.date_range(start='1/1/2016 01:00:00', end='1/1/2017', freq='H')
        else:
            prices_data = pd.read_excel('RTM_2016.xlsx', sheet_name=place)
            #prices_data = prices_data.groupby(pd.Grouper(freq='H')).mean()
            date_rng = pd.date_range(start='1/1/2016 01:00:00', periods=len(prices_data), freq='15T')
        prices_data = prices_data.rename(columns={'Settlement Point Price': place + ' $_mwh'})
        prices_data['date_time'] = pd.to_datetime(date_rng)
        #prices_data.set_index('date_time', inplace=True)

    return prices_data

def Wh_Energy_Purchases(data_path, dso_num, simdata=False, h1=5, h2=16, h3=20, place='Houston'):
    """
    Computes the total costs, total energy purchases and average price annually for bilateral, day-ahead and real-time
    markets from hourly and 5 min ERCOT energy and price data.
    :param ercot_path (str): path of the ERCOT energ and price data
    :param dso_num (int): dso number (1-8)
    :param simadata (bool): If True will seek simulation data.  If false will use 2016 ERCOT data.
    :param h1,h2,h3 (int): hours specified to define day, evening and night periods, respectively (e.g. weekday hours h1 to h2,
     evening hours from h2+1 to h3, and night hours are from h3+1 to h1 the next day)
    :param place (str): location of DSO
    :return MarketPurchases (dict): real-time, day-ahead, and bilateral market purchases (annual cost, energy and average price)
    """

    '''
    Loads hourly ERCOT energy and price data. Computes minimum wholesale price and quantity for day, evening, and weekend to represent the fixed prices and energy
    quantities for the bilateral market. Total annual average price, total cost and total energy purchases from the
    bilateral market are then computed.
    '''
    if simdata:
        price_name = 'Bus{} $_mwh'.format(dso_num)
    else:
        price_name = '{} $_mwh'.format(place)

    bilateral_MW_data = load_hourly_data(data_path, dso_num, simdata)
    # bilateral_MW_data['date_time'] = pd.to_datetime(bilateral_MW_data['date_time'])
    bilateral_MW_data['hour'] = bilateral_MW_data['date_time'].dt.hour
    bilateral_MW_data['month'] = bilateral_MW_data['date_time'].dt.month
    bilateral_MW_data['weekday'] = bilateral_MW_data['date_time'].dt.weekday

    #groups load data by day, evening and weekend hours
    conditions_Q =[(bilateral_MW_data['hour'] >= h1) & (bilateral_MW_data['hour'] < h2) & (bilateral_MW_data['weekday'] < 5),
                 ((bilateral_MW_data['hour'] >= h2) & (bilateral_MW_data['hour'] < h3) & (bilateral_MW_data['weekday'] < 5)) | ((bilateral_MW_data['hour'] >= h1) & (bilateral_MW_data['hour'] < h3) & (bilateral_MW_data['weekday'] >= 5)),
                 (bilateral_MW_data['hour'] < h1) | (bilateral_MW_data['hour'] >= h3)]
    #computes bilateral quantity for day, evening as the minimum load in each time period
    choices_Q = [bilateral_MW_data[(bilateral_MW_data['hour'] >= h1) & (bilateral_MW_data['hour'] < h2) & (bilateral_MW_data['weekday'] < 5)]['Bus{}'.format(dso_num)].min(),
               bilateral_MW_data[((bilateral_MW_data['hour'] >= h2) & (bilateral_MW_data['hour'] < h3) & (bilateral_MW_data['weekday'] < 5)) | ((bilateral_MW_data['hour'] >= h1) & (bilateral_MW_data['hour'] < h3) & (bilateral_MW_data['weekday'] >= 5))]['Bus{}'.format(dso_num)].min(),
               bilateral_MW_data[(bilateral_MW_data['hour'] < h1) | (bilateral_MW_data['hour'] >= h3)]['Bus{}'.format(dso_num)].min()]

    #determines the bilateral quantity for each hourly interval
    bilateral_MW_data = bilateral_MW_data.set_index(['date_time'])
    bilateral_MW_data['Fixed Quantity (MW)'] = np.select(conditions_Q, choices_Q, default='0')

    bilateral_price_data = load_price_data(data_path, 'DA', dso_num, simdata)
    bilateral_price_data['hour'] = bilateral_price_data['date_time'].dt.hour
    bilateral_price_data['weekday'] = bilateral_price_data['date_time'].dt.weekday

    # groups price data by day, evening and weekend hours
    conditions_P = [
        (bilateral_price_data['hour'] >= h1) & (bilateral_price_data['hour'] < h2) & (bilateral_price_data['weekday'] < 5),
        ((bilateral_price_data['hour'] >= h2) & (bilateral_price_data['hour'] < h3) & (bilateral_price_data['weekday'] < 5)) | (
        (bilateral_price_data['hour'] >= h1) & (bilateral_price_data['hour'] < h3) & (bilateral_price_data['weekday'] >= 5)),
        (bilateral_price_data['hour'] < h1) | (bilateral_price_data['hour'] >= h3)]

    #computes bilateral price for day, evening, and weekend as the average price in each time period
    choices_P = [bilateral_price_data[(bilateral_price_data['hour'] >= h1) & (bilateral_price_data['hour'] < h2) & (bilateral_price_data['weekday'] < 5)][price_name].mean(),
                bilateral_price_data[((bilateral_price_data['hour'] >= h2) & (bilateral_price_data['hour'] < h3) & (
                bilateral_price_data['weekday'] < 5)) | ((bilateral_price_data['hour'] >= h1) & (bilateral_price_data['hour'] < h3) & (
                bilateral_price_data['weekday'] >= 5))][price_name].mean(),
                bilateral_price_data[(bilateral_price_data['hour'] < h1) | (bilateral_price_data['hour'] >= h3)][price_name].mean()]

    #determines the bilateral price for each hourly interval
    bilateral_price_data = bilateral_price_data.set_index(['date_time'])
    bilateral_price_data['Fixed Price ($/MWh)'] = np.select(conditions_P, choices_P, default='0')

    # Monthly computations
    WhBLEnergyMonthly = (pd.to_numeric(bilateral_MW_data['Fixed Quantity (MW)']).resample('M')).sum()
    WhBLPurchasesMonthly = ((pd.to_numeric(bilateral_price_data['Fixed Price ($/MWh)'])*pd.to_numeric(bilateral_MW_data['Fixed Quantity (MW)']))).resample('M').sum()
    WhBLPriceMonthly = WhBLPurchasesMonthly/WhBLEnergyMonthly
    # Annual compuated from monthly computations
    WhBLEnergy = WhBLEnergyMonthly.sum()
    WhBLPurchases = WhBLPurchasesMonthly.sum()
    WhBLPrice = WhBLPriceMonthly.mean()

    '''
    Uses hourly ERCOT energy and price data to represent DA wholesale data. Annual average price, total costs and total 
    energy purchases are computed for DA wholesale market.   
    '''
    DA_MW_data = bilateral_MW_data #same data used for bilateral computations
    #DA_MW_data.rename(columns={'Bus{}'.format(dso_num):'Day-ahead (MWh)'}, inplace=True)
    #subtracts hourly bilateral quantities from total hourly load to get hourly Day-ahead quantities
    DA_MW_data['Day-ahead (MWh)'] = pd.to_numeric(DA_MW_data['Bus{}'.format(dso_num)]) - pd.to_numeric(bilateral_MW_data['Fixed Quantity (MW)'])
    DA_price_data = load_price_data(data_path, 'DA', dso_num, simdata)
    DA_price_data = DA_price_data.set_index(['date_time'])

    #Monthly computations
    WhDAEnergyMonthly = (pd.to_numeric(DA_MW_data['Day-ahead (MWh)']).resample('M')).sum()
    WhDAPurchasesMonthly = ((pd.to_numeric(DA_price_data[price_name])*pd.to_numeric(DA_MW_data["Day-ahead (MWh)"]))).resample('M').sum()
    WhDAPriceMonthly = WhDAPurchasesMonthly/WhDAEnergyMonthly
    #Annual compuated from monthly computations
    WhDAEnergy = WhDAEnergyMonthly.sum()
    WhDAPurchases = WhDAPurchasesMonthly.sum()
    WhDAPrice = WhDAPriceMonthly.mean()

    '''
    Gets 15 min ERCOT energy and price data to represent real-time spot market data. Annual average price, total costs 
    and total energy purchases are computed for DA wholesale market.   
    '''
    RT_MW_data = load_realtime_data(data_path, dso_num, simdata)
    RT_MW_data['month'] = RT_MW_data['date_time'].dt.month

    RT_MW_data = RT_MW_data.set_index(['date_time'])

    #Converts from 15 min MW data to hourly MWh data
    # TODO: Update to interpolate DA data to 5 or 15 minute data minute for simulation case
    RT_hourly_MWh_data = RT_MW_data[' Bus{}'.format(dso_num)].resample('H').mean() #MWh

    '''
      Annual Peak capacity is computed from hourly real-time load data which is equivalent to real bilateral + Day ahead +_real-time energy purchases.
      '''
    # TODO: This hourly mean is likely reducing the peak load from the 5 minute value.
    WholesalePeakLoadRate = max(RT_MW_data[' Bus{}'.format(dso_num)])


    # subtracts hourly load from 15 min real-time load data to compute real-time quantities purchased. It is assumed that hourly load is equivalent to the
    #bilateral + day ahead quantities.
    RT_hourly_MWh_data = RT_hourly_MWh_data - bilateral_MW_data['Bus{}'.format(dso_num)]
    RT_price_data = load_price_data(data_path, 'RT', dso_num, simdata)
    RT_price_data = RT_price_data.set_index(['date_time'])
    RT_data = RT_MW_data.join(RT_price_data)

    #Monthly computations
    WhRTEnergyMonthly = (pd.to_numeric(RT_hourly_MWh_data).resample('M')).sum()

    WhRTPurchasesMonthly = ((pd.to_numeric(RT_price_data[price_name]).resample('H').mean()*RT_hourly_MWh_data)).resample('M').sum()
    WhRTPriceMonthly = WhRTPurchasesMonthly/WhRTEnergyMonthly
    #Annual computed from monthly computations
    WhRTEnergy = WhRTEnergyMonthly.sum()
    WhRTPurchases = WhRTPurchasesMonthly.sum()
    WhRTPrice = WhRTPriceMonthly.mean()

    '''
    Creates a dataframe for all monthly energy purchase data and outputs to a csv file
    '''
    Monthly_Purchases = pd.concat([WhBLEnergyMonthly,WhDAEnergyMonthly,WhRTEnergyMonthly,
                                   WhBLPurchasesMonthly,WhDAPurchasesMonthly,WhRTPurchasesMonthly,
                                   WhBLPriceMonthly,WhDAPriceMonthly,WhRTPriceMonthly], axis=1,
                                  )

    Monthly_Purchases.rename(columns={'Fixed Quantity (MW)':'Bilateral (MWh)', ' Bus1': 'Real-time (MWh)',
                                         0:'Bilateral Purchases ($)', 1:'Day-ahead ($)', 2:'Real-time ($)',
                                         3:'Bilateral Avg Price ($/MWh)', 4:'Day-ahead Avg Price ($/MWh)', 5:'Real-time Avg Price ($/MWh)'}, inplace=True)

    # TO DO: Change the following path for the monthly purchases csv to the desired location
    # Monthly_Purchases.to_csv(r'C:\\Users\\mayh819\\PycharmProjects\\tesp-private\\tesp-private\\{}_DSO_{}_Monthly_Purchases.csv'.format(place,dso_num))
    MarketPurchases = {'WhEnergyPurchases': {
        'WhDAPurchases': {
            'WhDACosts': WhDAPurchases/1000,  # Day-ahead energy cost in $k
            'WhDAEnergy': WhDAEnergy,  # Day-ahead energy purchased in MWh
            'WhDAPrice': WhDAPurchases/WhDAEnergy  # Day-ahead average price in $/MWh
        },
        'WhRTPurchases': {
            'WhRTCosts': WhRTPurchases/1000,  # Real-time energy cost in $k
            'WhRTEnergy': WhRTEnergy,  # Real-time energy purchased in MWh
            'WhRTPrice': WhRTPurchases/WhRTEnergy  # Real-time average price in $/MWh
        },
        'WhBLPurchases': {
            'WhBLCosts': WhBLPurchases/1000,  # Bilateral energy cost in $k
            'WhBLEnergy': WhBLEnergy,  # Bilateral energy purchased in MWh
            'WhBLPrice': WhBLPurchases/WhBLEnergy  # Bilateral average price in $/MWh
        },
        'WholesalePeakLoadRate': WholesalePeakLoadRate  # peak capacity in MW
        },
        'OtherWholesale': {
            'WhLosses': 0  #  DSO specific ISO losses are zero for now (not calculated by DC power flow equation).
        }}

    return MarketPurchases


if __name__ == '__main__':
    simdata = False
    Market_Purchases = Wh_Energy_Purchases(data_path, dso_num, simdata)
    print(Market_Purchases)

    case_path = 'C:\\Users\\reev057\PycharmProjects\DSO+T\Data\May\Base_858c4e40'
    os.chdir(case_path)
    with open('DSO' + str(dso_num) + '_Wholesale_Purchases.json', 'w') as f:
        json.dump(Market_Purchases, f, indent=2)
