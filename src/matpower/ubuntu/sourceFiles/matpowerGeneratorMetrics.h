/*
==========================================================================================
Copyright (C) 2017, Battelle Memorial Institute
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

class generatorMetadata {
  public:
    generatorMetadata();
    Json::Value toJson();
};

class generatorBusValues {
  public:
    // string busID_;
    string genIndex_;
    Json::Value busValues_;
  public:
    generatorBusValues();
    void setGenIndex(int const genIndex); // generator index used to differentiate between generators linked to the same generator bus
    const string& genIndex() const;
    void setBusID(int const busID); // generator bus ID/number
    // const string& busID() const;
    void setBusPG(double const busPG); // real generated power
    void setBusQG(double const busQG); // reactive generated power
    void setBusStatus(double const busSt); // machine status
    void setBusLAMP(double const busLAMP); // generator bus LMP - real
    void setBusLAMQ(double const busLAMQ); // generator bus LMP - reactive
    const Json::Value busValues() const;
    void clearBusValues();
};

class generatorBusMetrics {
  private:
    Json::Value currentBusValues_;
    Json::Value generatorMetrics_;
  public:
    generatorBusMetrics();
    
    // Name to identify what system the metrics are for
    void setName(string const &name);
    
    // Starting time of the simulation; data is going to be saved to the JSON file
    // in time (seconds) increments starting at this time
    void setStartTime(string const &startTime);
    
    // Current time of data
    void setCurrentTimeBusValues(double const currentTime);
    
    // Set the metadata
    void setMetadata(generatorMetadata meta);
    Json::Value setBusValues(generatorBusValues busValues);

    // Saving the metrics to a JSON file
    void jsonSave(const char* filename);
};
