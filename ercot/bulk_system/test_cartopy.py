import cartopy.crs as ccrs
import matplotlib.pyplot as plt

ax = plt.axes(projection=ccrs.PlateCarree())
ax.coastlines()

# Save the plot by calling plt.savefig() BEFORE plt.show()
#plt.savefig('coastlines.pdf')
#plt.savefig('coastlines.png')

plt.show()
