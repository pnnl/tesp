import string;
import sys;
import math;
import re;

def parse_fncs_magnitude (arg):
  tok = arg.strip('+-; MWVAFKdegrij')
  vals = re.split(r'[\+-]+', tok)
  if len(vals) < 2: # only a real part provided
    vals.append('0')
  vals = [float(v) for v in vals]

  if '-' in tok:
    vals[1] *= -1.0
  if arg.startswith('-'):
    vals[0] *= -1.0
  return vals[0]

def parse_mva(arg):
  tok = arg.strip('; MWVAKdrij')
  bLastDigit = False
  bParsed = False
  vals = [0.0,0.0]
  for i in range(len(tok)):
    if tok[i] == '+' or tok[i] == '-':
      if bLastDigit:
        vals[0] = float(tok[:i])
        vals[1] = float(tok [i:])
        bParsed = True
        break
    bLastDigit = tok[i].isdigit()
  if not bParsed:
    vals[0] = float(tok)
#  print ('     vals', vals)

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
    p /= 1000.0
    q /= 1000.0
  elif 'MVA' in arg:
    p *= 1.0
    q *= 1.0
  else:  # VA
    p /= 1000000.0
    q /= 1000000.0

  return p, q

#print (parse_fncs_magnitude ('+75.0050832996 degF'))
#print (parse_fncs_magnitude ('+119.875+119.909d V'))
#print (parse_fncs_magnitude ('+119.582-0.306827d V'))

print (parse_mva ('+2.20712e+06-402143j VA'))
print (parse_mva ('+2.20712e+06'))
print (parse_mva ('2.20 MVA'))
print (parse_mva ('2200 KVA'))
print (parse_mva ('+2.20712e+06+402143j VA'))
print (parse_mva ('-2.20712e+06-402143j VA'))

