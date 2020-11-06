/*  Copyright (C) 2017-2020 Battelle Memorial Institute */
#ifndef PNNL_CONSENSUS
#define PNNL_CONSENSUS

#include "config.h"
#include <string>
#include <vector>
#include <set>
#include <map>
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

  Building (std::string a_name, double a_k, double a_kWScale, double *a_dP, double *a_dT, int a_size);
  Building (std::string a_name, double a_k, double a_kWScale, Json::Value &jdP, Json::Value &jdT);
  Building (Json::Value::const_iterator itr);
  ~Building ();

  void display ();
  double load_at_price (double p);
  double degF_at_load (double q);
};

typedef std::map<std::string,std::vector<double>> mvpq_t;

class Consensus {
private:
  bool bDirty;
  std::vector<double> pload;
  std::vector<double> qload;
  mvpq_t mvpq;

  void add_local_building (Building *pBldg);
  double load_at_price (double p, std::vector<double> &vpq);
  void update_building_loads ();

public:
  Consensus (std::vector<Building *> vBaseBuildings);
  Consensus (Building *pBaseBldg);

  void display ();
  double clear_offer (double offer_kw);
  void add_remote_building (std::string &key, std::vector<double> &vpq);
};
#endif
