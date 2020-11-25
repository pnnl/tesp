# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: substation.py

import sys
try:
  import tesp_support.fncs as fncs
except:
  pass
import tesp_support.simple_auction as auction
#import tesp_support.hvac as hvac
import tesp_support.helpers as helpers
import json
from datetime import datetime
from datetime import timedelta
import torch
from rnn import RNN
from rnn import RNNl
from arl import arl
from process_input_data import get_npy
from metrics_result import plot_arl_full
import numpy as np
import os
import time
if sys.platform != 'win32':
  import resource
   
  

def inner_substation_loop (configfile, metrics_root, house_num, hour_stop=72, flag='WithMarket'):
    """Helper function that initializes and runs the agents

    Reads configfile. Writes *auction_metrics_root_metrics.json* and
    *controller_metrics_root_metrics.json* upon completion.

    Args:
        configfile (str): fully qualified path to the JSON agent configuration file
        metrics_root (str): base name of the case for metrics output
        hour_stop (float): number of hours to simulation
        flag (str): WithMarket or NoMarket to use the simple_auction, or not
    """
    print ('starting substation loop', configfile, metrics_root, hour_stop, flag, flush=True)
    print ('##,tnow,tclear,ClearType,ClearQ,ClearP,BuyCount,BuyUnresp,BuyResp,SellCount,SellUnresp,SellResp,MargQ,MargFrac,LMP,RefLoad,ConSurplus,AveConSurplus,SupplierSurplus,UnrespSupplierSurplus', flush=True)
    bWantMarket = True
    if flag == 'NoMarket':
        bWantMarket = False
        print ('Disabled the market', flush=True)
    time_stop = int (hour_stop * 3600) # simulation time in seconds
    StartTime = '2018-05-28 00:00:00 -0800'
    time_fmt = '%Y-%m-%d %H:%M:%S %z'
    dt_now = datetime.strptime (StartTime, time_fmt)

    # ====== load the JSON dictionary; create the corresponding objects =========
    
#    os.mkdir('metrics') output file 
    os.makedirs('metrics', exist_ok = True)

# define rnns and load inputs
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
 
    # load trained network paramerters to the RNNs    
    rnn_bid = RNN(10,128,1)
    rnn_bid.load_state_dict(torch.load('input\\rnn_bid', map_location = device))
    rnn_response = RNNl(12,192,1)
    rnn_response.load_state_dict(torch.load('input\\rnn_response', map_location = device))     
    rnn_bid.to(device)
    rnn_response.to(device)
    
    hvac_sum = []  
    price = [] 
    load_hvac = [] 
    unresp = []
    agg_unresp = []
    agg_resp_max = []
    agg_deg = []
    agg_c2 = []
    agg_c1 = []
    lmp = []
#    load_feeder = [], hvac_state = [], bid_p=[] 

    lp = open (configfile).read()
    dict = json.loads(lp)

    market_key = list(dict['markets'].keys())[0]  # only using the first market
    market_row = dict['markets'][market_key]
    unit = market_row['unit']

    auction_meta = {'clearing_price':{'units':'USD','index':0},'clearing_type':{'units':'[0..5]=[Null,Fail,Price,Exact,Seller,Buyer]','index':1},'consumer_surplus':{'units':'USD','index':2},'average_consumer_surplus':{'units':'USD','index':3},'supplier_surplus':{'units':'USD','index':4}}
    controller_meta = {'bid_price':{'units':'USD','index':0},'bid_quantity':{'units':unit,'index':1}}
    auction_metrics = {'Metadata':auction_meta,'StartTime':StartTime}
    controller_metrics = {'Metadata':controller_meta,'StartTime':StartTime}

    aucObj = auction.simple_auction (market_row, market_key)
   
    hn=get_npy(house_num)  
    
    # initialize the ARL     
    RA = arl(house_num,rnn_bid,rnn_response,aucObj,hn)      

    dt = float(dict['dt'])
    period = aucObj.period

    topicMap = {} # to dispatch incoming FNCS messages; 0..5 for LMP, Feeder load, airtemp, mtr volts, hvac load, hvac state
    topicMap['LMP'] = [aucObj, 0]
    topicMap['refload'] = [aucObj, 1]
    
    # ==================== Time step looping under FNCS ===========================

    fncs.initialize()
    aucObj.initAuction()
    LMP = aucObj.mean
    refload = 0.0
    bSetDefaults = True

    tnext_bid = period - 2 * dt  #3 * dt  # controllers calculate their final bids
    tnext_agg = period - 2 * dt  # auction calculates and publishes aggregate bid
    tnext_opf = period - 1 * dt  # PYPOWER executes OPF and publishes LMP (no action here)
    tnext_clear = period         # clear the market with LMP
    tnext_adjust = period        # + dt   # controllers adjust setpoints based on their bid and clearing

    time_granted = 0
    time_last = 0
    
    day = 0
    step = 0
    clear_p = np.zeros(RA.house_number)

    tic=time.time()
    while (time_granted < time_stop):
        nextFNCSTime = int(min ([tnext_bid, tnext_agg, tnext_clear, tnext_adjust, time_stop]))
        fncs.update_time_delta (nextFNCSTime-time_granted)
        time_granted = fncs.time_request (nextFNCSTime)
        time_delta = time_granted - time_last
        time_last = time_granted
