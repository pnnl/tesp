import numpy as np;
import matplotlib.pyplot as plt;
import math;

def acf(x, t=1):
  return np.corrcoef(np.array([x[0:len(x)-t], x[t:len(x)]]))

days = 30
Pmax = 8700.0

Theta0 = 1.0 # 0.15
Theta1 = -0.7 # -0.1
Noise = 5.0 # 1.0
Psi1 = 1.0
Ylim = math.sqrt (Pmax) # 12.87
# A0 = 6.7

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

fig, ax = plt.subplots()
ax.set_title ('LARIMA(0,1,1) Wind Power Output Model')
ax.set_ylabel ('Power [MW]')
ax.set_xlabel ('Hours')
ax.grid (linestyle = '-')
ax.plot (h, p, 'r')
plt.show()

print ('mean', '{:.2f}'.format (p.mean()), 'std', '{:.2f}'.format (p.std()))
print (acf(p))
