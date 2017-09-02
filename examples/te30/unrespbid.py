import numpy as np
import math

p = np.array ([3.78,
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78,                 
							 3.78, 0.1, 0.09]) 

q = np.array([21.051080261180033,
5.23431332264,
5.41232981251,
3.94107748485,
4.61933606259,
3.95764546946,
5.04592857708,
6.3578895111,
3.58996519407,
7.30116421525,
7.28941108059,
6.77602869683,
5.81404808403,
9.86901489729,
3.914686252,
							10.0, 20.0
])

idx = np.argwhere (p == p[0])[-1][0]
unresp = np.cumsum(q[:idx+1])[-1]

n = p.size - idx - 1

if n < 1:
	a = 0
	b = 0
	qmax = 0
else:
	qresp = np.cumsum(q[idx+1:])
	presp = p[idx+1:]
	qmax = qresp[-1]
	if n == 1:
		a = 0
		b = presp[-1]
	else:
		resp_fit = np.polyfit (qresp, presp, 1)
		a = resp_fit[0]
		b = resp_fit[1]


bid = [p[0], unresp, a, b, qmax]
print(bid)
