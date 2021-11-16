/*  Copyright (C) 2017-2021 Battelle Memorial Institute 
*  file: eplus_agent_helics.cpp
*/

/* autoconf header */
#include "config.h"

/* C++ standard headers */
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <iomanip>
#include <sstream>
#include <string>
#include <utility>
#include <vector>
#include "consensus.h"

/* 3rd party headers */
#include "czmq.h"
#include <json/json.h>

/* helics headers */
#include <helics/application_api/ValueFederate.hpp>
#include <helics/application_api/Inputs.hpp>
#include <helics/application_api/Publications.hpp>
#include <helics/application_api/helicsTypes.hpp>
#include <helics/shared_api_library/api-data.h>
#include <helics/shared_api_library/helics.h>

using namespace ::std;

#define METRICS_MIN 0
#define METRICS_MAX 1
#define METRICS_SUM 2
#define METRICS_CNT 3
#define METRICS_LST 4
#define METRICS_NBR 5 // number of preceding subindices

typedef map<string,double *> metrics_t; // keys to min, max, sum, count

static helics::ValueFederate *pHelicsFederate(nullptr);
string BuildingID = "EnergyPlus Building";
int time_multiplier = 1;

void usage ()
{
  cerr << "Usage 1: eplus_agent_helics ep_agent_config.json" << endl;
  cerr << "Usage 2: eplus_agent_helics <stop time> <agg time> [bldg id] [output file] [ref price] [ramp] [limit hi] [limit lo] [helicsConfig]" << endl;
  exit(EXIT_FAILURE);
}

void reset_metric (double *pVals)
{
  pVals[METRICS_MIN] = DBL_MAX;
  pVals[METRICS_MAX] = -DBL_MAX;
  pVals[METRICS_SUM] = pVals[METRICS_CNT] = pVals[METRICS_LST] = 0.0;
}

void continue_metric (double *pVals)
{
  pVals[METRICS_MIN] = pVals[METRICS_LST];
  pVals[METRICS_MAX] = pVals[METRICS_LST];
  pVals[METRICS_SUM] = pVals[METRICS_CNT] = 0.0;
}

void update_metric (double *pVals, double newval)
{
  pVals[METRICS_LST] = newval;
  if (newval < pVals[METRICS_MIN]) pVals[METRICS_MIN] = newval;
  if (newval > pVals[METRICS_MAX]) pVals[METRICS_MAX] = newval;
  pVals[METRICS_SUM] += newval;
  pVals[METRICS_CNT] += 1.0;
}

void output_metrics (metrics_t metrics, Json::Value& root, Json::Value& ary, int time_granted, ostream& out)
{
  double *pVals;
  string key1 = to_string (time_granted * time_multiplier);  // we want FNCS time, or seconds
  string key2 = BuildingID;
  int idx = 0;
  for (metrics_t::iterator it = metrics.begin(); it != metrics.end(); ++it) {
    pVals = it->second;
    if (pVals[METRICS_CNT] > 0.0) {  // TODO: array has to be the same length each time
      ary[idx++] = pVals[METRICS_SUM] / pVals[METRICS_CNT];
      ary[idx++] = pVals[METRICS_MAX];
      ary[idx++] = pVals[METRICS_MIN];
    } else {
      ary[idx++] = pVals[METRICS_LST];
      ary[idx++] = pVals[METRICS_LST];
      ary[idx++] = pVals[METRICS_LST];
    }
    continue_metric (pVals);
  }
  Json::Value bldg;
  bldg[key2] = ary;
  root[key1] = bldg;
}

unordered_map<string, helics::Publication> mpubs;
unordered_map<string, helics::Input> msubs;

bool aggregate_this_subscription (string key)
{
  if (key.find("bid_curve") != string::npos) return false;
  return true;
}

