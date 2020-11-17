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
    print ('{:32s} {:9.2f} {:14s} {:14s} {:14s} {:14s}'.format (zname, zvol, Hsched, Csched, Helem, Celem))
fp.close()

print ('{:3d} zones total {:6.2f} m3'.format(nzones,volume))
print ('Heating Coils:', hcoils)
print ('Cooling Coils:', ccoils)

