import numpy as np;
import matplotlib.pyplot as plt;
import math;

days = 7
Pnorm = 165.6

wind_plants = np.array ([99.8, 1657.0, 2242.2, 3562.2, 8730.3])

nplants = wind_plants.shape[0]
n = 24 * days + 1

h = np.linspace (0, n - 1, n)
p = np.zeros (shape = (nplants, n))
a = np.zeros (shape = (nplants, n))
y = np.zeros (shape = (nplants, n))
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
	a[j,0] = Theta0[j]
	y[j,0] = Ylim[j]

for i in range (n):
	for j in range (nplants):
		if i > 0:
			a[j,i] = np.random.normal (0.0, StdDev[j])
			y[j,i] = Theta0[j] + a[j,i] - Theta1[j] * a[j,i-1] + Psi1[j] * y[j,i-1]
		if y[j,i] > Ylim[j]:
			y[j,i] = Ylim[j]
		elif y[j,i] < 0.0:
			y[j,i] = 0.0
		p[j,i] = y[j,i] * y[j,i]

CF = np.zeros (nplants)
COV = np.zeros (nplants)
msg = [None] * nplants
print ('Simulating', days, 'days')
for j in range (nplants):
	p_avg = p[j,:].mean()
	p_std = p[j,:].std()
	CF[j] = p_avg / wind_plants[j]
	COV[j] = p_std / p_avg
	msg[j] = '{:.1f}'.format (wind_plants[j]) + ' MW, CF = ' + '{:.2f}'.format (CF[j]) + ', COV = ' + '{:.2f}'.format (COV[j])	
	print (msg[j]) 

fig, ax = plt.subplots(nplants, 1)

for j in range (nplants):
	ax[j].set_title (msg[j])
	ax[j].set_ylabel ('MW vs. Hours')
	ax[j].grid (linestyle = '-')
	ax[j].plot (h, p[j,:], 'r')

plt.show()



