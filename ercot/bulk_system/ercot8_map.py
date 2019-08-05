import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
import csv
import networkx as nx
import numpy as np
import sys

featureScale = '50m'  # 10, 50 0r 110
urbanColor = 'seagreen'
shapePath = 'z:/Documents/ShapeFiles/'

rdr1 = shpreader.Reader(shapePath + 'Texas_County_Boundaries/Texas_County_Boundaries.shp')
counties = list(rdr1.geometries())
COUNTIES = cfeature.ShapelyFeature(counties, ccrs.PlateCarree())

rdr2 = shpreader.Reader(shapePath + 'urbanap010g.shp/urbanap010g.shp')
urban = list(rdr2.geometries())
COUNTIES = cfeature.ShapelyFeature(counties, ccrs.PlateCarree())
URBAN = cfeature.ShapelyFeature(urban, ccrs.PlateCarree())

plt.figure(figsize=(10, 10))

ax = plt.axes(projection=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND.with_scale(featureScale))
#ax.add_feature(cfeature.BORDERS.with_scale(featureScale))
ax.add_feature(cfeature.STATES.with_scale(featureScale))
ax.add_feature(cfeature.OCEAN.with_scale(featureScale))
ax.add_feature(cfeature.RIVERS.with_scale(featureScale), zorder=2)
ax.add_feature(cfeature.LAKES.with_scale(featureScale), zorder=2)
ax.add_feature(URBAN, facecolor=urbanColor, edgecolor=urbanColor)
ax.add_feature(COUNTIES, facecolor='none', edgecolor='gray')
ax.coastlines(featureScale)

ax.set_extent([-107.0, -93.0, 25.0, 37.0])

# name,bus1,bus2,kV,length[miles],#parallel,r1[Ohms/mile],x1[Ohms/mile],b1[MVAR/mile],ampacity,capacity[MW]
dlines = np.genfromtxt('Lines8.csv', dtype=str, skip_header=1, delimiter=',') # ['U',int,int,float,float,int,float,float,float,float,float], skip_header=1, delimiter=',')
# bus,lon,lat,load,gen,diff,caps
dbuses = np.genfromtxt('Buses8.csv', dtype=[int, float, float, float, float, float, float], skip_header=1, delimiter=',')
# idx,bus,mvabase,pmin,qmin,qmax,c2,c1,c0
dunits = np.genfromtxt('Units8.csv', dtype=[int, int, float, float, float, float, float, float, float], skip_header=1, delimiter=',')

lbl345 = {}
e345 = set()
n345 = set()
lst345 = []
w345 = []
graph = nx.Graph()
for e in dlines:
	if '//' not in e[0]:
		n1 = int(e[1])
		n2 = int(e[2])
		npar = int(e[5])
		graph.add_edge (n1, n2)
		n345.add (n1)
		n345.add (n2)
		lbl345[(n1, n2)] = e[0]
		e345.add ((n1, n2))
		lst345.append ((n1, n2))
		w345.append (1.5 * npar)

xy = {}
for b in dbuses:
	xy[b[0]] = [b[1], b[2]]

gnodes345 = nx.draw_networkx_nodes (graph, xy, nodelist=list(n345), node_color='k', node_size=60) # , alpha=0.3)
glines345 = nx.draw_networkx_edges (graph, xy, edgelist=lst345, edge_color='r', width=w345) # , alpha=0.8)

gnodes345.set_zorder(20)
glines345.set_zorder(18)

# Save the plot by calling plt.savefig() BEFORE plt.show()
plt.savefig('Ercot8.png')

plt.show()