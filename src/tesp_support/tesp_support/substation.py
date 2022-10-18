# Copyright (C) 2017-2022 Battelle Memorial Institute
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
import json

try:
    import helics
except:
    pass
try:
    import tesp_support.fncs as fncs
except:
    pass

from datetime import datetime
from datetime import timedelta

from .helpers import parse_kw, parse_magnitude
from .hvac import hvac
from .simple_auction import simple_auction

# import gc
# import cProfile
# import pstats
if sys.platform != 'win32':
    import resource


def helics_substation_loop(configfile, metrics_root, hour_stop, flag, helicsConfig):
    print('starting HELICS substation loop', configfile, metrics_root, hour_stop, flag, flush=True)
    print('##,tnow,tclear,ClearType,ClearQ,ClearP,BuyCount,BuyUnresp,BuyResp,' +
          'SellCount,SellUnresp,SellResp,MargQ,MargFrac,LMP,RefLoad,' +
          'ConSurplus,AveConSurplus,SupplierSurplus,UnrespSupplierSurplus', flush=True)
    bWantMarket = True
    if flag == 'NoMarket':
        bWantMarket = False
        print('Disabled the market', flush=True)
    time_stop = int(hour_stop * 3600)  # simulation time in seconds
    StartTime = '2013-07-01 00:00:00 -0800'
    time_fmt = '%Y-%m-%d %H:%M:%S %z'
    dt_now = datetime.strptime(StartTime, time_fmt)

    # ====== load the JSON dictionary; create the corresponding objects =========

    lp = open(configfile).read()
    diction = json.loads(lp)

    market_key = list(diction['markets'].keys())[0]  # only using the first market
    market_row = diction['markets'][market_key]
    unit = market_row['unit']

    auction_meta = {'clearing_price': {'units': 'USD', 'index': 0},
                    'clearing_type': {'units': '[0..5]=[Null,Fail,Price,Exact,Seller,Buyer]', 'index': 1},
                    'consumer_surplus': {'units': 'USD', 'index': 2},
                    'average_consumer_surplus': {'units': 'USD', 'index': 3},
                    'supplier_surplus': {'units': 'USD', 'index': 4}}
    controller_meta = {'bid_price': {'units': 'USD', 'index': 0}, 'bid_quantity': {'units': unit, 'index': 1}}
    auction_metrics = {'Metadata': auction_meta, 'StartTime': StartTime}
    controller_metrics = {'Metadata': controller_meta, 'StartTime': StartTime}

    aucObj = simple_auction(market_row, market_key)

    dt = float(diction['dt'])
    period = aucObj.period

    # Initialize controllers, map HELICS values to Python attributes
    subTemp = {}
    subVolt = {}
    subState = {}
    subHVAC = {}
    pubMtrMode = {}
    pubMtrPrice = {}
    pubMtrMonthly = {}
    pubHeating = {}
    pubCooling = {}
    pubDeadband = {}
    hFed = helics.helicsCreateValueFederateFromConfig(helicsConfig)
    pubCount = helics.helicsFederateGetPublicationCount(hFed)
    subCount = helics.helicsFederateGetInputCount(hFed)
    # for i in range(pubCount):
    #   pub = helics.helicsFederateGetPublicationByIndex(hFed, i)
    #   key = helics.helicsPublicationGetName (pub)
    #   print ('** Available HELICS publication key', i, key)
    # for i in range(subCount):
    #   sub = helics.helicsFederateGetInputByIndex(hFed, i)
    #   key = helics.helicsInputGetName(sub)
    #   target = helics.helicsSubscriptionGetTarget(sub)
    #   print ('== Available HELICS subscription key', i, key, 'target', target)
    gld_federate = diction['GridLABD']
    sub_federate = helics.helicsFederateGetName(hFed)
    tso_federate = 'pypower'

    bus = ''.join(ele for ele in sub_federate if ele.isdigit())
    # print('subLMP -> ' + tso_federate + '/LMP_' + bus, flush=True)
    subFeeder = helics.helicsFederateGetSubscription(hFed, gld_federate + '/distribution_load')
    subLMP = helics.helicsFederateGetSubscription(hFed, tso_federate + '/LMP_' + bus)
    pubC1 = helics.helicsFederateGetPublication(hFed, sub_federate + '/responsive_c1')
    pubC2 = helics.helicsFederateGetPublication(hFed, sub_federate + '/responsive_c2')
    pubDeg = helics.helicsFederateGetPublication(hFed, sub_federate + '/responsive_deg')
    pubMax = helics.helicsFederateGetPublication(hFed, sub_federate + '/responsive_max_mw')
    pubUnresp = helics.helicsFederateGetPublication(hFed, sub_federate + '/unresponsive_mw')
    pubAucPrice = helics.helicsFederateGetPublication(hFed, sub_federate + '/clear_price')

    pubSubMeters = set()
    hvacObjs = {}
    hvac_keys = list(diction['controllers'].keys())
    for key in hvac_keys:
        row = diction['controllers'][key]
        hvacObjs[key] = hvac(row, key, aucObj)
        ctl = hvacObjs[key]
        hseSubTopic = gld_federate + '/' + ctl.houseName
        mtrSubTopic = gld_federate + '/' + ctl.meterName
        ctlPubTopic = ctl.name
        mtrPubTopic = ctl.name + '/' + ctl.meterName
        # print('{:s} hseSub={:s} mtrSub={:s}  mtrPub={:s}  ctlPub={:s}'
        #       .format(key, hseSubTopic, mtrSubTopic, mtrPubTopic, ctlPubTopic), flush=True)
        subTemp[ctl] = helics.helicsFederateGetSubscription(hFed, hseSubTopic + '#air_temperature')
        subState[ctl] = helics.helicsFederateGetSubscription(hFed, hseSubTopic + '#power_state')
        subHVAC[ctl] = helics.helicsFederateGetSubscription(hFed, hseSubTopic + '#hvac_load')

        pubHeating[ctl] = helics.helicsFederateGetPublication(hFed, ctlPubTopic + '/heating_setpoint')
        pubCooling[ctl] = helics.helicsFederateGetPublication(hFed, ctlPubTopic + '/cooling_setpoint')
        pubDeadband[ctl] = helics.helicsFederateGetPublication(hFed, ctlPubTopic + '/thermostat_deadband')
        if ctl.meterName not in pubSubMeters:
            pubSubMeters.add(ctl.meterName)
            subVolt[ctl] = helics.helicsFederateGetSubscription(hFed, mtrSubTopic + '#measured_voltage_1')
            pubMtrMode[ctl] = helics.helicsFederateGetPublication(hFed, mtrPubTopic + '/bill_mode')
            pubMtrPrice[ctl] = helics.helicsFederateGetPublication(hFed, mtrPubTopic + '/price')
            pubMtrMonthly[ctl] = helics.helicsFederateGetPublication(hFed, mtrPubTopic + '/monthly_fee')

    helics.helicsFederateEnterExecutingMode(hFed)

    aucObj.initAuction()
    LMP = aucObj.mean
    refload = 0.0
    bSetDefaults = True

    tnext_bid = period - 2 * dt  # 3 * dt  # controllers calculate their final bids
    tnext_agg = period - 2 * dt  # auction calculates and publishes aggregate bid
    tnext_opf = period - 1 * dt  # PYPOWER executes OPF and publishes LMP (no action here)
    tnext_clear = period  # clear the market with LMP
    tnext_adjust = period  # + dt   # controllers adjust setpoints based on their bid and clearing

    time_granted = 0
    time_last = 0
    while time_granted < time_stop:
        nextHELICSTime = int(min([tnext_bid, tnext_agg, tnext_clear, tnext_adjust, time_stop]))
        time_granted = int(helics.helicsFederateRequestTime(hFed, nextHELICSTime))
        time_delta = time_granted - time_last
        time_last = time_granted
        hour_of_day = 24.0 * ((float(time_granted) / 86400.0) % 1.0)
        # print(dt_now, time_delta, timedelta (seconds=time_delta))
        dt_now = dt_now + timedelta(seconds=time_delta)
        day_of_week = dt_now.weekday()
        hour_of_day = dt_now.hour
        # print('STEP', time_last, time_granted, time_stop, time_delta, hour_of_day, day_of_week,
        # tnext_bid, tnext_agg, tnext_opf, tnext_clear, tnext_adjust, flush=True)
        LMP = helics.helicsInputGetDouble(subLMP)
        aucObj.set_lmp(LMP)
        refload = 0.001 * helics.helicsInputGetDouble(subFeeder)  # supposed to be kW?
        aucObj.set_refload(refload)
        for key, obj in hvacObjs.items():
            obj.set_air_temp_from_helics(helics.helicsInputGetDouble(subTemp[obj]))
            if obj in subVolt:
                cval = helics.helicsInputGetComplex(subVolt[obj])
                obj.set_voltage_from_helics(cval)
            obj.set_hvac_load_from_helics(helics.helicsInputGetDouble(subHVAC[obj]))
            obj.set_hvac_state_from_helics(helics.helicsInputGetString(subState[obj]))

        # set the time-of-day schedule
        for key, obj in hvacObjs.items():
            if obj.change_basepoint(hour_of_day, day_of_week):
                helics.helicsPublicationPublishDouble(pubCooling[obj], obj.basepoint)
        if bSetDefaults:
            for key, obj in hvacObjs.items():
                if obj in pubMtrMode:
                    helics.helicsPublicationPublishString(pubMtrMode[obj], 'HOURLY')
                    helics.helicsPublicationPublishDouble(pubMtrMonthly[obj], 0.0)
                helics.helicsPublicationPublishDouble(pubDeadband[obj], obj.deadband)
                helics.helicsPublicationPublishDouble(pubHeating[obj], 60.0)
            bSetDefaults = False
            # print('  SET DEFAULTS', flush=True)

        if time_granted >= tnext_bid:
            aucObj.clear_bids()
            time_key = str(int(tnext_clear))
            controller_metrics[time_key] = {}
            for key, obj in hvacObjs.items():
                bid = obj.formulate_bid()  # bid is [price, quantity, on_state]
                if bid is not None:
                    if bWantMarket:
                        aucObj.collect_bid(bid)
                    controller_metrics[time_key][obj.name] = [bid[0], bid[1]]
            tnext_bid += period
            # print('  COLLECT BIDS', flush=True)

        if time_granted >= tnext_agg:
            aucObj.aggregate_bids()
            helics.helicsPublicationPublishDouble(pubUnresp, aucObj.agg_unresp)
            helics.helicsPublicationPublishDouble(pubMax, aucObj.agg_resp_max)
            helics.helicsPublicationPublishDouble(pubC2, aucObj.agg_c2)
            helics.helicsPublicationPublishDouble(pubC1, aucObj.agg_c1)
            helics.helicsPublicationPublishInteger(pubDeg, aucObj.agg_deg)
            tnext_agg += period
            # print('  AGGREGATE BIDS', flush=True)

        if time_granted >= tnext_clear:
            if bWantMarket:
                aucObj.clear_market(tnext_clear, time_granted)
                aucObj.surplusCalculation(tnext_clear, time_granted)
                helics.helicsPublicationPublishDouble(pubAucPrice, aucObj.clearing_price)
                for key, obj in hvacObjs.items():
                    obj.inform_bid(aucObj.clearing_price)
            time_key = str(int(tnext_clear))
            auction_metrics[time_key] = {
                aucObj.name: [aucObj.clearing_price, aucObj.clearing_type, aucObj.consumerSurplus,
                              aucObj.averageConsumerSurplus, aucObj.supplierSurplus]}
            tnext_clear += period
            # print('  CLEARED MARKET', flush=True)

        if time_granted >= tnext_adjust:
            if bWantMarket:
                for key, obj in hvacObjs.items():
                    if obj in pubMtrPrice:
                        helics.helicsPublicationPublishDouble(pubMtrPrice[obj], aucObj.clearing_price)
                    if obj.bid_accepted():
                        helics.helicsPublicationPublishDouble(pubCooling[obj], obj.setpoint)
            tnext_adjust += period
            # print('  ADJUSTED', flush=True)

    # ==================== Finalize the metrics output ===========================

    print('writing metrics', flush=True)
    auction_op = open('auction_' + metrics_root + '_metrics.json', 'w')
    controller_op = open('controller_' + metrics_root + '_metrics.json', 'w')
    print(json.dumps(auction_metrics), file=auction_op)
    print(json.dumps(controller_metrics), file=controller_op)
    auction_op.close()
    controller_op.close()
    print('finalizing HELICS', flush=True)
    helics.helicsFederateDestroy(hFed)


