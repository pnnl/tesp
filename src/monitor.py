import sys
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox
import time
from random import random 
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import matplotlib.animation as animation
import matplotlib.pyplot as plt

Tmax = 48.0

class TespMonitorGUI:
  def __init__ (self, master):
    self.root = master
    self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
    self.top = self.root.winfo_toplevel()
    self.top.rowconfigure (0, weight=1)
    self.top.columnconfigure (0, weight=1)
    self.fig, self.ax = plt.subplots(4,1, sharex = 'col')
    plt.subplots_adjust (hspace = 0.35)

    ttk.Style().configure('TButton', foreground='blue')

    btn = ttk.Button(self.root, text='Open...', command=self.OpenConfig)
    btn.grid(row=0, column=0, sticky=tk.NSEW)
    btn = ttk.Button(self.root, text='Start All', command=self.launch_all)
    btn.grid(row=0, column=1, sticky=tk.NSEW)
    btn = ttk.Button(self.root, text='Kill All', command=self.kill_all)
    btn.grid(row=0, column=2, sticky=tk.NSEW)
    btn = ttk.Button(self.root, text='Quit', command=self.Quit)
    btn.grid(row=0, column=3, sticky=tk.NSEW)
    self.labelvar = tk.StringVar()
    self.labelvar.set('Case')
    lab = ttk.Label(self.root, textvariable=self.labelvar, relief=tk.RIDGE)
    lab.grid(row=0, column=4, sticky=tk.NSEW)

    self.root.rowconfigure (0, weight=0)
    self.root.rowconfigure (1, weight=1)
    self.root.columnconfigure (0, weight=0)
    self.root.columnconfigure (1, weight=0)
    self.root.columnconfigure (2, weight=0)
    self.root.columnconfigure (3, weight=0)
    self.root.columnconfigure (4, weight=1)

    self.hrs = [0.0]
    self.y0 = [0.0]
    self.y1 = [0.0]
    self.y2 = [0.0]
    self.y3 = [0.0]
    self.ln0 = Line2D (self.hrs, self.y0, color='green')
    self.ln1 = Line2D (self.hrs, self.y1, color='red')
    self.ln2 = Line2D (self.hrs, self.y2, color='blue')
    self.ln3 = Line2D (self.hrs, self.y3, color='magenta')

    self.ax[0].add_line (self.ln0)
    self.ax[0].set_ylabel('[pu]')
    self.ax[0].set_title ('PYPOWER Bus Voltage', fontsize=10)

    self.ax[1].add_line (self.ln1)
    self.ax[1].set_ylabel('[kW]')
    self.ax[1].set_title ('Primary School Load', fontsize=10)

    self.ax[2].add_line (self.ln2)
    self.ax[2].set_ylabel('[$]')
    self.ax[2].set_title ('Clearing Price and LMP', fontsize=10)

    self.ax[3].add_line (self.ln3)
    self.ax[3].set_ylabel('[kW]')
    self.ax[3].set_title ('Total Feeder Load', fontsize=10)

    self.ax[3].set_xlabel('Hours')

    self.ax[0].set_xlim(0.0, Tmax)
    self.ax[0].set_ylim(0.0, 1.1)

    self.ax[1].set_xlim(0.0, Tmax)
    self.ax[1].set_ylim(0.0, 400.0)

    self.ax[2].set_xlim(0.0, Tmax)
    self.ax[2].set_ylim(0.0, 100.0)

    self.ax[3].set_xlim(0.0, Tmax)
    self.ax[3].set_ylim(0.0, 1500.0)

    self.canvas = FigureCanvasTkAgg(self.fig, self.root)
    self.canvas.draw()
    self.canvas.get_tk_widget().grid(row=1,columnspan=5, sticky = tk.W + tk.E + tk.N + tk.S)

  def on_closing(self):
    if messagebox.askokcancel('Quit', 'Do you want to close this window? This is likely to stop all simulations.'):
      self.root.quit()
      self.root.destroy()

  def Quit(self):
    self.root.quit()
    self.root.destroy()

  def OpenConfig(self): 
    self.time_stop = int (Tmax * 60)
    self.yaml_delta = int (300 / 60)
    self.hour_stop = float (self.time_stop / 60.0)
    self.labelvar.set('ready to launch')

  def kill_all(self):
    print ('killed all processes')

  def launch_all(self):
    print('simulating message traffic')

    self.root.update()

    time_granted = 0
    nsteps = int (self.time_stop / self.yaml_delta)
    print ('time_stop, hour_stop and nsteps =', self.time_stop, self.hour_stop, nsteps)
    idxlast = -1
    while time_granted < self.time_stop: # time in minutes
      time_granted = time_granted + 1
      idx = int (time_granted / self.yaml_delta)
      if idx <= idxlast:
        continue
      idxlast = idx

      h = float (time_granted / 60.0)
#      print (time_granted, h, idx, idxlast)
      self.hrs.append (h)
      self.y0.append (1.0 + 0.05 * random()) # Vpu
      self.y1.append (200.0 + 50.0 * random())   # school kW
      self.y2.append (50.0 + 10.0 * random())    # price
      self.y3.append (1000.0 + 150.0 * random()) # feeder load
      self.ln0.set_data (self.hrs, self.y0)
      self.ln1.set_data (self.hrs, self.y1)
      self.ln2.set_data (self.hrs, self.y2)
      self.ln3.set_data (self.hrs, self.y3)

      self.root.update()
      self.fig.canvas.draw()
    print ('done simulating the simulators')

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

