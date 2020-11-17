# Copyright (C) 2017-2019 Battelle Memorial Institute
# file: substation.py
"""Manages the simple_auction and hvac agents for the te30 and sgip1 examples

Public Functions:
    :substation_loop: initializes and runs the agents

Todo:
    * Getting an overflow error when killing process - investigate whether that happens if simulation runs to completion
    * Allow changes in the starting date and time; now it's always midnight on July 1, 2013
    * Allow multiple markets per substation, e.g., 5-minute and day-ahead for the DSO+T study

"""
import sys
try:
  import tesp_support.fncs as fncs
except:
  pass
import tesp_support.simple_auction as auction
import tesp_support.hvac as hvac
import tesp_support.helpers as helpers
import json
from datetime import datetime
from datetime import timedelta
import numpy as np
from tesp_support.RLAgent import Agent
from tesp_support.RLagent import OUNoise
import torch as T



#import gc
#import cProfile
#import pstats
if sys.platform != 'win32':
  import resource

#
#configfile='RL_agent_dict.json'
#metrics_root='RL'
#hour_stop=24
#flag='WithMarket'

  

def inner_substation_loop (configfile, metrics_root, hour_stop=1667, flag='WithMarket'):
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
    StartTime = '2018-06-01 00:00:00 -0800'
    time_fmt = '%Y-%m-%d %H:%M:%S %z'
    dt_now = datetime.strptime (StartTime, time_fmt)

    # ====== load the JSON dictionary; create the corresponding objects =========

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

    dt = float(dict['dt'])
    period = aucObj.period

    topicMap = {} # to dispatch incoming FNCS messages; 0..5 for LMP, Feeder load, airtemp, mtr volts, hvac load, hvac state
    topicMap['LMP'] = [aucObj, 0]
    topicMap['refload'] = [aucObj, 1]

    hvacObjs = {}
    hvac_keys = list(dict['controllers'].keys())
    for key in hvac_keys:
        row = dict['controllers'][key]
        hvacObjs[key] = hvac.hvac (row, key, aucObj)
        ctl = hvacObjs[key]
        topicMap[key + '#Tair'] = [ctl, 2]
        topicMap[key + '#V1'] = [ctl, 3]
        topicMap[key + '#Load'] = [ctl, 4]
        topicMap[key + '#On'] = [ctl, 5]

                    
#        if key== 'R1_12_47_3_tn_1_hse_10_hvac':          ### l
#            topicMap['R1_12_47_3_tn_1_hse_10_hvac#Av']=[ctl, 6]  

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
    



    tnext_hvac_energy = 270
    tnext_action = 570

    time_granted = 0
    time_last = 0

    refloada=[]
    resload=[]
    unresload=[]
    T_room=[]
    T_base=[]
    E_hvac=[]###########
    T_set=[]
    P_clear=[]
    hvac_energy=0
    

    act_t=[]
    act_obs=[]
    state_t=[]
    state_obs=[]
#    hvac_obs=[]
    state_new_t=[]
    reward_t=[]
    price_obs=[]    
    score_history = []
    hvac_energy_t=[]
    
    step=0
    end=0

    noise = OUNoise()
    agent = Agent(alpha=0.000025, beta=0.00025, input_dims=[5], tau=0.001,
                         batch_size=72,  layer1_size=90, layer2_size=60, n_actions=1)   
#    agent = Agent(alpha=0.00025, beta=0.0025, input_dims=[5], tau=0.002,
#                         batch_size=288,  layer1_size=90, layer2_size=60, n_actions=1)
    
    
    alpha=0.5
    a1=0.04
    T_low=-2.5
   
#    agent.actor = T.load('act')    
#    agent.critic = T.load('crit')
#    agent.target_actor = T.load('target_act')
#    agent.target_critic = T.load('target_crit')


#    agent.load_models()
#    agent.check_actor_params()
    
    
    np.random.seed(0)
    T_out=np.load('T_out.npy')                         

                        
    score=0
    
    
#    key='R1_12_47_3_tn_1_hse_10_hvac'
#    hvacObjs[key]=hvacObjs[key]
#    obs=np.array([[hvacObjs[key].air_temp],[hvacObjs[key].setpoint],[hvacObjs[key].cleared_price]])
    
    
    
    
    
    while (time_granted < time_stop):
        nextFNCSTime = int(min ([tnext_hvac_energy, tnext_bid, tnext_agg, tnext_clear, tnext_adjust, time_stop, tnext_action]))
        
        fncs.update_time_delta (nextFNCSTime-time_granted)
        time_granted = fncs.time_request (nextFNCSTime)
        time_delta = time_granted - time_last
        time_last = time_granted
        hour_of_day = 24.0 * ((float(time_granted) / 86400.0) % 1.0)
