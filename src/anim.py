# Copyright (C) 2021 Battelle Memorial Institute
# file: anim.py

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
    self.y0 = [1.0]
    self.y1 = [0.0]
    self.y2 = [0.0]
    self.y3 = [0.0]
    self.y0min = 1.0
    self.y0max = 1.0
    self.y1min = 0.0
    self.y1max = 0.0
    self.y2min = 0.0
    self.y2max = 0.0
    self.y3min = 0.0
    self.y3max = 0.0

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
    self.ax[1].set_xlim(0.0, Tmax)
    self.ax[2].set_xlim(0.0, Tmax)
    self.ax[3].set_xlim(0.0, Tmax)

    self.ax[0].set_ylim(0.0, 1.1)

    self.canvas = FigureCanvasTkAgg(self.fig, self.root)
    self.canvas.draw()
    self.canvas.get_tk_widget().grid(row=1,columnspan=5, sticky = tk.W + tk.E + tk.N + tk.S)

  def on_closing(self):
    if messagebox.askokcancel('Close', 'Do you want to close this window? This is likely to stop all simulations.'):
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

  def update_plots(self, i):
    print ('.', end='')
    bRedraw = False
    while self.time_granted < self.time_stop: # time in minutes
      self.time_granted = self.time_granted + 1
      self.root.update()
      idx = int (self.time_granted / self.yaml_delta)
      if idx <= self.idxlast:
        continue
      self.idxlast = idx

      retval = [self.ln0, self.ln1, self.ln2, self.ln3]

      h = float (self.time_granted / 60.0)
      self.hrs.append (h)
      v0 = 1.0 + 0.05 * random()
      if v0 < self.y0min or v0 > self.y0max:
        if v0 < self.y0min:
          self.y0min = v0
        if v0 > self.y0max:
          self.y0max = v0
        self.ax[0].set_ylim (self.y0min, self.y0max)
        bRedraw = True
      v1 = 200.0 + 50.0 * random()
      if v1 < self.y1min or v1 > self.y1max:
        if v1 < self.y1min:
          self.y1min = v1
        if v1 > self.y1max:
          self.y1max = v1
        self.ax[1].set_ylim (self.y1min, self.y1max)
        bRedraw = True
      v2 = 50.0 + 10.0 * random()
      if v2 < self.y2min or v2 > self.y2max:
        if v2 < self.y2min:
          self.y2min = v2
        if v2 > self.y2max:
          self.y2max = v2
        self.ax[2].set_ylim (self.y2min, self.y2max)
        bRedraw = True
      v3 = 1000.0 + 150.0 * random()
      if v3 < self.y3min or v3 > self.y3max:
        if v3 < self.y3min:
          self.y3min = v3
        if v3 > self.y3max:
          self.y3max = v3
        self.ax[3].set_ylim (self.y3min, self.y3max)
        bRedraw = True

      self.y0.append (v0) # Vpu
      self.y1.append (v1) # school kW
      self.y2.append (v2) # price
      self.y3.append (v3) # feeder load
      self.ln0.set_data (self.hrs, self.y0)
      self.ln1.set_data (self.hrs, self.y1)
      self.ln2.set_data (self.hrs, self.y2)
      self.ln3.set_data (self.hrs, self.y3)

      if bRedraw:
        self.fig.canvas.draw()
      return retval

  def launch_all(self):
    print('simulating message traffic')
    self.root.update()
    self.nsteps = int (self.time_stop / self.yaml_delta)
    self.idxlast = -1
    self.time_granted = 0

    ani = animation.FuncAnimation (self.fig, self.update_plots, frames=self.nsteps,
                                   blit=True, repeat=False, interval=0)
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

