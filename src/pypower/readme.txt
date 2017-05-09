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
