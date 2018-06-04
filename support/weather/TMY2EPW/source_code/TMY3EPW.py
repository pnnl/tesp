import subprocess
import sys
import os

if os.path.isfile(sys.argv[1]+str('.tmy2')):
   os.remove(sys.argv[1]+str('.tmy2')) 

tmy2_generation=subprocess.Popen('Tmy3toTMY2_ansi '+sys.argv[1]+' >> '+sys.argv[1]+str('.tmy2'), shell=True)
tmy2_generation.wait()
file=sys.argv[1]+str('.tmy2')
epw_generation=subprocess.Popen('python TMY2EPW.py '+file, shell=True)
epw_generation.wait()