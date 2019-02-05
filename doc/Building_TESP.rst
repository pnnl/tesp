Building the TESP
=================

TESP has been designed to build and run with free compilers, including
MinGW but not Microsoft Visual C++ (MSVC) on Windows. The Python code
has been developed and tested with Python 3, including the NumPy, SciPy,
Matplotlib and Pandas packages. There are several suitable and free
Python distributions that will install these packages. MATPOWER has been
compiled into a shared object library with wrapper application, which
requires the MATLAB runtime to execute. This is a free download, but
it’s very large and the version must exactly match the MATLAB version
that TESP used in building the library and wrapper. This is true even if
you have a full version of MATLAB installed, so better solutions are
under investigation. At this time, we expect to support MATPOWER only
for Linux, with the alternative PYPOWER [`17 <#_ENREF_17>`__] supported
on Windows, Linux and Mac OS X. The code repository should always have
the most up-to-date information.

.. toctree::
   :maxdepth: 3

   Linux_Build_Link
   MacOSX_Build_Link
   Windows_Build_Link


