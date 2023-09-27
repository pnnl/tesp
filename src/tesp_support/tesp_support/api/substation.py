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

import json
import helics
from datetime import datetime
from datetime import timedelta

from tesp_support.original.hvac_agent import hvac
from tesp_support.original.simple_auction import simple_auction
from tesp_support.api.bench_profile import bench_profile

@bench_profile
def substation_loop(configfile, metrics_root, helicsConfig, hour_stop=48, flag='WithMarket'):
    """ Helper function that initializes and runs the agents

    Reads configfile. Writes *auction_metrics_root_metrics.json* and
    *controller_metrics_root_metrics.json* upon completion.

    Args:
        configfile (str): fully qualified path to the JSON agent configuration file
        metrics_root (str): base name of the case for metrics output
        hour_stop (float): number of hours to simulation
        flag (str): WithMarket or NoMarket to use the simple_auction, or not
        helicsConfig:
    """
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
    #   target = helics.helicsInputGetTarget(sub)
    #   print ('== Available HELICS subscription key', i, key, 'target', target)
    gld_federate = diction['GridLABD']
    sub_federate = helics.helicsFederateGetName(hFed)
    tso_federate = 'pypower'

    bus = ''.join(ele for ele in sub_federate if ele.isdigit())
    # print('subLMP -> ' + tso_federate + '/LMP_' + bus, flush=True)
    subFeeder = helics.helicsFederateGetInputByTarget(hFed, gld_federate + '/distribution_load')
    subLMP = helics.helicsFederateGetInputByTarget(hFed, tso_federate + '/LMP_' + bus)
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
        subTemp[ctl] = helics.helicsFederateGetInputByTarget(hFed, hseSubTopic + '#air_temperature')
        subState[ctl] = helics.helicsFederateGetInputByTarget(hFed, hseSubTopic + '#power_state')
        subHVAC[ctl] = helics.helicsFederateGetInputByTarget(hFed, hseSubTopic + '#hvac_load')

        pubHeating[ctl] = helics.helicsFederateGetPublication(hFed, ctlPubTopic + '/heating_setpoint')
        pubCooling[ctl] = helics.helicsFederateGetPublication(hFed, ctlPubTopic + '/cooling_setpoint')
        pubDeadband[ctl] = helics.helicsFederateGetPublication(hFed, ctlPubTopic + '/thermostat_deadband')
        if ctl.meterName not in pubSubMeters:
            pubSubMeters.add(ctl.meterName)
            subVolt[ctl] = helics.helicsFederateGetInputByTarget(hFed, mtrSubTopic + '#measured_voltage_1')
            pubMtrMode[ctl] = helics.helicsFederateGetPublication(hFed, mtrPubTopic + '/bill_mode')
            pubMtrPrice[ctl] = helics.helicsFederateGetPublication(hFed, mtrPubTopic + '/price')
            pubMtrMonthly[ctl] = helics.helicsFederateGetPublication(hFed, mtrPubTopic + '/monthly_fee')

    # ==================== Time step looping under HELICS ===========================

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
        if helics.helicsInputIsUpdated(subLMP):
            LMP = helics.helicsInputGetDouble(subLMP)
            aucObj.set_lmp(LMP)
        if helics.helicsInputIsUpdated(subFeeder):
            refload = 0.001 * helics.helicsInputGetDouble(subFeeder)  # supposed to be kW?
            aucObj.set_refload(refload)
        for key, obj in hvacObjs.items():
            if helics.helicsInputIsUpdated(subTemp[obj]):
                value = helics.helicsInputGetDouble(subTemp[obj])
                obj.set_air_temp_from_helics(value)
                # print('temp ', value, flush=True)
                if obj in subVolt:
                    cval = helics.helicsInputGetComplex(subVolt[obj])
                    obj.set_voltage_from_helics(cval)
                    # print('voltage ', cval, flush=True)
                value = helics.helicsInputGetDouble(subHVAC[obj])
                obj.set_hvac_load_from_helics(value)
                # print('load ', value, flush=True)
                value = helics.helicsInputGetString(subState[obj])
                obj.set_hvac_state_from_helics(value)
                # print('state ', value, flush=True)

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
