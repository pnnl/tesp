"""
    This file assists visual debugging analyses

    Develop only for debugging purposes 
        
    Intended for simple fast visual plots (works better on IDE so multiple plots can be compared)
    Does not save plots to file
"""

import json
import numpy as np
from copy import deepcopy
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
######################################################start conf plot
import matplotlib.pyplot as plt;
plt.rcParams['figure.figsize'] = (3, 4)
plt.rcParams['figure.dpi'] = 100
SMALL_SIZE = 14
MEDIUM_SIZE = 16
BIGGER_SIZE = 16
plt.rcParams["font.family"] = "Times New Roman"
plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
######################################################end conf plot

def get_metrics_full_multiple_KEY_Mdays(file_name,pre_file,pos_file):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys (i.e., "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    d1 = dict()
    for n in range(days):
        print(pre_file+file_name+pos_file)
        file = open(pre_file+file_name+str(n)+pos_file, 'r')
        text = file.read()
        file.close()

        I_ver = json.loads(text)
        meta_I_ver = I_ver.pop('Metadata')
        start_time = I_ver.pop('StartTime')
        d1.update(deepcopy(I_ver))

    I_ver = d1

    temp = {}
    if 'bid_four_point_rt' in meta_I_ver.keys():
        temp.update({'bid_four_point_rt_1':{'units':'kW','index':0}})
        temp.update({'bid_four_point_rt_2':{'units':'$','index':1}})
        temp.update({'bid_four_point_rt_3':{'units':'kW','index':2}})
        temp.update({'bid_four_point_rt_4':{'units':'$','index':3}})
        temp.update({'bid_four_point_rt_5':{'units':'kW','index':4}})
        temp.update({'bid_four_point_rt_6':{'units':'$','index':5}})
        temp.update({'bid_four_point_rt_7':{'units':'kW','index':6}})
        temp.update({'bid_four_point_rt_8':{'units':'$','index':7}})
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                pass
            else:
                temp.update({i:{'units':meta_I_ver[i]['units'],'index':meta_I_ver[i]['index']+7}})

    meta_I_ver = {}
    meta_I_ver = temp

    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))

    x = len(I_ver[times[0]].keys())
    y = len(times)
    z = len(meta_I_ver)
    data_I_ver = np.empty(shape=(x,y,z), dtype=np.float)

    j=0
    for node in list(I_ver[times[0]].keys()):
        i=0
        for t in times:
            #print (node,t)
            temp = I_ver[t][node]
            if len(I_ver[t][node][0])>1:
                temp = []
                for k in range(len(I_ver[t][node][0])):
                    for l in range(len(I_ver[t][node][0][0])):
                        temp.append(I_ver[t][node][0][k][l])
                for p in range(1,len(I_ver[t][node])):
                    temp.append(I_ver[t][node][p])

            data_I_ver[j,i,:]=temp
            i = i + 1
        j=j + 1

    if (int(times[1])-int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    Ip = pd.Panel(data_I_ver,major_axis=index)

    all_homes_I_ver = list()
    all_homes_I_ver.append(Ip.min(axis=0))
    all_homes_I_ver.append(Ip.mean(axis=0))
    all_homes_I_ver.append(Ip.max(axis=0))
    all_homes_I_ver.append(Ip.sum(axis=0))

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i,:,:], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual  #indovidual homes


