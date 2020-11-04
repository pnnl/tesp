/*  Copyright (C) 2017-2020 Battelle Memorial Institute */
#include "config.h"
#include <fstream>
#include <iostream>
#include <vector>
#include <set>
#include <iomanip>
#include <json/json.h>

using namespace ::std;

class Building {
public:
  string name;
  double k;
  double kWScale;
  double *dP;
  double *dT;
  double *bid_p;
  double *bid_q;
  int n;

  double load_at_price (double p) {
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

  double degF_at_load (double q) { // bid_q is decreasing into larger negative numbers
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

  Building (string a_name, double a_k, double a_kWScale, double *a_dP, double *a_dT, int a_size) {
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

  ~Building() {
    delete[] bid_p;
    delete[] bid_q;
  }

  void display () {
    cout << "Building " << name << endl;
    cout << "  k = " << k << endl;
    cout << "  kWScale = " << kWScale << endl;
    cout << "  idx    dP[i]    dT[i]  bidP[i]  bidQ[i]" << endl;
    for (int i = 0; i < n; i++) {
      cout << "  " << i << " " << dP[i] << "  " << dT[i] << "  " << bid_p[i] << "  " << bid_q[i] << endl;
    }
  }
};

class Consensus {
  set<double> psorted;
public:
  vector<double> pload;
  vector<double> qload;

  double clear_offer (double offer) {
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

  void collect_building_prices (Building *pBldg) {
    for (int i = 0; i < pBldg->n; i++) {
      psorted.insert(pBldg->bid_p[i]);
    }
  }

  void initialize_building_loads () {
    for (set<double>::iterator it = psorted.begin(); it != psorted.end(); ++it) {
      pload.push_back (*it);
      qload.push_back (0.0);
    }
  }

  void add_building_loads (Building *pBldg) {
    for (int i = 0; i < pload.size(); i++) {
      qload[i] += pBldg->load_at_price (pload[i]);
    }
  }

  Consensus () {
  }

  void display () {
    cout << "Consensus Market Composite Load Price, Quantity" << endl;
    for (int i = 0; i < pload.size(); i++) {
      cout << pload[i] << " " << qload[i] << endl;
    }
  }
};

void usage ()
{
  cerr << "Usage: test_comm BldgDef.json" << endl;
  exit(EXIT_FAILURE);
}

int main(int argc, char **argv)
{
  if (argc != 2) {
    cerr << "Two required parameters." << endl;
    usage ();
  }

  vector<Building *> vBuildings;
  Consensus market;

  Json::Value root;
  ifstream ifs;
  ifs.open (argv[1]);
  Json::CharReaderBuilder builder;
  JSONCPP_STRING errs;
  if (!parseFromStream(builder, ifs, &root, &errs)) {
    cout << errs << endl;
    return EXIT_FAILURE;
  }
  cout << "configuring from " << argv[1] << endl;
  if (root.size() > 0) {
    for (Json::Value::const_iterator itr = root.begin(); itr != root.end(); itr++) {
      Json::Value bldg = *itr;
      double k = bldg["k"].asDouble();
      double kWScale = bldg["kWScale"].asDouble();
      Json::Value jT = bldg["dT"];
      Json::Value jP = bldg["dP"];
      int asize = jP.size();
      double *dP = new double [asize];
      double *dT = new double [asize];
      for (int i = 0; i < asize; i++) {
        dP[i] = jP[i].asDouble();
        dT[i] = jT[i].asDouble();
      }
      Building *pBldg = new Building (itr.key().asString(), k, kWScale, dP, dT, asize);
      vBuildings.push_back(pBldg);
    }
  } else {
    cerr << "Invalid building definitions in " << argv[1] << endl;
    exit(EXIT_FAILURE);
  }

  for (int i = 0; i < vBuildings.size(); i++) {
    vBuildings[i]->display();
    market.collect_building_prices (vBuildings[i]);
  }
  market.initialize_building_loads();
  for (int i = 0; i < vBuildings.size(); i++) {
    market.add_building_loads (vBuildings[i]);
  }
  market.display();

  // testing output loop for comparison to test_comm.py plot
  cout << fixed << showpoint << setprecision(2);
  cout << "                    ";
  for (int i = 0; i < vBuildings.size(); i++) {
    cout << setw(20) << vBuildings[i]->name;
  }
  cout << endl;
  cout << "     Offer     Price";
  for (int i = 0; i < vBuildings.size(); i++) {
    cout << "   DeltaKW DeltaDegF";
  }
  cout << "   TotLoad" << endl;
  for (double offer = 0.0; offer <= 1901.0; offer += 100.0) {
    double p_clear = market.clear_offer (offer);
    cout << setw(10) << offer;
    cout << setw(10) << p_clear;
    double q_clear = 0.0;
    for (int i = 0; i < vBuildings.size(); i++) {
      double q_bldg = vBuildings[i]->load_at_price (p_clear);
      double t_bldg = vBuildings[i]->degF_at_load (q_bldg);
      q_clear += q_bldg;
      cout << setw(10) << q_bldg;
      cout << setw(10) << t_bldg;
    }
    cout << setw(10) << q_clear << endl;
  }

  for (int i = 0; i < vBuildings.size(); i++) {
    delete vBuildings[i];
  }

  return EXIT_SUCCESS;
}

