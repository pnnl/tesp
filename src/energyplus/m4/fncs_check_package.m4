# FNCS_CHECK_PACKAGE(pkg, header, library, function, [extra-libs],
#                  [action-if-found], [action-if-not-found])
# --------------------------------------------------------------
#
AC_DEFUN([FNCS_CHECK_PACKAGE], [
AS_VAR_PUSHDEF([HAVE_PKG],    m4_toupper(m4_translit([HAVE_$1], [-.], [__])))
AS_VAR_PUSHDEF([PKG_LIBS],    m4_toupper(m4_translit([$1_LIBS], [-.], [__])))
AS_VAR_PUSHDEF([PKG_LDFLAGS], m4_toupper(m4_translit([$1_LDFLAGS], [-.], [__])))
AS_VAR_PUSHDEF([PKG_CPPFLAGS],m4_toupper(m4_translit([$1_CPPFLAGS], [-.], [__])))
AS_VAR_SET([PKG_LIBS],[])
AS_VAR_SET([PKG_LDFLAGS],[])
AS_VAR_SET([PKG_CPPFLAGS],[])
AC_ARG_WITH([$1],
    [AS_HELP_STRING([--with-$1[[=ARG]]],
        [specify location of $1 install and/or other flags])],
    [],
    [with_$1=yes])
AS_CASE([$with_$1],
    [yes],  [],
    [no],   [],
            [FNCS_ARG_PARSE(
                [with_$1],
                [PKG_LIBS],
                [PKG_LDFLAGS],
                [PKG_CPPFLAGS])])
happy_header=no
# Check for header.
fncs_check_package_save_CPPFLAGS="$CPPFLAGS"; CPPFLAGS="$CPPFLAGS $PKG_CPPFLAGS"
AC_CHECK_HEADER([$2], [happy_header=yes], [$7])
CPPFLAGS="$fncs_check_package_save_CPPFLAGS"
happy_lib=no
# Check for library.
fncs_check_package_save_LIBS="$LIBS"; LIBS="$PKG_LIBS $LIBS"
fncs_check_package_save_LDFLAGS="$LDFLAGS"; LDFLAGS="$LDFLAGS $PKG_LDFLAGS"
AC_SEARCH_LIBS([$4], [$3], [happy_lib=yes], [], [$5])
LIBS="$fncs_check_package_save_LIBS"
LDFLAGS="$fncs_check_package_save_LDFLAGS"
AS_CASE([$ac_cv_search_$4],
    [*none*], [],
    [no], [],
    [AS_VAR_APPEND([PKG_LIBS], [$ac_cv_search_$4])])
AS_IF([test "x$happy_header" = xyes && test "x$happy_lib" = xyes],
    [$6
     AC_DEFINE([HAVE_PKG], [1], [set to 1 if we have the indicated package])
     AC_SUBST(PKG_LIBS)
     AC_SUBST(PKG_LDFLAGS)
     AC_SUBST(PKG_CPPFLAGS)
     ],
    [$7])
AM_CONDITIONAL(HAVE_PKG, [test "x$happy_header" = xyes && test "x$happy_lib" = xyes])
AS_VAR_POPDEF([HAVE_PKG])
AS_VAR_POPDEF([PKG_LIBS])
AS_VAR_POPDEF([PKG_LDFLAGS])
AS_VAR_POPDEF([PKG_CPPFLAGS])
])dnl
