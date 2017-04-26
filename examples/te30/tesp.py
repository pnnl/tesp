import sys;
import json;
import tkinter as tk
import tkinter.ttk as ttk
import subprocess
import os
import fncs

import numpy as np;
import matplotlib;
matplotlib.use("TkAgg");
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg;
from matplotlib.figure import Figure;
import matplotlib.pyplot as plt;

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

fig, ax = plt.subplots(4,1, sharex = 'col')
plt.ion()

def launch_all():
	print('launching all simulators')
	subprocess.Popen ('(export FNCS_BROKER="tcp://*:5571" && exec fncs_broker 36 &> broker.log &)', shell=True)
	subprocess.Popen ('(export FNCS_CONFIG_FILE=eplus.yaml && exec energyplus -w ../energyplus/USA_AZ_Tucson.Intl.AP.722740_TMY3.epw -d output -r ../energyplus/SchoolDualController.idf &> eplus.log &)', shell=True)
	subprocess.Popen ('(export FNCS_CONFIG_FILE=eplus_json.yaml && exec eplus_json 2d 5m School_DualController eplus_TE_Challenge_metrics.json &> eplus_json.log &)', shell=True)
	subprocess.Popen ('(exec ./launch_TE_Challenge_agents.sh &)', shell=True)
	subprocess.Popen ('(export FNCS_CONFIG_FILE=pypower30.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py TE_Challenge "2013-07-01 00:00:00" 172800 300 &> pypower.log &)', shell=True)

#	subprocess.Popen ('(export FNCS_BROKER="tcp://*:5571" && exec fncs_broker 3 &> broker.log &)', shell=True)
#	subprocess.Popen ('(export FNCS_LOG_STDOUT=yes && exec fncs_player 2d player.txt &> ppplayer.log &)', shell=True)
#	subprocess.Popen ('(export FNCS_CONFIG_FILE=pypower.yaml && export FNCS_FATAL=NO && export FNCS_LOG_STDOUT=yes && exec python fncsPYPOWER.py &> pypower.log &)', shell=True)

	print('launched all simulators')

	nb.select(2)
	root.update()

	os.environ['FNCS_CONFIG_FILE'] = 'tesp.yaml'
#	os.environ['FNCS_CONFIG_FILE'] = 'pptracer.yaml'
	os.environ['FNCS_FATAL'] = 'NO'
	print('config file = ', os.environ['FNCS_CONFIG_FILE'])

	fncs.initialize()
	time_granted = 0
	time_stop = 2 * 24 * 60
#	yaml_delta = 60
	yaml_delta = 5
	nsteps = int (time_stop / yaml_delta)
	hrs=np.linspace(0.0, 48.0, nsteps+1)
	idxlast = -1
	x0 = np.empty(nsteps+1)
	x1 = np.zeros(nsteps+1)
	x2 = np.zeros(nsteps+1)
	x3 = np.zeros(nsteps+1)
	while time_granted < time_stop:
		time_granted = fncs.time_request(time_stop)
		events = fncs.get_events()
		idx = int (time_granted / yaml_delta)
		if idx <= idxlast:
			continue
		idxlast = idx
		for key in events:
			tok = key.decode()
			if tok == 'power_A':
				val = 3.0 * float (fncs.get_value(key).decode().strip('+ degFkW')) / 1000.0
				x1[idx] = val
				ax[1].plot(hrs[1:idx],x1[1:idx],color='red')
			elif tok == 'house_air_temperature':
				val = float (fncs.get_value(key).decode().strip('+ degFkW'))
				x3[idx] = val
				ax[3].plot(hrs[1:idx],x3[1:idx],color='magenta')
			elif tok == 'vpos7':
				val = float (fncs.get_value(key).decode().strip('+ degFkW')) / 133000.0
				x0[idx] = val
				ax[0].plot(hrs[1:idx],x0[1:idx],color='green')
			elif tok == 'clear_price':
				val = float (fncs.get_value(key).decode().strip('+ degFkW'))
				x2[idx] = val
				ax[2].plot(hrs[1:idx],x2[1:idx],color='blue')
			elif tok == 'LMP7':
				val = float (fncs.get_value(key).decode().strip('+ degFkW'))
				x2[idx] = val
				ax[2].plot(hrs[1:idx],x2[1:idx],color='blue')
			elif tok == 'SUBSTATION7':
				val = float (fncs.get_value(key).decode().strip('+ degFkW')) # already in kW
				x1[idx] = val
				ax[1].plot(hrs[1:idx],x1[1:idx],color='red')
#			print (time_granted, key.decode(), fncs.get_value(key).decode())
		root.update()
		fig.canvas.draw()
	fncs.finalize()

def kill_all():
	print('kill all processes')

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
btn = ttk.Button(f2, text='Start All', command=launch_all)
btn.grid(row=2, column=1, sticky=tk.NSEW)
btn = ttk.Button(f2, text='Kill All', command=kill_all)
btn.grid(row=3, column=1, sticky=tk.NSEW)

f3 = ttk.Frame(nb, name='plots')
#fig = Figure(figsize=(5,5), dpi=100)
#a = fig.add_subplot(111)
#a.plot([1,2,3,4,5,6,7,8],[5,6,1,2,6,1,3,4])
#fig, ax = plt.subplots(4,1, sharex = 'col')

#ax[0].plot(np.array([1,2,3,4,5,6,7,8]),np.array([5,6,1,2,6,1,3,4]), color='red')
ax[0].set_ylabel('[pu]')
ax[0].set_title ('PYPOWER Bus Voltage')

ax[1].set_ylabel('[kW]')
ax[1].set_title ('Primary School Load')

ax[2].set_ylabel('[$]')
ax[2].set_title ('Clearing Price')

ax[3].set_ylabel('[degF]')
ax[3].set_title ('House Temperature')

ax[3].set_xlabel('Hours')
plt.xlim(0.0,48.0)

canvas = FigureCanvasTkAgg(fig, f3)
canvas.show()
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
toolbar = NavigationToolbar2TkAgg(canvas,f3)
toolbar.update()
canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

nb.add(f1, text='Configuration', underline=0, padding=2)
nb.add(f2, text='Launch', underline=0, padding=2)
nb.add(f3, text='Plots', underline=0, padding=2)

while True:
	try:
		root.mainloop()
		break
	except UnicodeDecodeError:
		pass