def get_metrics_full_multiple_KEY(file_name,pre_file,pos_file,to_hour=True):
    """Reads .json files with multiple Keys

    Args:
        file_name (str): name of json file to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dict): with Key of the variable containing the index and units
        start_time (str): start time of simulation
        all_homes_I_ver (list of DataFrame): min, mean, max, and the sum of the variables of all the Keys (i.e., "agent")
        data_individual (list of DataFrame): variables for individual homes
    """
    print(pre_file+file_name+pos_file)
    file = open(pre_file+file_name+pos_file, 'r')
    text = file.read()
    file.close()

    I_ver = json.loads(text)
    meta_I_ver = I_ver.pop('Metadata')

    temp = {}
    if 'bid_four_point_rt' in meta_I_ver.keys():
        temp.update({'bid_four_point_rt_1':{'units':'kW','index':0}})
        temp.update({'bid_four_point_rt_2':{'units':'$','index':1}})
        temp.update({'bid_four_point_rt_3':{'units':'kW','index':2}})
        temp.update({'bid_four_point_rt_4':{'units':'$','index':3}})
        temp.update({'bid_four_point_rt_5':{'units':'kW','index':4}})
        temp.update({'bid_four_point_rt_6':{'units':'$','index':5}})
        temp.update({'bid_four_point_rt_7':{'units':'kW','index':6}})
        temp.update({'bid_four_point_rt_8':{'units':'$','index':7}})
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                pass
            else:
                temp.update({i:{'units':meta_I_ver[i]['units'],'index':meta_I_ver[i]['index']+7}})

        meta_I_ver = {}
        meta_I_ver = temp


    start_time = I_ver.pop('StartTime')
    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))

    x = len(I_ver[times[0]].keys())
    y = len(times)
    z = len(meta_I_ver)
    data_I_ver = np.empty(shape=(x,y,z), dtype=np.float)
    #print (x,y,z)
    j=0
    for node in list(I_ver[times[0]].keys()):
        i=0
        for t in times:
            temp = I_ver[t][node]

            try:
                len(I_ver[t][node][0])
                if len(I_ver[t][node][0])>1:
                    temp = []
                    for k in range(len(I_ver[t][node][0])):
                        for l in range(len(I_ver[t][node][0][0])):
                            temp.append(I_ver[t][node][0][k][l])
                    for p in range(1,len(I_ver[t][node])):
                        temp.append(I_ver[t][node][p])
                data_I_ver[j,i,:]=temp
            except TypeError:
                #print (data_I_ver[j,i,:])
                #print (I_ver[t][node])
                data_I_ver[j,i,:]=I_ver[t][node]
            i = i + 1
        j=j + 1

    if (int(times[1])-int(times[0])) == 60:
        index = pd.date_range(start_time, periods=y, freq='1min')
    else:
        index = pd.date_range(start_time, periods=y, freq='5min')

    Ip = pd.Panel(data_I_ver,major_axis=index)

    all_homes_I_ver = list()
    all_homes_I_ver.append(Ip.min(axis=0))
    all_homes_I_ver.append(Ip.mean(axis=0))
    all_homes_I_ver.append(Ip.max(axis=0))
    all_homes_I_ver.append(Ip.sum(axis=0))

    data_individual = list()
    data_individual = [pd.DataFrame(data_I_ver[i,:,:], index=index) for i in range(x)]

    return meta_I_ver, start_time, all_homes_I_ver, data_individual  #indovidual homes

def make_convergency_test(t,data_s,tf=47):
    """Price convergency development

    Args:
        t (int): selects the number of DA run
        data_s (list of list 48 float): clear DA prices
        tf (int): selects hour to track the development

    Return:
        price (list): price convergency development
    """
    index = [tf-y for y in range(tf+1)]
    price = []
    price = list()
    for i in index:
        try:
#            oi = data_s[t][i]
#            print(oi)
            price.append(data_s[t][i])
        except:
            return price
        t = t + 1
    return deepcopy(price)

def get_first_h(data_s):
    """Gets the first hour of DA prices (DSO and retail)

    Args:
        t (int): selects the number of DA run
        data_s (list of list 48 float): clear DA prices

    Return:
        max_delta (int): worse hour in t
    """
    price = list()
    for i in range(len(data_s)):
        try:
            price.append(data_s[i][0])
        except:
            return price
    return price

