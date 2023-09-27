# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: test_wind.py

import numpy as np
import matplotlib.pyplot as plt
import math
from scipy import stats
from statsmodels import api as sm


def acf(x, t=1):
  return np.corrcoef(np.array([x[0:len(x)-t], x[t:len(x)]]))

days = 365
Pnorm = 165.6

#Pmax = 99.8
#Pmax = 165.6
#Pmax = 1675.0
#Pmax = 2242.2
#Pmax = 3562.2
Pmax = 8730.3

Theta0 = 0.05 * math.sqrt (Pmax / Pnorm)
Theta1 = -0.1 * (Pmax / Pnorm)
Noise = 1.172 * math.sqrt (Pmax / Pnorm)
Psi1 = 1.0
Ylim = math.sqrt (Pmax) # 12.87

n = 24 * days + 1
h = np.linspace (0, n - 1, n)
p = np.zeros (n)
a = np.zeros (n)
y = np.zeros (n)
stddev = math.sqrt (Noise)

a[0] = Theta0
y[0] = Ylim

for i in range (n):
  if i > 0:
    a[i] = np.random.normal (0.0, stddev)
    y[i] = Theta0 + a[i] - Theta1 * a[i-1] + Psi1 * y[i-1]
  if y[i] > Ylim:
    y[i] = Ylim
  elif y[i] < 0.0:
    y[i] = 0.0
  p[i] = y[i] * y[i]

p_pa = sm.tsa.pacf (p, 10)
p_acf = sm.tsa.acf (p, nlags=10)
y_pa = sm.tsa.pacf (y, 10)
y_acf = sm.tsa.acf (y, nlags=10)

p_avg = p.mean()
cf = p_avg / Pmax
cov = p.std() / p_avg

fig, ax = plt.subplots(4, 1)

ax[0].set_title ('LARIMA(0,1,1) Wind Power Output Model: CF = '
								 + '{:.2f}'.format (cf) + ', COV = ' + '{:.2f}'.format (cov))
ax[0].set_ylabel ('MW vs. Hours')
ax[0].grid (linestyle = '-')
ax[0].plot (h, p, 'r')

ax[1].set_ylabel ('ACF vs. Lag')
ax[1].grid (linestyle = '-')
ax[1].plot (p_acf, 'r', label='P')
ax[1].plot (y_acf, 'b', label='Y')
ax[1].legend (loc='best')

ax[2].set_ylabel ('PACF vs. Lag')
ax[2].grid (linestyle = '-')
ax[2].plot (p_pa, 'r', label='P')
ax[2].plot (y_pa, 'b', label='Y')
ax[2].legend (loc='best')

ax[3].hist (p, histtype='step', density=True, bins=15)

plt.show()



