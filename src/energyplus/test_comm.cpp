/*  Copyright (C) 2017-2020 Battelle Memorial Institute */
#include "config.h"
#include <fstream>
#include <iostream>
#include <vector>
#include <set>
#include <iomanip>
#include <json/json.h>
#include "consensus.h"

using namespace ::std;

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

