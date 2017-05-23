Installing Python 3.6
=====================

Download and run the Miniconda installer from https://repo.continuum.io/  

Then from a command prompt, invoke the following: 
 
   conda update conda
   conda install matplotlib
   conda install scipy
   conda install xarray
   pip install PYPOWER

(If Miniconda won't install mkl and numpy on Windows, download the "Python wheel" from from
http://www.lfd.uci.edu/~gohlke/pythonlibs/ and run 
"pip install numpy-1.12.1+mkl-cp36-cp36m-win_amd64.whl")

Patching PYPOWER if Necessary
=============================

Run "pf" or "opf" from a command prompt, and you'll see either warnings or 
errors from PYPOWER due to deprecated behaviors, primarily the use of 
floats for array indices.  To fix this: 

1. manually copy three Python files from c:\tesp\src\pypower

2. the target location depends on where Python and site packages were installed.  Some examples: 

   (Windows)  c:\Python36\Lib\site-packages\pypower

   (Mac OS X) $HOME/miniconda3/lib/python3.5/site-packages/PYPOWER-5.0.1-py3.5.egg/pypower

Installing TESP (includes GridLAB-D 4.0)
========================================
1a.  checkout https://github.com/pnnl/tesp to c:\tesp  OR
1b.  Unzip archive from USB to c:\tesp
2.  Create a new folder: c:\gridlab-d
3.  Unzip the archive c:\tesp\install\windows\install64.zip to c:\gridlab-d
4.  Unzip the archive c:\tesp\install\windows\MinGWredist.zip archive to c:\gridlab-d\install64\bin
5.  Add "c:\gridlab-d\install64\bin" to the system environment variable "Path"
6.  Create "GLPATH"  system environment variable, and set
      GLPATH = C:\gridlab-d\install64\share\gridlabd;C:\gridlab-d\install64\lib\gridlabd
7.  From a Command Prompt, enter "gridlabd --version" and "energyplus --version" to verify

Patching PYPOWER if Necessary
=============================

Run "pf" or "opf" from a command prompt, and you'll see either warnings or 
errors from PYPOWER due to deprecated behaviors, primarily the use of 
floats for array indices.  To fix this: 

1. manually copy three Python files from c:\tesp\src\pypower

2. the target location depends on where Python and site packages were installed.  Some examples: 

   (Windows)  c:\Python36\Lib\site-packages\pypower

   (Mac OS X) $HOME/miniconda3/lib/python3.5/site-packages/PYPOWER-5.0.1-py3.5.egg/pypower

TESP Uses TCP/IP port 5570 for communication
============================================
1.	list5570.bat will show all processes connected to port5570; use this or "dir *.log", "dir *.json", "dir *.csv" to show progress of a case solution
2.	kill5570.bat will terminate all processes connected to port5570; if you have to do this, make sure list5570 shows nothing before attempting another case

TestCase1 - from a command prompt in c:\tesp\examples\loadshed
==============================================================
1.	python glm_dict.py loadshed
2.	run
2a.      (GridLAB-D may crash after completion; check with list5570; then use kill5570 if needed; do step 3)
3.	python plot_loadshed.py loadshed

TestCase2 - from a command prompt in c:\tesp\examples\energyplus
================================================================
1.	run
2.	python process_eplus.py eplus

TestCase3 - from a command prompt in c:\tesp\examples\pypower
=============================================================
1.	runpp
2.	python process_pypower.py ppcase

TestCase4 - from a command prompt in c:\tesp\examples\te30
==========================================================
1.	python prep_agents.py te_challenge
2.	python glm_dict.py te_challenge
3.	run30
3a.     the simulation takes about 10 minutes, use "type TE*.csv" to show progress up to 172800 seconds
4.	python process_eplus.py te_challenge
5.	python process_pypower.py te_challenge
6.	python process_agents.py te_challenge
7.	python process_gld.py te_challenge

