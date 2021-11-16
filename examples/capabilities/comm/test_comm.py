# Copyright (C) 2021 Battelle Memorial Institute
# file: test_comm.py

import sys
import json
import math
import numpy as np
import matplotlib.pyplot as plt;

#bldgs = {'Office':{'LoadScale':2.1, 'RampSlope':25.0,
#            'dT':[0.0, 0.99, 1.99, 2.99, 4.99],
#            'dP':[0.0,-17.21,-26.64,-30.94,-35.31]},
#     'Apartments':{'LoadScale':50.0, 'RampSlope':20.0,
#            'dT':[0.0, 0.99, 1.99, 2.99, 4.99],
#            'dP':[0.0,-5.45,-10.63,-14.69,-20.45]},
#     'Shopping':{'LoadScale':31.25, 'RampSlope':30.0,
#            'dT':[0.0, 0.99, 1.99, 2.99, 4.99],
#            'dP':[0.0,-4.31,-8.61,-12.91,-20.98]}}

def load_bid (dT, dP, k, scale):
  bid = {'q': scale * np.array (dP), 'p': k * np.array(dT)}
  return bid

def interpolate_pq (x, ax, ay):
  return np.interp (x, ax, ay)

if __name__ == '__main__':
  print ('usage: python3 test_comm.py 50.0 10.0   plots the reponse to variable supply offers 50 +/- 10')
  print ('       python3 test_comm.py 70          tabulates the reponse to one supply offer of 70')
  print ('       python3 test_comm.py             tabulates the reponse to one default supply offer of 60')
  print ('       reads building load and bidding definitions from BldgDef.json')

  fp = open ('BldgDef.json', 'r')
  bldgs = json.load (fp)
  fp.close()

  print ('Summary of Buildings:')
  for bldg, row in bldgs.items():
    print ('  ', bldg, row)

# fp = open ('BldgDef.json', 'w')
# json.dump (bldgs, fp, indent=2)
# fp.close()

  # make python arrays into Numpy arrays
  for bldg, row in bldgs.items():
    row['dT'] = np.array (row['dT'])
    row['dP'] = np.array (row['dP'])

  # build the composite load bid curve
  pset = set()
  bids = {}

  print ('Building Bid Curves:')
  for key, row in bldgs.items():
    bid = load_bid (row['dT'], row['dP'], row['RampSlope'], row['LoadScale'])
    bids[key] = bid
    print ('  {:20s} quantity = '.format (key), bid['q'])
    print ('  {:20s}  price = '.format (' '), bid['p'])
    for p in bid['p']:
      pset.add(p)

  print ('Composite Load Bid Curve:')
  pload = np.array (sorted(pset))
  qload = np.zeros (len(pload))
  print ('     pload    qload')
  for i in range(len(pload)):
    for key, row in bids.items():
      qload[i] += interpolate_pq (pload[i], row['p'], row['q'])
    print ('  {:8.2f} {:8.2f}'.format (pload[i], qload[i]))

  supply = 60.0
  if len(sys.argv) > 2:  # plotting results
    mean = float(sys.argv[1])
    ampl = float(sys.argv[2])
    hrs = np.linspace (0.0, 24.0, 200)
    offers = -ampl * np.cos (2.0 * math.pi * hrs / 24.0) + mean
    price = np.zeros(len(hrs))
    total = np.zeros(len(hrs))

    bldg_plot = {}
    clrs = ['red', 'green', 'blue', 'magenta', 'orange']
    iclr = 0
    for key in bldgs:
      bldg_plot[key] = {'clr':clrs[iclr], 'qcleared':np.zeros(len(hrs)), 'dTemp':np.zeros(len(hrs))}
      iclr += 1

    for i in range(len(hrs)):
      supply = offers[i]
      qnet = qload + supply
      price[i] = np.interp (0.0, -qnet, pload)
      for key, row in bids.items():
        qval = abs (np.interp (price[i], row['p'], row['q']))
        total[i] += qval
        bldg_plot[key]['qcleared'][i] = qval
        bldg = bldgs[key]
        dTemp = np.interp (qval, -bldg['dP']*bldg['LoadScale'], bldg['dT'])
        bldg_plot[key]['dTemp'][i] = dTemp

    fig, ax = plt.subplots(1, 3, figsize=(18,8))

    ax[0].set_title ('Offer and Loads')
    ax[0].set_ylabel('MW')
    ax[0].plot(hrs, offers, label='Offer', color='black')
    ax[0].plot(hrs, total, label='Total', color='magenta')
    for key, row in bldg_plot.items():
      ax[0].plot(hrs, row['qcleared'], label=key, color=row['clr'])

    ax[1].set_title ('Prices')
    ax[1].set_ylabel('$/MWh')
    ax[1].plot(hrs, price, label='Cleared', color='black')

    ax[2].set_title ('Thermostat Changes')
    ax[2].set_ylabel('degF')
    for key, row in bldg_plot.items():
      ax[2].plot(hrs, row['dTemp'], label=key, color=row['clr'])

    for i in range(3):
      ax[i].grid (linestyle = '-')
      ax[i].set_xlim(0.0, 24.0)
      ax[i].set_xticks([0,4,8,12,16,20,24])
      ax[i].set_xlabel('Hours')
      ax[i].legend(loc='best')

    plt.show()
  else:  # spot-checking one offer
    if len(sys.argv) > 1:
      supply = float(sys.argv[1])

    print ('Net Bid Curve:')
    qnet = qload + supply
    print ('     pload     qnet')
    for i in range(len(pload)):
      print ('  {:8.2f} {:8.2f}'.format (pload[i], qnet[i]))

    pclear = np.interp (0.0, -qnet, pload)
    print ('Clearing price = {:.3f} for Supply = {:.2f}'.format (pclear, supply))

    qtotal = 0.0
    print ('  Building             qcleared  deltaT')
    for key, row in bids.items():
      qval = abs (np.interp (pclear, row['p'], row['q']))
      bldg = bldgs[key]
      dTemp = np.interp (qval, -bldg['dP']*bldg['LoadScale'], bldg['dT'])
      qtotal += qval
      print ('  {:20s} {:8.2f} {:7.2f}'.format (key, qval, dTemp))

    print ('Total Cleared Load = {:.2f} for Supply = {:.2f}'.format (qtotal, supply))
