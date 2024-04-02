# usage 'python ./plots.py metrics_root'
# run it from inside the metrics_root folder 
# .json file format only
import sys
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
import process_gld_dsot as pg
# import tesp_support.api.process_inv as gp
# import tesp_support.api.process_gld as gp

rootname = sys.argv[1]

cur_dir = os.getcwd()
new_dir = cur_dir + "/" + rootname + "/Substation_3"
os.chdir(new_dir)

if not os.path.exists("Figures"):
    os.mkdir("Figures")
print("*****current working directory is *** " + os.getcwd())

pg.process_gld("Substation_3")
#ph.process_houses(rootname)
#pi.process_inv(rootname)
#pv.process_voltages(rootname)
plt.show()