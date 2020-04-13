/*	Copyright (C) 2017-2020 Battelle Memorial Institute */
/* autoconf header */
#include "config.h"

/* C++ standard headers */
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

/* 3rd party headers */
#include "czmq.h"
#include <json/json.h>

/* fncs headers */
#include "fncs.hpp"

// #include "fncs_internal.hpp"
namespace fncs {
	/** Converts given time string, e.g., 1s, into a fncs time value. */
	FNCS_EXPORT fncs::time parse_time(const string &value);

	/** Converts given time value, assumed in ns, to sim's unit. */
	FNCS_EXPORT fncs::time convert_broker_to_sim_time(fncs::time value);
}

using namespace ::std;

#define METRICS_MIN 0
#define METRICS_MAX 1
#define METRICS_SUM 2
#define METRICS_CNT 3
#define METRICS_LST 4
#define METRICS_NBR 5 // number of preceding subindices

typedef map<string,double *> metrics_t; // keys to min, max, sum, count

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

string param_bldg_id = "EnergyPlus Building";
fncs::time time_multiplier = 1;

void output_metrics (metrics_t metrics, Json::Value& root, Json::Value& ary, fncs::time time_granted, ostream& out)
{
	double *pVals;
	string key1 = to_string (time_granted * time_multiplier);  // we want FNCS time, or seconds
	string key2 = param_bldg_id;
	int idx = 0;
	for (metrics_t::iterator it = metrics.begin(); it != metrics.end(); ++it) {
		pVals = it->second;
		if (pVals[METRICS_CNT] > 0.0)	{  // TODO: array has to be the same length each time
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

double collect_fncs_values (string key)
{
#if HAVE_STOD
	return stod(fncs::get_value(key));
#else
	return strtod ((fncs::get_value(key)).c_str(), NULL);
#endif
}

int main(int argc, char **argv)
{
	string param_time_stop = "";
	string param_time_agg = "";
	string param_file_name = "";
	fncs::time time_granted = 0;
	fncs::time time_stop = 0;
	fncs::time time_agg = 0;
	fncs::time time_written = 0;
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
	fncs::time mod;
	fncs::time hod;

	// for real-time pricing response - can redefine on the command line
	double base_price = 0.02;
	double degF_per_price = 25.0;
	double max_delta_hi = 4.0;
	double max_delta_lo = 4.0;

	if (argc < 3) {
		cerr << "Missing stop time and/or aggregating time parameters." << endl;
		cerr << "Usage: eplus_agent <stop time> <agg time> [bldg id] [output file] [ref price] [ramp] [limit hi] [limit lo]" << endl;
		exit(EXIT_FAILURE);
	}

	if (argc > 9) {
		cerr << "Too many parameters." << endl;
		cerr << "Usage: eplus_agent <stop time> <agg time> <bldg id> <output file> <ref price> <ramp> <limit hi> <limit lo>" << endl;
		exit(EXIT_FAILURE);
	}

	param_time_stop = argv[1];
	param_time_agg = argv[2];
	if (argc > 3)	param_bldg_id = argv[3];
	if (argc > 4) {
		param_file_name = argv[4];
		fout.open(param_file_name.c_str());
		if (!fout) {
			cerr << "Could not open output file '" << param_file_name << "'." << endl;
			exit(EXIT_FAILURE);
		}
		out.rdbuf(fout.rdbuf()); /* redirect out to use file buffer */
	}
	if (argc > 5) {
		base_price = atof (argv[5]);
	}
	if (argc > 6) {
		degF_per_price = atof (argv[6]);
	}
	if (argc > 7) {
		max_delta_hi = atof (argv[7]);
	}
	if (argc > 8) {
		max_delta_lo = atof (argv[8]);
	}

	double price = base_price;
	double cooling_delta = 0.0;
	double heating_delta = 0.0;
	double totalWatts = 0.0;
	double phaseWatts = 0.0;
	double delta;

	fncs::initialize();

	if (!fncs::is_initialized()) {
		cout << "did not connect to broker, exiting" << endl;
		fout.close();
		return EXIT_FAILURE;
	}

	time_stop = fncs::parse_time(param_time_stop);
	time_stop = fncs::convert_broker_to_sim_time(time_stop);
	time_agg = fncs::parse_time(param_time_agg);
	time_agg = fncs::convert_broker_to_sim_time(time_agg);
	cout << "stops at " << time_stop << " and aggregates at " << time_agg << " in sim time" << endl;
	time_multiplier = fncs::parse_time("1m") / 1000000000; // to output in seconds
	cout << "multiplier from EnergyPlus to FNCS time is " << time_multiplier << endl;

	// build the list of metrics to accumulate; zone occupants now accumulated within EnergyPlus EMS
	keys = fncs::get_keys();
	for (vector<string>::iterator it = keys.begin(); it != keys.end(); ++it) {
		pVals = new double[METRICS_NBR];
		reset_metric (pVals);
		metrics[*it] = pVals;
		cout << "aggregating " << *it << endl;
	}
	// add the thermostat deltas, which are generated within this agent
	pVals = new double[METRICS_NBR];
	reset_metric (pVals);
	metrics["cooling_setpoint_delta"] = pVals;
	pVals = new double[METRICS_NBR];
	reset_metric (pVals);
	metrics["heating_setpoint_delta"] = pVals;

	// write the simulation start time and metadata
	root.clear();
	meta.clear();
	jsn.clear();
	int idx = 0;
	string units;
	for (metrics_t::iterator it = metrics.begin(); it != metrics.end(); ++it) {
		units = "";
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
	root["StartTime"] = "2012-01-01 00:00:00 PST";
	root["Metadata"] = meta;

	// construct the array to hold all metrics
	Json::Value ary(Json::arrayValue);
	ary.resize(idx);

	do {
		time_granted = fncs::time_request(time_stop);
		events = fncs::get_events();
		for (vector<string>::iterator it=events.begin(); it!=events.end(); ++it) {
			newval = collect_fncs_values (*it);
			if ((*it).find("kwhr_price") == 0) {
				price = newval;
			}
			if ((*it).find("electric_demand_power") == 0) {
				totalWatts = newval;
			}
			if ((*it).find("outdoor_air") == 0) { // indoor air published from E+ in degF
				newval = newval * 1.8 + 32.0;
			}
			update_metric(metrics[*it], newval);
		}
		// this is price response
		delta = degF_per_price * (price - base_price);
	 	if (delta < -max_delta_lo) {
	 		delta = -max_delta_lo;
	 	} else if (delta > max_delta_hi) {
	 		delta = max_delta_hi;
	 	}
		update_metric(metrics["cooling_setpoint_delta"], delta);
		update_metric(metrics["heating_setpoint_delta"], -delta);

		if ((time_granted - time_written) >= time_agg) {
			time_written = time_granted;
			output_metrics (metrics, root, ary, time_granted, out);
		}

		fncs::publish ("cooling_setpoint_delta", to_string(delta));
		fncs::publish ("heating_setpoint_delta", to_string(-delta));
		phaseWatts = totalWatts / 3.0;
		fncs::publish ("power_A", to_string(phaseWatts));
		fncs::publish ("power_B", to_string(phaseWatts));
		fncs::publish ("power_C", to_string(phaseWatts));
		fncs::publish ("bill_mode", "HOURLY");
		fncs::publish ("price", to_string(price));
		fncs::publish ("monthly_fee", to_string(0.0));
	} while (time_granted < time_stop);
	if (time_granted > time_written) {
		output_metrics (metrics, root, ary, time_granted, out);
	}
	cout << "last time_granted was " << time_granted << endl;
	cout << "time_stop was " << time_stop << endl;

	cout << "done" << endl;

	out << root << endl;

	fout.close();

	for (vector<string>::iterator it = keys.begin(); it != keys.end(); ++it) {
		delete [] metrics[*it];
	}

	fncs::finalize();

	return EXIT_SUCCESS;
}

