# Copyright (C) 2020 Battelle Memorial Institute
import sys
import helics

def helics_loop (tmax, market_period, thresh_kW, max_offset_kW):
  offer_kW = 0.0
  feeder_kW = 0.0
  max_change_kW = 0.1 * max_offset_kW
  hFed = None
  pub_offer = None
  sub_load = None

  hFed = helics.helicsCreateValueFederateFromConfig ('commshedConfig.json')
  fedName = helics.helicsFederateGetName (hFed)
  pubCount = helics.helicsFederateGetPublicationCount (hFed)
  subCount = helics.helicsFederateGetInputCount (hFed)
#  period = int (helics.helicsFederateGetTimeProperty(hFed, helics.HELICS_PROPERTY_TIME_PERIOD))
  period = int (helics.helicsFederateGetTimeProperty(hFed, helics.helics_property_time_period))
  next_market = -period

  print ('Federate {:s} has {:d} pub and {:d} sub, {:d} period, {:d} market_period and {:d} next_market'.format (fedName, 
    pubCount, subCount, period, market_period, next_market), flush=True)

  for i in range(pubCount):
    pub = helics.helicsFederateGetPublicationByIndex (hFed, i)
    key = helics.helicsPublicationGetKey (pub)
    print ('HELICS publication key', i, key)
    if 'offer' in key:
      pub_offer = pub
  for i in range(subCount):
    sub = helics.helicsFederateGetInputByIndex (hFed, i)
    key = helics.helicsInputGetKey (sub)
    target = helics.helicsSubscriptionGetKey (sub)
    print ('HELICS subscription key', i, key, 'target', target)
    if 'distribution_load' in target:
      sub_load = sub
  helics.helicsFederateEnterExecutingMode (hFed)
  print ('### Entering Execution Mode ###')

  ts = 0

  while ts < tmax:
    # some notes on helicsInput timing
    #  1) initial values are garbage until the other federate actually publishes
    #  2) helicsInputIsValid checks the subscription pipeline for validity, but not the value
    #  3) helicsInputIsUpdated resets to False immediately after you read the value, will become True if value changes later
    #  4) helicsInputLastUpdateTime is > 0 only after the other federate published its first value
    if (sub_load is not None) and helics.helicsInputIsUpdated (sub_load) and (ts >= next_market):
      cval = helics.helicsInputGetComplex (sub_load)
      gld_load = complex(cval[0], cval[1])
      feeder_kW = gld_load.real / 1.0e3
      excess_kW = feeder_kW - thresh_kW
      excess_kW *= 0.25
#     if excess_kW > max_change_kW:
#       excess_kW = max_change_kW
#     elif excess_kW < -max_change_kW:
#       excess_kW = -max_change_kW
      if excess_kW > 0.0:
        offer_kW += excess_kW
      elif offer_kW > 0.0:
        offer_kW += excess_kW
      if offer_kW < 0.0:
        offer_kW = 0.0
      if offer_kW > max_offset_kW:
        offer_kW = max_offset_kW
      if pub_offer is not None:
        helics.helicsPublicationPublishDouble (pub_offer, offer_kW)
      print ('{:6d}s Feeder kW={:.2f}, Offer kW={:.2f}'.format (ts, feeder_kW, offer_kW), flush=True)
      next_market += market_period
    ts = int (helics.helicsFederateRequestTime (hFed, tmax))

  helics.helicsFederateDestroy (hFed)

if __name__ == '__main__':
  tmax = 86400
  market_period = 300
  thresh_kW = 12000.0
  max_offset_kW = 2000.0
  if len(sys.argv) > 1:
    tmax = int(sys.argv[1])
  if len(sys.argv) > 2:
    market_period = int(sys.argv[2])
  if len(sys.argv) > 3:
    thresh_kW = float(sys.argv[3])
  if len(sys.argv) > 4:
    max_offset_kW = float(sys.argv[4])
  helics_loop (tmax, market_period, thresh_kW, max_offset_kW)

