import sys

if len(sys.argv) < 3:
  print ('usage: python3 DeDeprecate.py SGIP1c.glm SGIP1c.new')

fp = open (sys.argv[1], 'r')
op = open (sys.argv[2], 'w')

bInSolar = False
bInBattery = False
for ln in fp:
  line = ln.rstrip()
  if 'object solar' in line:
    bInSolar = True
  elif 'object battery' in line:
    bInBattery = True
  if (bInSolar == True) and ('};' == line.lstrip()):
    bInSolar = False
  if (bInBattery == True) and ('};' == line.lstrip()):
    bInBattery = False
  bCopy = True
  if bInSolar:
    if 'generator_mode' in line:
      bCopy = False
    elif 'generator_status' in line:
      bCopy = False
  elif bInBattery:
    if 'generator_mode' in line:
      bCopy = False
    if 'generator_status' in line:
      bCopy = False
  if bCopy:
    print (line, file=op)

fp.close()
op.close()
