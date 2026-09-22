# Copyright (c) 2021-2025 Battelle Memorial Institute
# file: wind_plants.py

import math

import matplotlib.pyplot as plt
import numpy as np

days = 2
Pnorm = 165.6

wind_plants = np.array ([99.8, 1657.0, 2242.2, 3562.2, 8730.3])

nplants = wind_plants.shape[0]
n = 24 * days + 1

h = np.linspace (0, n - 1, n)
p = np.zeros (shape = (nplants, n))
alag = np.zeros (nplants)
ylag = np.zeros (nplants)
Theta0 = np.ones (nplants)
Theta1 = np.ones (nplants)
StdDev = np.ones (nplants)
Psi1 = np.ones (nplants)
Ylim = np.ones (nplants)

for j in range (nplants):
	scale = wind_plants [j] / Pnorm
	Theta0[j] = 0.05 * math.sqrt (scale)
	Theta1[j] = -0.1 * (scale)
	StdDev[j] = math.sqrt (1.172 * math.sqrt (scale))
	Psi1[j] = 1.0
	Ylim[j] = math.sqrt (wind_plants[j])
	alag[j] = Theta0[j]
	ylag[j] = Ylim[j]
	print (j, f'{wind_plants[j]:7.2f} {scale:7.4f} {Theta0[j]:7.4f} {Theta1[j]:7.4f} {StdDev[j]:7.4f} {Psi1[j]:7.4f} {Ylim[j]:7.2f}')

# time-stepping to mimic what will happen in fncsERCOT.py
i = 0
ts = 0
tmax = days * 24 * 3600
tnext_wind = 0
wind_period = 3600
dt = 300

while ts <= tmax:
	if ts >= tnext_wind:
		for j in range (nplants):
			if i > 0:
				a = np.random.normal (0.0, StdDev[j])
				y = Theta0[j] + a - Theta1[j] * alag[j] + Psi1[j] * ylag[j]
				alag[j] = a
			else:
				y = ylag[j]
			if y > Ylim[j]:
				y = Ylim[j]
			elif y < 0.0:
				y = 0.0
			p[j,i] = y * y
			if i > 0:
				ylag[j] = y
		i += 1
		tnext_wind += wind_period
	ts += dt

CF = np.zeros (nplants)
COV = np.zeros (nplants)
msg = [None] * nplants
print ('Simulating', days, 'days')
for j in range (nplants):
	p_avg = p[j,:].mean()
	p_std = p[j,:].std()
	CF[j] = p_avg / wind_plants[j]
	COV[j] = p_std / p_avg
	msg[j] = f'{wind_plants[j]:.1f}' + ' MW, CF = ' + f'{CF[j]:.2f}' + ', COV = ' + f'{COV[j]:.2f}'	
	print (msg[j]) 

fig, ax = plt.subplots(nplants, 1)

for j in range (nplants):
	ax[j].set_title (msg[j])
	ax[j].set_ylabel ('MW vs. Hours')
	ax[j].grid (linestyle = '-')
	ax[j].plot (h, p[j,:], 'r')

plt.show()



