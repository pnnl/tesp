Installing Python 3.6
=====================

One option is to download and run the Miniconda installer from 
https://repo.continuum.io/ .  Then from a command prompt, invoke the 
following: 
 
conda update conda
conda install matplotlib
conda install scipy
conda install xarray
pip install PYPOWER
 
1.       Xarray: http://xarray.pydata.org/en/stable/
    a.       Required dependencies : Numpy, and pandas
    b.       Optional:
         i.      matplotlib (for plotting)
        ii.      netCDF4 (  use xarray for reading or writing netCDF files)
2.       Numpy
3.       Pandas
4.       Matplotlib
 

Installing TESP (includes GridLAB-D 4.0)
========================================
1.  Unzip archive to c:\tesp
2.  Create a new folder: c:\gridlab-d
3.  Unzip the archive install64.zip to this folder
4.  Unzip the archive MinGWredist.zip archive to c:\gridlab-d\install64\bin
5.  Add "c:\gridlab-d\install64\bin" to the system environment variable "Path"
6.  Create "GLPATH"  system environment variable, and set
      GLPATH = C:\gridlab-d\install64\share\gridlabd;C:\gridlab-d\install64\lib\gridlabd

TESP Uses TCP/IP port 5570 for communication
============================================
1.	list5570.bat will show all processes connected to port5570
2.	kill5570.bat will terminate all processes connected to port5570

TestCase1 - from c:\tesp\examples\loadshed
==========================================
1.	python glm_dict.py loadshed
2.	run
3.	python plot_loadshed.py loadshed

TestCase2 - from c:\tesp\examples\energyplus
============================================
1.	run
2.	python process_eplus.py eplus

TestCase3 - from c:\tesp\examples\pypower
=========================================
1.	run
2.	python process_pypower.py ppcase

TestCase4 - from c:\tesp\examples\te30
======================================
1.	python prep_agents.py te_challenge
2.	python glm_dict.py te_challenge
3.	run30
4.	python process_eplus.py te_challenge
5.	python process_pypower.py te_challenge
6.	python process_agents.py te_challenge
7.	python process_gld.py te_challenge

