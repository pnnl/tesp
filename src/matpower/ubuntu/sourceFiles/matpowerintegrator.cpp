/*
``matpowerintegrator'' represents the collection of functions necessary to implement the right communication
between the distribution simulator/player (GridLAB-D) and the transmission player (MATPOWER)
==========================================================================================
Copyright (c) 2015-2023 Battelle Memorial Institute
Written by Laurentiu Dan Marinovici, Pacific Northwest National Laboratory
Updated: 03/24/2015
   Purpose: GETPOWER function rewritten to compy to FNCS2 standards
     - The power value is read as a string containing a complex value and a unit
     - Separate the actual number and unit
     - Eliminate spaces in the complex power value (apparent power) and unit strings
     - Bring units to upper case for easy comparison (needed for eventual conversion)
     - Scan the complex number string to get the active and reactive powers
     - Power is returned in MW or Mvar as needed by MATPOWER
Last update: 04/15/2015
   Purpose: Fixing the GETPOWER function to account for all types of complex values, that is
     - 1 - polar coordinates with angle in degrees
     - 2 - carthesian coordinates with "i" for imaginary
     - 3 - polar coordinates with angle in radians
     - 4 - carthesian coordinates with "j" for imaginary
     in this specific order
==========================================================================================
*/
#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm> // for the transform function
#include <cmath> // (math.h) for the absolute value
using namespace std;
#include <string.h>
#include "fncs.hpp"
#include "matpowerintegrator.h"

#define PI 3.14159265

TIME currentTime = 0;
TIME messageTime = 0;

TIME getCurrentTime()
{
  return currentTime;
}

bool synchronize(bool ack) // acknowledge message has been received or sent
{

  TIME nextTime, deltaTime;
  if (ack) // if message have been received or sent
  {
     if (currentTime % 300 >= 0 && currentTime % 300 < 295)
     {
        deltaTime = 295 - currentTime % 300;
     }
     else
     {
        deltaTime = 295 - currentTime % 300 + 300;
     }
     nextTime = fncs::time_request(currentTime + deltaTime);
     cout << "*************************** TIMING TIMING TIMING *********************************" << endl;
     cout << "current time = " << currentTime << endl;
     cout << "GLD published, so MATPOWER jump at next time = " << nextTime << endl;
     cout << "delta time = " << deltaTime << " left till MATPOWER market cycle" << endl;
     cout << "**********************************************************************************" << endl;
     currentTime = nextTime;
     return 1;
  }
  else
  {
     return 0;
     cout << "========= SYNCHRONIZE -->> NO MESSAGE RECEIVED OR SENT!!! ==========" << endl;
  }
}


// See details about GETPOWER in this file preamble
void getpower(string lookupKey, int *has, double *real, double *imag, string &actUnit, string &reactUnit)
{
  string lookupKval;
  lookupKval = fncs::get_value(lookupKey); // get the power value from the corresponding global key published by GLD

  if (!lookupKval.empty())
  {
    // The complex power value from GridLAB-D can come in several formats; see file preamble for details
    size_t foundD = lookupKval.find("d"); // find the ``d''; polar format with angle in degrees
    size_t foundR = lookupKval.find("r"); // find the ``r''; polar format with angle in radians
    size_t foundI = lookupKval.find("i"); // find the ``i'' (complex) position
    size_t foundJ = lookupKval.find("j"); // find the ``j'' (complex) position
    string unit; // just the unit string
    try
    {
      if (foundD != string::npos)
      {
        double magnitude, phase;
        string complexValue = lookupKval.substr(0, foundD + 1); // separate the complex power value as string
        complexValue = delSpace(complexValue); // eliminate the white spaces in the complex value string
        sscanf(&complexValue[0], "%lf%lf%*[^d]", &magnitude, &phase); // parse the polar complex value string to get magnitude and phase in degrees
        unit = lookupKval.substr(foundD + 1, string::npos); // separate the unit string
        *real = magnitude * cos(phase * PI / 180); // real part in rectangular coordinates (active power)
        *imag = magnitude * sin(phase * PI / 180); // imaginary part in rectangular coordinates (reactive power)
      }
      else if (foundJ != string::npos)
      {
        string complexValue = lookupKval.substr(0, foundJ + 1); // separate the complex power value as string
        complexValue = delSpace(complexValue); // eliminate the white spaces in the complex value string
        sscanf(&complexValue[0], "%lf%lf%*[^j]", real, imag); // parse the rectangular complex value string to get active and reactive powers
        unit = lookupKval.substr(foundJ + 1, string::npos); // separate the unit string
      }
      else if (foundI != string::npos)
      {
        string complexValue = lookupKval.substr(0, foundI + 1); // separate the complex power value as string
        complexValue = delSpace(complexValue); // eliminate the white spaces in the complex value string
        sscanf(&complexValue[0], "%lf%lf%*[^i]", real, imag); // parse the rectangular complex value string to get active and reactive powers
        unit = lookupKval.substr(foundI + 1, string::npos); // separate the unit string
      }
      else if (foundR != string::npos)
      {
        double magnitude, phase;
        string complexValue = lookupKval.substr(0, foundR + 1); // separate the complex power value as string
        complexValue = delSpace(complexValue); // eliminate the white spaces in the complex value string
        sscanf(&complexValue[0], "%lf%lf%*[^r]", &magnitude, &phase); // parse the polar complex value string to get magnitude and phase in radians
        unit = lookupKval.substr(foundR + 1, string::npos); // separate the unit string
        *real = magnitude * cos(phase); // real part in rectangular coordinates (active power)
        *imag = magnitude * sin(phase); // imaginary part in rectangular coordinates (reactive power)
      }
      else
      {
        throw 225;
      }
      unit = delSpace(unit); // eliminate spaces in the unit string
      std::transform(unit.begin(), unit.end(), unit.begin(), ::toupper); // transform unit string to upper string for comparison purposes
    }
    catch (int e)
    {
      cout << "The power format might be wrong!!!" << endl;
      fncs::die();
      exit(EXIT_FAILURE);
    }
    try
    {
      if (unit.compare("VA") == 0)
      {
        *real /= 1000000; // W to MW conversion
        *imag /= 1000000; // VAR to Mvar conversion
        actUnit = string("MW");
        reactUnit = string("Mvar");    }
      else if (unit.compare("MVA") == 0)
      {
        actUnit = string("MW");
        reactUnit = string("Mvar");
      }
      else if (unit.compare("KVA") == 0)
      {
        *real /= 1000; // KW to MW conversion
        *imag /= 1000; // KVAR to Mvar conversion
        actUnit = string("MW");
        reactUnit = string("Mvar");
      }
      else
      {
        throw 225; // just an exception code
      }
    }
    catch (int e)
    {
      cout << "Unit is not correct. Check ZPL file or the GLD side!" << endl;
      fncs::die();
      exit(EXIT_FAILURE);
    }
    *has = 1; // message found
  }
  else
  {
    *has = 0; // no message found
  }
}

