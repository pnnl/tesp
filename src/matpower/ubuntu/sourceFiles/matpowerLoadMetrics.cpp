/*
==========================================================================================
Copyright (C) 2017-2022, Battelle Memorial Institute
Written by Laurentiu Dan Marinovici, Pacific Northwest National Laboratory
==========================================================================================
*/
#include "matpowerLoadMetrics.h"

using namespace std;

// =============================== METADATA ========================================
loadMetadata::loadMetadata() {}

Json::Value loadMetadata::toJson() {
  Json::Value loadMetadata(Json::objectValue), metaElement(Json::objectValue);
  int metaIdx = 0;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "USD";
  loadMetadata["LMP_P"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "USD";
  loadMetadata["LMP_Q"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "MW";
  loadMetadata["PD"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "MVAR";
  loadMetadata["PQ"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "deg";
  loadMetadata["Vang"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "pu";
  loadMetadata["Vmag"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "pu";
  loadMetadata["Vmax"] = metaElement;
  metaElement["index"] = metaIdx++;
  metaElement["units"] = "pu";
  loadMetadata["Vmin"] = metaElement;
  return loadMetadata;
}

// =================== BUS METRICS =======================================
loadBusValues::loadBusValues() {}

// ==== BUS ID ====
void loadBusValues::setBusID(int const busID) {
  ostringstream convert;
  convert << busID;
  busID_ = convert.str();
}
const string& loadBusValues::busID() const {
  return busID_;
}

void loadBusValues::setBusPD(double const busPD) {
  busValues_.append(busPD);
}

void loadBusValues::setBusQD(double const busQD) {
  busValues_.append(busQD);
}

void loadBusValues::setBusVM(double const busVA) {
  busValues_.append(busVA);
}
void loadBusValues::setBusVA(double const busVM) {
  busValues_.append(busVM);
}

void loadBusValues::setBusVMAX(double const busVMAX) {
  busValues_.append(busVMAX);
}

void loadBusValues::setBusVMIN(double const busVMIN) {
  busValues_.append(busVMIN);
}

void loadBusValues::setBusLAMP(double const busLAMP) {
  busValues_.append(busLAMP);
}

void loadBusValues::setBusLAMQ(double const busLAMQ) {
  busValues_.append(busLAMQ);
}

void loadBusValues::clearBusValues() {
  busValues_.clear();
}

const Json::Value loadBusValues::busValues() const {
  return busValues_;
}

// =================== METRICS DEFINITIONS and FILE WRITING ===============================
loadBusMetrics::loadBusMetrics() {}

// ============= NAME ========================
void loadBusMetrics::setName(string const &name) {
  loadMetrics_["Network name"] = name;
}

// ============= START TIME ========================
void loadBusMetrics::setStartTime(string const &startTime) {
  loadMetrics_["Start Time"] = startTime;
}

// =============== CURRENT TIME BUS VALUES ========================
void loadBusMetrics::setCurrentTimeBusValues(double const time) {
  string currentTime;
  ostringstream convert;
  convert << time;
  currentTime = convert.str();
  loadMetrics_[currentTime] = currentBusValues_;
}

Json::Value loadBusMetrics::setBusValues(loadBusValues busValues) {
  currentBusValues_[busValues.busID_] = busValues.busValues_;
  return currentBusValues_;
}

void loadBusMetrics::setMetadata(loadMetadata meta) {
  Json::Value loadMetadata;
  loadMetadata = meta.toJson();
  loadMetrics_["Metadata"] = loadMetadata;
}

void loadBusMetrics::jsonSave(const char* filename) {
  ofstream out(filename, ofstream::out);
  
  // Just write
  out << loadMetrics_;
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
