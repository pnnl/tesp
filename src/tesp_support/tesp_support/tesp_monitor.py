# Copyright (C) 2017-2022 Battelle Memorial Institute
# file: tesp_monitor.py
"""Presents a GUI to launch a TESP simulation and monitor its progress

Public Functions:
  :show_tesp_monitor: Initializes and runs the monitor GUI

References:
  `Graphical User Interfaces with Tk <https://docs.python.org/3/library/tk.html>`_

  `Matplotlib Animation <https://matplotlib.org/api/animation_api.html>`_
"""
import json
import os
import subprocess
import sys
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox

from .helpers import parse_kw

import matplotlib

try:
    matplotlib.use('TkAgg')
except:
    pass
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import matplotlib.animation as animation
import matplotlib.pyplot as plt

helics = None
fncs = None


class TespMonitorGUI:
    """Manages a GUI with 4 plotted variables, and buttons to stop TESP

    The GUI reads a JSON file with scripted shell commands to launch
    other FNCS federates, and a YAML file with FNCS subscriptions to update
    the solution status. Both JSON and YAML files are written by *tesp.tesp_config*
    The plotted variables provide a sign-of-life and sign-of-stability indication
    for each of the major federates in the te30 or sgip1 examples, namely
    GridLAB-D, PYPOWER, EnergPlus, and the substation_loop that manages a simple_auction
    with multiple hvac agents. If a solution appears to be unstable or must be
    stopped for any other reason, exiting the solution monitor will do so.

    The plots are created and updated with animated and bit-blitted Matplotlib
    graphs hosted on a TkInter GUI. When the JSON and YAML files are loaded,
    the x axis is laid out to match the total TESP simulation time range.

    Args:
        master:

    Attributes:
      root (Tk): the TCL Tk toolkit instance
      top (Window): the top-level TCL Tk Window
      labelvar (StringVar): used to display the monitor JSON configuration file path
      hrs ([float]): x-axis data array for time in hours, shared by all plots
      y0 ([float]): y-axis data array for PYPOWER bus voltage
      y1 ([float]): y-axis data array for EnergyPlus load
      y2lmp ([float]): y-axis data array for PYPOWER LMP
      y2auc ([float]): y-axis data array for simple_auction cleared_price
      y3fncs ([float]): y-axis data array for GridLAB-D load via FNCS
      y3gld ([float]): y-axis data array for sample-and-hold GridLAB-D load
      gld_load (float): the most recent load published by GridLAB-D; due to the deadband, this value isn't necessary published at every FNCS time step
      y0min (float): the first y axis minimum value
      y0max (float): the first y axis maximum value
      y1min (float): the second y axis minimum value
      y1max (float): the second y axis maximum value
      y2min (float): the third y axis minimum value
      y2max (float): the third y axis maximum value
      y3min (float): the fourth y axis minimum value
      y3max (float): the fourth y axis maximum value
      hour_stop (float): the maximum x axis time value to plot
      ln0 (Line2D): the plotted PYPOWER bus voltage, color GREEN
      ln1 (Line2D): the plotted EnergyPlus load, color RED
      ln2lmp (Line2D): the plotted PYPOWER locational marginal price (LMP), color BLUE
      ln2auc (Line2D): the plotted simple_auction cleared_price, color BLACK
      ln3gld (Line2D): the plotted sample-and-hold GridLAB-D substation load, color MAGENTA
      ln3fncs (Line2D): the plotted GridLAB-D substation load published via FNCS; may be zero if not published for the current animation frame, color CYAN
      fig (Figure): animated Matplotlib figure hosted on the GUI
      ax (Axes): set of 4 xy axes to plot on
      canvas (FigureCanvasTkAgg): a TCL Tk canvas that can host Matplotlib
      bFNCSactive (Boolean): True if a TESP simulation is running with other FNCS federates, False if not
      bHELICSactive (Boolean): True if a HELICS simulation is running with other HELICS federates, False if not
    """

    def __init__(self, master, HELICS=True):
        self.root = master
        self.HELICS = HELICS
        self.pids = []
        self.idxlast = -1
        self.time_granted = 0
        self.hFed = None
        self.bFNCSactive = False
        self.bHELICSactive = False

        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.top = self.root.winfo_toplevel()
        self.top.rowconfigure(0, weight=1)
        self.top.columnconfigure(0, weight=1)

        ttk.Style().configure('TButton', foreground='blue')

        self.btn0 = ttk.Button(self.root, text='Open...', command=self.OpenConfig)
        self.btn0.grid(row=0, column=0, sticky=tk.NSEW)
        self.filename = 'monitor.json'
        if HELICS:
            self.btn1 = ttk.Button(self.root, text='Start All', command=self.launch_all, state=tk.DISABLED)
        else:
            self.btn1 = ttk.Button(self.root, text='Start All', command=self.launch_all_f, state=tk.DISABLED)
        self.btn1.grid(row=0, column=1, sticky=tk.NSEW)
        self.btn2 = ttk.Button(self.root, text='Kill All', command=self.kill_all, state=tk.DISABLED)
        self.btn2.grid(row=0, column=2, sticky=tk.NSEW)
        btn = ttk.Button(self.root, text='Quit', command=self.Quit)
        btn.grid(row=0, column=3, sticky=tk.NSEW)
        self.labelvar = tk.StringVar()
        self.labelvar.set('Case')
        lab = ttk.Label(self.root, textvariable=self.labelvar, relief=tk.RIDGE)
        lab.grid(row=0, column=4, sticky=tk.NSEW)

        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=0)
        self.root.columnconfigure(2, weight=0)
        self.root.columnconfigure(3, weight=0)
        self.root.columnconfigure(4, weight=1)
        self.hour_stop = 4
        self.reset_plot()

    def reset_plot(self):
        self.fig, self.ax = plt.subplots(4, 1, sharex='col')
        plt.subplots_adjust(hspace=0.35)
        self.hrs = [0.0]
        self.y0 = [1.0]
        self.y1 = [0.0]
        self.y2lmp = [0.0]
        self.y2auc = [0.0]
        self.y3fncs = [0.0]  # GridLAB-D publishes only when changed
        self.gld_load = 0.0
        self.y3gld = [0.0]
        self.y0min = 1.0
        self.y0max = 1.0
        self.y1min = 0.0
        self.y1max = 0.0
        self.y2min = 0.0
        self.y2max = 0.0
        self.y3min = 0.0
        self.y3max = 0.0

        self.ln0 = Line2D(self.hrs, self.y0, color='green')
        self.ln1 = Line2D(self.hrs, self.y1, color='red')
        self.ln2auc = Line2D(self.hrs, self.y2auc, color='black')
        self.ln2lmp = Line2D(self.hrs, self.y2lmp, color='blue')
        self.ln3fncs = Line2D(self.hrs, self.y3fncs, color='cyan')
        self.ln3gld = Line2D(self.hrs, self.y3gld, color='magenta')

        self.ax[0].clear()
        self.ax[0].add_line(self.ln0)
        self.ax[0].set_ylabel('[pu]')
        self.ax[0].set_title('PYPOWER Bus Voltage', fontsize=10)

        self.ax[1].clear()
        self.ax[1].add_line(self.ln1)
        self.ax[1].set_ylabel('[kW]')
        self.ax[1].set_title('Primary School Load', fontsize=10)

        self.ax[2].clear()
        self.ax[2].add_line(self.ln2auc)
        self.ax[2].add_line(self.ln2lmp)
        self.ax[2].set_ylabel('[$]')
        self.ax[2].set_title('LMP and Clearing Price', fontsize=10)

        self.ax[3].clear()
        self.ax[3].add_line(self.ln3fncs)
        self.ax[3].add_line(self.ln3gld)
        self.ax[3].set_ylabel('[kW]')
        self.ax[3].set_title('Total Feeder Load', fontsize=10)

        self.ax[3].set_xlabel('Hours')
        self.ax[0].set_xlim(0.0, self.hour_stop)
        self.ax[1].set_xlim(0.0, self.hour_stop)
        self.ax[2].set_xlim(0.0, self.hour_stop)
        self.ax[3].set_xlim(0.0, self.hour_stop)
        self.ax[0].set_ylim(0.9, 1.1)

        self.canvas = FigureCanvasTkAgg(self.fig, self.root)
        self.canvas.get_tk_widget().grid(row=1, columnspan=5, sticky=tk.W + tk.E + tk.N + tk.S)

    def on_closing(self):
        """Verify whether the user wants to stop TESP simulations before exiting the monitor

        This monitor is itself a FNCS federate, so it can not be shut down without shutting
        down all other FNCS federates in the TESP simulation.
        """
        if messagebox.askokcancel('Quit', 'Do you want to close this window? This is likely to stop all simulations.'):
            self.Quit()

    def Quit(self):
        """Shuts down this monitor, and also shuts down FNCS/HELICS if active
        """
        if self.bFNCSactive or self.bHELICSactive:
            self.kill_all()

        self.root.quit()
        self.root.destroy()

    def OpenConfig(self):
        """Read the JSON configuration file for this monitor, and initialize the plot axes
        """
        fname = filedialog.askopenfilename(initialdir='.',
                                           initialfile=self.filename,
                                           title='Open JSON Monitor Configuration',
                                           filetypes=(('JSON files', '*.json'), ('all files', '*.*')),
                                           defaultextension='json')
        lp = open(fname)
        cfg = json.loads(lp.read())
        if self.HELICS:
            self.msg_config = cfg['helics_config']
            self.commands = cfg['commands']
        else:
            self.msg_config = cfg['fncs_config']
            self.commands = cfg['commands_f']
        # no longer converting seconds to minutes
        self.time_stop = int(cfg['time_stop'])
        self.yaml_delta = int(cfg['yaml_delta'])
        self.hour_stop = float(self.time_stop / 3600.0)
        dirpath = os.path.dirname(fname)
        os.chdir(dirpath)
        self.labelvar.set(dirpath)
        self.btn1['state'] = tk.NORMAL
        if self.HELICS:
            self.launch_all()
        else:
            self.launch_all_f()

    def kill_all(self):
        """Shut down all FNCS/HELICS federates in TESP, except for this monitor
        """
        self.root.update()
        for proc in self.pids:
            if not proc == self.broker:
                print('Trying to kill', proc.pid, flush=True)
                try:
                    os.kill(proc.pid, 9)
                    os.wait()
                except:
                    pass
                del proc
        self.pids = []

        print('Trying to finalize federation', flush=True)
        if self.bFNCSactive:
            # fncs.finalize()
            self.bFNCSactive = False
            print('FNCS finalized', flush=True)
        if self.bHELICSactive:
            # helics.helicsFederateDestroy(self.hFed)
            self.bHELICSactive = False
            print('HELICS finalized', flush=True)

        print('Terminating broker process', flush=True)
        # it seems are there are two HELICS broker processes
        for line in os.popen("ps ax | grep broker | grep -v grep"):
            fields = line.split()
            pid = fields[0]
            os.kill(int(pid), 9)
            os.wait()

        self.btn0['state'] = tk.NORMAL
        self.btn1['state'] = tk.NORMAL
        self.btn2['state'] = tk.DISABLED
        print("Process successfully terminated", flush=True)

    def expand_limits(self, v, vmin, vmax):
        """Whenever a variable meets a vertical axis limit, expand the limits with 10% padding above and below

        Args:
          v (float): the out of range value
          vmin (float): the current minimum vertical axis value
          vmax (float): the current maximum vertical axis value

        Returns:
          float, float: the new vmin and vmax
        """
        if v < vmin:
            vpad = 0.1 * (vmax - v)
            vmin = v - vpad
        if v > vmax:
            vpad = 0.1 * (v - vmin)
            vmax = v + vpad
        return vmin, vmax

    def update_plots_f(self, i):
        """This function is called by Matplotlib for each animation frame

        Each time called, collect FNCS messages until the next time to plot
        has been reached. Then update the plot quantities and return the
        Line2D objects that have been updated for plotting. Check for new
        data outside the plotted vertical range, which triggers a full
        re-draw of the axes. On the last frame, finalize FNCS.

        Args:
          i (int): the animation frame number
        """
        # print ('.', end='', flush=True)
        # print ('frame', i, 'of', self.nsteps, flush=True)
        bRedraw = False
        while self.time_granted <= self.time_stop:  # time in seconds
            try:
                # find the time value and index into the time (X) array
                self.time_granted = fncs.time_request(self.time_stop)
                events = fncs.get_events()
                self.root.update()
                idx = int(self.time_granted / self.yaml_delta)
                if idx <= self.idxlast:
                    continue
                self.idxlast = idx
                h = float(self.time_granted / 3600.0)
                self.hrs.append(h)

                # find the newest Y values
                v0 = 0.0
                v1 = 0.0
                v2auc = 0.0
                v2lmp = 0.0
                v3 = 0.0
                for topic in events:
                    value = fncs.get_value(topic)
                    if topic == 'power_A':
                        v1 = 3.0 * float(value.strip('+ degFkW')) / 1000.0
                    elif topic == 'TPV_7':
                        v0 = float(value.strip('+ degFkW')) / 133000.0
                    elif topic == 'clear_price':
                        v2auc = float(value.strip('+ degFkW'))
                    elif topic == 'LMP_7':
                        v2lmp = float(value.strip('+ degFkW'))
                    elif topic == 'electric_demand_power':
                        v1 = float(value.strip('+ degFkW'))  # already in kW
                    elif topic == 'distribution_load':
                        v3 = parse_kw(value)
                        self.gld_load = v3

                # expand the Y axis limits if necessary, keeping a 10% padding around the range
                if v0 < self.y0min or v0 > self.y0max:
                    self.y0min, self.y0max = self.expand_limits(v0, self.y0min, self.y0max)
                    self.ax[0].set_ylim(self.y0min, self.y0max)
                    bRedraw = True
                if v1 < self.y1min or v1 > self.y1max:
                    self.y1min, self.y1max = self.expand_limits(v1, self.y1min, self.y1max)
                    self.ax[1].set_ylim(self.y1min, self.y1max)
                    bRedraw = True
                if v2auc > v2lmp:
                    v2max = v2auc
                    v2min = v2lmp
                else:
                    v2max = v2lmp
                    v2min = v2auc
                if v2min < self.y2min or v2max > self.y2max:
                    self.y2min, self.y2max = self.expand_limits(v2min, self.y2min, self.y2max)
                    self.y2min, self.y2max = self.expand_limits(v2max, self.y2min, self.y2max)
                    self.ax[2].set_ylim(self.y2min, self.y2max)
                    bRedraw = True
                if v3 < self.y3min or v3 > self.y3max:
                    self.y3min, self.y3max = self.expand_limits(v3, self.y3min, self.y3max)
                    self.ax[3].set_ylim(self.y3min, self.y3max)
                    bRedraw = True

                # update the Y axis data to draw
                self.y0.append(v0)  # Vpu
                self.y1.append(v1)  # school kW
                self.y2auc.append(v2auc)  # price
                self.y2lmp.append(v2lmp)  # LMP
                self.y3fncs.append(v3)  # this feeder load from FNCS (could be zero if no update)
                self.y3gld.append(self.gld_load)  # most recent feeder load from FNCS
                self.ln0.set_data(self.hrs, self.y0)
                self.ln1.set_data(self.hrs, self.y1)
                self.ln2auc.set_data(self.hrs, self.y2auc)
                self.ln2lmp.set_data(self.hrs, self.y2lmp)
                self.ln3fncs.set_data(self.hrs, self.y3fncs)
                self.ln3gld.set_data(self.hrs, self.y3gld)

                if bRedraw:
                    self.fig.canvas.draw()
            except:
                # print('exception frame', i, 'of', self.nsteps, flush=True)
                pass

            return self.ln0, self.ln1, self.ln2auc, self.ln2lmp, self.ln3fncs, self.ln3gld

        if self.bFNCSSactive:
            print('finalizing FNCS', flush=True)
            # fncs.finalize()
            self.kill_all()
        return self.ln0, self.ln1, self.ln2auc, self.ln2lmp, self.ln3fncs, self.ln3gld

    def launch_all_f(self):
        """Launches the simulators, initializes FNCS and starts the animated plots
        """
        self.root.update()

        print('launching all simulators', flush=True)
        self.pids = []
        for row in self.commands:
            procargs = row['args']
            if sys.platform == 'win32':
                if procargs[0] == 'python3':
                    procargs[0] = 'python'  # python3 not defined on Windows
            procenv = os.environ.copy()
            if 'env' in row:
                for var in row['env']:
                    procenv[var[0]] = var[1]
            logfd = None
            if 'log' in row:
                logfd = open(row['log'], 'w')
            proc = subprocess.Popen(procargs, env=procenv, stdout=logfd)
            if "broker" in procargs[0]:
                self.broker = proc
            self.pids.append(proc)

        print('launched', len(self.pids), 'simulators', flush=True)
        self.root.update()

        os.environ["FNCS_CONFIG_FILE"] = self.msg_config
        fncs.initialize()
        self.bFNCSactive = True
        print('FNCS initialized', flush=True)

        self.nsteps = int(self.time_stop / self.yaml_delta)
        print('Number of time steps -> ' + str(self.nsteps), flush=True)
        self.idxlast = -1
        self.time_granted = 0
        self.btn2['state'] = tk.NORMAL
        self.btn1['state'] = tk.DISABLED
        self.btn0['state'] = tk.DISABLED

        self.reset_plot()
        ani = animation.FuncAnimation(self.fig, self.update_plots_f, frames=self.nsteps,
                                      blit=True, repeat=False, interval=0)
        self.fig.canvas.draw()

    def update_plots(self, i):
        """This function is called by Matplotlib for each animation frame

        Each time called, collect HELICS messages until the next time to plot
        has been reached. Then update the plot quantities and return the
        Line2D objects that have been updated for plotting. Check for new
        data outside the plotted vertical range, which triggers a full
        re-draw of the axes. On the last frame, finalize HELICS.

        Args:
          i (int): the animation frame number
        """
        # print ('.', end='', flush=True)
        # print('frame', i, 'of', self.nsteps, flush=True)

        bRedraw = False
        while self.time_granted <= self.time_stop:  # time in seconds
            try:  # when
                # find the time value and index into the time (X) array
                self.time_granted = int(helics.helicsFederateRequestTime(self.hFed, self.time_stop))
                self.root.update()
                idx = int(self.time_granted / self.yaml_delta)
                if idx <= self.idxlast:
                    continue
                self.idxlast = idx
                h = float(self.time_granted / 3600.0)
                self.hrs.append(h)

                # find the newest Y values
                v0 = 0.0
                v1 = 0.0
                v2auc = 0.0
                v2lmp = 0.0
                v3 = 0.0

                if self.sub_power_A:
                    if helics.helicsInputIsUpdated(self.sub_power_A):
                        v1 = 3.0 * helics.helicsInputGetDouble(self.sub_power_A) / 1000.0
                if helics.helicsInputIsUpdated(self.sub_TPV_7):
                    v0 = helics.helicsInputGetDouble(self.sub_TPV_7) / 133000.0
                if helics.helicsInputIsUpdated(self.sub_clear_price):
                    v2auc = helics.helicsInputGetDouble(self.sub_clear_price)
                if helics.helicsInputIsUpdated(self.sub_LMP_7):
                    v2lmp = helics.helicsInputGetDouble(self.sub_LMP_7)
                if self.sub_TEDP:
                    if helics.helicsInputIsUpdated(self.sub_TEDP):
                        v1 = helics.helicsInputGetDouble(self.sub_TEDP)
                if helics.helicsInputIsUpdated(self.sub_dist_load):
                    cval = helics.helicsInputGetComplex(self.sub_dist_load)
                    v3 = cval.real / 1.0e3
                    self.gld_load = v3

                # expand the Y axis limits if necessary, keeping a 10% padding around the range
                if v0 < self.y0min or v0 > self.y0max:
                    self.y0min, self.y0max = self.expand_limits(v0, self.y0min, self.y0max)
                    self.ax[0].set_ylim(self.y0min, self.y0max)
                    bRedraw = True
                if v1 < self.y1min or v1 > self.y1max:
                    self.y1min, self.y1max = self.expand_limits(v1, self.y1min, self.y1max)
                    self.ax[1].set_ylim(self.y1min, self.y1max)
                    bRedraw = True
                if v2auc > v2lmp:
                    v2max = v2auc
                    v2min = v2lmp
                else:
                    v2max = v2lmp
                    v2min = v2auc
                if v2min < self.y2min or v2max > self.y2max:
                    self.y2min, self.y2max = self.expand_limits(v2min, self.y2min, self.y2max)
                    self.y2min, self.y2max = self.expand_limits(v2max, self.y2min, self.y2max)
                    self.ax[2].set_ylim(self.y2min, self.y2max)
                    bRedraw = True
                if v3 < self.y3min or v3 > self.y3max:
                    self.y3min, self.y3max = self.expand_limits(v3, self.y3min, self.y3max)
                    self.ax[3].set_ylim(self.y3min, self.y3max)
                    bRedraw = True

                # update the Y axis data to draw
                self.y0.append(v0)  # Vpu
                self.y1.append(v1)  # school kW
                self.y2auc.append(v2auc)  # price
                self.y2lmp.append(v2lmp)  # LMP
                self.y3fncs.append(v3)  # this feeder load from HELICS (could be zero if no update)
                self.y3gld.append(self.gld_load)  # most recent feeder load from HELICS
                self.ln0.set_data(self.hrs, self.y0)
                self.ln1.set_data(self.hrs, self.y1)
                self.ln2auc.set_data(self.hrs, self.y2auc)
                self.ln2lmp.set_data(self.hrs, self.y2lmp)
                self.ln3fncs.set_data(self.hrs, self.y3fncs)
                self.ln3gld.set_data(self.hrs, self.y3gld)

                if bRedraw:
                    self.fig.canvas.draw()
            except:
                # print('exception frame', i, 'of', self.nsteps, flush=True)
                pass

            return self.ln0, self.ln1, self.ln2auc, self.ln2lmp, self.ln3fncs, self.ln3gld

        if self.bHELICSactive:
            print('finalizing HELICS', flush=True)
            # helics.helicsFederateDestroy(self.hFed)
            self.kill_all()
        return self.ln0, self.ln1, self.ln2auc, self.ln2lmp, self.ln3fncs, self.ln3gld

    def launch_all(self):
        """Launches the simulators, initializes HELICS and starts the animated plots
        """
        self.root.update()

        print('launching all simulators', flush=True)
        self.pids = []
        for row in self.commands:
            procargs = row['args']
            if sys.platform == 'win32':
                if procargs[0] == 'python3':
                    procargs[0] = 'python'  # python3 not defined on Windows
            procenv = os.environ.copy()
            if 'env' in row:
                for var in row['env']:
                    procenv[var[0]] = var[1]
            logfd = None
            if 'log' in row:
                logfd = open(row['log'], 'w')
            proc = subprocess.Popen(procargs, env=procenv, stdout=logfd)
            if "broker" in procargs[0]:
                self.broker = proc
            self.pids.append(proc)

        print('launched', len(self.pids), 'simulators', flush=True)
        self.root.update()

        self.hFed = None
        self.sub_power_A = None
        self.sub_TEDP = None
        self.sub_clear_price = None
        self.sub_LMP_7 = None
        self.sub_TPV_7 = None
        self.sub_dist_load = None

        # Initialize controllers, map HELICS values to Python attributes
        self.hFed = helics.helicsCreateValueFederateFromConfig(self.msg_config)
        subCount = helics.helicsFederateGetInputCount(self.hFed)
        for i in range(subCount):
            sub = helics.helicsFederateGetInputByIndex(self.hFed, i)
            key = helics.helicsInputGetName(sub)
            target = helics.helicsSubscriptionGetTarget(sub)
            print('HELICS subscription key', i, key, 'target', target, flush=True)
            if 'power_A' in target:
                self.sub_power_A = sub
            if 'three_phase_voltage_7' in target:
                self.sub_TPV_7 = sub
            if 'LMP_7' in target:
                self.sub_LMP_7 = sub
            if 'clear_price' in target:
                self.sub_clear_price = sub
            if 'WHOLE BUILDING' in target:
                self.sub_TEDP = sub
            if 'distribution_load' in target:
                self.sub_dist_load = sub
        print('Done HELICS subscriptions', flush=True)
        helics.helicsFederateEnterExecutingMode(self.hFed)
        self.bHELICSactive = True
        print('HELICS initialized', flush=True)

        self.nsteps = int(self.time_stop / self.yaml_delta)
        print('Number of time steps -> ' + str(self.nsteps), flush=True)
        self.idxlast = -1
        self.time_granted = 0
        self.btn2['state'] = tk.NORMAL
        self.btn1['state'] = tk.DISABLED
        self.btn0['state'] = tk.DISABLED

        self.reset_plot()
        ani = animation.FuncAnimation(self.fig, self.update_plots, frames=self.nsteps,
                                      blit=True, repeat=False, interval=0)
        self.fig.canvas.draw()


def show_tesp_monitor(HELICS=True):
    """Creates and displays the monitor GUI
    """
    global helics, fncs
    if HELICS:
        import helics as helics
    else:
        import tesp_support.fncs as fncs

    root = tk.Tk()
    root.title('Transactive Energy Simulation Platform: Solution Monitor')
    my_gui = TespMonitorGUI(root, HELICS)
    root.update()
    while True:
        try:
            root.mainloop()
            break
        except UnicodeDecodeError:
            pass
