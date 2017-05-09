Installing Python 3.6
=====================

Download and run the Miniconda installer from https://repo.continuum.io/  

Then from a command prompt, invoke the following: 
 
   conda update conda
   conda install matplotlib
   conda install scipy
   conda install xarray
   pip install PYPOWER

Installing TESP (includes GridLAB-D 4.0)
========================================
1a.  checkout https://github.com/pnnl/tesp to ~/tesp  OR
1b.  Unzip archive from USB to ~/tesp
2.  Unzip the archive ~/tesp/install/MacOSX/Archive_usr_local_bin.zip to /usr/local/bin
3.  Unzip the archive ~/tesp/install/MacOSX/Archive_usr_local_lib.zip to /usr/local/lib
4.  Unzip the archive ~/tesp/install/MacOSX/Archive_usr_local_share.zip to /usr/local/share
5a.  Manually create the directory /usr/local/opt/jsoncpp
5b.  Unzip the archive ~/tesp/install/MacOSX/Archive_usr_local_opt_jsoncpp.zip to /usr/local/opt/jsoncpp
6.  From a Terminal, enter "gridlabd --version" and "energyplus --version" to verify

Patching PYPOWER if Necessary
=============================

Run "pf" or "opf" from a Terminal, and you'll see either warnings (up to Python 3.5) or 
errors (in Python 3.6) from PYPOWER due to deprecated behaviors, primarily the use of 
floats for array indices.  To fix this: 

1. You will manually copy the three patched Python files from ~/tesp/src/pypower

2. The target location depends on where Python and site packages have been installed. Please search
your installation for directories containing the three files to patch: ext2int.py, opf_hessfcn.py 
and pipsopf_solver.py. Some examples: 

   (Windows)  c:\Python36\Lib\site-packages\pypower

   (Mac OS X) $HOME/miniconda3/lib/python3.5/site-packages/PYPOWER-5.0.1-py3.5.egg/pypower


TESP Uses TCP/IP port 5570 for communication
============================================
1.	"lsof -i :5570" will show all processes connected to port 5570; use this or "ls -al *.log", "ls -al *.json", "ls -al *.csv" to show progress of a case solution
2.	"./kill5570.sh" will terminate all processes connected to port 5570; if you have to do this, make sure "lsof -i :5570" shows nothing before attempting another case

TestCase1 - from a Terminal in ~/tesp/examples/loadshed
=======================================================
1.	python glm_dict.py loadshed
2.	./run.sh
3.	python plot_loadshed.py loadshed

TestCase2 - from a Terminal in ~/tesp/examples/energyplus
=========================================================
1.	./run.sh
2.	python process_eplus.py eplus

TestCase3 - from a Terminal in ~/tesp/examples/pypower
======================================================
1.	./runpp.sh
2.	python process_pypower.py ppcase

TestCase4 - from a Terminal in ~/tesp/examples/te30
===================================================
1.	python prep_agents.py te_challenge
2.	python glm_dict.py te_challenge
3.	./run30.sh
3a.     the simulation takes about 10 minutes, use "cat TE*.csv" to show progress up to 172800 seconds
4.	python process_eplus.py te_challenge
5.	python process_pypower.py te_challenge
6.	python process_agents.py te_challenge
7.	python process_gld.py te_challenge

