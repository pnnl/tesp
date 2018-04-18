import sys
import json
import tkinter as tk
import tkinter.ttk as ttk
import subprocess
import os
import fncs
import time

import numpy as np;
import matplotlib;
matplotlib.use("TkAgg");
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg;
from matplotlib.figure import Figure;
import matplotlib.pyplot as plt;

root = tk.Tk()
root.title('Transactive Energy Simulation Platform: Solution Monitor')

#nb.pack(fill='both', expand='yes')

fig, ax = plt.subplots(4,1, sharex = 'col')
plt.ion()

def launch_all():
	print('launching all simulators')
	if sys.platform == 'win32':
		subprocess.Popen ('call run30.bat', shell=True)
	else:
		subprocess.Popen ('(export simNum=36 && ./runVisualTE30ChallengeDocker.sh &)', shell=True)

	print('launched all simulators')

	root.update()

	os.environ['FNCS_CONFIG_FILE'] = 'tespTE30.yaml'
	os.environ['FNCS_FATAL'] = 'NO'
	print('config file =', os.environ['FNCS_CONFIG_FILE'])

	fncs.initialize()
	time_granted = 0
	time_stop = 2 * 24 * 60
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
		bWantX0 = True
		bWantX1 = True
		bWantX2 = True
		bWantX3 = True
		for key in events:
			tok = key.decode()
			if bWantX1 and tok == 'power_A':
				val = 3.0 * float (fncs.get_value(key).decode().strip('+ degFkW')) / 1000.0
				x1[idx] = val
				ax[1].plot(hrs[1:idx],x1[1:idx],color='red')
				bWantX1 = False
			elif bWantX3 and tok == 'house_air_temperature':
				val = float (fncs.get_value(key).decode().strip('+ degFkW'))
				x3[idx] = val
				ax[3].plot(hrs[1:idx],x3[1:idx],color='magenta')
				bWantX3 = False
			elif bWantX0 and tok == 'vpos7':
				val = float (fncs.get_value(key).decode().strip('+ degFkW')) / 133000.0
				x0[idx] = val
				ax[0].plot(hrs[1:idx],x0[1:idx],color='green')
				bWantX0 = False
			elif bWantX2 and tok == 'clear_price':
				val = float (fncs.get_value(key).decode().strip('+ degFkW'))
				x2[idx] = val
				ax[2].plot(hrs[1:idx],x2[1:idx],color='blue')
				bWantX2 = False
			elif bWantX2 and tok == 'LMP7':
				val = float (fncs.get_value(key).decode().strip('+ degFkW'))
				x2[idx] = val
				ax[2].plot(hrs[1:idx],x2[1:idx],color='blue')
				bWantX2 = False
			elif bWantX1 and tok == 'SUBSTATION7':
				val = float (fncs.get_value(key).decode().strip('+ degFkW')) # already in kW
				x1[idx] = val
				ax[1].plot(hrs[1:idx],x1[1:idx],color='red')
				bWantX1 = False
#			print (time_granted, key.decode(), fncs.get_value(key).decode())
		root.update()
		fig.canvas.draw()
	fncs.finalize()

def kill_all():
	if sys.platform == 'win32':
		fncs.finalize()
		subprocess.Popen ('call kill5570.bat', shell=True)
	else:
		print('TODO: kill all processes')

ttk.Style().configure('TButton', foreground='blue')
lab = ttk.Label(root, text='Case', relief=tk.RIDGE)
lab.grid(row=0, column=0, sticky=tk.NSEW)
ent = ttk.Entry(root)
ent.insert(0,'Working Directory')
ent.grid(row=0, column=1, sticky=tk.NSEW)
btn = ttk.Button(root, text='Start All', command=launch_all)
btn.grid(row=0, column=2, sticky=tk.NSEW)
btn = ttk.Button(root, text='Kill All', command=kill_all)
btn.grid(row=0, column=3, sticky=tk.NSEW)

ax[0].set_ylabel('[pu]')
ax[0].set_title ('PYPOWER Bus Voltage', fontsize=10)

ax[1].set_ylabel('[kW]')
ax[1].set_title ('Primary School Load', fontsize=10)

ax[2].set_ylabel('[$]')
ax[2].set_title ('Clearing Price', fontsize=10)

ax[3].set_ylabel('[degF]')
ax[3].set_title ('House Temperature', fontsize=10)

ax[3].set_xlabel('Hours')
plt.xlim(0.0,48.0)

canvas = FigureCanvasTkAgg(fig, root)
canvas.show()
#canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
#toolbar = NavigationToolbar2TkAgg(canvas,root)
#toolbar.update()
canvas.get_tk_widget().grid(row=1,columnspan=4)
#canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

root.update()

while True:
	try:
		root.mainloop()
		break
	except UnicodeDecodeError:
		pass
