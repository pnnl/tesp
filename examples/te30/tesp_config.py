import sys
import json
import tkinter as tk
import tkinter.ttk as ttk
import subprocess
import os
import fncs
import time

#import numpy as np;

root = tk.Tk()
root.title('Transactive Energy Simulation Platform')

nb = ttk.Notebook(root)
nb.pack(fill='both', expand='yes')

StartTime = "2013-07-01 00:00:00"
Tmax = 2 * 24 * 3600

vars = [['MATPOWER','GLD Bus',7,''],
				['MATPOWER','Amp Factor',400,''],
				['MATPOWER','Unit Out',2,''],
				['MATPOWER','Outage Start',108000,'s'],
				['MATPOWER','Outage End',158400,'s'],
				['EnergyPlus','Base Price',0.02,'$'],
				['EnergyPlus','Ramp',25,'degF/$'],
				['EnergyPlus','Max Delta',4,'degF'],
				['Auction','Initial Price',0.02078,'$'],
				['Auction','Std Dev Price',0.00361,'$'],
				['Auction','Price Cap',3.78,'$'],
				['Houses','Ramp Lo: Mean',2.0,'$(std dev)/degF'],
				['Houses','Ramp Lo: Band',0.5,'$(std dev)/degF'],
				['Houses','Ramp Hi: Mean',2.0,'$(std dev)/degF'],
				['Houses','Ramp Hi: Band',0.0,'$(std dev)/degF'],
				['Houses','Range Lo: Mean',-3.0,'degF'],
				['Houses','Range Lo: Band',1.0,'degF'],
				['Houses','Range Hi: Mean',2.0,'degF'],
				['Houses','Range Hi: Band',0.0,'degF'],
				['Houses','Base Cooling: Mean',78.0,'degF'],
				['Houses','Base Cooling: Band',2.0,'degF'],
				['Houses','Bid Delay',60,'s']
				];

f1 = ttk.Frame(nb, name='configuration')
lab = ttk.Label(f1, text='Simulator', relief=tk.RIDGE)
lab.grid(row=0, column=0, sticky=tk.NSEW)
lab = ttk.Label(f1, text='Parameter', relief=tk.RIDGE)
lab.grid(row=0, column=1, sticky=tk.NSEW)
lab = ttk.Label(f1, text='Value', relief=tk.RIDGE)
lab.grid(row=0, column=2, sticky=tk.NSEW)
lab = ttk.Label(f1, text='Units', relief=tk.RIDGE)
lab.grid(row=0, column=3, sticky=tk.NSEW)
for i in range(len(vars)):
	lab = ttk.Label(f1, text=vars[i][0], relief=tk.RIDGE)
	lab.grid(row=i+1, column=0, sticky=tk.NSEW)
	lab = ttk.Label(f1, text=vars[i][1], relief=tk.RIDGE)
	lab.grid(row=i+1, column=1, sticky=tk.NSEW)
	ent = ttk.Entry(f1)
	ent.insert(0, vars[i][2])
	ent.grid(row=i+1, column=2, sticky=tk.NSEW)
	lab = ttk.Label(f1, text=vars[i][3], relief=tk.RIDGE)
	lab.grid(row=i+1, column=3, sticky=tk.NSEW)

f2 = ttk.Frame(nb, name='launch')
lab = ttk.Label(f2, text='Start Date/Time', relief=tk.RIDGE)
lab.grid(row=0, column=0, sticky=tk.NSEW)
ent = ttk.Entry(f2)
ent.insert(0,StartTime)
ent.grid(row=0, column=1, sticky=tk.NSEW)
lab = ttk.Label(f2, text='Simulation Length', relief=tk.RIDGE)
lab.grid(row=1, column=0, sticky=tk.NSEW)
ent = ttk.Entry(f2)
ent.insert(0,Tmax)
ent.grid(row=1, column=1, sticky=tk.NSEW)
lab = ttk.Label(f2, text='[s]', relief=tk.RIDGE)
lab.grid(row=1, column=2, sticky=tk.NSEW)
#btn = ttk.Button(f2, text='Start All', command=launch_all)
#btn.grid(row=2, column=1, sticky=tk.NSEW)
#btn = ttk.Button(f2, text='Kill All', command=kill_all)
#btn.grid(row=3, column=1, sticky=tk.NSEW)

nb.add(f1, text='Configuration', underline=0, padding=2)
nb.add(f2, text='Launch', underline=0, padding=2)

while True:
	try:
		root.mainloop()
		break
	except UnicodeDecodeError:
		pass
