#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.68])
AC_INIT([TESP EnergyPlus Metrics], [1.0.0], [thomas.mcdermott@pnnl.gov])
AC_CONFIG_SRCDIR([config.h.in])
AC_CONFIG_HEADERS([config.h])
AC_CONFIG_MACRO_DIR([m4])

AC_LANG([C++])

AM_INIT_AUTOMAKE([foreign -Wall -Werror])

# Checks for programs.
AC_PROG_CXX
AC_PROG_CC

# Checks for libraries.
FNCS_CHECK_PACKAGE([zmq], [zmq.h], [zmq], [zmq_ctx_new])
fncs_save_CPPFLAGS="$CPPFLAGS"
fncs_save_LDFLAGS="$LDFLAGS"
fncs_save_LIBS="$LIBS"
CPPFLAGS="$CPPFLAGS $ZMQ_CPPFLAGS"
LDFLAGS="$LDFLAGS $ZMQ_LDFLAGS"
LIBS="$LIBS $ZMQ_LIBS"
FNCS_CHECK_PACKAGE([czmq], [czmq.h], [czmq], [zctx_new])
CPPFLAGS="$CPPFLAGS $CZMQ_CPPFLAGS"
LDFLAGS="$LDFLAGS $CZMQ_LDFLAGS"
LIBS="$LIBS $CZMQ_LIBS"
FNCS_CHECK_PACKAGE([fncs], [fncs.hpp], [fncs], [fncs_get_simulator_count])
CPPFLAGS="$fncs_save_CPPFLAGS"
LDFLAGS="$fncs_save_LDFLAGS"
LIBS="$fncs_save_LIBS"

# Checks for header files.
FNCS_CHECK_HEADERS([cstdint])
FNCS_CHECK_HEADERS([stdint.h])
FNCS_CHECK_HEADERS([sys/time.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_TYPE_INT8_T
AC_TYPE_INT16_T
AC_TYPE_INT32_T
AC_TYPE_INT64_T
AC_TYPE_UINT8_T
AC_TYPE_UINT16_T
AC_TYPE_UINT32_T
AC_TYPE_UINT64_T
AC_CHECK_SIZEOF([int8_t])
AC_CHECK_SIZEOF([int16_t])
AC_CHECK_SIZEOF([int32_t])
AC_CHECK_SIZEOF([int64_t])
AC_CHECK_SIZEOF([uint8_t])
AC_CHECK_SIZEOF([uint16_t])
AC_CHECK_SIZEOF([uint32_t])
AC_CHECK_SIZEOF([uint64_t])
AC_CHECK_SIZEOF([short])
AC_CHECK_SIZEOF([char])
AC_CHECK_SIZEOF([int])
AC_CHECK_SIZEOF([long])
AC_CHECK_SIZEOF([long long])
AC_CHECK_SIZEOF([unsigned char])
AC_CHECK_SIZEOF([unsigned short])
AC_CHECK_SIZEOF([unsigned int])
AC_CHECK_SIZEOF([unsigned long])
AC_CHECK_SIZEOF([unsigned long long])
AC_CHECK_SIZEOF([void*])
FNCS_CXX_NULLPTR

# Checks for library functions.
FNCS_CHECK_FUNCS([gettimeofday stod])

AC_CONFIG_FILES([Makefile])
AC_OUTPUT

