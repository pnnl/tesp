//
// MATLAB Compiler: 6.4 (R2017a)
// Date: Thu Apr 13 14:21:49 2017
// Args:
// "-B""macro_default""-W""cpplib:libMATPOWER""-T""link:lib""-d""/home/laurentiu
// /work/MATPOWER4CoSimulation""-v""mpoption.m""runpf.m""runopf.m"
//

#ifndef __libMATPOWER_h
#define __libMATPOWER_h 1

#if defined(__cplusplus) && !defined(mclmcrrt_h) && defined(__linux__)
#  pragma implementation "mclmcrrt.h"
#endif
#include "mclmcrrt.h"
#include "mclcppclass.h"
#ifdef __cplusplus
extern "C" {
#endif

#if defined(__SUNPRO_CC)
/* Solaris shared libraries use __global, rather than mapfiles
 * to define the API exported from a shared library. __global is
 * only necessary when building the library -- files including
 * this header file to use the library do not need the __global
 * declaration; hence the EXPORTING_<library> logic.
 */

#ifdef EXPORTING_libMATPOWER
#define PUBLIC_libMATPOWER_C_API __global
#else
#define PUBLIC_libMATPOWER_C_API /* No import statement needed. */
#endif

#define LIB_libMATPOWER_C_API PUBLIC_libMATPOWER_C_API

#elif defined(_HPUX_SOURCE)

#ifdef EXPORTING_libMATPOWER
#define PUBLIC_libMATPOWER_C_API __declspec(dllexport)
#else
#define PUBLIC_libMATPOWER_C_API __declspec(dllimport)
#endif

#define LIB_libMATPOWER_C_API PUBLIC_libMATPOWER_C_API


#else

#define LIB_libMATPOWER_C_API

#endif

/* This symbol is defined in shared libraries. Define it here
 * (to nothing) in case this isn't a shared library. 
 */
#ifndef LIB_libMATPOWER_C_API 
#define LIB_libMATPOWER_C_API /* No special import/export declaration */
#endif

extern LIB_libMATPOWER_C_API 
bool MW_CALL_CONV libMATPOWERInitializeWithHandlers(
       mclOutputHandlerFcn error_handler, 
       mclOutputHandlerFcn print_handler);

extern LIB_libMATPOWER_C_API 
bool MW_CALL_CONV libMATPOWERInitialize(void);

extern LIB_libMATPOWER_C_API 
void MW_CALL_CONV libMATPOWERTerminate(void);



extern LIB_libMATPOWER_C_API 
void MW_CALL_CONV libMATPOWERPrintStackTrace(void);

extern LIB_libMATPOWER_C_API 
bool MW_CALL_CONV mlxMpoption(int nlhs, mxArray *plhs[], int nrhs, mxArray *prhs[]);

extern LIB_libMATPOWER_C_API 
bool MW_CALL_CONV mlxRunpf(int nlhs, mxArray *plhs[], int nrhs, mxArray *prhs[]);

extern LIB_libMATPOWER_C_API 
bool MW_CALL_CONV mlxRunopf(int nlhs, mxArray *plhs[], int nrhs, mxArray *prhs[]);


#ifdef __cplusplus
}
#endif

#ifdef __cplusplus

/* On Windows, use __declspec to control the exported API */
#if defined(_MSC_VER) || defined(__BORLANDC__)

#ifdef EXPORTING_libMATPOWER
#define PUBLIC_libMATPOWER_CPP_API __declspec(dllexport)
#else
#define PUBLIC_libMATPOWER_CPP_API __declspec(dllimport)
#endif

#define LIB_libMATPOWER_CPP_API PUBLIC_libMATPOWER_CPP_API

#else

#if !defined(LIB_libMATPOWER_CPP_API)
#if defined(LIB_libMATPOWER_C_API)
#define LIB_libMATPOWER_CPP_API LIB_libMATPOWER_C_API
#else
#define LIB_libMATPOWER_CPP_API /* empty! */ 
#endif
#endif

#endif

extern LIB_libMATPOWER_CPP_API void MW_CALL_CONV mpoption(int nargout, mwArray& opt, const mwArray& varargin);

extern LIB_libMATPOWER_CPP_API void MW_CALL_CONV mpoption(int nargout, mwArray& opt);

extern LIB_libMATPOWER_CPP_API void MW_CALL_CONV runpf(int nargout, mwArray& MVAbase, mwArray& bus, mwArray& gen, mwArray& branch, mwArray& success, mwArray& et, const mwArray& casedata, const mwArray& mpopt, const mwArray& fname, const mwArray& solvedcase);

extern LIB_libMATPOWER_CPP_API void MW_CALL_CONV runopf(int nargout, mwArray& MVAbase, mwArray& bus, mwArray& gen, mwArray& gencost, mwArray& branch, mwArray& f, mwArray& success, mwArray& et, const mwArray& casedata, const mwArray& mpopt, const mwArray& fname, const mwArray& solvedcase);

#endif
#endif