// =================================================================
// Laurentiu Dan Marinovici - 2017/06/27
// =================================================================
void getDispLoad(string lookupKey, int *has, double *maxDispLoad, double *dispLoad)
{
  string lookupKval;
  // get the maximum dispatchable load, if exists, from the corresponding global key published by the "aggregator"
  lookupKval = fncs::get_value(lookupKey);

  if (!lookupKval.empty())
  {
    sscanf(&lookupKval[0], "%lf,%lf", maxDispLoad, dispLoad); // parse the value to get the numeric maximum dispatchable load; should be in MW
    *has = 1; // message found
  }
  else
  {
    *has = 0; // no message found
  }
}

void getDLDemandCurve(string lookupKey, int *has, double *c2, double *c1, double *c0)
{
string lookupKval;
  // get the demand curve for the dispatchable load, if exists, from the corresponding global key published by the "aggregator"
  lookupKval = fncs::get_value(lookupKey);

  if (!lookupKval.empty())
  {
    lookupKval = delSpace(lookupKval);
    sscanf(&lookupKval[0], "%lf,%lf,%lf", c2, c1, c0); // parse the comma separated vector of coefficients
    *has = 1; // message found
  }
  else
  {
    *has = 0; // no message found
  }
}

// ===================================================================================================================
string delSpace (string complexValue)
{
  int i = 0;
  do
  {
    if (isspace(complexValue[i]))
    {
      complexValue.erase(i, 1);
      complexValue = delSpace(complexValue);
    }
    i += 1;
  }
  while (i < complexValue.length());
  return complexValue;
}

// makeComplexStr will return a string in the form a+/-bj
// The main issue with creating the string is that the plus sign of the imaginary part
// does not get added automatically, so it needs to be explicitely set
// Therefore, to accomodate the GLD side, I will add the signs explicitely to both real and imaginary part
string makeComplexStr(double *real, double *imag)
{
  std::stringstream tempRealStr, tempImStr;
  if (*real < 0)
  {
    tempRealStr << "-" << abs(*real);
  }
  else
  {
    tempRealStr << "+" << abs(*real);
  }
  if (*imag < 0)
  {
    tempImStr << "-" << abs(*imag);
  }
  else
  {
    tempImStr << "+" << abs(*imag);
  }
  string complexString = tempRealStr.str() + tempImStr.str() + "j";
  return complexString;
}

// Returns the amount of milliseconds elapsed since the UNIX epoch.
uint64 GetTimeMs64()
{
  #ifdef _WIN32
  // Windows
  #else
  // Linux
    struct timeval timeValue;
    gettimeofday(&timeValue, NULL);
    uint64 timeOfDay = timeValue.tv_usec; // time of day in micro seconds
    timeOfDay /= 1000; // time of day in milliseconds
    timeOfDay += (timeValue.tv_sec * 1000); // adding the seconds to the milliseconds to get the overall time
    return timeOfDay;
  #endif
}