#        hour_of_day = 24.0 * ((float(time_granted) / 86400.0) % 1.0)

        dt_now = dt_now + timedelta (seconds=time_delta)
#        day_of_week = dt_now.weekday()
#        hour_of_day = dt_now.hour

        events = fncs.get_events()
        for topic in events:
            value = fncs.get_value(topic)
            row = topicMap[topic]
            if row[1] == 0:
                LMP = helpers.parse_fncs_magnitude (value)
                aucObj.set_lmp (LMP)
            elif row[1] == 1:
                refload = helpers.parse_kw (value)
                aucObj.set_refload (refload)
                
                
        if time_granted >= tnext_bid:
            aucObj.clear_bids()
            time_key = str (int (tnext_clear))
            controller_metrics [time_key] = {}            
#            load_feeder.append(refload)

            #generate bids with RNN
            if day != 0 and step <= 2 :
                pass
            else:
                bid = RA.generate_bidsps(day,step)  
                bid[0]=bid[0]*RA.Y_bid_max 
            
            if bWantMarket:
                for n in range(RA.house_number):
                    aucObj.collect_bid(bid[:,n])

            if day == 0 and step <= 3:
                aucObj.unresp = RA.agg_un_tesp[day,step]
            else :
                aucObj.unresp=int(refload-np.sum(load_list)*RA.Y_response_max) 
                
            unresp.append(aucObj.unresp)
            agg_unresp.append(aucObj.agg_unresp)
            agg_resp_max.append(aucObj.agg_resp_max)
            agg_deg.append(aucObj.agg_deg)
            agg_c2.append(aucObj.agg_c2)
            agg_c1.append(aucObj.agg_c1)
            lmp.append(aucObj.lmp)
            
            tnext_bid += period

        if time_granted >= tnext_agg:
                        
            aucObj.aggregate_bids()
            fncs.publish ('unresponsive_mw', aucObj.agg_unresp)
            fncs.publish ('responsive_max_mw', aucObj.agg_resp_max)
            fncs.publish ('responsive_c2', aucObj.agg_c2)
            fncs.publish ('responsive_c1', aucObj.agg_c1)
            fncs.publish ('responsive_deg', aucObj.agg_deg)
            tnext_agg += period

        if time_granted >= tnext_clear:
            if bWantMarket:
                aucObj.clear_market(tnext_clear, time_granted)
                aucObj.surplusCalculation(tnext_clear, time_granted)
                fncs.publish ('clear_price', aucObj.clearing_price)
                
                RA.inform_bid (aucObj.clearing_price)
            time_key = str (int (tnext_clear))
            auction_metrics [time_key] = {aucObj.name:[aucObj.clearing_price, aucObj.clearing_type, aucObj.consumerSurplus, aucObj.averageConsumerSurplus, aucObj.supplierSurplus]}
            tnext_clear += period