def fncs_substation_loop(configfile, metrics_root, hour_stop, flag):
    """Helper function that initializes and runs the agents

    Reads configfile. Writes *auction_metrics_root_metrics.json* and
    *controller_metrics_root_metrics.json* upon completion.

    Args:
        configfile (str): fully qualified path to the JSON agent configuration file
        metrics_root (str): base name of the case for metrics output
        hour_stop (float): number of hours to simulation
        flag (str): WithMarket or NoMarket to use the simple_auction, or not
    """
    print('starting FNCS substation loop', configfile, metrics_root, hour_stop, flag, flush=True)
    print('##,tnow,tclear,ClearType,ClearQ,ClearP,BuyCount,BuyUnresp,BuyResp,' +
          'SellCount,SellUnresp,SellResp,MargQ,MargFrac,LMP,RefLoad,' +
          'ConSurplus,AveConSurplus,SupplierSurplus,UnrespSupplierSurplus', flush=True)
    bWantMarket = True
    if flag == 'NoMarket':
        bWantMarket = False
        print('Disabled the market', flush=True)
    time_stop = int(hour_stop * 3600)  # simulation time in seconds
    StartTime = '2013-07-01 00:00:00 -0800'
    time_fmt = '%Y-%m-%d %H:%M:%S %z'
    dt_now = datetime.strptime(StartTime, time_fmt)

    # ====== load the JSON dictionary; create the corresponding objects =========

    lp = open(configfile).read()
    diction = json.loads(lp)

    market_key = list(diction['markets'].keys())[0]  # only using the first market
    market_row = diction['markets'][market_key]
    unit = market_row['unit']

    auction_meta = {'clearing_price': {'units': 'USD', 'index': 0},
                    'clearing_type': {'units': '[0..5]=[Null,Fail,Price,Exact,Seller,Buyer]', 'index': 1},
                    'consumer_surplus': {'units': 'USD', 'index': 2},
                    'average_consumer_surplus': {'units': 'USD', 'index': 3},
                    'supplier_surplus': {'units': 'USD', 'index': 4}}
    controller_meta = {'bid_price': {'units': 'USD', 'index': 0}, 'bid_quantity': {'units': unit, 'index': 1}}
    auction_metrics = {'Metadata': auction_meta, 'StartTime': StartTime}
    controller_metrics = {'Metadata': controller_meta, 'StartTime': StartTime}

    aucObj = simple_auction(market_row, market_key)

    dt = float(diction['dt'])
    period = aucObj.period

    # to dispatch incoming FNCS messages; 0..5 for LMP, Feeder load, airtemp, mtr volts, hvac load, hvac state
    topicMap = {'LMP': [aucObj, 0],
                'refload': [aucObj, 1]}

    hvacObjs = {}
    hvac_keys = list(diction['controllers'].keys())
    for key in hvac_keys:
        row = diction['controllers'][key]
        hvacObjs[key] = hvac(row, key, aucObj)
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

    tnext_bid = period - 2 * dt  # 3 * dt  # controllers calculate their final bids
    tnext_agg = period - 2 * dt  # auction calculates and publishes aggregate bid
    tnext_opf = period - 1 * dt  # PYPOWER executes OPF and publishes LMP (no action here)
    tnext_clear = period  # clear the market with LMP
    tnext_adjust = period  # + dt   # controllers adjust setpoints based on their bid and clearing

    time_granted = 0
    time_last = 0
    while time_granted < time_stop:
        nextFNCSTime = int(min([tnext_bid, tnext_agg, tnext_clear, tnext_adjust, time_stop]))
        fncs.update_time_delta(nextFNCSTime - time_granted)
        time_granted = fncs.time_request(nextFNCSTime)
        time_delta = time_granted - time_last
        time_last = time_granted
        hour_of_day = 24.0 * ((float(time_granted) / 86400.0) % 1.0)
        #        print (dt_now, time_delta, timedelta (seconds=time_delta))
        dt_now = dt_now + timedelta(seconds=time_delta)
        day_of_week = dt_now.weekday()
        hour_of_day = dt_now.hour
        #        print ('  ', time_last, time_granted, time_stop, time_delta, hour_of_day, day_of_week, flush=True)
        # update the data from FNCS messages
        events = fncs.get_events()
        for topic in events:
            value = fncs.get_value(topic)
            row = topicMap[topic]
            if row[1] == 0:
                LMP = parse_magnitude(value)
                aucObj.set_lmp(LMP)
            elif row[1] == 1:
                refload = parse_kw(value)
                aucObj.set_refload(refload)
            elif row[1] == 2:
                row[0].set_air_temp_from_fncs_str(value)
            elif row[1] == 3:
                row[0].set_voltage_from_fncs_str(value)
            elif row[1] == 4:
                row[0].set_hvac_load_from_fncs_str(value)
            elif row[1] == 5:
                row[0].set_hvac_state_from_fncs_str(value)

        # set the time-of-day schedule
        for key, obj in hvacObjs.items():
            if obj.change_basepoint(hour_of_day, day_of_week):
                fncs.publish(obj.name + '/cooling_setpoint', obj.basepoint)
        if bSetDefaults:
            for key, obj in hvacObjs.items():
                fncs.publish(obj.name + '/bill_mode', 'HOURLY')
                fncs.publish(obj.name + '/monthly_fee', '0.0')
                fncs.publish(obj.name + '/thermostat_deadband', obj.deadband)
                fncs.publish(obj.name + '/heating_setpoint', '60.0')
            bSetDefaults = False

        if time_granted >= tnext_bid:
            aucObj.clear_bids()
            time_key = str(int(tnext_clear))
            controller_metrics[time_key] = {}
            for key, obj in hvacObjs.items():
                bid = obj.formulate_bid()  # bid is [price, quantity, on_state]
                if bid is not None:
                    if bWantMarket:
                        aucObj.collect_bid(bid)
                    controller_metrics[time_key][obj.name] = [bid[0], bid[1]]
            tnext_bid += period

        if time_granted >= tnext_agg:
            aucObj.aggregate_bids()
            fncs.publish('unresponsive_mw', aucObj.agg_unresp)
            fncs.publish('responsive_max_mw', aucObj.agg_resp_max)
            fncs.publish('responsive_c2', aucObj.agg_c2)
            fncs.publish('responsive_c1', aucObj.agg_c1)
            fncs.publish('responsive_deg', aucObj.agg_deg)
            tnext_agg += period

        if time_granted >= tnext_clear:
            if bWantMarket:
                aucObj.clear_market(tnext_clear, time_granted)
                aucObj.surplusCalculation(tnext_clear, time_granted)
                fncs.publish('clear_price', aucObj.clearing_price)
                for key, obj in hvacObjs.items():
                    obj.inform_bid(aucObj.clearing_price)
            time_key = str(int(tnext_clear))
            auction_metrics[time_key] = {
                aucObj.name: [aucObj.clearing_price, aucObj.clearing_type, aucObj.consumerSurplus,
                              aucObj.averageConsumerSurplus, aucObj.supplierSurplus]}
            tnext_clear += period
        #            print ('garbage collecting at', time_granted, 'finds', gc.collect(), 'unreachable objects', flush=True)

        if time_granted >= tnext_adjust:
            if bWantMarket:
                for key, obj in hvacObjs.items():
                    fncs.publish(obj.name + '/price', aucObj.clearing_price)
                    if obj.bid_accepted():
                        fncs.publish(obj.name + '/cooling_setpoint', obj.setpoint)
            tnext_adjust += period

    # ==================== Finalize the metrics output ===========================

    print('writing metrics', flush=True)
    auction_op = open('auction_' + metrics_root + '_metrics.json', 'w')
    controller_op = open('controller_' + metrics_root + '_metrics.json', 'w')
    print(json.dumps(auction_metrics), file=auction_op)
    print(json.dumps(controller_metrics), file=controller_op)
    auction_op.close()
    controller_op.close()

    print('finalizing FNCS', flush=True)
    fncs.finalize()


def substation_loop(configfile, metrics_root, hour_stop=48, flag='WithMarket', helicsConfig=None):
    """Wrapper for *inner_substation_loop*

    When *inner_substation_loop* finishes, timing and memory metrics will be printed
    for non-Windows platforms.
    """
    if helicsConfig is not None:
        helics_substation_loop(configfile, metrics_root, hour_stop, flag, helicsConfig)
    else:
        fncs_substation_loop(configfile, metrics_root, hour_stop, flag)

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
    # substation_loop('C:\\Users\\wang690\\Desktop\\projects\\TESP\\tesp_1st\\ercot\\case8\\Bus1_agent_dict.json','Bus1',24)
    # substation_loop('TE_Challenge_agent_dict.json', 'TE_ChallengeH0', helicsConfig='TE_Challenge_substation.json', flag='NoMarket')
    # substation_loop('SGIP1b_agent_dict.json', 'SGIP1a', flag='NoMarket', helicsConfig='SGIP1a_substation.json')
    substation_loop('Test_agent_dict.json', 'Test', helicsConfig='Test_substation.json')
