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
