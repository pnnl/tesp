import sys
import os
import json
import numpy as np

bldgs = {'LargeOffice':{'kW':1716.4, 'k':25.0,
                        'dT':np.array([0.0, 0.99, 1.99, 2.99, 4.99]),
                        'dP':np.array([0.0,-17.21,-26.64,-30.94,-35.31])},
         'MidriseApartment':{'kW':54.1, 'k':20.0,
                        'dT':np.array([0.0, 0.99, 1.99, 2.99, 4.99]),
                        'dP':np.array([0.0,-5.45,-10.63,-14.69,-20.45])},
         'StandaloneRetail':{'kW':135.5, 'k':30.0,
                        'dT':np.array([0.0, 0.99, 1.99, 2.99, 4.99]),
                        'dP':np.array([0.0,-4.31,-8.61,-12.91,-20.98])}}

def load_bid (dT, dP, k, scale):
    bid = {'q': scale * np.array (dP), 'p': k * np.array(dT)}
    return bid

def interpolate_pq (x, ax, ay):
    return np.interp (x, ax, ay)

if __name__ == '__main__':
#  print (bldgs)
  supply = 60.0
  price = 0.2

  pset = set()
  bids = {}

  for key, row in bldgs.items():
      bid = load_bid (row['dT'], row['dP'], row['k'], 1.0)
      bids[key] = bid
      print ('{:20s} quantity = '.format (key), bid['q'])
      print ('{:20s}    price = '.format (' '), bid['p'])
      for p in bid['p']:
          pset.add(p)

  pload = np.array (sorted(pset))
  qload = np.zeros (len(pload))
  print ('   pload    qload')
  for i in range(len(pload)):
      for key, row in bids.items():
          qload[i] += interpolate_pq (pload[i], row['p'], row['q'])
      print ('{:8.2f} {:8.2f}'.format (pload[i], qload[i]))

  qnet = qload + supply
  print ('   pload     qnet')
  for i in range(len(pload)):
      print ('{:8.2f} {:8.2f}'.format (pload[i], qnet[i]))

  pclear = np.interp (0.0, -qnet, pload)
  print ('clearing price = {:.3f}'.format (pclear))

  qtotal = 0.0
  print ('Building             qcleared')
  for key, row in bids.items():
      qval = abs (np.interp (pclear, row['p'], row['q']))
      qtotal += qval
      print ('{:20s} {:8.2f}'.format (key, qval))

  print ('Total Cleared Load = {:8.2f} for Supply = {:8.2f}'.format (qtotal, supply))