int main(int argc, char **argv)
{
  // configuration variables to define on command line or in a JSON file
  helics_time time_stop = 0;
  helics_time time_agg = 0;
  double load_scale = 1.0;
  string StartTime = "2012-01-01 00:00:00 PST";
  string HelicsConfigFile = "";
  string MetricsFileName = "";
  double base_price = 0.02;  // next 4 implement real-time pricing response 
  double degF_per_price = 25.0;
  double max_delta_hi = 4.0;
  double max_delta_lo = 4.0;
  bool bUsePriceRamp = true;
  bool bUseConsensus = false;

  helics_time time_granted = 0;
  helics_time time_written = 0;
  vector<string> events;
  vector<string> keys;
  ofstream fout;
  ostream out(cout.rdbuf()); /* share cout's stream buffer */
  Json::Value root;
  Json::Value jsn;
  Json::Value meta;
  metrics_t metrics;
  double *pVals;
  double newval;
  helics::Publication hPubA, hPubB, hPubC, hPubPrice, hPubMode, hPubFee, hCoolDelta, hHeatDelta, hCurve;

  // for the consensus mechanism
  Building *pBldg = nullptr;
  Consensus *pMarket = nullptr;
  bool bPublishBidCurve = false;

  if (argc == 2) {
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
    cout << root << endl;

    StartTime = root["StartTime"].asString();
    MetricsFileName = root["MetricsFileName"].asString();
    HelicsConfigFile = root["HelicsConfigFile"].asString();
    BuildingID = root["BuildingID"].asString();
    time_stop = root["StopSeconds"].asInt();
    time_agg = root["MetricsPeriod"].asInt();
    base_price = root["BasePrice"].asDouble();
    degF_per_price = root["RampSlope"].asDouble();
    max_delta_hi = root["MaxDeltaCool"].asDouble();
    max_delta_lo = root["MaxDeltaHeat"].asDouble();
    load_scale = root["LoadScale"].asDouble();
    bUsePriceRamp = root["UsePriceRamp"].asBool();
    bUseConsensus = root["UseConsensus"].asBool();
    if (root.isMember ("dT") && root.isMember ("dP")) {
      pBldg = new Building (BuildingID, degF_per_price, load_scale, root["dP"], root["dT"]);
      pBldg->display();
      pMarket = new Consensus (pBldg);
      pMarket->display();
      bPublishBidCurve = true;
    }
  } else if (argc < 3) {
    cerr << "Not enough parameters." << endl;
    usage ();
  } else if (argc > 10) {
    cerr << "Too many parameters." << endl;
    usage ();
  } else { // configure from the command line, but StartTime and load_scale not supported this way
    string param_time_stop = argv[1];
    string param_time_agg = argv[2];
    time_stop = helics::getDoubleFromString(param_time_stop);
    time_agg = helics::getDoubleFromString(param_time_agg);
    if (argc > 3) BuildingID = argv[3];
    if (argc > 4) MetricsFileName = argv[4];
    if (argc > 5) base_price = atof (argv[5]);
    if (argc > 6) degF_per_price = atof (argv[6]);
    if (argc > 7) max_delta_hi = atof (argv[7]);
    if (argc > 8) max_delta_lo = atof (argv[8]);
    if (argc > 9) HelicsConfigFile = argv[9];
  }

  fout.open(MetricsFileName.c_str());
  if (!fout) {
    cerr << "Could not open metrics output file '" << MetricsFileName << "'." << endl;
    exit(EXIT_FAILURE);
  }
  out.rdbuf(fout.rdbuf()); /* redirect out to use file buffer */

  // create the required HELICS federate, publications and subscriptions
  bool bPubA = false, bPubB = false, bPubC = false, bPubFee = false, bPubPrice = false, bPubMode = false, bPubCool = false, bPubHeat = false;
  bool bPubCurve = true;
  if (pBldg) bPubCurve = false; // meaning that we must be able to publish our bid curve
  cout << "creating a ValueFederate from '" << HelicsConfigFile << "'" << endl;
  pHelicsFederate = new helics::ValueFederate(HelicsConfigFile);
  int pub_count = pHelicsFederate->getPublicationCount();
  int sub_count = pHelicsFederate->getInputCount();
  cout << " ==> " << pub_count << " publications and " << sub_count << " subscriptions" << endl;
  for (int i = 0; i < pub_count; i++) {
    helics::Publication pub = pHelicsFederate->getPublication(i);
    if (pub.isValid() ) {
      cout << " pub " << i << ":" << pub.getName() << ":" << pub.getKey() << ":" << pub.getType() << ":" << pub.getUnits() << endl;
      auto pubkey = pub.getKey();
      mpubs[pubkey] = pub;
      if (pub.getKey().find("power_A") != string::npos) {
        bPubA = true;
        hPubA = pub;
      } else if (pub.getKey().find("power_B") != string::npos) {
        bPubB = true;
        hPubB = pub;
      } else if (pub.getKey().find("power_C") != string::npos) {
        bPubC = true;
        hPubC = pub;
      } else if (pub.getKey().find("monthly_fee") != string::npos) {
        bPubFee = true;
        hPubFee = pub;
      } else if (pub.getKey().find("price") != string::npos) {
        bPubPrice = true;
        hPubPrice = pub;
      } else if (pub.getKey().find("bill_mode") != string::npos) {
        bPubMode = true;
        hPubMode = pub;
      } else if (pub.getKey().find("cooling_setpoint_delta") != string::npos) {
        bPubCool = true;
        hCoolDelta = pub;
      } else if (pub.getKey().find("heating_setpoint_delta") != string::npos) {
        bPubHeat = true;
        hHeatDelta = pub;
      } else if (pub.getKey().find("bid_curve") != string::npos) {
        bPubCurve = true;
        hCurve = pub;
      }
    }
  } // pub_count
  for (int i = 0; i < sub_count; i++) {
    helics::Input sub = pHelicsFederate->getInput(i);
    if (sub.isValid() ) {
      string thisInfo = string(sub.getInfo());
      cout << "Subscribing to " << thisInfo << endl;
      msubs[thisInfo] = sub;
    }
  }
  if (!bPubA || !bPubB || !bPubC || !bPubFee || !bPubPrice || !bPubMode || !bPubCool || !bPubHeat || !bPubCurve) {
    if (!bPubA) cout << "missing publication for power_A" << endl;
    if (!bPubB) cout << "missing publication for power_B" << endl;
    if (!bPubC) cout << "missing publication for power_C" << endl;
    if (!bPubPrice) cout << "missing publication for (meter) price" << endl;
    if (!bPubFee) cout << "missing publication for (meter) monthly_fee" << endl;
    if (!bPubMode) cout << "missing publication for (meter) bill_mode" << endl;
    if (!bPubCool) cout << "missing publication for cooling_setpoint_delta" << endl;
    if (!bPubHeat) cout << "missing publication for heating_setpoint_delta" << endl;
    if (!bPubCurve) cout << "missing publication for consensus bid curve" << endl;
    exit(EXIT_FAILURE);
  }

  double price = base_price;
  double cooling_delta = 0.0;
  double heating_delta = 0.0;
  double totalWatts = 0.0;
  double phaseWatts = 0.0;
  double delta = 0.0, delta_price = 0.0, delta_offer = 0.0;
  double last_offer_kw = 0.0, offer_kw = 0.0;

  cout << "stops at " << time_stop << " and aggregates at " << time_agg << " in sim time" << endl;
  time_multiplier = 1;
  cout << "multiplier from EnergyPlus to HELICS time is " << time_multiplier << endl;

  // build the list of metrics to accumulate; zone occupants now accumulated within EnergyPlus EMS
  for (auto it = msubs.begin(); it != msubs.end(); ++it) {
    if (!aggregate_this_subscription (it->first)) continue;
    pVals = new double[METRICS_NBR];
    reset_metric (pVals);
    metrics[it->first] = pVals;
    cout << "aggregating " << it->first << endl;
  }
  // add the thermostat deltas and consensus market parameters, which are generated within this agent
  pVals = new double[METRICS_NBR];
  reset_metric (pVals);
  metrics["cooling_setpoint_delta"] = pVals;
  pVals = new double[METRICS_NBR];
  reset_metric (pVals);
  metrics["heating_setpoint_delta"] = pVals;
  if (bUseConsensus) {
    pVals = new double[METRICS_NBR];
    reset_metric (pVals);
    metrics["offer_cleared_price"] = pVals;
    pVals = new double[METRICS_NBR];
    reset_metric (pVals);
    metrics["offer_cleared_kw"] = pVals;
    pVals = new double[METRICS_NBR];
    reset_metric (pVals);
    metrics["offer_cleared_degF"] = pVals;
  }

  // write the simulation start time and metadata
  root.clear();
  meta.clear();
  jsn.clear();
  int idx = 0;
  string units;
  for (metrics_t::iterator it = metrics.begin(); it != metrics.end(); ++it) {
    units = "";
    if ((it->first).find("offer_kw") != string::npos) units = "kW";
    if ((it->first).find("offer_cleared_price") != string::npos) units = "$/mwh";
    if ((it->first).find("offer_cleared_kw") != string::npos) units = "kW";
    if ((it->first).find("offer_cleared_degF") != string::npos) units = "degF";
    if ((it->first).find("temperature") != string::npos) units = "degF";
    if ((it->first).find("setpoint") != string::npos) units = "degF";
    if ((it->first).find("outdoor_air") != string::npos) units = "degF";
    if ((it->first).find("indoor_air") != string::npos) units = "degF";
    if ((it->first).find("volume") != string::npos) units = "m3";
    if ((it->first).find("demand_power") != string::npos) units = "W";
    if ((it->first).find("controlled_load") != string::npos) units = "W";
    if ((it->first).find("hours") != string::npos) units = "hours";
    if ((it->first).find("kwhr_price") != string::npos) units = "$/kwh";
    jsn["units"] = units;
    jsn["index"] = idx++;
    meta[it->first + "_avg"] = jsn; 
    jsn["index"] = idx++;
    meta[it->first + "_max"] = jsn; 
    jsn["index"] = idx++;
    meta[it->first + "_min"] = jsn; 
  }
  root["StartTime"] = StartTime;
  root["LoadScale"] = load_scale;
  root["Metadata"] = meta;

  // construct the array to hold all metrics
  Json::Value ary(Json::arrayValue);
  ary.resize(idx);

  // launch the HELICS federate
  cout << "HELICS enter intializing mode" << endl;
  pHelicsFederate->enterInitializingMode();
  cout << "HELICS enter executing mode" << endl;
  pHelicsFederate->enterExecutingMode();
  helics_time deltaTime = pHelicsFederate->getTimeProperty(helics_property_time_period);
  helics_time nextTime = 0;
  do {
    auto currentTime = pHelicsFederate->getCurrentTime();
    for (auto it = msubs.begin(); it != msubs.end(); ++it ) {
      auto thissub = it->second;
      if (thissub.isUpdated()) {
        if((it->first).find("bid_curve") == 0) {  // no metrics aggregation here
          vector<double> vec = thissub.getValue<vector<double>>();
          cout << fixed << showpoint << setprecision(2);
          cout << "&&& " << it->first << ":" << vec.size() << endl;
          for (int i = 0; i < vec.size(); i++) {
            cout << setw(10) << vec[i];
          }
          cout << endl;
          string key = it->first;
          pMarket->add_remote_building (key, vec);
          pMarket->display();
        } else if ((it->first).find("offer_kw") == 0) { // also aggregate the consensus parameters
          offer_kw = thissub.getValue<double>();
          if (offer_kw != last_offer_kw) {
            if (bUseConsensus) {
              last_offer_kw = offer_kw;
              double cleared_price = pMarket->clear_offer (offer_kw);
              double cleared_load = pBldg->load_at_price (cleared_price);
              delta_offer = pBldg->degF_at_load (cleared_load);
              cout << fixed << showpoint << setprecision(2);
              cout << "&&& new supply reduction offer " << offer_kw << " kW at HELICS time " << time_granted << endl;
              cout << "    clearing price, load, degF change are " << setw(10) << cleared_price;
              cout << setw(10) << cleared_load << setw(10) << delta_offer << endl;
              update_metric (metrics["offer_kw"], offer_kw);
              update_metric (metrics["offer_cleared_kw"], cleared_load);
              update_metric (metrics["offer_cleared_price"], cleared_price);
              update_metric (metrics["offer_cleared_degF"], delta_offer);
            } else {
              cout << "!!! ignoring offer_kw" << endl;
            }
          }
        } else { // metrics from E+ to aggregate
          auto value = thissub.getValue<double>();
          if ((it->first).find("kwhr_price") == 0) {
            price = value;
            cout << "new price " << price << " at HELICS time " << time_granted << endl;
          }
          if ((it->first).find("electric_demand_power") == 0) {
            totalWatts = value;
          }
          if ((it->first).find("outdoor_air") == 0) { // indoor air published from E+ in degF
            value = value * 1.8 + 32.0;
          }
          if((it->first).find("heating_setpoint_temperature") == 0) {
//            cout << it->first << ": " << value << endl;
          }
          if((it->first).find("cooling_setpoint_temperature") == 0) {
//            cout << it->first << ": " << value << endl;
          }
          if (aggregate_this_subscription (it->first)) update_metric(metrics[it->first], value);
        }
      }
    }
    // incorporate the basic ramp and consensus price responses
    if (bUsePriceRamp) {
      delta_price = degF_per_price * (price - base_price);
    }
    delta = delta_price + delta_offer;
    if (delta < -max_delta_lo) {
      delta = -max_delta_lo;
    } else if (delta > max_delta_hi) {
      delta = max_delta_hi;
    }
    cout << fixed << showpoint << setprecision(2);
    cout << "## delta, delta_price, delta_offer = " << setw(10) << delta;
    cout << setw(10) << delta_price << setw(10) << delta_offer << endl;
    update_metric(metrics["cooling_setpoint_delta"], delta);
    update_metric(metrics["heating_setpoint_delta"], -delta);

    if ((time_granted - time_written) >= time_agg) {
      time_written = time_granted;
      output_metrics (metrics, root, ary, (int)time_granted, out);
    }

    phaseWatts = load_scale * totalWatts / 3.0;
    hPubA.publish(phaseWatts);
    hPubB.publish(phaseWatts);
    hPubC.publish(phaseWatts);
    hPubPrice.publish(price);
    hPubFee.publish(0.0);
    hPubMode.publish("HOURLY");
    hCoolDelta.publish(delta);
    hHeatDelta.publish(-delta);
    if (bPublishBidCurve) {
      vector<double> vBidCurve;
      for (int i = 0; i < pBldg->n; i++) {
        vBidCurve.push_back (pBldg->bid_p[i]);
        vBidCurve.push_back (pBldg->bid_q[i]);
      }
      cout << "publishing the bid curve: " << endl;
      cout << fixed << showpoint << setprecision(2);
      for (int i = 0; i < vBidCurve.size(); i++) {
        cout << setw(10) << vBidCurve[i];
      }
      cout << endl;
      hCurve.publish (vBidCurve);
      bPublishBidCurve = false;
    }
    nextTime = currentTime + deltaTime;
    time_granted = pHelicsFederate->requestTime(nextTime);
  } while (time_granted < time_stop);

  if (time_granted > time_written) {
    output_metrics (metrics, root, ary, (int)time_granted, out);
  }
  cout << "last time_granted was " << time_granted << endl;
  cout << "time_stop was " << time_stop << endl;
  cout << "done" << endl;

  out << root << endl;

  fout.close();

  for (auto it = msubs.begin(); it != msubs.end(); ++it ){
    delete [] metrics[it->first];
  }

  if (pBldg) delete pBldg;
  if (pMarket) delete pMarket;

  if (pHelicsFederate) {
    pHelicsFederate->finalize();
    helics::cleanupHelicsLibrary();
  }

  return EXIT_SUCCESS;
}

