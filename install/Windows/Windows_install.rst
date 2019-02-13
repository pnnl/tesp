Installing on Windows
---------------------

This procedure has been tested on Windows 7 and Windows 10, 
without an existing Python installation. If Python is already installed,
additional steps may be needed to ensure Python3 support, including
the Tcl/Tk interface used for plotting and graphical user interfaces (GUI).

1. Install **64-bit** Python 3.7 from http://www.python.org. Make sure to check the optional **pip** and **Tcl/Tk IDLE** components as well.
2. Install (or update) Java 8 or later, both runtime (JRE) and development kit (JDK) from https://www.oracle.com/technetwork/java/javase/downloads/index.html 
3. Download and run the current Windows TESP installer from https://github.com/pnnl/tesp/releases. Install **both** the Data and Executable files.
4. On Windows 7, the MSVC 2015 Redistributables may also be required for PYPOWER to work. See https://www.microsoft.com/en-us/download/details.aspx?id=52685 
5. From a terminal/command window, enter the following commands, substituting your own user name for *username*:

::

 pip install tesp_support --upgrade
 opf
 cd \Users\username\tesp

That last step should place you in the directory above TESP examples. To continue:

1. Try the video tutorial at https://github.com/pnnl/tesp/releases
2. Try :ref:`RunExamples` 

You may also use the `Docker Version`_. This option is useful for distributed processing, and for 
isolating TESP from your other software, including other versions of GridLAB-D. 
However, it may require a little more data file management and it doesn't support Windows 8 or earlier.

.. _`Docker Version`: https://github.com/pnnl/tesp/blob/develop/install/Docker/ReadMe.md


