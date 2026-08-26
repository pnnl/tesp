import csv
import sys

root = sys.argv[1]

zones = {}
hcoils = []
ccoils = []
volume = 0
nzones = 0

print ('** Summary of', root)
fp = open('out' + root + '/eplusout.eio', 'r')
rdr = csv.reader (fp)
for row in rdr:
  if row[0].strip() == 'Zone Information':
    zname = row[1].strip()
    zvol = float(row[19])
    Hsched = 'Hsched'
    Csched = 'Csched'
    Helem = 'Helem'
    Celem = 'Celem'
    zones[zname] = {'zvol':zvol, 'Hsched': Hsched, 'Csched': Csched, 'Helem': Helem, 'Celem': Celem}
    nzones += 1
    volume += zvol
    print (f'{zname:32s} {zvol:9.2f} {Hsched:14s} {Csched:14s} {Helem:14s} {Celem:14s}')
fp.close()

print (f'{nzones:3d} zones total {volume:6.2f} m3')
print ('Heating Coils:', hcoils)
print ('Cooling Coils:', ccoils)