#        print (dt_now, time_delta, timedelta (seconds=time_delta))
        dt_now = dt_now + timedelta (seconds=time_delta)
        day_of_week = dt_now.weekday()
        hour_of_day = dt_now.hour
#        print ('  ', time_last, time_granted, time_stop, time_delta, hour_of_day, day_of_week, flush=True)
        # update the data from FNCS messages

        if time_granted >= tnext_hvac_energy:
#            key=='R1_12_47_3_tn_1_hse_10_hvac'
##                        key='R1_12_47_3_tn_1_hse_10_hvac'
#            hvacObjs[key]=hvacObjs[key]
            
            tnext_hvac_energy += dt

       
        events = fncs.get_events()
#        loadave.append(str(events))
        for topic in events:
            value = fncs.get_value(topic)
            row = topicMap[topic]
            if row[1] == 0:
                LMP = helpers.parse_fncs_magnitude (value)
                aucObj.set_lmp (LMP)
            elif row[1] == 1:
                refload = helpers.parse_kw (value)
                aucObj.set_refload (refload)
            elif row[1] == 2:
                row[0].set_air_temp (value)
            elif row[1] == 3:
                row[0].set_voltage (value)
            elif row[1] == 4:
                row[0].set_hvac_load (value)
                if topic == 'R1_12_47_3_tn_1_hse_10_hvac#Load':
                    hvac_energy += helpers.parse_fncs_number(value)
            elif row[1] == 5:
                row[0].set_hvac_state (value)

              
                
                
        if bSetDefaults:
            for key, obj in hvacObjs.items():
                fncs.publish (obj.name + '/bill_mode', 'HOURLY')
                fncs.publish (obj.name + '/monthly_fee', 0.0)
                fncs.publish (obj.name + '/thermostat_deadband', obj.deadband)
                fncs.publish (obj.name + '/heating_setpoint', -400)
            bSetDefaults = False
            
            
        if time_granted >= tnext_action:
            refloada.append(aucObj.refload)
            resload.append(aucObj.agg_resp_max)
            unresload.append(aucObj.agg_unresp)
            
            key = 'R1_12_47_3_tn_1_hse_10_hvac'
#                        key='R1_12_47_3_tn_1_hse_10_hvac'
#                hvacObjs[key]=hvacObjs[key]
            
            if step >= 1 or end == 1:
                hvacObjs[key].reset(hour_of_day,day_of_week)
                
            T_bound=hvacObjs[key].get_basepoint(hour_of_day,day_of_week)
        #store the  price
            price_obs.append(hvacObjs[key].cleared_price)
    
#            if step == 0 :
#                hvacObjs[key].setpoint=hvacObjs[key].basepoint

            state = np.array([[hvacObjs[key].air_temp,hvacObjs[key].setpoint,T_bound,T_out[step],hvacObjs[key].cleared_price]])
            # choose action based on the state

            state_obs.append(np.array([[hvacObjs[key].air_temp,hvacObjs[key].setpoint,T_bound,T_out[step],hvacObjs[key].cleared_price]]))
            

            act = agent.choose_action(state)+noise.get_noise(step)
            act_obs.append(act)
            


            
            
#            # make change on the temperature setting point
#            hvacObjs[key].basepoint=hvacObjs[key].basepoint+act[0,0]
            # directly choose
            hvacObjs[key].basepoint = hvacObjs[key].basepoint + act[0,0]*9
            
            
            T_base.append(hvacObjs[key].basepoint)
           
#            fncs.publish (hvacObjs[key].name + '/cooling_setpoint', hvacObjs[key].basepoint)   #           
            fncs.publish (hvacObjs[key].name + '/heating_setpoint', -100)
#            fncs.publish (hvacObjs[key].name + '/cooling_setpoint', hvacObjs[key].setpoint)

            
            
            if step >=1:
                
                state = state_obs[step-1]
                act = act_obs[step-1]

                state_new = state_obs[step]
                
