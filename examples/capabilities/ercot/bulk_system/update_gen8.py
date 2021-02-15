import json

fp = open ('../case8/ercot_8.json', mode='r')
ppc_base = json.load (fp)
fp.close ()

fp = open ('ercot_8.json', mode='r')
ppc_new = json.load (fp)
fp.close ()

for key in ['gen', 'gencost', 'genfuel']:
  ppc_base[key] = ppc_new[key]

fp = open ('../case8/ercot_new_8.json', 'w')
json.dump (ppc_base, fp, indent=2)
fp.close ()

