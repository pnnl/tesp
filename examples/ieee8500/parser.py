import string;
import sys;
import fncs;
import json;
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

#  if 'd' in arg:
#    vals[1] *= (math.pi / 180.0)
#    p = vals[0] * math.cos(vals[1])
#    q = vals[0] * math.sin(vals[1])
#  elif 'r' in arg:
#    p = vals[0] * math.cos(vals[1])
#    q = vals[0] * math.sin(vals[1])
#  else:
#    p = vals[0]
#    q = vals[1]
  return vals[0]

# final air temperatures {'F1_house_C29': '+75.0050832996 degF', 'F1_house_A28': '+73.3239433896 degF', 'F1_house_C27': '+75.8389549538 degF', 'F1_house_A26': '+75.0149104609 degF', 'F1_house_A25': '+75.795475052 degF', 'F1_house_B24': '+75.9367016015 degF', 'F1_house_B23': '+75.2267894908 degF', 'F1_house_B22': '+76.0602579605 degF', 'F1_house_C21': '+75.2507708178 degF', 'F1_house_B20': '+74.5087137724 degF', 'F1_house_B19': '+75.1403447269 degF', 'F1_house_C18': '+75.8405187415 degF', 'F1_house_C17': '+73.9444102008 degF', 'F1_house_A16': '+73.8777241369 degF', 'F1_house_A15': '+75.830114001 degF', 'F1_house_C14': '+74.7223215893 degF', 'F1_house_A13': '+75.7720827161 degF', 'F1_house_A12': '+75.3027431741 degF', 'F1_house_A11': '+76.003111343 degF', 'F1_house_C10': '+75.648483206 degF', 'F1_house_A9': '+74.8601907818 degF', 'F1_house_A8': '+76.104772981 degF', 'F1_house_B7': '+74.3806585639 degF', 'F1_house_B6': '+75.6570906619 degF', 'F1_house_A5': '+75.1539082037 degF', 'F1_house_B4': '+74.8095577224 degF', 'F1_house_B3': '+75.9464395762 degF', 'F1_house_C2': '+75.7808015659 degF', 'F1_house_C1': '+75.8408359009 degF', 'F1_house_B0': '+75.5392544796 degF'}
#final meter voltages {'F1_house_C29': '+119.875+119.909d V', 'F1_house_A28': '+119.582-0.306827d V', 'F1_house_C27': '+119.875+119.909d V', 'F1_house_A26': '+119.582-0.306827d V', 'F1_house_A25': '+119.582-0.306827d V', 'F1_house_B24': '+119.346-120.48d V', 'F1_house_B23': '+119.346-120.48d V', 'F1_house_B22': '+119.3-120.479d V', 'F1_house_C21': '+119.875+119.909d V', 'F1_house_B20': '+119.312-120.479d V', 'F1_house_B19': '+119.346-120.48d V', 'F1_house_C18': '+119.875+119.909d V', 'F1_house_C17': '+119.875+119.909d V', 'F1_house_A16': '+119.582-0.306827d V', 'F1_house_A15': '+119.582-0.306827d V', 'F1_house_C14': '+119.875+119.909d V', 'F1_house_A13': '+119.582-0.306827d V', 'F1_house_A12': '+119.582-0.306827d V', 'F1_house_A11': '+119.566-0.306326d V', 'F1_house_C10': '+119.875+119.909d V', 'F1_house_A9': '+119.582-0.306827d V', 'F1_house_A8': '+119.553-0.305896d V', 'F1_house_B7': '+119.346-120.48d V', 'F1_house_B6': '+119.346-120.48d V', 'F1_house_A5': '+119.582-0.306827d V', 'F1_house_B4': '+119.346-120.48d V', 'F1_house_B3': '+119.346-120.48d V', 'F1_house_C2': '+119.875+119.909d V', 'F1_house_C1': '+119.875+119.909d V', 'F1_house_B0': '+119.346-120.48d V'}
print (parse_fncs_magnitude ('+75.0050832996 degF'))
print (parse_fncs_magnitude ('+119.875+119.909d V'))
print (parse_fncs_magnitude ('+119.582-0.306827d V'))


