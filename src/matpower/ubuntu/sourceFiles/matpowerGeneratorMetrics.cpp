/*
==========================================================================================
Copyright (c) 2017-2023 Battelle Memorial Institute
Written by Laurentiu Dan Marinovici, Pacific Northwest National Laboratory
==========================================================================================
*/
#include "matpowerGeneratorMetrics.h"

using namespace std;

// =============================== METADATA ========================================
generatorMetadata::generatorMetadata() {}

Json::Value generatorMetadata::toJson() {
  Json::Value generatorMetadata(Json::objectValue), metaElement(Json::objectValue);
  int metaIdx = 0;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "N/A";
  generatorMetadata["GEN_BUS"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "MW";
  generatorMetadata["PG"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "MVAr";
  generatorMetadata["QG"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "N/A";
  generatorMetadata["GEN_STATUS"] = metaElement;
  // metaElement["index"] = metaIdx++;
  // metaElement["units"] = "USD";
  // generatorMetadata["startup cost"] = metaElement;
  // metaElement["index"] = metaIdx++;
  // metaElement["units"] = "USD";
  // generatorMetadata["shutdown cost"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "USD";
  generatorMetadata["LMP_P"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "USD";
  generatorMetadata["LMP_Q"] = metaElement;
  return generatorMetadata;
}

// =================== BUS METRICS =======================================
generatorBusValues::generatorBusValues() {}

// ==== GENERATOR INDEX ====
void generatorBusValues::setGenIndex(int const genIndex) {
  ostringstream convert;
  convert << genIndex;
  genIndex_ = convert.str();
}
const string& generatorBusValues::genIndex() const {
  return genIndex_;
}

// ==== BUS ID ====
/*
void generatorBusValues::setBusID(int const busID) {
  ostringstream convert;
  convert << busID;
  busID_ = convert.str();
}
const string& generatorBusValues::busID() const {
  return busID_;
}
*/
void generatorBusValues::setBusID(int const busID) {
  busValues_.append(busID);
}

void generatorBusValues::setBusPG(double const busPG) {
  busValues_.append(busPG);
}

void generatorBusValues::setBusQG(double const busQG) {
  busValues_.append(busQG);
}

void generatorBusValues::setBusStatus(double const busSt) {
  if (busSt > 0) {
    busValues_.append("in-service");
  } else {
    busValues_.append("out-of-service");
  }
}

void generatorBusValues::setBusLAMP(double const busLAMP) {
  busValues_.append(busLAMP);
}

void generatorBusValues::setBusLAMQ(double const busLAMQ) {
  busValues_.append(busLAMQ);
}

void generatorBusValues::clearBusValues() {
  busValues_.clear();
}

const Json::Value generatorBusValues::busValues() const {
  return busValues_;
}

// =================== METRICS DEFINITIONS and FILE WRITING ===============================
generatorBusMetrics::generatorBusMetrics() {}

// ============= NAME ========================
void generatorBusMetrics::setName(string const &name) {
  generatorMetrics_["Network name"] = name;
}

// ============= START TIME ========================
void generatorBusMetrics::setStartTime(string const &startTime) {
  generatorMetrics_["Start Time"] = startTime;
}

// =============== CURRENT TIME BUS VALUES ========================
void generatorBusMetrics::setCurrentTimeBusValues(double const time) {
  string currentTime;
  ostringstream convert;
  convert << time;
  currentTime = convert.str();
  generatorMetrics_[currentTime] = currentBusValues_;
}

Json::Value generatorBusMetrics::setBusValues(generatorBusValues busValues) {
  // currentBusValues_[busValues.busID_] = busValues.busValues_;
  currentBusValues_[busValues.genIndex_] = busValues.busValues_;
  return currentBusValues_;
}

void generatorBusMetrics::setMetadata(generatorMetadata meta) {
  Json::Value generatorMetadata;
  generatorMetadata = meta.toJson();
  generatorMetrics_["Metadata"] = generatorMetadata;
}

void generatorBusMetrics::jsonSave(const char* filename) {
  ofstream out(filename, ofstream::out);
  
  // Just write
  out << generatorMetrics_;
  // Styled writing
  /*
  Json::StyledWriter styledWriter;
  out << styledWriter.write(loadMetrics_);
  */
  
  // Writing in one big string/one line
  /*
  Json::FastWriter fastWriter;
  out << fastWriter.write(loadMetrics_);
  */
  out.close();
}
