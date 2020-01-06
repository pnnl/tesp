import csv
zones = {}

fp = open('output/eplusout.eio', 'r')
rdr = csv.reader (fp)
for row in rdr:
  if row[0].strip() == 'Zone Information':
    zname = row[1].strip()
    zones[zname] = float(row[19])
fp.close()

volume = 0
for zname, zvol in zones.items():
  print ('{:32s} {:6.1f}'.format (zname, zvol))
  volume += zvol
print ('{:3d} zones total {:6.2f} m3'.format(len(zones),volume))