def get_data_multiple_days(V_analis,days,pre_file,pos_file):
    """Read a defined number of days

    Args:
        V_analis (str): a portion of the file name
        days (int): number of days to be read
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file

    Return:
        meta_I_ver (dic): Metadata of .json file
        start_time (str): Start time of the simulation
        Order (list of Metadata): list of matadata in proper time order

    """
    d1 = dict()
    for n in range(days):
        file_name = V_analis+str(n)+'_metrics'
        file = open(pre_file+file_name+pos_file, 'r')
        text = file.read()
        file.close()

        I_ver = json.loads(text)
        meta_I_ver = I_ver.pop('Metadata')
        start_time = I_ver.pop('StartTime')

        d1.update(deepcopy(I_ver))

    I_ver = d1

    times = list(I_ver.keys())
    times = list(map(int, times))
    times.sort()
    times = list(map(str, times))

    temp = [[]]*len(I_ver[times[0]].keys())
    j = 0
    for node in list(I_ver[times[0]].keys()):
        for t in times:
            temp[j].append(I_ver[t][node])
        j=j+1

    Order = [[] for i in range(len(meta_I_ver))]
    for i in meta_I_ver:
        index = meta_I_ver[i]['index']
        for t in range(len(temp[0])):
            Order[index].append(temp[0][t][index])


    return meta_I_ver, start_time, Order



if __name__ == "__main__":
    pre_file_out ='TMG_helics_3_agent/'#
    pos_file ='.h5'
    days = 2
    da_convergence_start = 24*0 # DA interaction to start looking for convergence
    N_convergence_hours = 24 # number of hours to visualize convergence (set to zero neglect)

    DSO = False #plot DSO
    Retail = False #plot Retail
    Inverters = False #plot inverters
    Homes = False #read homes for HVAC and water heater
    Water = False #plot water heater
    HVAC = False
    HVAC_agent = True

    pre_file = pre_file_out + 'Microgrid_1/'
