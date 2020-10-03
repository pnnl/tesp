import pypower.api as pp

ppc = pp.loadcase('rtmcase.py')
ppopt_market = pp.ppoption(VERBOSE=0, OUT_ALL=0, PF_DC=1, OPF_ALG_DC=200)
ropf = pp.runopf(ppc, ppopt_market)
Pload = 0.0
Pgen = 0.0
Presp = 0.0
for row in ropf['bus']:
  Pload += float (row[2])
for row in ropf['gen']:
  Pg = float (row[1])
  if Pg > 0.0:
    Pgen += Pg
  elif Pg < 0.0:
    Presp -= Pg

print ('Gen={:.2f}, FixedLoad={:.2f}, RespLoad={:.2f}'.format (Pgen, Pload, Presp))

print ('Bus     LMP  RespMax  Cleared')
for row in ropf['gen']:
  Pmin = row[9]
  if Pmin < 0.0:
    Pg = row[1]
    busidx = int(row[0])
    lmp = ropf['bus'][busidx-1][13]
    print ('{:2d} {:8.3f} {:8.3f} {:8.3f}'.format (busidx, lmp, -Pmin, -Pg))
