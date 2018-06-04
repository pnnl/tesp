import subprocess
import sys

tmy2_generation=subprocess.Popen('Tmy3toTMY2_ansi '+sys.argv[1]+' >> '+sys.argv[1]+str('.tmy2'), shell=True)
tmy2_generation.wait()
file=sys.argv[1]+str('.tmy2')
#subprocess.Popen('python TMY2EPW.py '+file, shell=True)