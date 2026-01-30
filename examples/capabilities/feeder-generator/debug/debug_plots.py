import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
import numpy as np

cooling = pd.read_csv("cooling_setpt.csv")
heating = pd.read_csv("heating_setpt.csv")
hvac_l = pd.read_csv("hvac_load.csv")
hvac_p = pd.read_csv("hvac_power.csv")
#sub = pd.read_csv("sub_power.csv")


#plt.plot(cooling)
#plt.plot(heating)
plt.plot(hvac_l)
plt.show()