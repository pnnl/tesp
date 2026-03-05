# Copyright (c) 2017-2025 Battelle Memorial Institute
# file: tesp_monitor.py
"""
This tesp_monitor.py is adapted from original/tesp_monitor.py to work with DSOT.
The monitor is designed follow a DSOT simulation run and plot the following 
values as they are received:
    - day-ahead LMPs (DA LMP), 
    - the real-time LMPs (RT LMP), 
    - the market clearing price (Clearing Price), and 
    - the substation load (Total Feeder Load)

Contains two classes:
  - TespMonitorJSON: Creates the monitor.json file(s) describing the 
  subscriptions used by the tesp monitor GUI (called by prepare_case_glm_dsot.py)
  - TespMonitorGUI: calls the run script to start the TESP simulation and then
  creates and launches the GUI to monitor its progress (launched by tesp_monitor.sh)

To use this monitor, set "monitor" in the case config file to "true". That will
call tesp_monitor.py to create the required monitor config files. 

TODO: tesp_monitor works with HELICS messenger, the FNCS version needs debugging.

Then, from the case folder, run `./tesp_monitor.sh`. The GUI will launch and ask
you to select the monitor config file you wish to use. The default is "monitor.json", 
which points to DSO 1. To change which substation to monitor, edit the file to 
specify the DSO you wish, like: "DSO_{dso_num}_monitor_helics.json

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
from datetime import datetime
from api.parse_helpers import parse_kw
from api.helpers import HelicsMsg
import matplotlib

try:
    matplotlib.use('TkAgg')
except Exception:
    pass
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
import matplotlib.animation as animation
import matplotlib.pyplot as plt


class TespMonitorJSON:
    """Creates required files for TespMonitorGUI while preparing the DSOT case:
    - monitor.[json/yaml] config files required to launch the GUI. 
    - DSO_[dso_num]_monitor_[helics/fncs].json files specifying the subscribed 
       values to be plotted by the GUI
    
    Adapted from tesp_support/original/tesp_case.py: write_tesp_case()

    * DSO_[dso_num]_monitor_[helics/fncs].json: configuration data for the 
       solution monitor GUI
    * monitor.json: HELICS subscriptions and time step for the solution 
        monitor GUI
    * monitor.yaml: FNCS subscriptions and time step for the solution 
        monitor GUI

    Returns:
        None
    """

    def write_monitor(config, caseName):
        """
        Writes either monitor.json or monitor.yaml depending on whether messenger
        is HELICS or FNCS.
        
        Args:
            config (dict): Configuration
            caseName (str): Name of simulation or test case
        """
        mtr_federate = "monitor"
        casePath = os.path.expandvars("$TESPDIR/examples/analysis/glm_dsot/code/")
        casePath = os.path.join(casePath, caseName)
        StartTime = config['StartTime']
        EndTime = config['EndTime']
        time_fmt = '%Y-%m-%d %H:%M:%S'
        dt1 = datetime.strptime(StartTime, time_fmt)
        dt2 = datetime.strptime(EndTime, time_fmt)
        seconds = int((dt2 - dt1).total_seconds())

        if sys.platform == 'win32':
            pycall = 'python'
        else:
            pycall = 'python3'

        if config["messenger"] == 'FNCS':
            # write a YAML for the solution monitor
            yamlstr = """name: """ + mtr_federate + """
    time_delta: """ + str(config['AgentPrep']['HVAC']['MarketClearingPeriod']) + """s
    broker: tcp://localhost:""" + str(config['port']) + """
    aggregate_sub: true
    values:
    TPV_""" + dso_num + """:
        topic: """ """pypower/lmp_da""" + dso_num + """
        default: 0
        type: double
        list: false
    LMP_""" + dso_num + """:
        topic: """  """pypower/lmp_rt_""" + dso_num + """
        default: 0
        type: double
        list: false
    clear_price:
        topic: """ """/pypower/cleared_q_rt_ """ + dso_num + """
        default: 0
        type: double
        list: false
    distribution_load:
        topic: """  """/gldSubstation_ """ + dso_num + """
        default: 0
        type: complex
        list: false
    """
            
            for dso_num in range (1,9):
                dso_num = str(dso_num)
                monitor_gui_file = "monitor.json" # GUI launcher config
                monitor_fed_file = f"DSO_{dso_num}_monitor_fncs.yaml"  # federate config

                op = open(os.path.join(caseName, monitor_fed_file), 'w')
                print(yamlstr, file=op)
                op.close()

            cmds = {'time_stop': seconds,
                    'yaml_delta': int(config['AgentPrep']['HVAC']['MarketClearingPeriod']),
                    'helics_config': 'DSO_1_monitor_helics.json'}
            
            op = open(caseName + monitor_gui_file, 'w')
            json.dump(cmds, op, indent=2)
            op.close()

        elif config["messenger"] == 'HELICS':
            for dso_num in range(1,9):
                dso_num = str(dso_num)
                monitor_gui_file = "monitor.json" # GUI launcher config
                monitor_fed_file = f"DSO_{dso_num}_monitor_helics.json"  # federate config
                # Write HELICS federate config for the monitor
                ppc = HelicsMsg(mtr_federate, config['AgentPrep']['HVAC']['MarketClearingPeriod'])
                ppc.subs_n("pypower/lmp_da_" + dso_num, "string")
                ppc.subs_n("pypower/lmp_rt_" + dso_num, "string")
                ppc.subs_n("pypower/cleared_q_rt_" + dso_num, "string")
                ppc.subs_n("gldSubstation_" + dso_num + "/gld_load", "string")
                ppc.write_file(os.path.join(caseName, monitor_fed_file))

            cmds = {'time_stop': seconds,
                'yaml_delta': int(config['AgentPrep']['HVAC']['MarketClearingPeriod']),
                'helics_config': 'DSO_1_monitor_helics.json'}

            with open(os.path.join(caseName, monitor_gui_file), 'w') as op:
                json.dump(cmds, op, indent=2)    

class TespMonitorGUI:
    """ Manages a GUI with 4 plotted variables, and buttons to stop the monitor
    The GUI calls the ./run.sh to run the simulation, then reads the json monitor
    config file assigning the HELICS/FNCS federates, or the YAML monitor config 
    file with HELICS/FNCS subscriptions to update the solution status.
     
    Both JSON and YAML files are written by TespMonitorJSON. The plotted 
    variables provide a sign-of-life and sign-of-stability indication for each 
    of the major federates in the DSOT simulation, namely GridLAB-D, PYPOWER, 
    and the substation_loop that manages a market with multiple agents. 

    If a solution appears to be unstable or must be stopped for any other reason,
    exiting the solution monitor will kill the run.

    The plots are created and updated with animated and bit-blitted Matplotlib
    graphs hosted on a TkInter GUI. When the JSON and YAML files are loaded,
    the x axis is laid out to match the total TESP simulation time range.

    Args:


    Attributes:
      root (Tk): the TCL Tk toolkit instance
      top (Window): the top-level TCL Tk Window
      labelvar (StringVar): used to display the monitor JSON configuration file 
        path
      hrs ([float]): x-axis data array for time in hours, shared by all plots
      y0da ([float]): y-axis data array for day-ahead LMPs
      y1rt ([float]): y-axis data array for the real-time LMPs
      y2lmp ([float]): y-axis data array for PYPOWER LMP
      y2auc ([float]): TODO: y-axis data array for auction cleared_price
      y3fncs ([float]): y-axis data array for GridLAB-D load via HELICS/FNCS
      y3gld ([float]): TODO: y-axis data array for sample-and-hold GridLAB-D load
      gld_load (float): the most recent load published by GridLAB-D; due to the 
        deadband, this value isn't necessary published at every HELICS/FNCS time step
      y0damin (float): the first y axis minimum value
      y0damax (float): the first y axis maximum value
      y1rtmin (float): the second y axis minimum value
      y1rtmax (float): the second y axis maximum value
      y2min (float): the third y axis minimum value
      y2max (float): the third y axis maximum value
      y3min (float): the fourth y axis minimum value
      y3max (float): the fourth y axis maximum value
      hour_stop (float): the maximum x axis time value to plot
      ln0da (Line2D): the plotted PYPOWER bus voltage, color GREEN
      ln1rt (Line2D): the plotted EnergyPlus load, color RED
      ln2lmp (Line2D): the plotted PYPOWER locational marginal price (LMP), 
        color BLUE
      ln2auc (Line2D): the plotted simple_auction cleared_price, color BLACK
      ln3gld (Line2D): the plotted sample-and-hold GridLAB-D substation load, 
        color MAGENTA
      ln3fncs (Line2D): the plotted GridLAB-D substation load published via FNCS;
        may be zero if not published for the current animation frame, color CYAN
      fig (Figure): animated Matplotlib figure hosted on the GUI
      ax (Axes): set of 4 xy axes to plot on
      canvas (FigureCanvasTkAgg): a TCL Tk canvas that can host Matplotlib
      bFNCSactive (bool): True if a TESP simulation is running with other FNCS 
        federates, False if not
      bHELICSactive (bool): True if a TESP simulation is running with other 
        HELICS federates, False if not
    """

    def __init__(self, master):
        self.root = master
        self.HELICS = None
        self.pids = []
        self.broker = None
        self.idxlast = -1
        self.time_granted = 0
        self.hFed = None
        self.bFNCSactive = False
        self.bHELICSactive = False
        # monitor HELICS inputs
        self.sub_lmp_da = None
        self.sub_lmp_rt = None
        self.sub_cleared_q_rt = None
        self.sub_gld_load = None
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.top = self.root.winfo_toplevel()
        self.top.rowconfigure(0, weight=1)
        self.top.columnconfigure(0, weight=1)

        ttk.Style().configure('TButton', foreground='blue')
        self.btn0 = ttk.Button(self.root, text='Open...', command=self.OpenConfig)
        self.btn0.grid(row=0, column=0, sticky=tk.NSEW)
        self.filename = 'monitor.json'
        self.btn1 = ttk.Button(self.root, text='Start All', command=self.start_all, state=tk.DISABLED)
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
        self.da_hrs = [0.0]
        self.y0da = [1.0]
        self.y1rt = [0.0]
        self.y2lmp = [0.0]
        self.y2auc = [0.0]
        self.y3fncs = [0.0]  # GridLAB-D publishes only when changed
        self.gld_load = 0.0
        self.y3gld = [0.0]
        self.y0damin = 1.0
        self.y0damax = 1.0
        self.y1rtmin = 0.0
        self.y1rtmax = 0.0
        self.y2min = 0.0
        self.y2max = 0.0
        self.y3min = 0.0
        self.y3max = 0.0

        self.ln0da = Line2D(self.hrs, self.y0da, color='green')
        self.ln1rt = Line2D(self.hrs, self.y1rt, color='red')
        self.ln2auc = Line2D(self.hrs, self.y2auc, color='black')
        self.ln2lmp = Line2D(self.hrs, self.y2lmp, color='blue')
        self.ln3fncs = Line2D(self.hrs, self.y3fncs, color='cyan')
        self.ln3gld = Line2D(self.hrs, self.y3gld, color='magenta')

        self.ax[0].clear()
        self.ax[0].add_line(self.ln0da)
        self.ax[0].set_ylabel('[$]')
        self.ax[0].set_title('DA LMP', fontsize=10)

        self.ax[1].clear()
        self.ax[1].add_line(self.ln1rt)
        self.ax[1].set_ylabel('[$]')
        self.ax[1].set_title('RT LMP', fontsize=10)

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
        """ Verify whether the user wants to stop TESP simulations before exiting
            the monitor

        This monitor is itself a FNCS federate, so it can not be shut down 
            without shutting down all other FNCS federates in the TESP simulation.
        """
        if messagebox.askokcancel('Quit', 'Do you want to close this window? This is likely to stop all simulations.'):
            self.Quit()

    def Quit(self):
        """ Shuts down this monitor, and also shuts down FNCS/HELICS if active
        """
        if self.bFNCSactive or self.bHELICSactive:
            self.kill_all()

        self.root.quit()
        self.root.destroy()

    def OpenConfig(self):
        """ Read the JSON configuration file for this monitor, and initialize the
            plot axes
        """
        fname = filedialog.askopenfilename(initialdir='.',
                                           initialfile=self.filename,
                                           title='Open Monitor Configuration',
                                           filetypes=[('JSON files', '*.json'),
                                                      ('YAML files', ('*.yaml', '*.yml')),
                                                      ('all files', '*.*')],
                                           defaultextension='json')
        
        ext = os.path.splitext(fname)[1].lower()

        if ext == ".json":
            self.HELICS = True

        elif ext in [".yaml", ".yml"]:
            self.HELICS = False

        with open(fname) as lp:
            cfg = json.loads(lp.read())

        if self.HELICS:
            self.msg_config = cfg['helics_config']

        else:
            self.msg_config = cfg['fncs_config']

        self.time_stop = int(cfg['time_stop'])
        self.yaml_delta = int(cfg['yaml_delta'])
        self.hour_stop = float(self.time_stop / 3600.0)
        dirpath = os.path.dirname(fname)
        os.chdir(dirpath)
        self.labelvar.set(dirpath)
        self.btn1['state'] = tk.NORMAL
        
    def start_all(self):
        if self.HELICS:
            self.launch_all()
        else:
            self.launch_all_f()

    def kill_all(self):
        """ Shut down all FNCS/HELICS federates in TESP, except for this monitor
        """
        self.root.update()
        for proc in self.pids:
            if proc is None:
                continue
            if self.broker is not None and proc == self.broker:
                continue
            print('Trying to kill', getattr(proc, 'pid', proc), flush=True)
            try:
                if hasattr(proc, 'pid'):
                    os.kill(proc.pid, 9)
                    os.wait()
            except Exception:
                pass
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
        # it seems there are two HELICS broker processes
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
        """ Whenever a variable meets a vertical axis limit, expand the limits 
            with 10% padding above and below

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
        """
        This function is called by Matplotlib for each animation frame
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
        artists = self.ln0da, self.ln1rt, self.ln2auc, self.ln2lmp, self.ln3fncs, self.ln3gld
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
                if v0 < self.y0damin or v0 > self.y0damax:
                    self.y0damin, self.y0damax = self.expand_limits(v0, self.y0damin, self.y0damax)
                    self.ax[0].set_ylim(self.y0damin, self.y0damax)
                    bRedraw = True
                if v1 < self.y1rtmin or v1 > self.y1rtmax:
                    self.y1rtmin, self.y1rtmax = self.expand_limits(v1, self.y1rtmin, self.y1rtmax)
                    self.ax[1].set_ylim(self.y1rtmin, self.y1rtmax)
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
                self.y0da.append(v0)  # Vpu
                self.y1rt.append(v1)  # school kW
                self.y2auc.append(v2auc)  # price
                self.y2lmp.append(v2lmp)  # LMP
                self.y3fncs.append(v3)  # this feeder load from FNCS (could be zero if no update)
                self.y3gld.append(self.gld_load)  # most recent feeder load from FNCS
                self.ln0da.set_data(self.hrs, self.y0da)
                self.ln1rt.set_data(self.hrs, self.y1rt)
                self.ln2auc.set_data(self.hrs, self.y2auc)
                self.ln2lmp.set_data(self.hrs, self.y2lmp)
                self.ln3fncs.set_data(self.hrs, self.y3fncs)
                self.ln3gld.set_data(self.hrs, self.y3gld)
                if bRedraw:
                    self.fig.canvas.draw()
            except Exception:
                # print('exception frame', i, 'of', self.nsteps, flush=True)
                pass
            return artists
        if self.bFNCSSactive:
            print('finalizing FNCS', flush=True)
            # fncs.finalize()
            self.kill_all()
        return artists
    
    def launch_all_f(self):
        """ Launches the simulators, initializes FNCS and starts the animated plots
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
            try:
                proc = subprocess.Popen(procargs, env=procenv, stdout=logfd, cwd = os.getcwd())
            except FileNotFoundError:
                #print(f'procargs = {procargs}, env = {procenv}, stdout = {logfd}')
                print(f"Couldn't find proc for {row}")
                proc = "tcp://localhost:5570" 
            if "broker" in procargs[0]:
                self.broker = proc

            self.pids.append(self.broker)
            
        print('launched', len(self.pids), 'simulators', flush=True)
        self.root.update()

        os.environ["FNCS_CONFIG_FILE"] = self.msg_config
        fncs.initialize()
        self.bFNCSactive = True
        print('FNCS initialized', flush=True)
        
        # Updates when the market clears (yaml_delta)
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
        """
        This function is called by Matplotlib for each animation frame

        Each time called, collect HELICS messages until the next time to plot
        has been reached. Then update the plot quantities and return the
        Line2D objects that have been updated for plotting. Check for new
        data outside the plotted vertical range, which triggers a full
        re-draw of the axes. On the last frame, finalize HELICS.

        Args:
          i (int): the animation frame number
        """
        import ast

        artists = self.ln0da, self.ln1rt, self.ln2auc, self.ln2lmp, self.ln3fncs, self.ln3gld
        # print ('.', end='', flush=True)
        # print('frame', i, 'of', self.nsteps, flush=True)
        if not self.bHELICSactive:
            # Nothing to do; simulation has been finalized
            return artists
    
        bRedraw = True

        # request time only up to next plotting instant, e.g. (i+1)*self.yaml_delta
        request_time = min(self.time_stop, (i + 1) * self.yaml_delta)
        # find the time value and index into the time (X) array
        self.time_granted = int(helics.helicsFederateRequestTime(self.hFed, request_time))
        self.root.update()

        # Debugging: if your GUI exits too soon, check time request against granted
        print(f'time requested: {request_time}. time granted: {self.time_granted}. time stop: {self.time_stop}')
        v_da = 0.0
        v_da_24 = 0.0
        v_rt = 0.0
        v_clear = 0.0
        v_load = 0.0
            
        # i goes from 0 to self.nsteps - 1
        if self.time_granted >= self.time_stop:
            if self.bHELICSactive:
                print('time granted >= time_stop: finalizing HELICS', flush=True)
                self.kill_all()
            return artists
        
        #while self.time_granted <= self.time_stop    
        while request_time < self.time_stop:
            self.time_granted = int(helics.helicsFederateRequestTime(self.hFed, request_time))
            self.root.update()
            #print(f'time requested: {request_time}. time granted: {self.time_granted}')
            try:
                
                idx = int(self.time_granted / self.yaml_delta)
                if idx <= self.idxlast:
                    return artists
                self.idxlast = idx

                h = float(self.time_granted / 3600.0)
                self.hrs.append(h)
                
                # find the newest Y values
                if self.sub_lmp_da and helics.helicsInputIsUpdated(self.sub_lmp_da):
                    v_da = helics.helicsInputGetString(self.sub_lmp_da)
                    print(f"frame {i}, {h} hours, "f"v_da={v_da}", flush=True)
                if self.sub_lmp_rt and helics.helicsInputIsUpdated(self.sub_lmp_rt):
                    v_rt = helics.helicsInputGetString(self.sub_lmp_rt)
                    print(f"frame {i}, {h} hours, "f"v_rt={v_rt}", flush=True)
                if self.sub_cleared_q_rt and helics.helicsInputIsUpdated(self.sub_cleared_q_rt):
                    v_clear = helics.helicsInputGetString(self.sub_cleared_q_rt)
                    print(f"frame {i}, {h} hours, "f"v_clear={v_clear}", flush=True)
                if self.sub_gld_load and helics.helicsInputIsUpdated(self.sub_gld_load):
                   v_load = helics.helicsInputGetString(self.sub_gld_load)
                   print(f"frame {i}, {h} hours, "f"v_load={v_load}", flush=True)
                   sub_load = v_load


                # Debugging: Note that this will print many 0s when values do not change
                #print(f"frame {i}, time {self.time_granted}, "f"v_da={v_da}, v_rt={v_rt}, v_clear={v_clear}, v_load={v_load}", flush=True)


                # update the Y axis data to draw
                # If there is no change in value, HELICS does not update
                # Only show changes in plots
                if v_da != 0.0:
                    v_da_24 = list(map(float, ast.literal_eval(v_da)))
                    self.y0da.extend(v_da_24)
                    self.da_hrs.extend(h + k for k in range(len(v_da_24)))
                    # expand the Y axis limits if necessary, keeping a 10% padding around the range
                    if min(v_da_24) < self.y0damin or max(v_da_24) > self.y0damax:
                        self.y0damin, self.y0damax = self.expand_limits(min(v_da_24), self.y0damin, self.y0damax)
                        self.y0damin, self.y0damax = self.expand_limits(max(v_da_24), self.y0damin, self.y0damax)
                        self.ax[0].set_ylim(self.y0damin, self.y0damax)
                        bRedraw = True
                # else: 
                #     self.da_hrs = self.hrs
                #     self.y0da.append(self.y0da[-1])
                
                if v_rt != 0.0:
                    v_rt_fl = float(ast.literal_eval(v_rt)[0])
                    self.y1rt.append(v_rt_fl)
                    if v_rt_fl < self.y1rtmin or v_rt_fl > self.y1rtmax:
                        self.y1rtmin, self.y1rtmax = self.expand_limits(v_rt_fl, self.y1rtmin, self.y1rtmax)
                        self.ax[1].set_ylim(self.y1rtmin, self.y1rtmax)
                        bRedraw = True
                else: 
                    self.y1rt.append(self.y1rt[-1])
                
                if v_clear != 0.0:
                    v_clear_fl = float(v_clear)
                    self.y2auc.append(v_clear_fl)
                    self.y2lmp.append(v_clear_fl)
                    if v_clear_fl < self.y2min or v_clear_fl > self.y2max:
                        self.y2min, self.y2max = self.expand_limits(v_clear_fl, self.y2min, self.y2max)
                        self.ax[2].set_ylim(self.y2min, self.y2max)
                        bRedraw = True
                else: 
                    self.y2auc.append(self.y2auc[-1])
                    self.y2lmp.append(self.y2lmp[-1]) 
                
                if v_load != 0:
                    # Handle substation load as both a string and complex value
                    v_load_fl = ast.literal_eval(sub_load)
                    v_load_real = v_load_fl[0]
                    #print(f'v_load_real: {v_load_real}, type: {type(v_load_real)}')
                    v_load_kW = v_load_real / 1.0e3
                    self.gld_load = v_load_kW
                    self.y3fncs.append(v_load_kW) # feeder load from HELICS (could be zero if no update)
                    self.y3gld.append(self.gld_load)  # most recent feeder load from HELICS

                    if v_load_kW < self.y3min or v_load_kW > self.y3max:
                        self.y3min, self.y3max = self.expand_limits(v_load_kW, self.y3min, self.y3max)
                        self.ax[3].set_ylim(self.y3min, self.y3max)
                        bRedraw = True
                else:
                    v_load_kW = 0.0
                    self.gld_load = 0.0
                    # feeder load from HELICS could be zero if no update
                    self.y3fncs.append(self.y3fncs[-1]) 
                    self.y3gld.append(self.y3gld[-1])

                self.ln0da.set_data(self.da_hrs, self.y0da)
                self.ln1rt.set_data(self.hrs, self.y1rt)
                self.ln2auc.set_data(self.hrs, self.y2auc)
                self.ln2lmp.set_data(self.hrs, self.y2lmp)
                self.ln3fncs.set_data(self.hrs, self.y3fncs)
                self.ln3gld.set_data(self.hrs, self.y3gld)
                
                if bRedraw:
                    self.fig.canvas.draw()
                    bRedraw = False

            
            except Exception as e:
                print("Exception in update_plots:", repr(e), flush=True)
            
            return artists

        
    def launch_all(self):
        """ Launches the simulators, initializes HELICS and starts the animated 
            plots
        """
        import socket, time
        self.root.update()
        self.pids = []

        # Make sure nothing else is running (most relevant when debugging)
        subprocess.run(["pkill", "-f", "helics_broker"], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, check=False)
        subprocess.run(["pkill", "-f", "helics_broker_server"], stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, check=False)
        time.sleep(5)
        
        # Start the run
        print('Launching simulation using run.sh', flush=True)
        proc = subprocess.Popen(['bash', './run.sh'], stdout=open('run.log', 'w'))
        self.pids.append(proc)
        self.broker = proc
        self.root.update()

        # Wait for the HELICS federation to start up
        time.sleep(60)
        print('Connecting to the broker')

        def wait_port(host, port, timeout):
            t0 = time.time()
            while time.time() - t0 < timeout:
                try:
                    with socket.create_connection((host, port), timeout=1):
                        #print(subprocess.check_output(["bash","-lc","ss -ltnp | grep 23405"], text=True))
                        print("Connected.")
                        return True
                except OSError:
                    time.sleep(0.2)
            return False
        
        # Make sure we're connected
        if not wait_port("127.0.0.1", 23405, 120):
            raise RuntimeError("Broker did not open port 23405")
        self.root.update()

        # Initialize tesp_monitor
        from pathlib import Path
        config_path = Path(self.msg_config)
        print("Creating HELICS monitor federate from:", config_path, flush=True)
    
        self.hFed = None
        self.sub_lmp_da = None
        self.sub_lmp_rt = None
        self.sub_clear_price = None
        self.sub_cleared_q_rt = None
        self.sub_gld_load = None
        self.sub_dist_load = None

        # Initialize controllers, map HELICS values to Python attributes
        self.hFed = helics.helicsCreateValueFederateFromConfig(str(config_path))
        subCount = helics.helicsFederateGetInputCount(self.hFed)
        for i in range(subCount):
            sub = helics.helicsFederateGetInputByIndex(self.hFed, i)
            key = helics.helicsInputGetName(sub)
            target = helics.helicsInputGetTarget(sub)

            print("Monitor subscription:", i, "key:", key, "target:", target, flush=True)
            if target.__contains__("lmp_da_"):
                self.sub_lmp_da = sub
            elif target.__contains__("lmp_rt_"):
                self.sub_lmp_rt = sub
            elif target.__contains__("cleared_q_rt_"):
                self.sub_cleared_q_rt = sub
            elif target.__contains__("gld_load"):
                self.sub_gld_load = sub

        self.root.update()
        print('Done securing HELICS subscriptions', flush=True)
        helics.helicsFederateEnterExecutingMode(self.hFed)

        self.bHELICSactive = True
        print('HELICS initialized', flush=True)

        # Updates when the market clears (yaml_delta)
        self.nsteps = int(self.time_stop / self.yaml_delta)
        print('Simulation number of time steps: ' + str(self.nsteps), flush=True)
        self.idxlast = -1
        self.time_granted = 0
        self.btn2['state'] = tk.NORMAL
        self.btn1['state'] = tk.DISABLED
        self.btn0['state'] = tk.DISABLED

        self.reset_plot()
        ani = animation.FuncAnimation(self.fig, self.update_plots, frames=self.nsteps,
                                      blit=True, repeat=False, interval=0)
        self.fig.canvas.draw()

def show_tesp_monitor():
    """ Creates and displays the monitor GUI
    """
    global helics, fncs
    import helics
    from original import fncs as fncs

    root = tk.Tk()
    root.title('Transactive Energy Simulation Platform: Solution Monitor')
    my_gui = TespMonitorGUI(root)
    root.update()
    while True:
        try:
            root.mainloop()
            break
        except UnicodeDecodeError:
            pass

if __name__ == '__main__':
    show_tesp_monitor()