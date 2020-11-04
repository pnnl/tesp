/*  Copyright (C) 2017-2020 Battelle Memorial Institute */
#include "config.h"
#include "consensus.h"
//#include <fstream>
#include <iostream>
#include <vector>
#include <set>
#include <json/json.h>

using namespace ::std;

Building::Building (Json::Value::const_iterator itr) {
  Json::Value bldg = *itr;
  name = itr.key().asString();
  k = bldg["k"].asDouble();
  kWScale = bldg["kWScale"].asDouble();
  Json::Value jT = bldg["dT"];
  Json::Value jP = bldg["dP"];
  n = jP.size();
  dP = new double [n];
  dT = new double [n];
  bid_p = new double[n];
  bid_q = new double[n];
  for (int i = 0; i < n; i++) {
    dP[i] = jP[i].asDouble();
    dT[i] = jT[i].asDouble();
    bid_p[i] = k * dT[i];
    bid_q[i] = kWScale * dP[i];
  }
}

double Building::load_at_price (double p) {
  if (p <= bid_p[0]) return bid_q[0];
  if (p >= bid_p[n-1]) return bid_q[n-1];
  for (int i = 1; i < n; i++) {
    if (p <= bid_p[i]) {
      double m = (bid_q[i] - bid_q[i-1]) / (bid_p[i] - bid_p[i-1]);
      return bid_q[i-1] + m * (p - bid_p[i-1]);
    }
  }
  return 0.0;
}

double Building::degF_at_load (double q) { // bid_q is decreasing into larger negative numbers
  q /= kWScale;
  if (q >= dP[0]) return dT[0];
  if (q <= dP[n-1]) return dT[n-1];
  for (int i = 1; i < n; i++) {
    if (q >= dP[i]) {
      double m = (dT[i] - dT[i-1]) / (dP[i] - dP[i-1]);
      return dT[i-1] + m * (q - dP[i-1]);
    }
  }
  return 0.0;
}

Building::Building (string a_name, double a_k, double a_kWScale, double *a_dP, double *a_dT, int a_size) {
  name = a_name;
  k = a_k;
  kWScale = a_kWScale;
  dP = a_dP;
  dT = a_dT;
  n = a_size;
  bid_p = new double[n];
  bid_q = new double[n];
  for (int i = 0; i < n; i++) {
    bid_p[i] = k * dT[i];
    bid_q[i] = kWScale * dP[i];
  }
}

Building::~Building() {
  delete[] bid_p;
  delete[] bid_q;
}

void Building::display () {
  cout << "Building " << name << endl;
  cout << "  k = " << k << endl;
  cout << "  kWScale = " << kWScale << endl;
  cout << "  idx    dP[i]    dT[i]  bidP[i]  bidQ[i]" << endl;
  for (int i = 0; i < n; i++) {
    cout << "  " << i << " " << dP[i] << "  " << dT[i] << "  " << bid_p[i] << "  " << bid_q[i] << endl;
  }
}

double Consensus::clear_offer (double offer) {
  vector<double> qnet;
  int n = qload.size();
  for (int i = 0; i < n; i++) {
    qnet.push_back (-1.0 * (qload[i] + offer)); // should be increasing
  }
  if (qnet[0] > 0.0) return pload[0];
  if (qnet[n-1] < 0.0) return pload[n-1];
  for (int i = 1; i < n; i++) {
    if (qnet[i] >= 0.0) {
      double m = (pload[i] - pload[i-1]) / (qnet[i] - qnet[i-1]);
      return pload[i-1] + m * (0.0 - qnet[i-1]);
    }
  }
  return 0.0;
}

void Consensus::collect_building_prices (Building *pBldg) {
  for (int i = 0; i < pBldg->n; i++) {
    psorted.insert(pBldg->bid_p[i]);
  }
}

void Consensus::initialize_building_loads () {
  for (set<double>::iterator it = psorted.begin(); it != psorted.end(); ++it) {
    pload.push_back (*it);
    qload.push_back (0.0);
  }
}

void Consensus::add_building_loads (Building *pBldg) {
  for (int i = 0; i < pload.size(); i++) {
    qload[i] += pBldg->load_at_price (pload[i]);
  }
}

Consensus::Consensus (vector<Building *> vBuildings) {
  for (int i = 0; i < vBuildings.size(); i++) {
    collect_building_prices (vBuildings[i]);
  }
  initialize_building_loads();
  for (int i = 0; i < vBuildings.size(); i++) {
    add_building_loads (vBuildings[i]);
  }
}

void Consensus::display () {
  cout << "Consensus Market Composite Load Price, Quantity" << endl;
  for (int i = 0; i < pload.size(); i++) {
    cout << pload[i] << " " << qload[i] << endl;
  }
}

