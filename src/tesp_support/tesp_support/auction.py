import sys
import tesp_support.fncs as fncs
import tesp_support.simple_auction as simple_auction
import json
from datetime import datetime
from datetime import timedelta
#import gc
#import cProfile
#import pstats
if sys.platform != 'win32':
  import resource

# these should be in a configuration file as well; TODO synch the proper hour of day
def inner_auction_loop (configfile, metrics_root, hour_stop=48, flag='WithMarket'):
    print ('starting auction loop', configfile, metrics_root, hour_stop, flag, flush=True)
    print ('##,tnow,tclear,ClearType,ClearQ,ClearP,BuyCount,BuyUnresp,BuyResp,SellCount,SellUnresp,SellResp,MargQ,MargFrac,LMP,RefLoad', flush=True)
    bWantMarket = True
    if flag == 'NoMarket':
        bWantMarket = False
        print ('Disabled the market', flush=True)
    time_stop = int (hour_stop * 3600) # simulation time in seconds
    StartTime = '2013-07-01 00:00:00 -0800'
    time_fmt = '%Y-%m-%d %H:%M:%S %z'
    dt_now = datetime.strptime (StartTime, time_fmt)

    # ====== load the JSON dictionary; create the corresponding objects =========

    lp = open (configfile).read()
    dict = json.loads(lp)

    market_key = list(dict['markets'].keys())[0]  # TODO: only using the first market
    market_row = dict['markets'][market_key]
    unit = market_row['unit']

    auction_meta = {'clearing_price':{'units':'USD','index':0},'clearing_type':{'units':'[0..5]=[Null,Fail,Price,Exact,Seller,Buyer]','index':1}}
    controller_meta = {'bid_price':{'units':'USD','index':0},'bid_quantity':{'units':unit,'index':1}}
    auction_metrics = {'Metadata':auction_meta,'StartTime':StartTime}
    controller_metrics = {'Metadata':controller_meta,'StartTime':StartTime}

    aucObj = simple_auction.simple_auction (market_row, market_key)

    dt = float(dict['dt'])
    period = aucObj.period

    topicMap = {} # to dispatch incoming FNCS messages; 0..5 for LMP, Feeder load, airtemp, mtr volts, hvac load, hvac state
    topicMap['LMP'] = [aucObj, 0]
    topicMap['refload'] = [aucObj, 1]

    hvacObjs = {}
    hvac_keys = list(dict['controllers'].keys())
    for key in hvac_keys:
        row = dict['controllers'][key]
        hvacObjs[key] = simple_auction.hvac (row, key, aucObj)
        ctl = hvacObjs[key]
        topicMap[key + '#Tair'] = [ctl, 2]
        topicMap[key + '#V1'] = [ctl, 3]
        topicMap[key + '#Load'] = [ctl, 4]
        topicMap[key + '#On'] = [ctl, 5]

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
    while (time_granted < time_stop):
        time_granted = fncs.time_request(time_stop)
        time_delta = time_granted - time_last
        time_last = time_granted
        hour_of_day = 24.0 * ((float(time_granted) / 86400.0) % 1.0)
# TODO - getting an overflow error when killing process - investigate whether that happens if simulation runs to completion
#        print (dt_now, time_delta, timedelta (seconds=time_delta))
        dt_now = dt_now + timedelta (seconds=time_delta)
        day_of_week = dt_now.weekday()
        hour_of_day = dt_now.hour
#        print ('  ', time_last, time_granted, time_stop, time_delta, hour_of_day, day_of_week, flush=True)
        # update the data from FNCS messages
        events = fncs.get_events()
        for topic in events:
            value = fncs.get_value(topic)
            row = topicMap[topic]
            if row[1] == 0:
                LMP = simple_auction.parse_fncs_magnitude (value)
                aucObj.set_lmp (LMP)
            elif row[1] == 1:
                refload = simple_auction.parse_kw (value)
                aucObj.set_refload (refload)
            elif row[1] == 2:
                row[0].set_air_temp (value)
            elif row[1] == 3:
                row[0].set_voltage (value)
            elif row[1] == 4:
                row[0].set_hvac_load (value)
            elif row[1] == 5:
                row[0].set_hvac_state (value)

        # set the time-of-day schedule
        for key, obj in hvacObjs.items():
            if obj.change_basepoint (hour_of_day, day_of_week):
                fncs.publish (obj.name + '/cooling_setpoint', obj.basepoint)
        if bSetDefaults:
            for key, obj in hvacObjs.items():
                fncs.publish (obj.name + '/bill_mode', 'HOURLY')
                fncs.publish (obj.name + '/monthly_fee', 0.0)
                fncs.publish (obj.name + '/thermostat_deadband', obj.deadband)
                fncs.publish (obj.name + '/heating_setpoint', 60.0)
            bSetDefaults = False

        if time_granted >= tnext_bid:
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
                fncs.publish ('clear_price', aucObj.clearing_price)
                for key, obj in hvacObjs.items():
                    obj.inform_bid (aucObj.clearing_price)
            time_key = str (int (tnext_clear))
            auction_metrics [time_key] = {aucObj.name:[aucObj.clearing_price, aucObj.clearing_type]}
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


def auction_loop (configfile, metrics_root, hour_stop=48, flag='WithMarket'):
    inner_auction_loop (configfile, metrics_root, hour_stop, flag)
#    gc.enable() 
#    gc.set_debug(gc.DEBUG_LEAK) 

#    profiler = cProfile.Profile ()
#    args = (configfile, metrics_root, hour_stop, flag)
#    profiler.runcall (inner_auction_loop, *args)
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
 