#            print ('garbage collecting at', time_granted, 'finds', gc.collect(), 'unreachable objects', flush=True)

        if time_granted >= tnext_adjust:
            if bWantMarket:

                cleared_p_norm = (RA.cleared_price-RA.X_response_min[0])/(RA.X_response_max[0]-RA.X_response_min[0])
                for n in range(RA.house_number):
                    clear_p[n] = cleared_p_norm
                clear_p_ = torch.tensor(clear_p).type(torch.FloatTensor).to(device)    
                RA.inputs_norm[:house_num,day,step,0] = clear_p_                   
                                   
                # generate hvac load with RNN
                load_list=RA.set_hvac_load(day,step)
                load_hvac.append(load_list)
                
                RA.update_unresposive_load(day,step)
                               
                load = RA.res_load*1000/3
                fncs.publish ('RA/res_load', str(load).strip('[]'))
                
                load_unres = RA.unres_load*1000/3
                fncs.publish ('RA/unres_load', str(load_unres).strip('[]'))
                
            tnext_adjust += period
            
            hvac_sum.append(RA.res_load)
            price.append(RA.cleared_price)
            
            step += 1
            
            if step%288 == 0:
                day +=1
                step=0   
                
                toc = time.time()
                time_consume=toc-tic
                np.save('metrics\\time_ra'+str(house_num),time_consume)                          
                np.save('metrics\\hvacload'+str(house_num),hvac_sum)
                np.save('metrics\\price_ra'+str(house_num),price)
                
    #plot the result with a full model case for comparison           
    plot_arl_full(house_num)
    print ('Simulation time :', time_consume,'s', flush=True)
                         
    # ==================== Finalize the metrics output ===========================

    print ('writing metrics', flush=True)
    auction_op = open ('auction_' + metrics_root + '_metrics.json', 'w')
    controller_op = open ('controller_' + metrics_root + '_metrics.json', 'w')
    print (json.dumps(auction_metrics), file=auction_op)
    print (json.dumps(controller_metrics), file=controller_op)
    auction_op.close()
    controller_op.close()

    print ('finalizing FNCS', flush=True)
    fncs.finalize()


def substation_loop (configfile, metrics_root, house_num, hour_stop=72, flag='WithMarket'):
    """Wrapper for *inner_substation_loop*

    When *inner_substation_loop* finishes, timing and memory metrics will be printed
    for non-Windows platforms.
    """
    inner_substation_loop (configfile, metrics_root, house_num, hour_stop, flag)
#    gc.enable() 
#    gc.set_debug(gc.DEBUG_LEAK) 

#    profiler = cProfile.Profile ()
#    args = (configfile, metrics_root, hour_stop, flag)
#    profiler.runcall (inner_substation_loop, *args)
#    stats = pstats.Stats(profiler)
#    stats.strip_dirs()
#    stats.sort_stats('cumulative')
#    stats.print_stats()

#    print (gc.collect (), 'unreachable objects')
#    for x in gc.garbage:
#        s = str(x) 
#        print (type(x), ':', len(s), flush=True)
    if sys.platform != 'win32':
        usage = resource.getrusage(resource.RUSAGE_SELF)
        RESOURCES = [
            ('ru_utime', 'User time'),
            ('ru_stime', 'System time'),
            ('ru_maxrss', 'Max. Resident Set Size'),
            ('ru_ixrss', 'Shared Memory Size'),
            ('ru_idrss', 'Unshared Memory Size'),
            ('ru_isrss', 'Stack Size'),
            ('ru_inblock', 'Block inputs'),
            ('ru_oublock', 'Block outputs')]
        print('Resource usage:')
        for name, desc in RESOURCES:
            print('  {:<25} ({:<10}) = {}'.format(desc, name, getattr(usage, name)))
 

if __name__ == '__main__':
    substation_loop('C:\\Users\\wang690\\Desktop\\projects\\TESP\\tesp_1st\\ercot\\case8\\Bus1_agent_dict.json','Bus1',24)