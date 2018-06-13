import numpy as np
import math

p = 1000.0 * np.array ([3.7800000,0.0503724,0.0440233,0.0440194,0.0434324,0.0416101,0.0404729,0.0391547,0.0345153,0.0330981,0.0327054,0.0300381,0.0280677,0.0276301,0.0271848,0.0262352,0.0259875,0.0249008,0.0224730,0.0192500,0.0169162,0.0150734,0.0140829,0.0110085,0.0100196,0.0065160,0.0045085,0.0021653,0.0000552]) 
q = np.array([0.17470563,0.00540141,0.00407373,0.00502706,0.00915404,0.00525426,0.00379635,0.00571114,0.00485273,0.00362974,0.00419777,0.00373671,0.00385281,0.00304635,0.00428825,0.00636283,0.00588409,0.00367807,0.00675699,0.00675697,0.00367489,0.00313626,0.00590408,0.00267553,0.00468004,0.00290578,0.00365922,0.00467316,0.00628048])

#p = 1000.0 * np.array ([3.7800000,0.0503724,0.0440233]) 
#q = np.array([0.17470563,0.00540141,0.00407373])

#p = 1000.0 * np.array ([3.7800000,0.0503724]) 
#q = np.array([0.17470563,0.00540141])

idx = np.argwhere (p == p[0])[-1][0]
unresp = np.cumsum(q[:idx+1])[-1]

n = p.size - idx - 1
print ('fitting',n,'bidders')

qresp = np.cumsum(q[idx+1:])
presp = p[idx+1:]
qmax = qresp[-1]
cost = np.cumsum(np.multiply(presp, q[idx+1:]))
#resp_fit = np.polyfit (qresp, cost, 2)
#c2 = resp_fit[0]
#c1 = resp_fit[1]
#c0 = resp_fit[2]

#bid = [p[0], unresp, c2, c1, c0, qmax]
#print('polyfit',bid)

if n <= 2:
	A = np.vstack([qresp, np.ones(len(qresp))]).T
else:
	A = np.vstack([qresp**2, qresp, np.ones(len(qresp))]).T
print(A)

ret = np.linalg.lstsq(A,cost)[0]
print ('full fit', ret)

ret = np.linalg.lstsq(A[:, :-1],cost)[0]
print ('c0=0', ret)

