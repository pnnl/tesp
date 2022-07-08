import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
#from matplotlib.ticker import MultipleLocator
from matplotlib.ticker import FixedLocator
#from matplotlib.ticker import PercentFormatter
import math, os, json, sys
import datetime as dt
from matplotlib import rcParams
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Times']
import seaborn as sns

LOWER_BOUND = 0.95
UPPER_BOUND = 1.05
VREFtoPU = 7199.558
SMALLEST_SIZE = 12 # 10
SMALLER_SIZE = 16 # 12
SMALL_SIZE = 18 # 24
MEDIUM_SIZE = 24 # 32
BIG_SIZE = 32 # 48
SAVE_FIG = False
timeIdx = 0
current_palette = sns.xkcd_palette(sns.xkcd_rgb)  # color_palette('pastel')
sns.set_palette(current_palette)
# sns.palplot(current_palette)
colorSpec = ['xkcd:royal blue', 'xkcd:green', 'xkcd:orange', 'xkcd:red', 'xkcd:magenta', 'xkcd:violet', 'xkcd:yellow', 'xkcd:teal']
lineStyles = ['solid', 'dashed', 'dashdot', 'dotted', (0, (3, 1, 1, 1, 1, 1)), (0, (3, 5, 1, 5, 1, 5)), 'dashed', (0, (3, 5, 1, 5, 1, 5))]

def convert_time(data, timeUnit = None):

  timeValues = data['# timestamp']

  if timeUnit is None:
    timeUnit = 'ms'
  if timeUnit == 'ms':
    timeValuesMinutes = np.array([pd.to_datetime(x).time().minute for x in timeValues])
    timeValuesSeconds = np.array([pd.to_datetime(x).time().second for x in timeValues])
    timeValuesMicroSec = np.array([pd.to_datetime(x).time().microsecond/1000000 for x in timeValues])
    # time values in seconds with decimal milliseconds
    timeValuesSec = [round(x, 3) for x in (60 * timeValuesMinutes + timeValuesSeconds + timeValuesMicroSec)]
    return timeValuesSec
  elif timeUnit == 's':
    # day from date
    timeValuesD = np.array([pd.to_datetime(x).date().day for x in timeValues])
    # number of days in the current simulation
    timeValuesDnum = timeValuesD - timeValuesD[0]
    # hours from time
    timeValuesHours = np.array([pd.to_datetime(x).time().hour for x in timeValues])
    # minutes from time
    timeValuesMinutes = np.array([pd.to_datetime(x).time().minute for x in timeValues])
    # seconds from time
    timeValuesSeconds = np.array([pd.to_datetime(x).time().second for x in timeValues])
    # Second of the day from start of simulation
    timeValuesS = 24 * 3600 * timeValuesDnum + 3600 * timeValuesHours + 60 * timeValuesMinutes + timeValuesSeconds
    return timeValuesS
  elif timeUnit == 'm':
    # day from date
    timeValuesD = np.array([pd.to_datetime(x).date().day for x in timeValues])
    # number of days in the current simulation
    timeValuesDnum = timeValuesD - timeValuesD[0]
    # hours from time
    timeValuesHours = np.array([pd.to_datetime(x).time().hour for x in timeValues])
    # minutes from time
    timeValuesMinutes = np.array([pd.to_datetime(x).time().minute for x in timeValues])
    # Minute of the day from start of simulation
    timeValuesM = 24 * 60 * timeValuesDnum + 60 * timeValuesHours + timeValuesMinutes
    return timeValuesM
  elif timeUnit == 'h':
    # day from date
    timeValuesD = np.array([pd.to_datetime(x).date().day for x in timeValues])
    # number of days in the current simulation
    timeValuesDnum = timeValuesD - timeValuesD[0]
    # hours from time
    timeValuesHours = np.array([pd.to_datetime(x).time().hour for x in timeValues])
    # Hour of the day from start of simulation
    timeValuesH = 24 * timeValuesDnum + timeValuesHours
    # timeValues = [x.replace('EDT', 'UTC-4') for x in timeValues if 'EDT' in x] 
    return timeValuesH

def plot_substation_load(fig, Axis, data, timeValues):
  timeInd = data['# timestamp']
  measValues = data['network_node'] * 1e-6 # W to MW
  # hPlot = Axis.step(timeValues, measValues, where = 'post')
  hPlot = Axis.plot(timeValues, measValues)
  Axis.set_xlim([timeValues[0], timeValues[-2]])
  return hPlot

def plot_status(fig, Axis, data, timeValues):
  measValues = data['service_status']
  hPlot = Axis.plot(timeValues, measValues)
  Axis.set_xlim([timeValues[0], timeValues[-2]])
  return hPlot

def plot_load(fig, Axis, data, timeValues):
  measValues = data['measured_real_power'] * 1e-3 # W to kW
  hPlot = Axis.plot(timeValues, measValues)
  Axis.set_xlim([timeValues[0], timeValues[-2]])
  return hPlot

