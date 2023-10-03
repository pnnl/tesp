/*  Copyright (c) 2017-2023 Battelle Memorial Institute
*  file: consensus.cpp
*/
#include "config.h"
#include <iostream>
#include <vector>
#include <set>
#include <iomanip>
#include <json/json.h>
#include "consensus.h"

using namespace ::std;

void Building::fill_arrays_from_json (Json::Value &jdP, Json::Value &jdT) {
  n = jdP.size();
  dP = new double [n];
  dT = new double [n];
  bid_p = new double[n];
  bid_q = new double[n];
  for (int i = 0; i < n; i++) {
    dP[i] = jdP[i].asDouble();
    dT[i] = jdT[i].asDouble();
    bid_p[i] = k * dT[i];
    bid_q[i] = kWScale * dP[i];
  }
}

Building::Building (Json::Value::const_iterator itr) {
  Json::Value bldg = *itr;
  name = itr.key().asString();
  k = bldg["RampSlope"].asDouble();
  kWScale = bldg["LoadScale"].asDouble();
  Json::Value jdP = bldg["dP"];
  Json::Value jdT = bldg["dT"];
  fill_arrays_from_json (jdP, jdT);
}

Building::Building (std::string a_name, double a_k, double a_kWScale, Json::Value &jdP, Json::Value &jdT) {
  name = a_name;
  k = a_k;
  kWScale = a_kWScale;
  fill_arrays_from_json (jdP, jdT);
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
  cout << fixed << showpoint << setprecision(2);
  cout << "Building: " << name << endl;
  cout << "  RampSlope = " << k << endl;
  cout << "  LoadScale = " << kWScale << endl;
  cout << "  idx       dP[i]       dT[i]     bidP[i]     bidQ[i]" << endl;
  for (int i = 0; i < n; i++) {
    cout << setw(5) << i;
    cout << setw(12) << dP[i];
    cout << setw(12) << dT[i];
    cout << setw(12) << bid_p[i];
    cout << setw(12) << bid_q[i] << endl;
  }
}

///////////////////////////////////////////////////////////////////////////////

double Consensus::clear_offer (double offer_kw) {
  if (bDirty) {
    update_building_loads();
  }
  vector<double> qnet;
  int n = qload.size();
  for (int i = 0; i < n; i++) {
    qnet.push_back (-1.0 * (qload[i] + offer_kw)); // should be increasing
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

double Consensus::load_at_price (double p, vector<double> &vpq) {
  int n = vpq.size();  // interleaved pq pairs; bid_p = vpq[0,2,4,...,n-2] and bid_q = vpq[1,3,5,...,n-1]
  if (p <= vpq[0]) return vpq[1];
  if (p >= vpq[n-2]) return vpq[n-1];
  for (int i = 2; i < n; i += 2) {  // bid_p = vpq[i] and bid_q = vpq[i+1]
    if (p <= vpq[i]) {
      double m = (vpq[i+1] - vpq[i-1]) / (vpq[i] - vpq[i-2]);
      return vpq[i-1] + m * (p - vpq[i-2]);
    }
  }
  return 0.0;
}

void Consensus::update_building_loads () {
  qload.clear();
  pload.clear();
  std::set<double> psorted;

  // find all of the prices used
  for (mvpq_t::iterator it = mvpq.begin(); it != mvpq.end(); ++it) {
    for (int i = 0; i < it->second.size(); i += 2) {
      psorted.insert(it->second[i]);
    }
  }

  // build a sorted list of price-quantity pairs
  for (set<double>::iterator it = psorted.begin(); it != psorted.end(); ++it) {
    pload.push_back (*it);
    qload.push_back (0.0);
  }

  // sum the quantities at each price
  for (mvpq_t::iterator it = mvpq.begin(); it != mvpq.end(); ++it) {
    for (int i = 0; i < qload.size(); ++i) {
      qload[i] += load_at_price (pload[i], it->second);
    }
  }

  bDirty = false;
}

Consensus::Consensus (vector<Building *> vBaseBuildings) : bDirty(true) {
  for (int i = 0; i < vBaseBuildings.size(); i++) {
    add_local_building (vBaseBuildings[i]);
  }
}

Consensus::Consensus (Building *pBaseBldg) : bDirty(true) {
  add_local_building (pBaseBldg);
}

void Consensus::display () {
  if (bDirty) {
    update_building_loads();
  }
  cout << "Consensus Market Composite Load" << endl;
  cout << "     Price  Quantity" << endl;
  cout << fixed << showpoint << setprecision(2);
  for (int i = 0; i < pload.size(); i++) {
    cout << setw(10) << pload[i];
    cout << setw(10) << qload[i] << endl;
  }
  cout << "  Included Buildings:";
  for (mvpq_t::iterator it = mvpq.begin(); it != mvpq.end(); ++it) {
    cout << " " << it->first;
  }
  cout << endl;
}

void Consensus::add_local_building (Building *pBldg) {
  vector<double> vpq;
  for (int i = 0; i < pBldg->n; i++) {
    vpq.push_back (pBldg->bid_p[i]);
    vpq.push_back (pBldg->bid_q[i]);
  }
  mvpq[pBldg->name] = vpq;
  bDirty = true;
}

void Consensus::add_remote_building (std::string &key, std::vector<double> &vpq) {
  cout << "add_remote_building: " << key << endl;
  cout << fixed << showpoint << setprecision(2);
  for (int i = 0; i < vpq.size(); i++) {
    cout << setw(10) << vpq[i];
  }
  cout << endl;

  mvpq[key] = vpq;
  bDirty = true;
}

