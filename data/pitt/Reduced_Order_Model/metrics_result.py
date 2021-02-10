# -*- coding: utf-8 -*-
"""
@author: liubo
"""
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
#from process_input_data import get_npy
from process_input_data import most_close_num



def plot_arl_full(num):
    
    housenum=num
    day=3
    sns.set_style('white')
    hn=most_close_num(housenum)
    time_ra=np.load('metrics\\time_ra'+str(housenum)+'.npy')
    print(time_ra)
    
    price_tesp=np.load('input\\fullmodel_price.npy',allow_pickle=True).item().get(str(hn))
    hvac_sum_tesp=np.load('input\\fullmodel_hvacload.npy',allow_pickle=True).item().get(str(hn))
    
    price_ra=np.load('metrics\\price_ra'+str(housenum)+'.npy',allow_pickle=True)
    load_ra=np.load('metrics\\hvacload'+str(housenum)+'.npy',allow_pickle=True)
    
    timetick= ['0:00','6:00','12:00','18:00']
    timeticks=day*timetick
    
#    fig, ax = plt.subplots(2, 1, sharex = 'all',figsize=(12,6.3))
    fig, ax = plt.subplots(2, 1, sharex = 'all',figsize=(13,5.3))
    
    ax[0].plot(price_ra[0:day*288],label='ARL '+str(housenum)+' houses')
    ax[0].plot(price_tesp[0:day*288],label='Full '+str(hn)+' houses')
    ax[0].legend(loc='best',fontsize=13)
    ax[0].set_title('Cleared price',fontsize=15)
    ax[0].set_xlabel('Time',fontsize=14)
    ax[0].set_ylabel('USD',fontsize=14)
    ax[0].tick_params(labelsize=12,bottom=True)
    plt.xticks(np.arange(0,day*288,72), timeticks)
    
    ax[1].plot(load_ra[0:day*288],label='ARL '+str(housenum)+' houses',linewidth=2)
    ax[1].plot(hvac_sum_tesp[0:day*288],label='Full '+str(hn)+' houses',linewidth=2)
    ax[1].legend(loc='best',fontsize=13)
    ax[1].set_title('Aggregate HVAC Load',fontsize=15)
    ax[1].set_xlabel('Time',fontsize=14)
    ax[1].set_ylabel('Load (kW)',fontsize=14)
    ax[1].tick_params(labelsize=12,bottom=True)
    plt.xticks(np.arange(0,day*288,72), timeticks)
    plt.show()
    #plt.tick_params(labelsize=14)   
    return

if __name__=="__main__":
    
    # input a house number
    plot_arl_full(900)



