import sys
import json
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
import subprocess
import os
import tesp_support.fncs as fncs
import time

import numpy as np;
import matplotlib;
matplotlib.use("TkAgg");
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg;
from matplotlib.figure import Figure;
import matplotlib.pyplot as plt;

class TespMonitorGUI:
  def __init__ (self, master):
    self.root = master
    self.fig, self.ax = plt.subplots(4,1, sharex = 'col')
    plt.ion()

    ttk.Style().configure('TButton', foreground='blue')
    btn = ttk.Button(self.root, text='Open...', command=self.OpenConfig)
    btn.grid(row=0, column=0, sticky=tk.NSEW)
    btn = ttk.Button(self.root, text='Start All', command=self.launch_all)
    btn.grid(row=0, column=1, sticky=tk.NSEW)
    btn = ttk.Button(self.root, text='Kill All', command=self.kill_all)
    btn.grid(row=0, column=2, sticky=tk.NSEW)
    self.labelvar = tk.StringVar()
    self.labelvar.set('Case')
    lab = ttk.Label(self.root, textvariable=self.labelvar, relief=tk.RIDGE)
    lab.grid(row=0, column=3, sticky=tk.NSEW)

    self.ax[0].set_ylabel('[pu]')
    self.ax[0].set_title ('PYPOWER Bus Voltage', fontsize=10)

    self.ax[1].set_ylabel('[kW]')
    self.ax[1].set_title ('Primary School Load', fontsize=10)

    self.ax[2].set_ylabel('[$]')
    self.ax[2].set_title ('Clearing Price and LMP', fontsize=10)

    self.ax[3].set_ylabel('[kW]')
    self.ax[3].set_title ('Total Feeder Load', fontsize=10)

    self.ax[3].set_xlabel('Hours')
    plt.xlim(0.0,48.0)

    self.canvas = FigureCanvasTkAgg(self.fig, self.root)
    self.canvas.show()
    self.canvas.get_tk_widget().grid(row=1,columnspan=4)

  def OpenConfig(self): 
    fname = filedialog.askopenfilename(initialdir = '.',
                                       initialfile = 'tesp_monitor.json',
                                       title = 'Open JSON Monitor Configuration', 
                                       filetypes = (('JSON files','*.json'),('all files','*.*')),
                                       defaultextension = 'json')
    lp = open (fname)
    cfg = json.loads(lp.read())
    self.commands = cfg['commands']
    # convert seconds to minutes
    self.time_stop = int (cfg['time_stop'] / 60)
    self.yaml_delta = int (cfg['yaml_delta'] / 60)
    self.hour_stop = float (self.time_stop / 60.0)
#    print ('current directory', os.getcwd())
#    print (fname, self.time_stop, self.yaml_delta)
    dirpath = os.path.dirname (fname)
    os.chdir (dirpath)
#    print ('current directory', os.getcwd())
    self.labelvar.set(dirpath)

  def kill_all(self):
    for proc in self.pids:
      print ('trying to kill', proc)
      proc.kill()
    fncs.finalize()

  def launch_all(self):
    print('launching all simulators')
    self.pids = []
    for row in self.commands:
      procargs = row['args']
      procenv = os.environ.copy()
      for var in row['env']:
        procenv[var[0]] = var[1]
      logfd = None
      if 'log' in row:
        logfd = open (row['log'], 'w')
#      print (procargs, logfd)
      proc = subprocess.Popen (procargs, env=procenv, stdout=logfd)
      self.pids.append (proc)

    print('launched', len(self.pids), 'simulators') # , self.pids)

    self.root.update()
    print ('root update')

    fncs.initialize()
    print ('FNCS initialized')
    time_granted = 0
    nsteps = int (self.time_stop / self.yaml_delta)
#    plt.xlim(0.0, self.hour_stop)

    hrs=np.linspace(0.0, self.hour_stop, nsteps+1)
    print ('time_stop, hour_stop and nsteps =', self.time_stop, self.hour_stop, nsteps)
    idxlast = -1
    x0 = np.empty(nsteps+1)
    x1 = np.zeros(nsteps+1)
    x2 = np.zeros(nsteps+1)
    x3 = np.zeros(nsteps+1)
    while time_granted < self.time_stop:
      time_granted = fncs.time_request(self.time_stop)
      events = fncs.get_events()
      idx = int (time_granted / self.yaml_delta)
      if idx <= idxlast:
        continue
      idxlast = idx
      bWantX0 = True # pu volts
      bWantX1 = True # school load
      bWantX2 = True # prices
      bWantX3 = True # total feeder load
      for key in events:
        tok = key.decode()
        if bWantX1 and tok == 'power_A':
          val = 3.0 * float (fncs.get_value(key).decode().strip('+ degFkW')) / 1000.0
          x1[idx] = val
          self.ax[1].plot(hrs[1:idx],x1[1:idx],color='red')
          bWantX1 = False
        elif bWantX3 and tok == 'distribution_load':
          val = float (fncs.get_value(key).decode().strip('+ degFkW'))
          x3[idx] = val
          self.ax[3].plot(hrs[1:idx],x3[1:idx],color='magenta')
          bWantX3 = False
        elif bWantX0 and tok == 'vpos7':
          val = float (fncs.get_value(key).decode().strip('+ degFkW')) / 133000.0
          x0[idx] = val
          self.ax[0].plot(hrs[1:idx],x0[1:idx],color='green')
          bWantX0 = False
        elif bWantX2 and tok == 'clear_price':
          val = float (fncs.get_value(key).decode().strip('+ degFkW'))
          x2[idx] = val
          self.ax[2].plot(hrs[1:idx],x2[1:idx],color='blue')
          bWantX2 = False
        elif bWantX2 and tok == 'LMP7':
          val = float (fncs.get_value(key).decode().strip('+ degFkW'))
          x2[idx] = val
          self.ax[2].plot(hrs[1:idx],x2[1:idx],color='blue')
          bWantX2 = False
        elif bWantX1 and tok == 'SUBSTATION7':
          val = float (fncs.get_value(key).decode().strip('+ degFkW')) # already in kW
          x1[idx] = val
          self.ax[1].plot(hrs[1:idx],x1[1:idx],color='red')
          bWantX1 = False
      print (time_granted, key.decode(), fncs.get_value(key).decode())
      self.root.update()
      self.fig.canvas.draw()
    fncs.finalize()

def show_tesp_monitor ():
  root = tk.Tk()
  root.title('Transactive Energy Simulation Platform: Solution Monitor')
  my_gui = TespMonitorGUI (root)
  root.update()
  while True:
    try:
      root.mainloop()
      break
    except UnicodeDecodeError:
      pass

#show_tesp_monitor()
