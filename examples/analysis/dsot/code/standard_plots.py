"""This file assists visual debugging analyses and standard plots

    Develop only for json output 
        
    The file will first reads all the requiers input files. The plots are made 
    by functions that receave the objects with the input data.
"""
import itertools
import json
import numpy as np
from copy import deepcopy
import pandas as pd
import warnings
warnings.filterwarnings("ignore")
######################################################start conf plot
import matplotlib.pyplot as plt

plt.rcParams['figure.figsize'] = (7, 8)
plt.rcParams['figure.dpi'] = 100
SMALL_SIZE = 14
MEDIUM_SIZE = 16
BIGGER_SIZE = 16
plt.rcParams["font.family"] = "Times New Roman"
plt.rc('font'  , size=SMALL_SIZE)        # controls default text sizes
plt.rc('axes'  , titlesize=SMALL_SIZE)   # fontsize of the axes title
plt.rc('axes'  , labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
plt.rc('xtick' , labelsize=SMALL_SIZE)   # fontsize of the tick labels
plt.rc('ytick' , labelsize=SMALL_SIZE)   # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
######################################################end conf plot
class MarkerCollorsJSONpython:
    """Object contains the markers, colors, and lines 
    """
    def __init__(self):
        """Create the variables
        """
        self.lines             = ['-','--','-.',':']
        self.Marker            = ['.','o','v','^','<','>','1','2','3','4','8','s','p','P','*','h','H','+','x','X','D','d','|','_']
        self.Color_convergency = ['IndianRed','DarkSalmon','Red','MediumVioletRed','Coral','DarkOrange','Gold','Moccasin','GreenYellow','Lime','LimeGreen','MediumSeaGreen','Green','YellowGreen','Olive','LightSeaGreen','BurlyWood','Tan','RosyBrown','DarkGoldenrod','Peru','Chocolate','SlateGray','Black']
        self.Color_market      = ['LightSkyBlue','DeepSkyBlue','DodgerBlue','MediumSlateBlue','MediumBlue','DarkBlue']
        self.Color_DA          = ['BurlyWood','RosyBrown','SandyBrown','DarkGoldenrod','Peru','Chocolate','SaddleBrown','Sienna','Brown','Maroon','Silver','Gray','SlateGray','Black'] 
        self.Color_RT          = ['GreenYellow','Lime','LimeGreen','MediumSpringGreen','MediumSeaGreen','SeaGreen','Green','DarkGreen','YellowGreen','Olive','LightSeaGreen','Teal','Aqua','Turquoise','CadetBlue','SkyBlue','DeepSkyBlue','DodgerBlue']
        self.Color_GLD         = ['IndianRed','Salmon','DarkSalmon','LightSalmon','Crimson','Red','DarkRed','Pink','MediumVioletRed','Coral','OrangeRed','DarkOrange','Gold','Moccasin','PeachPuff','khaki','Violet','Indigo']
#        gld = ['IndianRed','DarkSalmon','Red','MediumVioletRed','Coral','DarkOrange','Gold','Moccasin']
#        rt  = ['GreenYellow','Lime','LimeGreen','MediumSeaGreen','Green','YellowGreen','Olive','LightSeaGreen']
#        da  = ['BurlyWood','Tan','RosyBrown','DarkGoldenrod','Peru','Chocolate','SlateGray','Black']

class marketJSONpython:
    """This object will read and organize the output 300 and 3600 json market python files
    
    Args:
        days (int) (2 X 1): start day end day
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file
    """
    def __init__(self,  days, pre_file, pos_file):
        """Initializes the class
        """
        self.startDAY = int(days[0])
        self.endDAY = int(days[1])
        self.pre_file = pre_file
        self.pos_file = pos_file
        
        self.fileNAMES_market  = list(['dso_market_TE_Base_s1_3600_',
                                       'retail_market_TE_Base_s1_3600_',
                                       'dso_market_TE_Base_s1_300_',
                                       'retail_market_TE_Base_s1_300_'])
        self.DSO3600 = self.get_market_data(0)
        self.RET3600 = self.get_market_data(1)
        self.DSO300  = self.get_market_data(2)
        self.RET300  = self.get_market_data(3)
                
    def get_market_data(self,index):
        """Read a defined number of days
    
        Args:
            index (int): position in the list of the name 
    
        Return:
            list
                meta_I_ver (dic): Metadata of .json file
                start_time (str): Start time of the simulation
                Order (list of Metadata): list of matadata in proper time order
        """
        d1 = dict()
        for n in range(self.startDAY,self.endDAY):
            file_name = self.fileNAMES_market[index]+str(n)+'_metrics'
            file = open(self.pre_file+file_name+self.pos_file, 'r')
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
        return list([meta_I_ver, start_time, Order])

class DERsJSON:
    """This object will read and organize the output 300 and 3600 json DER python files
    
    Args:
        days (int) (2 X 1): start day end day
        pre_file (str): pre-portion of the path to file
        pos_file (str): extension of the file
        GLD (boolean): if from GLD
    """    
    def __init__(self,  days, pre_file, pos_file, GLD):
        """Initializes the class
        """
        self.startDAY = int(days[0])
        self.endDAY = int(days[1])
        self.pre_file = pre_file
        self.pos_file = pos_file
        
        self.GLD = GLD
        if GLD:
            self.DER_D = self.get_DER_data()
        else:
            self.DER_5m = self.get_DER_data(NaMe='_TE_Base_s1_300_')
            self.DER_1h = self.get_DER_data(NaMe='_TE_Base_s1_3600_')
        
    def get_DER_data(self,NaMe=''):
        """Read a defined number of days
    
        Return:
            list
                meta_I_ver (dic): Metadata of .json file
                start_time (str): Start time of the simulation
                agregated_DERs (dataframe): agregated metadata
                list
                    DERs (dataframe): metadata by DER
                home_keys (list): home key or DER key
        """
        d1 = dict()
        
        if self.GLD:
            file = open(self.pre_file+self.pos_file, 'r')
            text = file.read()
            file.close()
    
            I_ver = json.loads(text)
            meta_I_ver = I_ver.pop('Metadata')
            start_time = I_ver.pop('StartTime')
    
            d1.update(deepcopy(I_ver))
        else:
            for n in range(self.startDAY,self.endDAY):
                file_name = str(n)+'_metrics'
                file = open(self.pre_file+NaMe+file_name+self.pos_file, 'r')
                text = file.read()
                file.close()
        
                I_ver = json.loads(text)
                meta_I_ver = I_ver.pop('Metadata')
                start_time = I_ver.pop('StartTime')
        
                d1.update(deepcopy(I_ver))
                
        I_ver = d1
        
        temp = {}
        index = 0
        for i in meta_I_ver.keys():
            if 'bid_four_point_rt' in i:
                for i in range(4):
                    temp.update({('bid_4P_rt_Q_'+str(i)):{'units':'kW','index':index}})
                    index = index + 1
                    temp.update({('bid_4P_rt_P_'+str(i)):{'units':'$','index':index}})
                    index = index + 1
            elif 'bid_four_point_da' in i:
                for h in range(48):
                    for i in range(4):
                        temp.update({('bid_4P_da_H_'+str(h)+'_Q_'+str(i)):{'units':'kW','index':index}})
                        index = index + 1
                        temp.update({('bid_4P_da_H_'+str(h)+'_P_'+str(i)):{'units':'$','index':index}})
                        index = index + 1
            else:
                temp.update({i:{'units':meta_I_ver[i]['units'],'index':index}})
                index = index + 1
        if self.GLD:
            pass
        else:
            meta_I_ver = {}
            meta_I_ver = temp
        
        times = list(I_ver.keys())
        times = list(map(int, times))
        times.sort()
        times = list(map(str, times))
        
        home_keys = list(I_ver[times[0]].keys())
        
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
                try:
                    len(I_ver[t][node][0])
                    if len(I_ver[t][node][0])>1:
                        temp = []
                        for k in range(len(I_ver[t][node][0])):
                            for l in range(len(I_ver[t][node][0][0])):
                                temp.append(I_ver[t][node][0][k][l])
                        for p in range(1,len(I_ver[t][node])):
                            temp.append(I_ver[t][node][p])
                    try:
                        temp = list(itertools.chain.from_iterable(temp))
                    except:
                        pass
                    data_I_ver[j,i,:]=temp
                except:
                    data_I_ver[j,i,:]=I_ver[t][node]
                i = i + 1
            j=j + 1
            
        hour = pd.Timedelta('1H')#agents do not participate in the 1 hour
        StArT_TiMe = pd.to_datetime(start_time)#start
        if self.GLD:
            pass
        else:
            StArT_TiMe = StArT_TiMe + hour
        
        if (int(times[1])-int(times[0])) == 60:
            index = pd.date_range(start_time, periods=y, freq='1min')
        elif (int(times[1])-int(times[0])) == 60*60:
            index = pd.date_range(start_time, periods=y, freq='60min')
        else:
            index = pd.date_range(start_time, periods=y, freq='5min')
            
        Ip = pd.Panel(data_I_ver,major_axis=index)
        
        all_homes_I_ver = list()
        all_homes_I_ver.append(Ip.min(axis=0))#0
        all_homes_I_ver.append(Ip.mean(axis=0))#1
        all_homes_I_ver.append(Ip.max(axis=0))#2
        all_homes_I_ver.append(Ip.sum(axis=0))#3
        
        data_individual = list()
        data_individual = [pd.DataFrame(data_I_ver[i,:,:], index=index) for i in range(x)]
        
        if self.GLD:
            day = pd.Timedelta('1D')
            startD = day*self.startDAY+StArT_TiMe + hour #to mach with python files
            endD = day*self.endDAY+StArT_TiMe
            for i in range(len(all_homes_I_ver)):
                all_homes_I_ver[i] = all_homes_I_ver[i].loc[startD:endD]
            for n in range(len(data_individual)):
                data_individual[n] = data_individual[n].loc[startD:endD]
        
        return list([meta_I_ver, start_time, all_homes_I_ver, data_individual, home_keys])

########################################################## Function
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
            price.append(data_s[t][i])
        except:
            return price
        t = t + 1
    return deepcopy(price)
########################################################## Plots
def Markets(obj_Market,obj_Color):
    """Plot DSO and Retail markets
    
    Args:
        obj_Market (obj): contain market info
        obj_Color (obj): contain colors
    """
    markers=obj_Color.Marker
    #### Plot DSO and RET for DA and RT
    plt.figure('Plot DSO and RET for DA and RT')
    
    V_analis = 'trial_cleared_price_da'
    first_h = get_first_h(data_s=obj_Market.DSO3600[2][obj_Market.DSO3600[0][V_analis]['index']])
    temp=[first_h[i//12] for i in range(len(first_h)*12)]
    first_h = temp
    M_in=0
    M_cc=0
    plt.plot(first_h,color = obj_Color.Color_DA[M_cc],marker=markers[M_in],label='DSO-DA')
    M_in = M_in + 1
    M_cc = M_cc + 1
    V_analis = 'cleared_price_da'
    first_h = get_first_h(data_s=obj_Market.RET3600[2][obj_Market.RET3600[0][V_analis]['index']])
    temp=[first_h[i//12] for i in range(len(first_h)*12)]
    first_h = temp
    plt.plot(first_h,color = obj_Color.Color_DA[M_cc],marker=markers[M_in],label='RET-DA')
    M_in = M_in + 1
    M_cc = 0
    V_analis = 'cleared_price_rt'
    first_h = obj_Market.DSO300[2][obj_Market.DSO300[0][V_analis]['index']]
    plt.plot(first_h,color = obj_Color.Color_RT[M_cc],marker=markers[M_in],label='DSO-RT')
    M_in = M_in + 1
    M_cc = M_cc + 1
    V_analis = 'cleared_price_rt'
    first_h = obj_Market.RET300[2][obj_Market.RET300[0][V_analis]['index']]
    plt.plot(first_h,color = obj_Color.Color_RT[M_cc],marker=markers[M_in],label='RET-RT')
    plt.ylabel('price ($/kWh)');plt.xlabel('time (5-min)');plt.legend(bbox_to_anchor=(1.1, 1.00));plt.grid(True);plt.show()
    
    
def DSOplots(obj_Market,obj_Color):
    """Plot DSO market
    
    Args:
        obj_Market (obj): contain market info
        obj_Color (obj): contain colors
    """
    markers=obj_Color.Marker
    
    V_analis = 'trial_cleared_price_da'
#    first_h = get_first_h(data_s=obj_Market.DSO3600[2][obj_Market.DSO3600[0][V_analis]['index']])
#    #### Plot clear DSO
#    plt.plot(first_h,color = obj_Color.Color_market[0],marker='x');plt.ylabel('DSO price ($/kWh)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
    #### Plot convergency of DSO market
    plt.figure('Plot convergency of DSO market')
    
    M_in=0
    for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        convergency_max = make_convergency_test(data_s=obj_Market.DSO3600[2][obj_Market.DSO3600[0][V_analis]['index']],t=i)
        plt.plot(convergency_max,marker=markers[M_in],color = obj_Color.Color_convergency[M_in],label=str(i)+'-h',linewidth=1,markersize=5);plt.ylabel('DSO price ($/kWh)');plt.xlabel('from time ahead to present (hours)')
        M_in = M_in + 1
    plt.grid(True);plt.legend(bbox_to_anchor=(1.1, 1.00));plt.show()

def RETplots(obj_Market,obj_Color):
    """Plot Retail market
    
    Args:
        obj_Market (obj): contain market info
        obj_Color (obj): contain colors
    """
    markers=obj_Color.Marker
    
    V_analis = 'cleared_price_da'
#    first_h = get_first_h(data_s=obj_Market.RET3600[2][obj_Market.RET3600[0][V_analis]['index']])
#    #### Plot clear DSO
#    plt.plot(first_h,color = obj_Color.Color_market[0],marker='x');plt.ylabel('retail price ($/kWh)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
    #### Plot convergency of RET market
    plt.figure('Plot convergency of RET market')
            
    M_in=0
    for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        convergency_max = make_convergency_test(data_s=obj_Market.RET3600[2][obj_Market.RET3600[0][V_analis]['index']],t=i)
        plt.plot(convergency_max,marker=markers[M_in],color = obj_Color.Color_convergency[M_in],label=str(i)+'-h',linewidth=1,markersize=5);plt.ylabel('retail price ($/kWh)');plt.xlabel('from time ahead to present (hours)')
        M_in = M_in + 1
    plt.grid(True);plt.legend(bbox_to_anchor=(1.1, 1.00));plt.show()

def Inverter(obj_Market,obj_DER_PYT_battery,obj_DER_GLD_inverter,obj_Color):
    """Inverter plots
    
    Args:
        obj_Market (obj): contain market info
        obj_DER_PYT_battery (obj): contains python battery agent info
        obj_DER_GLD_inverter (obj): GLD inverter
        obj_Color (obj): contain colors
    """
    markers=obj_Color.Marker
    #### Plot individual DA, RT, and GLD quantity Inv
    plt.figure('Plot individual DA, RT, and GLD quantity Inv')
    
    M_in=0
    home = 0 
    home_name = obj_DER_PYT_battery.DER_1h[4][home]
    home = obj_DER_PYT_battery.DER_1h[4].index(home_name)
    
    V_analis = 'bid_4P_da_H_0_Q_1'
    df = obj_DER_PYT_battery.DER_1h[3][home]
    meta = obj_DER_PYT_battery.DER_1h[0]
    indexM = meta[V_analis]['index']
    sumAgreDA = df.loc[:,indexM]
    
    home = obj_DER_PYT_battery.DER_5m[4].index(home_name)
    V_analis = 'bid_4P_rt_Q_1'
    df = obj_DER_PYT_battery.DER_5m[3][home]
    meta = obj_DER_PYT_battery.DER_5m[0]
    indexM = meta[V_analis]['index']
    sumAgreRT = df.loc[:,indexM]
    
    home = obj_DER_GLD_inverter.DER_D[4].index(home_name)
    V_analis = 'real_power_avg'
    df = obj_DER_GLD_inverter.DER_D[3][home]
    meta = obj_DER_GLD_inverter.DER_D[0]
    indexM = meta[V_analis]['index']
    sumAgreGLD = df.loc[:,indexM]
    
    plt.plot(sumAgreDA.resample('5min').fillna('ffill').values,color = obj_Color.Color_DA[M_in],marker=markers[M_in],label='DA')
    M_in = M_in + 1
    plt.plot(sumAgreRT.resample('5min').mean().values,color = obj_Color.Color_RT[M_in],marker=markers[M_in],label='RT')
    M_in = M_in + 1
    to_kW = -1000
    plt.plot((sumAgreGLD.resample('5min').mean()/to_kW).values,color = obj_Color.Color_GLD[M_in],marker=markers[M_in],label='GLD')
    plt.title('Inv individual '+home_name)
    plt.ylabel('quantity (kW)');plt.xlabel('time (5-min)');plt.legend(bbox_to_anchor=(1.1, 1.00));plt.grid(True);plt.show()   

    
    #### Plot agregated sum DA, RT, and GLD quantity Inv
    plt.figure('Plot agregated sum DA, RT, and GLD quantity Inv')
    
    M_in=0
    
    V_analis = 'bid_4P_da_H_0_Q_1'
    df = obj_DER_PYT_battery.DER_1h[2][3]
    meta = obj_DER_PYT_battery.DER_1h[0]
    indexM = meta[V_analis]['index']
    sumAgreDA = df.loc[:,indexM]
    
    V_analis = 'bid_4P_rt_Q_1'
    df = obj_DER_PYT_battery.DER_5m[2][3]
    meta = obj_DER_PYT_battery.DER_5m[0]
    indexM = meta[V_analis]['index']
    sumAgreRT = df.loc[:,indexM]
    
    V_analis = 'real_power_avg'
    df = obj_DER_GLD_inverter.DER_D[2][3]
    meta = obj_DER_GLD_inverter.DER_D[0]
    indexM = meta[V_analis]['index']
    sumAgreGLD = df.loc[:,indexM]
    
    plt.plot(sumAgreDA.resample('5min').mean().values,color = obj_Color.Color_DA[M_in],marker=markers[M_in],label='DA')
    M_in = M_in + 1
    plt.plot(sumAgreRT.resample('5min').mean().values,color = obj_Color.Color_RT[M_in],marker=markers[M_in],label='RT')
    M_in = M_in + 1
    to_kW = -1000
    plt.plot((sumAgreGLD.resample('5min').mean()/to_kW).values,color = obj_Color.Color_GLD[M_in],marker=markers[M_in],label='GLD')
    plt.ylabel('agregated sum quantity (kW)');plt.xlabel('time (5-min)');plt.legend(bbox_to_anchor=(1.1, 1.00));plt.grid(True);plt.show()   
    #### Plot inverter sum power and RET price Inv  
    #plt.figure('Plot inverter sum power and RET price Inv')
    
    V_analis = 'real_power_avg'
    data_s = obj_DER_GLD_inverter.DER_D[2][3]
    meta_S = obj_DER_GLD_inverter.DER_D[0]
    AVG_power = data_s[meta_S[V_analis]['index']]
    
    V_analis = 'cleared_price_da'
    first_h = get_first_h(data_s=obj_Market.RET3600[2][obj_Market.RET3600[0][V_analis]['index']])
#    Output power and market
    fig = plt.figure('Plot inverter sum power and RET price Inv'); ax1 = fig.add_subplot(111);ax1.plot((AVG_power.resample('60min').mean()/1000).values,marker='x',color=obj_Color.Color_GLD[0]);ax1.set_xlabel('time (hours)');ax1.set_ylabel('agregated sum inverter power (kW)',color=obj_Color.Color_GLD[0])
    ax2 = ax1.twinx(); ax2.plot(first_h,marker='o',color=obj_Color.Color_market[0]);ax2.set_ylabel('DA retail price ($/kWh)',color=obj_Color.Color_market[0]);plt.grid(True);plt.show()
    #### Plot Convergency sum optimal agregated quantity bid Inv
    plt.figure('Plot Convergency sum optimal agregated quantity bid Inv')
    
    V_analis = 'bid_4P_da_H_0_Q_1'
    df = obj_DER_PYT_battery.DER_1h[2][3]
    meta = obj_DER_PYT_battery.DER_1h[0]
    indexM = meta[V_analis]['index']
    x = list()
    for i in range(48):
        x.append(indexM+i*8)
    df = df.loc[:,x]
    MEETAA = np.array(list(meta.keys()))#[x]
    MEETAA = MEETAA[x]
    
    row_list = list()
    for index, rows in df.iterrows():
        my_list = list(rows)
        row_list.append(my_list)
    
    M_in=0
    for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        convergency_max = make_convergency_test(data_s=row_list,t=i)
        plt.plot(convergency_max,marker=markers[M_in],color = obj_Color.Color_convergency[M_in],label=str(i)+'-h');plt.ylabel('agregated sum optimal quantity bid (kWh)');plt.xlabel('from time ahead to present (hours)')
        M_in = M_in + 1
    plt.grid(True);plt.legend(bbox_to_anchor=(1.1, 1.00));plt.title('Inverter');plt.show()


def Water_Heater(obj_Market,obj_DER_PYT_water,obj_DER_GLD_house,obj_Color):
    """Water heater plots
    
    Args:
        obj_Market (obj): contain market info
        obj_DER_PYT_water (obj): contains python battery agent info
        obj_DER_GLD_house (obj): GLD house info
        obj_Color (obj): contain colors
    """
    markers=obj_Color.Marker
    
    #### Plot upper set point WH
    plt.figure('Plot upper set point WH')
    
    M_in=0
    
    #obj_DER_PYT_water.DER_5m[2][3] = data_s for the sum
    #obj_DER_PYT_water.DER_5m[0] = meta_S 
    
    V_analis = 'upper_tank_setpoint'
    AVG_power = obj_DER_PYT_water.DER_5m[2][3][obj_DER_PYT_water.DER_5m[0][V_analis]['index']]
    to_kW = 1
    plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker=markers[M_in],color = obj_Color.Color_RT[M_in]);plt.ylabel('agregated sum upper tank setpoint (F)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
    #### Plot lower set point WH
    plt.figure('Plot lower set point WH')
    
    M_in = M_in + 1
    
    V_analis = 'lower_tank_setpoint'
    AVG_power = obj_DER_PYT_water.DER_5m[2][3][obj_DER_PYT_water.DER_5m[0][V_analis]['index']]
    plt.plot((AVG_power.resample('60min').mean()/to_kW).values,marker=markers[M_in],color = obj_Color.Color_RT[M_in]);plt.ylabel('agregated sum lower tank setpoint (F)');plt.xlabel('time (hours)');plt.grid(True);plt.show()
    
    #### Plot convergency of individual bids WH
    plt.figure('Plot convergency of individual bids WH')
    home = 0
    
    V_analis = 'bid_4P_da_H_0_Q_1'
    df = obj_DER_PYT_water.DER_1h[3][home]
    meta = obj_DER_PYT_water.DER_1h[0]
    indexM = meta[V_analis]['index']
    x = list()
    for i in range(48):
        x.append(indexM+i*8)
    df = df.loc[:,x]
    MEETAA = np.array(list(meta.keys()))#[x]
    MEETAA = MEETAA[x]
    
    row_list = list()
    for index, rows in df.iterrows():
        my_list = list(rows)
        row_list.append(my_list)
    
    M_in=0
    for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        convergency_max = make_convergency_test(data_s=row_list,t=i)
        plt.plot(convergency_max,marker=markers[M_in],color = obj_Color.Color_convergency[M_in],label=str(i)+'-h');plt.ylabel('optimal quantity bid (kWh)');plt.xlabel('from time ahead to present (hours)')
        M_in = M_in + 1
    plt.grid(True);plt.legend(bbox_to_anchor=(1.1, 1.00));plt.title('Water heater individual '+obj_DER_PYT_water.DER_1h[4][home]);plt.show()
    
    #### Plot convergency of sum bids WH
    plt.figure('Plot convergency of sum bids WH')
    
    V_analis = 'bid_4P_da_H_0_Q_1'
    df = obj_DER_PYT_water.DER_1h[2][3]
    meta = obj_DER_PYT_water.DER_1h[0]
    indexM = meta[V_analis]['index']
    x = list()
    for i in range(48):
        x.append(indexM+i*8)
    df = df.loc[:,x]
    MEETAA = np.array(list(meta.keys()))#[x]
    MEETAA = MEETAA[x]
    
    row_list = list()
    for index, rows in df.iterrows():
        my_list = list(rows)
        row_list.append(my_list)
    
    M_in=0
    for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        convergency_max = make_convergency_test(data_s=row_list,t=i)
        plt.plot(convergency_max,marker=markers[M_in],color = obj_Color.Color_convergency[M_in],label=str(i)+'-h');plt.ylabel('agregated sum optimal quantity bid (kWh)');plt.xlabel('from time ahead to present (hours)')
        M_in = M_in + 1
    plt.grid(True);plt.legend(bbox_to_anchor=(1.1, 1.00));plt.title('Water heater sum');plt.show()

def HVAC(obj_Market,obj_DER_PYT_hvac,obj_DER_GLD_house,obj_Color):
    """HVAC plots
    
    Args:
        obj_Market (obj): contain market info
        obj_DER_PYT_hvac (obj): contains python HVAC agent info
        obj_DER_GLD_house (obj): GLD house info
        obj_Color (obj): contain colors
    """
    markers=obj_Color.Marker
    #### Plot temperatures and price
    fig = plt.figure('Plot individual temperature and price HVAC'); ax1 = fig.add_subplot(111)
    
    M_in=0
    V_analis = ['room_air_temperature','outdoor_temperature','cooling_setpoint','cooling_basepoint','heating_setpoint']
    home = 0 
    df = obj_DER_PYT_hvac.DER_5m[3][home]
    meta = obj_DER_PYT_hvac.DER_5m[0]
    for i in V_analis:
        indexM = meta[i]['index']
        ax1.plot(df.loc[:,indexM].values,marker=markers[M_in],color = obj_Color.Color_RT[M_in],label=i)
        M_in = M_in + 1
    
    ax1.set_ylabel('temperature (F)',color=obj_Color.Color_RT[0])  
    V_analis = 'cleared_price'
    indexM = meta[V_analis]['index']
    ax2 = ax1.twinx()
    ax2.plot(df.loc[:,indexM].values,marker=markers[M_in],color = obj_Color.Color_market[0]);ax2.set_ylabel('RT retail HVAC agent price ($/kWh)',color=obj_Color.Color_market[0])
    ax1.legend(bbox_to_anchor=(1.2, 1.00))
    ax1.set_xlabel('time (5-min)')
    plt.grid(True);plt.title('HVAC individual '+obj_DER_PYT_hvac.DER_5m[4][home]);plt.show()
        
    
    #### Plot convergency of individual bids HVAC
    plt.figure('Plot convergency of individual bids HVAC')
    home = 0 
    
    V_analis = 'bid_4P_da_H_0_Q_1'
    df = obj_DER_PYT_hvac.DER_1h[3][0]
    meta = obj_DER_PYT_hvac.DER_1h[0]
    indexM = meta[V_analis]['index']
    x = list()
    for i in range(48):
        x.append(indexM+i*8)
    df = df.loc[:,x]
    MEETAA = np.array(list(meta.keys()))#[x]
    MEETAA = MEETAA[x]
    
    row_list = list()
    for index, rows in df.iterrows():
        my_list = list(rows)
        row_list.append(my_list)
    
    M_in=0
    for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        convergency_max = make_convergency_test(data_s=row_list,t=i)
        plt.plot(convergency_max,marker=markers[M_in],color = obj_Color.Color_convergency[M_in],label=str(i)+'-h');plt.ylabel('optimal quantity bid (kWh)');plt.xlabel('from time ahead to present (hours)')
        M_in = M_in + 1
    plt.grid(True);plt.legend(bbox_to_anchor=(1.1, 1.00));plt.title('HVAC individual '+obj_DER_PYT_hvac.DER_5m[4][home]);plt.show()

    #### Plot convergency of sum bids HVAC
    plt.figure('Plot convergency of sum bids HVAC')
    
    V_analis = 'bid_4P_da_H_0_Q_1'
    df = obj_DER_PYT_hvac.DER_1h[2][3]
    meta = obj_DER_PYT_hvac.DER_1h[0]
    indexM = meta[V_analis]['index']
    x = list()
    for i in range(48):
        x.append(indexM+i*8)
    df = df.loc[:,x]
    MEETAA = np.array(list(meta.keys()))#[x]
    MEETAA = MEETAA[x]
    
    row_list = list()
    for index, rows in df.iterrows():
        my_list = list(rows)
        row_list.append(my_list)
    
    M_in=0
    for i in range(da_convergence_start,da_convergence_start+N_convergence_hours):
        convergency_max = make_convergency_test(data_s=row_list,t=i)
        plt.plot(convergency_max,marker=markers[M_in],color = obj_Color.Color_convergency[M_in],label=str(i)+'-h');plt.ylabel('agregated sum optimal quantity bid (kWh)');plt.xlabel('from time ahead to present (hours)')
        M_in = M_in + 1
    plt.grid(True);plt.legend(bbox_to_anchor=(1.1, 1.00));plt.title('HVAC sum');plt.show()

    
    
    
if __name__ == "__main__":
    """All the data will be loaded first for the requested days
    """
    pre_file_out ='TE_test/dso_1/'
    pos_file ='.json'
    days = list([0,3])
    da_convergence_start = 24*0 # DA interaction to start looking for convergence
    N_convergence_hours = 24 # number of hours to visualize convergence (set to zero neglect)

    obj_Market = marketJSONpython(days,pre_file_out,pos_file)
    
    obj_DER_PYT_battery = DERsJSON(days, pre_file_out+'battery_agent', pos_file, GLD=False)
    obj_DER_PYT_hvac    = DERsJSON(days, pre_file_out+'hvac_agent', pos_file, GLD=False)
    obj_DER_PYT_water   = DERsJSON(days, pre_file_out+'water_heater_agent', pos_file, GLD=False)
    
    pre_file_out ='TE_test/TE_Base_s1/'
#    pos_file ='.json.json' # New GLD json output files
    
    obj_DER_GLD_substation = DERsJSON(days, pre_file_out+'substation_TE_Base_s1_metrics', pos_file, GLD=True)
    obj_DER_GLD_inverter   = DERsJSON(days, pre_file_out+'inverter_TE_Base_s1_metrics', pos_file, GLD=True)
    obj_DER_GLD_house      = DERsJSON(days, pre_file_out+'house_TE_Base_s1_metrics', pos_file, GLD=True)
    
    obj_Color = MarkerCollorsJSONpython()
    
    #### Making plots
    Markets(obj_Market,obj_Color)
    DSOplots(obj_Market,obj_Color)
    RETplots(obj_Market,obj_Color)
    #### Inverter plots
    Inverter(obj_Market,obj_DER_PYT_battery,obj_DER_GLD_inverter,obj_Color)
    #### Water heater
    Water_Heater(obj_Market,obj_DER_PYT_water,obj_DER_GLD_house,obj_Color)
    #### HVAC plots
    HVAC(obj_Market,obj_DER_PYT_hvac,obj_DER_GLD_house,obj_Color)
    
    
    