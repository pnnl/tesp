# Copyright (C) 2018-2022 Battelle Memorial Institute
# file: tesp_monitor_ercot.py
"""Presents a GUI to launch a TESP simulation and monitor its progress

This version differs from the one in *tesp_monitor*, in that the
user can select the FNCS federate and topic to plot. The number of
monitored plots is still fixed at 4.

Public Functions:
  :show_tesp_monitor: Initializes and runs the monitor GUI

References:
  `Graphical User Interfaces with Tk <https://docs.python.org/3/library/tk.html>`_

  `Matplotlib Animation <https://matplotlib.org/api/animation_api.html>`_
"""
import os
import json
import yaml
import subprocess

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox

import tesp_support.fncs as fncs
from .helpers import parse_kw

import matplotlib
try:
    matplotlib.use('TkAgg')
except:
    pass
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import matplotlib.animation as animation
import matplotlib.pyplot as plt


class TespMonitorGUI:
    """Version of the monitor GUI that hosts 4 choosable plots

    Args:
        master:

    Attributes:
        root (Tk): the TCL Tk toolkit instance
        top (Window): the top-level TCL Tk Window
        labelvar (StringVar): used to display the monitor JSON configuration file path
        plot0 (ChoosablePlot): first plot
        plot1 (ChoosablePlot): second plot
        plot2 (ChoosablePlot): third plot
        plot3 (ChoosablePlot): fourth plot
        topicDict:
        plots (Frame):
        scrollbar (Scrollbar):
        frameInCanvas (Frame):
        canvas (FigureCanvasTkAgg): a TCL Tk canvas that can host Matplotlib
        bFNCSactive (Boolean): True if a TESP simulation is running with other FNCS federates, False if not
    """
    def __init__(self, master):
        self.root = master
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.topicDict = {}
        # self.topicDict = {'pypower/LMP_Bus8' : 'LMP8',
        #                   'gridlabdBus8/distribution_load' : 'distribution_load8',
        #                   'pypower/three_phase_voltage_Bus1' : 'vpos1',
        #                   'pypower/three_phase_voltage_Bus8' : 'vpos8'}

        self.top = self.root.winfo_toplevel()
        self.top.rowconfigure(0, weight=1)
        self.top.columnconfigure(0, weight=1)

        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=0)
        self.root.columnconfigure(2, weight=0)
        self.root.columnconfigure(3, weight=0)
        self.root.columnconfigure(4, weight=1)

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

        self.plots = tk.Frame(self.root, bg="#ffffff")
        self.plots.grid(row=1, column=0, columnspan=5, sticky=tk.NSEW)
        self.plots.grid_rowconfigure(0, weight=1)
        self.plots.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.plots, borderwidth=0, background="#ffffff")
        self.canvas.grid(row=0, column=0, sticky=tk.NSEW)
        self.scrollbar = tk.Scrollbar(self.plots, command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.frameInCanvas = tk.Frame(self.canvas, background="#ffffff")
        self.frameInCanvas.grid(row=0, column=0, sticky='news')
        self.canvas.create_window((0, 0), window=self.frameInCanvas, anchor=tk.NW, tags="self.frameInCanvas")
        self.frameInCanvas.bind("<Configure>", self.onFrameConfigure)

        self.canvas.rowconfigure(0, weight=0)
        self.canvas.columnconfigure(0, weight=0)
        self.frameInCanvas.rowconfigure(0, weight=1)
        self.frameInCanvas.rowconfigure(1, weight=1)
        self.frameInCanvas.rowconfigure(2, weight=1)
        self.frameInCanvas.rowconfigure(3, weight=2)
        self.frameInCanvas.columnconfigure(0, weight=1)

        self.plot0 = ChoosablePlot(self.frameInCanvas, color='green', topicDict=self.topicDict)
        self.plot0.grid(row=0, sticky=tk.NSEW)
        self.plot1 = ChoosablePlot(self.frameInCanvas, color='red', topicDict=self.topicDict)
        self.plot1.grid(row=1, sticky=tk.NSEW)
        self.plot2 = ChoosablePlot(self.frameInCanvas, color='blue', topicDict=self.topicDict)
        self.plot2.grid(row=2, sticky=tk.NSEW)
        self.plot3 = ChoosablePlot(self.frameInCanvas, color='magenta', xLabel='Hours', topicDict=self.topicDict)
        self.plot3.grid(row=3, sticky=tk.NSEW, pady=(0, 50))
        # self.plot0.pack()
        # self.plot1.pack()
        # self.plot2.pack()
        # self.plot3.pack()
        # self.fig0, self.ax0 = plt.subplots(1,1)
        # cax = plt.gca()
        # cax.axes.xaxis.set_ticklabels([])
        # self.fig1, self.ax1 = plt.subplots(1,1)
        # cax = plt.gca()
        # cax.axes.xaxis.set_ticklabels([])
        # self.fig2, self.ax2 = plt.subplots(1,1)
        # cax = plt.gca()
        # cax.axes.xaxis.set_ticklabels([])
        # self.fig3, self.ax3 = plt.subplots(1,1)
        # cax = plt.gca()
        # cax.axes.xaxis.set_ticklabels([])
        # plt.subplots_adjust (hspace = 0.35)
        #
        # self.hrs = [0.0]
        # self.y0 = [0.0]
        # self.y1 = [0.0]
        # self.y2 = [0.0]
        # self.y3 = [0.0]
        # self.y0min = 0
        # self.y0max = 2
        # self.y1min = 0.0
        # self.y1max = 2
        # self.y2min = 0.0
        # self.y2max = 0.0
        # self.y3min = 0.0
        # self.y3max = 0.0
        # self.hour_stop = 4.0
        #
        # self.ln0 = Line2D (self.hrs, self.y0, color='red')
        # self.ln1 = Line2D (self.hrs, self.y1, color='red')
        # self.ln2 = Line2D (self.hrs, self.y2, color='blue')
        # self.ln3 = Line2D (self.hrs, self.y3, color='magenta')
        #
        # self.ax0.add_line (self.ln0)
        # self.ax0.set_ylabel('[pu]')
        # self.ax0.set_title ('vpos8', fontsize=10)
        #
        # self.ax1.add_line (self.ln1)
        # self.ax1.set_ylabel('[pu]')
        # self.ax1.set_title ('vpos1', fontsize=10)
        #
        # self.ax2.add_line (self.ln2)
        # self.ax2.set_ylabel('[$]')
        # self.ax2.set_title ('LMP8', fontsize=10)
        #
        # self.ax3.add_line (self.ln3)
        # self.ax3.set_ylabel('[kW]')
        # self.ax3.set_title ('distribution_load8', fontsize=10)
        #
        # self.ax3.set_xlabel('Hours')
        #
        # self.canvas0 = FigureCanvasTkAgg(self.fig0, self.frame)
        # self.canvas0.draw()
        # self.canvas0.get_tk_widget().grid(row=0, sticky = tk.W + tk.E + tk.N + tk.S)
        #
        # self.canvas1 = FigureCanvasTkAgg(self.fig1, self.frame)
        # self.canvas1.draw()
        # self.canvas1.get_tk_widget().grid(row=1, sticky = tk.W + tk.E + tk.N + tk.S)
        #
        # self.canvas2 = FigureCanvasTkAgg(self.fig2, self.frame)
        # self.canvas2.draw()
        # self.canvas2.get_tk_widget().grid(row=2, sticky = tk.W + tk.E + tk.N + tk.S)
        #
        # self.canvas3 = FigureCanvasTkAgg(self.fig3, self.frame)
        # self.canvas3.draw()
        # self.canvas3.get_tk_widget().grid(row=3, sticky = tk.W + tk.E + tk.N + tk.S)
        self.bFNCSactive = False
        self.canvas.config(width=self.frameInCanvas.winfo_width(), height=self.frameInCanvas.winfo_height())

        # topics = fncs.get_keyss()
        # for topic in topics:
        #   pass

    def onFrameConfigure(self, event):
        """Reset the scroll region to encompass the inner frame
        """
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_closing(self):
        """Verify whether the user wants to stop TESP simulations before exiting the monitor

        This monitor is itself a FNCS federate, so it can not be shut down without shutting
        down all other FNCS federates in the TESP simulation.
        """
        if messagebox.askokcancel('Quit', 'Do you want to close this window? This is likely to stop all simulations.'):
            self.root.quit()
            self.root.destroy()
            if self.bFNCSactive:
                fncs.finalize()
                self.bFNCSactive = False

    def Quit(self):
        """Shuts down this monitor, and also shuts down FNCS if active
        """
        self.root.quit()
        self.root.destroy()
        if self.bFNCSactive:
            fncs.finalize()
            self.bFNCSactive = False

    def OpenConfig(self):
        """Read the JSON configuration file for this monitor, and initialize the plot axes
        """ 
        fname = filedialog.askopenfilename(initialdir='.',
                                           initialfile='tesp_monitor_ercot.json',
                                           title='Open JSON Monitor Configuration',
                                           filetypes=(('JSON files', '*.json'), ('all files', '*.*')),
                                           defaultextension='json')
        lp = open(fname)
        cfg = json.loads(lp.read())
        self.commands = cfg['commands']
        # for row in self.commands:
        #     args = row['args']
        #     if "fncs_broker" in args:
        #         for en in row['env']:
        #             if "FNCS_CONFIG_FILE" in en:
        #                 self.fncsyaml = en[1]
        #                 break
        #         else:
        #             continue
        #         break
        self.fncsyaml = os.environ['FNCS_CONFIG_FILE']
        if os.path.isfile(self.fncsyaml):
            with open(self.fncsyaml, 'r') as stream:
                try:
                    dd = yaml.load(stream)['values'].items()
                    self.topicDict = dict((v['topic'], k) for k, v in dd)
                except yaml.YAMLError as ex:
                    print(ex)
        else:
            print('could not open FNCS_CONFIG_FILE for fncs')
        topics = list(self.topicDict.keys())
        self.plot0.topicDict = self.topicDict
        self.plot0.combobox.config(values=topics)
        self.plot0.listOfTopics = topics
        self.plot0.title.set(topics[0])
        self.plot1.topicDict = self.topicDict
        self.plot1.combobox.config(values=topics)
        self.plot1.listOfTopics = topics
        self.plot1.title.set(topics[0])
        self.plot2.topicDict = self.topicDict
        self.plot2.combobox.config(values=topics)
        self.plot2.listOfTopics = topics
        self.plot2.title.set(topics[0])
        self.plot3.topicDict = self.topicDict
        self.plot3.combobox.config(values=topics)
        self.plot3.listOfTopics = topics
        self.plot3.title.set(topics[0])
        # convert seconds to minutes
        self.time_stop = cfg['time_stop']
        self.yaml_delta = cfg['yaml_delta']
        self.hour_stop = float(self.time_stop / 3600.0)
        dirpath = os.path.dirname(fname)
        os.chdir(dirpath)
        self.labelvar.set(dirpath)

        self.plot0.ax.set_xlim(0.0, self.hour_stop)
        self.plot1.ax.set_xlim(0.0, self.hour_stop)
        self.plot2.ax.set_xlim(0.0, self.hour_stop)
        self.plot3.ax.set_xlim(0.0, self.hour_stop)
        # self.plot0.ax.set_ylim(0.9, 1.1)
        # self.plot1.ax.set_ylim(0.9, 1.1)
        self.plot0.canvas.draw()
        self.plot1.canvas.draw()
        self.plot2.canvas.draw()
        self.plot3.canvas.draw()

    def kill_all(self):
        """Shut down all FNCS federates in TESP, except for this monitor
        """
        for proc in self.pids:
            print('trying to kill', proc.pid)
            proc.terminate()
        self.root.update()
        print('trying to finalize FNCS')
        if self.bFNCSactive:
            fncs.finalize()
            self.bFNCSactive = False
        print('FNCS finalized')

    def update_plots(self, i):
        """This function is called by Matplotlib for each animation frame

        Each time called, collect FNCS messages until the next time to plot
        has been reached. Then update the plot quantities and return the
        Line2D objects that have been updated for plotting. Check for new
        data outside the plotted vertical range, which triggers a full
        re-draw of the axes. On the last frame, finalize FNCS.

        Args:
          i (int): the animation frame number
        """
        print('.', end='')
        #    print ('frame', i, 'of', self.nsteps)
        bRedraw = False
        while self.time_granted < self.time_stop:  # time in minutes
            self.time_granted = fncs.time_request(self.time_stop)
            events = fncs.get_events()
            self.root.update()
            idx = int(self.time_granted / self.yaml_delta)
            if idx <= self.idxlast:
                continue
            self.idxlast = idx

            v0 = 0.0
            v1 = 0.0
            v2 = 0.0
            v3 = 0.0

            # for topic in events:
            #   value = fncs.get_value(topic)
            #   # if topic == 'vpos8':
            #   #   v1 = float (value.strip('+ degFkW')) / 199185.0
            #   if topic == 'vpos1':
            #     v1 = float(value.strip('+ degFkW')) / 199185.0
            #   elif topic == 'distribution_load8':
            #     v3 = parse_kw (value)
            #   elif topic == 'vpos8':
            #     v0 = float (value.strip('+ degFkW')) / 199185.0
            #   # elif topic == 'clear_price':
            #   #   v2 = float (value.strip('+ degFkW'))
            #   elif topic == 'LMP8':
            #     v2 = float (value.strip('+ degFkW'))
            #   # elif topic == 'SUBSTATION7':
            #   #   v1 = float (value.strip('+ degFkW')) # already in kW

            for topic in events:
                value = fncs.get_value(topic)
                if topic == self.topicDict[self.plot0.title.get()]:
                    v0 = self.CalculateValue(topic, value, self.plot0)
                elif topic == self.topicDict[self.plot1.title.get()]:
                    v1 = self.CalculateValue(topic, value, self.plot1)
                elif topic == self.topicDict[self.plot2.title.get()]:
                    v2 = self.CalculateValue(topic, value, self.plot2)
                elif topic == self.topicDict[self.plot3.title.get()]:
                    v3 = self.CalculateValue(topic, value, self.plot3)

            retval = [self.plot0.ln, self.plot1.ln, self.plot2.ln, self.plot3.ln]

            h = float(self.time_granted / 3600.0)
            self.plot0.hrs.append(h)
            self.plot1.hrs.append(h)
            self.plot2.hrs.append(h)
            self.plot3.hrs.append(h)
            self.plot0.y.append(v0)  # Vpu
            self.plot1.y.append(v1)  # school kW
            self.plot2.y.append(v2)  # price
            self.plot3.y.append(v3)  # feeder load
            self.plot0.ln.set_data(self.plot0.hrs, self.plot0.y)
            self.plot1.ln.set_data(self.plot1.hrs, self.plot1.y)
            self.plot2.ln.set_data(self.plot2.hrs, self.plot2.y)
            self.plot3.ln.set_data(self.plot3.hrs, self.plot3.y)
            if len(self.plot0.y) == 2:
                diff = abs(self.plot0.y[0] - self.plot0.y[1])
                if diff == 0:
                    self.plot0.ymin = self.plot0.y[0] - 0.00001
                    self.plot0.ymax = self.plot0.y[0] + 0.00001
                else:
                    self.plot0.ymin = min(self.plot0.y) - 0.00001 * diff
                    self.plot0.ymax = max(self.plot0.y) + 0.00001 * diff
                if self.plot0.ymin < 0:
                    self.plot0.ymin = 0
                self.plot0.ax.set_ylim(self.plot0.ymin, self.plot0.ymax)
                self.plot0.fig.canvas.draw()
                diff = abs(self.plot1.y[0] - self.plot1.y[1])
                if diff == 0:
                    self.plot1.ymin = self.plot1.y[0] - 0.00001
                    self.plot1.ymax = self.plot1.y[0] + 0.00001
                else:
                    self.plot1.ymin = min(self.plot1.y) - 0.00001 * diff
                    self.plot1.ymax = max(self.plot1.y) + 0.00001 * diff
                if self.plot1.ymin < 0:
                    self.plot1.ymin = 0
                self.plot1.ax.set_ylim(self.plot1.ymin, self.plot1.ymax)
                self.plot1.fig.canvas.draw()
                diff = abs(self.plot2.y[0] - self.plot2.y[1])
                if diff == 0:
                    self.plot2.ymin = self.plot2.y[0] - 0.00001
                    self.plot2.ymax = self.plot2.y[0] + 0.00001
                else:
                    self.plot2.ymin = min(self.plot2.y) - 0.00001 * diff
                    self.plot2.ymax = max(self.plot2.y) + 0.00001 * diff
                if self.plot2.ymin < 0:
                    self.plot2.ymin = 0
                self.plot2.ax.set_ylim(self.plot2.ymin, self.plot2.ymax)
                self.plot2.fig.canvas.draw()
                diff = abs(self.plot3.y[0] - self.plot3.y[1])
                if diff == 0:
                    self.plot3.ymin = self.plot3.y[0] - 0.00001
                    self.plot3.ymax = self.plot3.y[0] + 0.00001
                else:
                    self.plot3.ymin = min(self.plot3.y) - 0.00001 * diff
                    self.plot3.ymax = max(self.plot3.y) + 0.00001 * diff
                if self.plot3.ymin < 0:
                    self.plot3.ymin = 0
                self.plot3.ax.set_ylim(self.plot3.ymin, self.plot3.ymax)
                self.plot3.fig.canvas.draw()
            else:
                if v0 < self.plot0.ymin or v0 > self.plot0.ymax:
                    if v0 < self.plot0.ymin:
                        self.plot0.ymin = v0
                    if v0 > self.plot0.ymax:
                        self.plot0.ymax = v0
                    self.plot0.ax.set_ylim(self.plot0.ymin, self.plot0.ymax)
                    self.plot0.fig.canvas.draw()
                if v1 < self.plot1.ymin or v1 > self.plot1.ymax:
                    if v1 < self.plot1.ymin:
                        self.plot1.ymin = v1
                    if v1 > self.plot1.ymax:
                        self.plot1.ymax = v1
                    self.plot1.ax.set_ylim(self.plot1.ymin, self.plot1.ymax)
                    self.plot1.fig.canvas.draw()
                if v2 < self.plot2.ymin or v2 > self.plot2.ymax:
                    if v2 < self.plot2.ymin:
                        self.plot2.ymin = v2
                    if v2 > self.plot2.ymax:
                        self.plot2.ymax = v2
                    self.plot2.ax.set_ylim(self.plot2.ymin, self.plot2.ymax)
                    self.plot2.fig.canvas.draw()
                if v3 < self.plot3.ymin or v3 > self.plot3.ymax:
                    if v3 < self.plot3.ymin:
                        self.plot3.ymin = v3
                    if v3 > self.plot3.ymax:
                        self.plot3.ymax = v3
                    self.plot3.ax.set_ylim(self.plot3.ymin, self.plot3.ymax)
                    self.plot3.fig.canvas.draw()

            # if bRedraw:
            #   self.plot0.fig.canvas.draw()
            #   self.plot1.fig.canvas.draw()
            #   self.plot2.fig.canvas.draw()
            #   self.plot3.fig.canvas.draw()
            if i >= (self.nsteps - 1):
                fncs.finalize()
                self.bFNCSactive = False
            return retval

    def CalculateValue(self, topic, value, plot):
        """Parses a value from FNCS to plot

        Args:
            topic (str): the FNCS topic
            value (str): the FNCS value
            plot (ChoosablePlot): the plot that will be updated; contains the voltage base if needed

        Returns:
            float: the parsed value
        """
        if 'vpos' in topic:
            return float(value.strip('+ degFkW')) / float(plot.voltageBase.get())
        elif 'distribution_load' in topic:
            return parse_kw(value)
        elif 'airtemp' in topic:
            return float(value.strip('+ degFkW'))
        elif 'LMP' in topic:
            return float(value.strip('+ degFkW'))
        else:
            return float(value.strip('+ degFkW'))

    def launch_all(self):
        """Launches the simulators, initializes FNCS and starts the animated plots
        """
        self.root.update()

        print('launching all simulators')
        self.pids = []
        for row in self.commands:
            procargs = row['args']
            procenv = os.environ.copy()
            for var in row['env']:
                procenv[var[0]] = var[1]
            logfd = None
            if 'log' in row:
                logfd = open(row['log'], 'w')
            proc = subprocess.Popen(procargs, env=procenv, stdout=logfd)
            self.pids.append(proc)

        print('launched', len(self.pids), 'simulators')
        self.root.update()

        fncs.initialize()
        self.bFNCSactive = True
        print('FNCS initialized')
        self.nsteps = int(self.time_stop / self.yaml_delta)
        self.idxlast = -1
        self.time_granted = 0

        ani = animation.FuncAnimation(self.plot0.fig, self.update_plots, frames=self.nsteps,
                                      blit=True, repeat=False, interval=0)
        ani = animation.FuncAnimation(self.plot1.fig, self.update_plots, frames=self.nsteps,
                                      blit=True, repeat=False, interval=0)
        ani = animation.FuncAnimation(self.plot2.fig, self.update_plots, frames=self.nsteps,
                                      blit=True, repeat=False, interval=0)
        ani = animation.FuncAnimation(self.plot3.fig, self.update_plots, frames=self.nsteps,
                                      blit=True, repeat=False, interval=0)
        self.plot0.fig.canvas.draw()
        self.plot1.fig.canvas.draw()
        self.plot2.fig.canvas.draw()
        self.plot3.fig.canvas.draw()


#    fncs.finalize()

def show_tesp_monitor():
    """Creates and displays the monitor GUI
    """
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


class ChoosablePlot(tk.Frame):
    """Hosts one Matplotlib animation with a selected variable to plot

    Args:
        master:
        color (str): Matplotlib color of the line to plot
        xLabel (str): label for the x axis
        topicDict (dict): dictionary of FNCS topic choices to plot
        kwargs: arbitrary keyword arguments
    Attributes:
        topicDict:
        listOfTopics:
        root (Tk): the TCL Tk toolkit instance
        fig (Figure): animated Matplotlib figure hosted on the GUI
        ax (Axes): set of 4 xy axes to plot on
        xLabel (str): horizontal axis label
        yLabel (str): vertical axis label
        hrs:
        y:
        ymin (float):
        ymax (float):
        color:
        title (str):
        ln (Line2D):
        topicSelectionRow:
        topicLabel:
        combobox:
        voltageLabel:
        voltageBase:
        voltageBaseTextbox:
    """
    def __init__(self, master, color='red', xLabel='', topicDict={}, **kwargs):
        super().__init__(master, background='#ffffff', **kwargs)
        self.root = master
        self.fig, self.ax = plt.subplots(1, 1, figsize=(9, 1.8))
        self.topicDict = topicDict
        self.listOfTopics = list(topicDict.keys())
        self.xLabel = xLabel
        self.yLabel = ''

        self.hrs = []
        self.y = []
        self.ymin = 0
        self.ymax = 0
        self.color = color
        self.title = tk.StringVar(self)
        if self.listOfTopics:
            self.title.set(self.listOfTopics[0])

        self.ln = Line2D(self.hrs, self.y, color=color)
        self.ax.add_line(self.ln)
        self.ax.set_ylabel('[LMP]')
        self.ax.set_title(self.title.get(), fontsize=10)

        if self.xLabel == '':
            cax = plt.gca()
            cax.axes.xaxis.set_ticklabels([])
        else:
            self.ax.set_xlabel(self.xLabel)
            plt.gcf().set_size_inches(9, 2.5)
            plt.gcf().subplots_adjust(bottom=0.35)
            plt.gca().set_autoscale_on(False)
        # self.rowconfigure (0, weight=0)
        # self.columnconfigure (0, weight=1)
        # self.columnconfigure (1, weight=10)
        # self.columnconfigure (2, weight=2)
        # self.columnconfigure (3, weight=10)
        self.topicSelectionRow = tk.Frame(self, background='#ffffff')
        self.topicSelectionRow.grid(row=0, sticky='w', padx=(75, 0))

        self.topicLabel = tk.Label(self.topicSelectionRow, text="Topic: ", background='#ffffff')
        self.topicLabel.pack(side='left')

        self.combobox = ttk.Combobox(self.topicSelectionRow, values=self.listOfTopics, textvariable=self.title,
                                     background="#ffffff", width=50, state="readonly")
        self.combobox.pack(side='left')
        self.combobox.bind("<<ComboboxSelected>>", self.onTopicSelected)

        self.voltageLabel = tk.Label(self.topicSelectionRow, text="Voltage Base: ", background='#ffffff')
        self.voltageLabel.pack(side='left', padx=(30, 0))

        self.voltageBase = tk.StringVar(self)
        self.voltageBase.set('199185')
        self.voltageBaseTextbox = tk.Entry(self.topicSelectionRow, textvariable=self.voltageBase, relief=tk.RIDGE,
                                           background="#ffffff", width=15, highlightthickness=0,
                                           highlightbackground='White')
        self.voltageBaseTextbox.pack(side='left')

        self.voltageLabel.pack_forget()
        self.voltageBaseTextbox.pack_forget()

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1)

    def onTopicSelected(self, event):
        """ Change the GUI labels to match selected plot variable

        Args:
            event:
        """
        selectedTopic = self.title.get()
        self.ax.set_title(selectedTopic, fontsize=10)
        if 'vpos' in self.topicDict[selectedTopic]:
            self.voltageLabel.pack(side='left')
            self.voltageBaseTextbox.pack(side='left')
            self.ax.set_ylabel('[pu]')
        else:
            self.voltageLabel.pack_forget()
            self.voltageBaseTextbox.pack_forget()
            if 'distribution_load' in self.topicDict[selectedTopic]:
                self.ax.set_ylabel('[kW]')
            elif 'airtemp' in self.topicDict[selectedTopic]:
                self.ax.set_ylabel('[degF]')
            elif 'LMP' in self.topicDict[selectedTopic]:
                self.ax.set_ylabel('[$]')
            else:
                self.ax.set_ylabel('[$]')
        self.canvas.draw()
