import math
import re
import sys
from pprint import pprint

arg = "+2.27679e+06+10.6156d VA"

#arg = "+6.34297e+06+1.01234e-01d VA"

#arg = "+2.23899e+06-419382j"

tok = arg.strip('; MWVAKdrij')

nsign = nexp = ndot = 0
for i in range(len(tok)):
	if (tok[i] == '+') or (tok[i] == '-'):
		nsign += 1
	elif (tok[i] == 'e') or (tok[i] == 'E'):
		nexp += 1
	elif tok[i] == '.':
		ndot += 1
	if nsign == 2 and nexp == 0:
		kpos = i
		break
	if nsign == 3:
		kpos = i
		break

#kdot = tok.rfind('.')
#kpos = tok.rfind('+',0,kdot)
#kneg = tok.rfind('-',0,kdot)
#if kpos < kneg:
#	kpos = kneg

vals = [tok[:kpos],tok[kpos:]]

print (arg, tok,vals)
vals = [float(v) for v in vals]

if 'd' in arg:
    vals[1] *= (math.pi / 180.0)
    p = vals[0] * math.cos(vals[1])
    q = vals[0] * math.sin(vals[1])
elif 'r' in arg:
    p = vals[0] * math.cos(vals[1])
    q = vals[0] * math.sin(vals[1])
else:
    p = vals[0]
    q = vals[1]

if 'KVA' in arg:
    p *= 1.0
    q *= 1.0
elif 'MVA' in arg:
    p *= 1000.0
    q *= 1000.0
else:  # VA
    p /= 1000.0
    q /= 1000.0

print(p,q)
    
