/*  Copyright (C) 2017-2020 Battelle Memorial Institute */
#ifndef PNNL_CONSENSUS
#define PNNL_CONSENSUS

#include "config.h"
#include <string>
#include <vector>
#include <set>
#include <json/json.h>

class Building {
private:
  void fill_arrays_from_json (Json::Value &jdP, Json::Value &jdT);
public:
  std::string name;
  double k;
  double kWScale;
  double *dP;
  double *dT;
  double *bid_p;
  double *bid_q;
  int n;

  double load_at_price (double p);
  double degF_at_load (double q);
  Building (std::string a_name, double a_k, double a_kWScale, double *a_dP, double *a_dT, int a_size);
  Building (std::string a_name, double a_k, double a_kWScale, Json::Value &jdP, Json::Value &jdT);
  Building (Json::Value::const_iterator itr);
  ~Building ();
  void display ();
};

class Consensus {
  std::set<double> psorted;
public:
  std::vector<double> pload;
  std::vector<double> qload;

  double clear_offer (double offer);
  void collect_building_prices (Building *pBldg);
  void initialize_building_loads ();
  void add_building_loads (Building *pBldg);
  Consensus (std::vector<Building *> vBuildings);
  Consensus (Building *pBldg);
  void display ();
};
#endif
