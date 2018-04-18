Installing on Windows
---------------------

An installation procedure is provided only for Windows; Linux and Mac OS X
users will build TESP instead. Even for Windows, the installation requires
access to the GitHub repository for file downloads, and it's a manual process.

Instal Python 3.6, PYPOWER and Optionally Java
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download and run the Miniconda installer for Python 3.6 (or later) 
from https://repo.continuum.io/  

Then from a command prompt, invoke the following: 
 
- conda update conda
- conda install matplotlib
- conda install scipy
- conda install xarray
- pip install PYPOWER
- opf

If Miniconda won't install mkl and numpy on Windows, download the "Python wheel" from from
http://www.lfd.uci.edu/~gohlke/pythonlibs/ and run 
"pip install numpy-1.12.1+mkl-cp36-cp36m-win_amd64.whl"

If you'll be developing agents in Java, download and install the Java 8 JDK from 
http://www.oracle.com/technetwork/java/javase/downloads/index.html

Install TESP (includes GridLAB-D 4.0 feature/1048 build)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Git checkout https://github.com/pnnl/tesp to c:\\tesp
- Create a new folder: c:\\gridlab-d
- Find the latest Windows/FNCS GridLAB-D/EnergyPlus release at https://github.com/pnnl/tesp/releases and download install64.zip from there
- Unzip the archive install64.zip to c:\\gridlab-d
- Unzip the archive c:\\tesp\\install\\windows\\MinGWredist.zip archive to c:\\gridlab-d\\install64\\bin
- Add "c:\\gridlab-d\\install64\\bin" to the system environment variable "Path"
- Create "GLPATH"  system environment variable, and set GLPATH = C:\\gridlab-d\\install64\\share\\gridlabd;C:\\gridlab-d\\install64\\lib\\gridlabd
- From a Command Prompt, enter "gridlabd --version" and "energyplus --version" to verify
- Try RunExamples_


