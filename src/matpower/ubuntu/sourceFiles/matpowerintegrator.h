/*
==========================================================================================
Copyright (C) 2015, Battelle Memorial Institute
Written by Laurentiu Dan Marinovici, Pacific Northwest National Laboratory
==========================================================================================
*/
#include "fncs.hpp"

#ifdef _WIN32
  #include <Windows.h>
#else
  #include <sys/time.h> // for Unix time/POSIX time/epoch time
  #include <ctime>
#endif

/* Remove if already defined */
typedef long long int64;
typedef unsigned long long uint64;

typedef unsigned long long TIME;

TIME getCurrentTime();

bool synchronize(bool ack);

void getpower(string lookupKey, int *has, double *real, double *imag, string &actUnit, string &reactUnit);
void getDispLoad(string lookupKey, int *has, double *maxDispLoad, double *dispLoad);
void getDLDemandCurve(string lookupKey, int *has, double *c2, double *c1, double *c0);

string delSpace(string complexValue);
string makeComplexStr(double *real, double *imag);

uint64 GetTimeMs64();