def main():
  figWidth = 16
  figHeight = 8
  tickInt = 10
  scenarios = ['noNS3_noLoadShed', 'noNS3_LoadShed', 'withNS3_LoadShed']
  nCol = 1 #2
  nRow = 1 #5
  hBigFig = plt.figure(constrained_layout = True, figsize = (figWidth, figHeight))
  hFigs = hBigFig.subfigures(1, 2, wspace = 0.07)
  hFig = hFigs[0] # plt.figure(constrained_layout = True, figsize = (figWidth, figHeight))
  gs = GridSpec(nRow, nCol, figure = hFig)
  xLabelText = 'time [sec]'
  yLabelText = 'substation load [MW]'
  legendText = ['no load shed', 'load shed, no communication network', 'load shed, with communication network']
  hAxis = hFig.add_subplot(gs[0, 0]) #(gs[0:5, 0])
  titleText = f'substation load'
  for scen in scenarios:
    if scenarios.index(scen) == 2:
      lw = 2
    else:
      lw = 3
    resultsFolder = os.path.abspath(f'./R1-12.47-1/outputs_{scen}')
    fileName = f'substation_load.csv'
    filePath = os.path.join(resultsFolder, fileName)
    data = pd.read_csv(filePath, skiprows = 8)
    # Doing the actual conversion of time takes too long to worth it.
    # Since the actual time does not really matter, we can go by sample number
    timeValues = convert_time(data, timeUnit = 's')
    hPlot = plot_substation_load(hFig, hAxis, data, timeValues)
    hPlot[0].set(color = colorSpec[scenarios.index(scen)], linewidth = lw, linestyle = lineStyles[0]) # scenarios.index(scen)
  hAxis.tick_params(axis = 'both', which = 'major', labelsize = SMALL_SIZE, width = 2, labelrotation = 0, labelcolor = 'black')
  hAxis.grid(axis = 'both', alpha = 0.4, linestyle = ':', color = 'black')
  hAxis.xaxis.set_major_locator(plt.MaxNLocator(12))
  hAxis.yaxis.set_major_locator(plt.MaxNLocator(8))
  # hAxis.set_title(titleText, fontsize = BIG_SIZE, fontweight = 'bold')
  hAxis.set_xlabel(xLabelText, fontsize = MEDIUM_SIZE, fontweight = 'bold')
  hAxis.set_ylabel(yLabelText, fontsize = MEDIUM_SIZE, fontweight = 'bold')
  hAxis.set_title('Substation', fontsize = MEDIUM_SIZE, fontweight = 'bold')
  hAxis.legend(legendText, fontsize = SMALL_SIZE, markerscale = 2, loc = 'lower right')
  
  hFig = hFigs[1]
  nCol = 1
  nRow = 5
  gs = GridSpec(nRow, nCol, figure = hFig)
  shedLoad = ['R1_12_47_1_tn_15_mhse_1', 'R1_12_47_1_tn_128_mhse_2', 'R1_12_47_1_tn_459_mhse_4', 'R1_12_47_1_tn_564_mhse_4', 'R1_12_47_1_tn_506_mhse_1']
  yLabelText = 'load [kW]'
  for ld in shedLoad:
    hAxis = hFig.add_subplot(gs[shedLoad.index(ld), 0]) #1])
    for scen in scenarios[1:]:
      if scenarios.index(scen) == 2:
        lw = 2
      else:
        lw = 3
      resultsFolder = os.path.abspath(f'./R1-12.47-1/outputs_{scen}')
      fileName = f'{ld}_rec.csv'
      filePath = os.path.join(resultsFolder, fileName)
      data = pd.read_csv(filePath, skiprows = 8)
      # print(data['service_status'].values)
      # data['service_status'].values[np.where(data['service_status'].values == 'OUT_OF_SERVICE')] = 0
      # data['service_status'].values[np.where(data['service_status'].values == 'IN_SERVICE')] = 1
      timeValues = convert_time(data, timeUnit = 's')
      # hPlot = plot_status(hFig, hAxis, data, timeValues)
      hPlot = plot_load(hFig, hAxis, data, timeValues)
      hPlot[0].set(color = colorSpec[scenarios.index(scen)], linewidth = lw, linestyle = lineStyles[0]) # scenarios.index(scen)
    hAxis.tick_params(axis = 'both', which = 'major', labelsize = SMALL_SIZE, width = 2, labelrotation = 0, labelcolor = 'black')
    hAxis.grid(axis = 'both', alpha = 0.4, linestyle = ':', color = 'black')
    hAxis.xaxis.set_major_locator(plt.MaxNLocator(12))
    hAxis.yaxis.set_major_locator(plt.MaxNLocator(4))
    # if shedLoad.index(ld) == len(shedLoad) - 1:
    #   hAxis.set_xlabel(xLabelText, fontsize = MEDIUM_SIZE, fontweight = 'bold')

    # hAxis.set_ylabel(yLabelText, fontsize = MEDIUM_SIZE, fontweight = 'bold')
    # if shedLoad.index(ld) == 0:
    #   hAxis.set_title(yLabelText, fontsize = MEDIUM_SIZE, fontweight = 'bold')
    # hAxis.legend(legendText[1:], fontsize = SMALL_SIZE, markerscale = 2)
    hAxis.set_title(ld, fontsize = MEDIUM_SIZE, fontweight = 'bold')

  hFig.supxlabel(xLabelText, fontsize = MEDIUM_SIZE, fontweight = 'bold')
  hFig.supylabel(yLabelText, fontsize = MEDIUM_SIZE, fontweight = 'bold')

  if SAVE_FIG:
    hFig.savefig(os.path.join(os.path.abspath('./'), 'generation.png'), format = 'png')

if __name__ == '__main__':
  main()
  plt.show()
