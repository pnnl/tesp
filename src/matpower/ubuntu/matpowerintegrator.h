/*	Copyright (C) 2017 Battelle Memorial Institute */
// #include "cintegrator.h"
#include "fncs.hpp"

typedef unsigned long long TIME;

TIME getCurrentTime();

bool synchronize(bool ack);

void getpower(string lookupKey, int *has, double *real, double *imag, string &actUnit, string &reactUnit);

string delSpace(string complexValue);
string makeComplexStr(double *real, double *imag);