#### DSO
    if DSO:
        V_file = 'dso_market_Substation_2_3600_'
        meta_I_ver, start_time, Order = get_data_multiple_days(V_file,days,pre_file,pos_file)
        V_analis = 'trial_cleared_price_da'
        first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
        #### Plot clear DSO
        plt.plot(first_h,marker='x');plt.ylabel('DSO price ($/kWh)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
        #### Plot convergency of DSO market
        for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
            convergency_max = make_convergency_test(data_s=Order[meta_I_ver[V_analis]['index']],t=i)
            plt.plot(convergency_max,marker='x');plt.ylabel('DSO price ($/kWh)');plt.xlabel('from time ahead to present (hours)');plt.title('hour 48 of t: '+str(i));plt.grid(True);plt.show()
#### Retail
    if Retail:
        V_file = 'retail_market_Substation_2_3600'
        meta_I_ver, start_time, Order = get_data_multiple_days(V_file,days,pre_file,pos_file)
        V_analis = 'cleared_price_da'
        first_h = get_first_h(data_s=Order[meta_I_ver[V_analis]['index']])
        #### Plot clear DSO
#        plt.plot(first_h,marker='x');plt.ylabel('retail price ($/kWh)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
        #### Plot convergency of DSO market
        markers = ['.','o','v','^','<','>','1','2','3','4','8','s','p','P','*','h','H','+','x','X','D','d','|','_']
        M_in=0
        for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
            convergency_max = make_convergency_test(data_s=Order[meta_I_ver[V_analis]['index']],t=i)
            plt.plot(convergency_max,marker=markers[M_in],label=str(i)+'-h',linewidth=1,markersize=5);plt.ylabel('retail price ($/kWh)');plt.xlabel('from time ahead to present (hours)')#;plt.title('hour 48 of t: '+str(i));plt.grid(True);plt.show()
            M_in = M_in + 1
        plt.grid(True);plt.legend(bbox_to_anchor=(1.1, 1.00));plt.show()

        first_h_df = pd.DataFrame(first_h)
        first_h_df.index = pd.date_range(start_time,periods=len(first_h), freq='1H')
        first_h_df_rt = first_h_df.resample('5min').ffill()

#        V_file = 'retail_market_Substation_2_300_'
#        meta_I_ver, start_time, Order = get_data_multiple_days(V_file,days,pre_file,pos_file)
#        V_analis = 'cleared_price_rt'
#        first_h_rt = Order[meta_I_ver[V_analis]['index']]
##        plt.plot(first_h_df_rt.values,label='DA');
##        plt.plot(first_h_rt,label='RT');plt.legend();plt.ylabel('price ($/kWh)');plt.xlabel('time (5-min)');plt.grid(True);plt.show()
#
#        first_h_rt = pd.DataFrame(first_h_rt)
#        first_h_rt.index = first_h_df_rt.index[0:len(first_h_rt)]

#######################################################
#######################################################
#######################################################
    pre_file = pre_file_out + 'Substation_2/'
#### Inverters
    if Inverters:
        V_file = 'inverter_Substation_2_metrics'
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY(V_file,pre_file,pos_file)
        V_analis = 'real_power_avg'#variable being analized
        AVG_power = data_s[3][meta_S[V_analis]['index']]
        #### Plot
        plt.plot((AVG_power.resample('60min').mean()/1000).values,marker='x');plt.ylabel('agregated inverter power (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.show()

        fig = plt.figure(); ax1 = fig.add_subplot(111);ax1.plot((AVG_power.resample('60min').mean()/1000).values,marker='x',color='r');ax1.set_xlabel('time (hours)');ax1.set_ylabel('agregated inverter power (kW)',color='tab:red')
        ax2 = ax1.twinx(); ax2.plot(first_h,marker='o',color='b');ax2.set_ylabel('DA retail price ($/kWh)',color='tab:blue');plt.grid(True);plt.show()

#        fig = plt.figure(); ax1 = fig.add_subplot(111);ax1.plot((AVG_power.resample('60min').mean()/1000).values,marker='x',color='r');ax1.set_xlabel('time (hours)');ax1.set_ylabel('agregated inverter power (kW)',color='tab:red')
#        ax2 = ax1.twinx(); ax2.plot((first_h_rt.resample('60min').mean()).values,marker='o',color='b');ax2.set_ylabel('RT retail price ($/kWh)',color='tab:blue');plt.grid(True);plt.show()


        x=list(range(0,108))
        plt.plot(x,(AVG_power/1000).values[x],marker='x');plt.ylabel('agregated inverter power (kW)');plt.xlabel('time (5-min)');plt.grid(True)
        [plt.axvline(x=i*12,color='k') for i in range(0,int(len(x)/12))]
        plt.show()
#### Homes
    if Homes:
        V_file = 'house_Substation_2_metrics'
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY(V_file,pre_file,pos_file)
#### Water
        if Water:
            V_analis = 'waterheater_load_avg'
            AVG_power = data_s[1][meta_S[V_analis]['index']]#plots mean
            to_kW = 1
            plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('agregated mean water heater power (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
            for i in range(len(data_individual)):
                AVG_power = data_individual[i][meta_S[V_analis]['index']]
                plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('water heater power (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.title('home: '+str(i));plt.show()
            V_analis = 'waterheater_load_max'
            AVG_power = data_s[0][meta_S[V_analis]['index']]#plots min
            plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('min min water heater power (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
            AVG_power = data_s[2][meta_S[V_analis]['index']]#plots max
            plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('max max water heater power (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.show()


        if HVAC:
            V_analis = 'hvac_load_avg'
            AVG_power = data_s[1][meta_S[V_analis]['index']]#plots mean
            to_kW = 1
            plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('avg agregated hvac load (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
            for i in [14]:#range(len(data_individual)):
                AVG_power = data_individual[i][meta_S[V_analis]['index']]
                plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('hvac load (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.title('home: '+str(i));plt.show()
            V_analis = 'hvac_load_avg'
            AVG_power = data_s[0][meta_S[V_analis]['index']]#plots min
            plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('min min hvac_load (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
            AVG_power = data_s[2][meta_S[V_analis]['index']]#plots max
            plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x');plt.ylabel('max max hvac_load_avg (kW)');plt.xlabel('time (hours)');plt.grid(True);plt.show()



#### new HVAC
    if HVAC_agent and 0:
        #for iday in range(3):
        pre_file = pre_file_out + 'dso_1/'
        iday = 0
        V_file = 'hvac_agent_Substation_2_300_{:.0f}_metrics'.format(iday)
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY(V_file,pre_file,pos_file)
        #meta_I_ver, start_time, Order = get_data_multiple_days(V_file, days, pre_file, pos_file)
        V_analis = ['room_air_temperature','outdoor_temperature','thermostat_setpoint','cooling_basepoint','cleared_price']
        to_kW = 1
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        for i in range(14,15):#range(len(data_individual)):
            for ivar in range(len(V_analis)-1):
                AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
                ax1.plot((AVG_power/to_kW).values,marker='x',label=V_analis[ivar]);ax1.set_ylabel('(F)');plt.xlabel('time (hours)');plt.grid(True);plt.title('home '+str(i)+' - day {:.0f}'.format(iday));
            ax1.legend()
            AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
            ax2.plot((AVG_power/to_kW).values,'-', color='k',label=V_analis[-1]);ax2.set_ylabel('price ($/kW)');plt.xlabel('time (hours)');plt.grid(True)
            #ax2.legend()
            plt.show()

    if HVAC_agent and 0:
        pre_file = pre_file_out + 'dso_1/'
        V_file = 'hvac_agent_Substation_2_3600_'
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY_Mdays(V_file,pre_file,'_metrics'+pos_file)
        V_analis = ['room_air_temperature','outdoor_temperature','thermostat_setpoint','cooling_basepoint','cleared_price']
        to_kW = 1
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        for i in [14]:#range(len(data_individual)):
            for ivar in range(len(V_analis)-1):
                AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
                ax1.plot((AVG_power/to_kW).values,marker='x',label=V_analis[ivar]);ax1.set_ylabel('(F)');plt.xlabel('time (hours)');plt.grid(True);plt.title('home '+str(i));
            ax1.legend()
            AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
            ax2.plot((AVG_power/to_kW).values,'-', color='k',label=V_analis[-1]);ax2.set_ylabel('price ($/kW)');plt.xlabel('time (hours)');plt.grid(True)
            #ax2.legend()
            plt.show()

    if HVAC_agent and 1:
        pre_file = pre_file_out + 'Microgrid_1/'
        V_file = 'hvac_agent_Microgrid_1_300_'
        meta_S, start_time, data_s, data_individual = get_metrics_full_multiple_KEY_Mdays(V_file,pre_file,'_metrics'+pos_file)
        V_analis = ['DA_quantity']
        to_kW = 1
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        for i in [14]:#range(len(data_individual)):
            for ivar in range(len(V_analis)):
                AVG_power = data_individual[i][meta_S[V_analis[ivar]]['index']]
                ax1.plot((AVG_power.resample('60min').mean()/to_kW).values,marker='x',label=V_analis[ivar]);plt.xlabel('time (hours)');plt.grid(True);plt.title('home '+str(i));#ax1.set_ylabel('(F)');
            ax1.legend()
            '''
            AVG_power = data_individual[i][meta_S[V_analis[-1]]['index']]
            ax2.plot((AVG_power/to_kW).values,'-', color='k',label=V_analis[-1]);ax2.set_ylabel('price ($/kW)');plt.xlabel('time (hours)');plt.grid(True)
            #ax2.legend()
            '''
            plt.show()


#import matplotlib.pyplot as plt
#
#f = plt.figure(1); f.clf()
#ax = f.add_subplot(111)
#ax.plot([1,2,3,4,5])
#ax.plot([5,4,3,2,1])
#ax.plot([2,3,2,3,2])
#
#import itertools
#for l, ms in zip(ax.lines, itertools.cycle('>^+*')):
#    l.set_marker(ms)
#    print(ms)
##    l.set_color('black')
#
#plt.show()
#
#
#markers = [(i,j,0) for i in range(2,10) for j in range(1, 3)]