#                T_d=abs(T_base[step-1]-state_obs[step-1][0][2])
                T_d = state_obs[step][0][0]-state_obs[step][0][2]
                
                if state_obs[step][0][0] <= 60 or state_obs[step][0][0] >= 100 or state_obs[step][0][2] <= 66 or state_obs[step][0][2]>=88 : 
                    reward = -10                    
                    end = 1
                else: 
                    if T_d >= 0 :  
                        reward= -1*alpha*price_obs[step-1]*hvac_energy-(1-alpha)*a1*T_d**2
                    elif T_d < 0 and T_d >= T_low :
                        reward= -1*alpha*price_obs[step-1]*hvac_energy
                    elif T_d < T_low :
                        reward= -1*alpha*price_obs[step-1]*hvac_energy-(1-alpha)*a1*(T_d-T_low)**2
                    end=0
                                    
                
                state_t.append(state)
                act_t.append(act)                                                                          
                state_new_t.append(state_new)
                reward_t.append(reward)
                hvac_energy_t.append(hvac_energy)
                
                agent.remember(state, act, reward, state_new)
                agent.learn() 
                                                                                       
                score+=reward               

                            
                            
            step+=1 
            hvac_energy=0
            
            if step%288==0 and step>0:
                
                score_history.append(score)
                score=0
                            
            T_set.append(hvacObjs[key].setpoint)
            T_room.append(hvacObjs[key].air_temp)
            E_hvac.append(hvacObjs[key].ave)
            P_clear.append(hvacObjs[key].cleared_price)
            
            if step%1000 == 0 and step > 0 :
                agent.save_models() 

    
                np.save('T_room', T_room)   
                np.save('T_set', T_set)  
                np.save('P_clear', P_clear)  
                np.save('E_hvac', E_hvac)
#                np.save('loadave', loadave)
                np.save('state_obs',state_obs)
                np.save('act_obs',act_obs)
                np.save('state_t',state_t)
                np.save('act_t',act_t)
                np.save('state_new_t',state_new_t)
                np.save('reward_t',reward_t)
                np.save('score_history',score_history)
                np.save('hvac_energy',hvac_energy_t)
                np.save('T_base',T_base)   
                np.save('resload',resload)
                np.save('unresload',unresload)
                np.save('refload',refload)           
        
            tnext_action += period

       
        
        
        if time_granted >= tnext_bid:
            # set the time-of-day schedule
            for key, obj in hvacObjs.items():
                if key != 'R1_12_47_3_tn_1_hse_10_hvac':
                    if obj.change_basepoint (hour_of_day, day_of_week):
                        fncs.publish (obj.name + '/cooling_setpoint', obj.basepoint)  
                if key == 'R1_12_47_3_tn_1_hse_10_hvac' and step == 0 :
                    if obj.change_basepoint (hour_of_day, day_of_week):
                        fncs.publish (obj.name + '/cooling_setpoint', obj.basepoint)  
                    
            
            
            aucObj.clear_bids()
            time_key = str (int (tnext_clear))
            controller_metrics [time_key] = {}
            for key, obj in hvacObjs.items():
                bid = obj.formulate_bid () # bid is [price, quantity, on_state]
                if bWantMarket:
                    aucObj.collect_bid (bid)
                controller_metrics[time_key][obj.name] = [bid[0], bid[1]]
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
                for key, obj in hvacObjs.items():
                    obj.inform_bid (aucObj.clearing_price)
            time_key = str (int (tnext_clear))
            auction_metrics [time_key] = {aucObj.name:[aucObj.clearing_price, aucObj.clearing_type, aucObj.consumerSurplus, aucObj.averageConsumerSurplus, aucObj.supplierSurplus]}
            tnext_clear += period
#            print ('garbage collecting at', time_granted, 'finds', gc.collect(), 'unreachable objects', flush=True)
            
        if time_granted >= tnext_adjust:
            if bWantMarket:
                for key, obj in hvacObjs.items():                    
                    fncs.publish (obj.name + '/price', aucObj.clearing_price)                                    
                    if obj.bid_accepted ():
                        fncs.publish (obj.name + '/cooling_setpoint', obj.setpoint)
            

            
            tnext_adjust += period



            

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


def substation_loop (configfile, metrics_root, hour_stop=1667, flag='WithMarket'):
    """Wrapper for *inner_substation_loop*

    When *inner_substation_loop* finishes, timing and memory metrics will be printed
    for non-Windows platforms.
    """
    inner_substation_loop (configfile, metrics_root, hour_stop, flag)
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