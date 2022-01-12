/*
==========================================================================================
Copyright (C) 2017-2022, Battelle Memorial Institute
Written by Laurentiu Dan Marinovici, Pacific Northwest National Laboratory
==========================================================================================
*/
#pragma once
#include <string.h>
#include <vector>
#include <fstream>
#include <sstream>

# include "json/json.h"

using namespace std;

class loadMetadata {
  public:
    loadMetadata();
    Json::Value toJson();
};

class loadBusValues {
  public:
    string busID_;
    Json::Value busValues_;
  public:
    loadBusValues();
    void setBusID(int const busID);
    const string& busID() const;
    void setBusPD(double const busPD);
    void setBusQD(double const busQD);
    void setBusVM(double const busVM);
    void setBusVA(double const busVA);
    void setBusVMAX(double const busVMAX);
    void setBusVMIN(double const busVMIN);
    void setBusLAMP(double const busLAMP);
    void setBusLAMQ(double const busLAMQ);
    const Json::Value busValues() const;
    void clearBusValues();
};

class loadBusMetrics {
  private:
    Json::Value currentBusValues_;
    Json::Value loadMetrics_;
  public:
    loadBusMetrics();
    
    // Name to identify what system the metrics are for
    void setName(string const &name);
    
    // Starting time of the simulation; data is going to be saved to the JSON file
    // in time (seconds) increments starting at this time
    void setStartTime(string const &startTime);
    
    // Current time of data
    void setCurrentTimeBusValues(double const currentTime);
    
    // Set the metadata
    void setMetadata(loadMetadata meta);
    Json::Value setBusValues(loadBusValues busValues);

    // Saving the metrics to a JSON file
    void jsonSave(const char* filename);
};
