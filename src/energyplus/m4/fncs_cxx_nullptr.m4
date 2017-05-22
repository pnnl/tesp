# FNCS_CXX_NULLPTR
# ----------------
# Check whether CXX has defined nullptr and attempt a substitute if not found.
AC_DEFUN([FNCS_CXX_NULLPTR], [
AC_LANG_ASSERT([C++])
AC_CACHE_CHECK([for C++ nullptr],
    [fncs_cv_cxx_nullptr],
    [AC_LINK_IFELSE(
        [AC_LANG_PROGRAM([], [[int *address=nullptr;]])],
        [fncs_cv_cxx_nullptr=yes],
        [fncs_cv_cxx_nullptr=no])])
AS_IF([test "x$fncs_cv_cxx_nullptr" = xno],
    [AC_DEFINE([nullptr], [0], [if nullptr is not defined, attempt a substitute])])
])# FNCS_CXX_NULLPTR
