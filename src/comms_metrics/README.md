
# Introduction

Welcome!

As the use of wirelessly connected devices continues to rise, the need to evaluate the communication quality of these devices rises also. In particular, power distribution systems are converting to a wirelessly connected system to become more efficient. 

We have limited access to the raw power distribution systems data. So, we use models to represent these systems. However, we needed a way to evaluate how well our models match the real-world data we *do* have. Thus, we have created `validation`. `validation` is a Python package that evaluates how well meters within power distribution system models can communicate with each other.

Wirelessly connected power distribution meters generally have a maximum range of communication they can cover. So, the metrics we've developed calculate things like, how many meters are within a certain radius of each other, how many meters are isolated, among other things.

## Installation
This package is not currently deployed for public use. For now, clone this repository and explore the modules using your desired Python IDE. Once this package is deployed for public use, type `pip install validation` into your command prompt and hit `enter` (or `return`). From there, you will be able to import the package like normal.

## Details

As mentioned above, `validation` is a Python package. Not only can it perform metric calculations, it also has the ability to plot the models as a network and parse different file formats as pre-processing for the data analysis. Some required tools to be able to do these things are as follows:
* [pandas](https://pandas.pydata.org/docs/)
* numpy
* xlrd
* openpyxl
* xarray\*
* datashader\*
* [holoviews](https://holoviews.org/)
* [hvplot](https://hvplot.holoviz.org/)
* [networkx](https://networkx.org/documentation/stable/index.html)
* pyproj\**

\* *Note: These might automatically be installed when installing holoviews and hvplot. If not, please install them before making and/or saving plots.*
\** *Note: This might automatically be installed when installing python. If not, please install it before performing the metrics calculations.*

All the methods and functions throughout `validation` are well documented within the documentation strings. Please reference those for more detailed explanations.

## Examples

Let's look at some examples of what `validation` can do.
### `utils`
`utils` is a module within `validation` that provides some file parsing to reformat data for the data analysis efforts. The current file formats that are used are JSON, [DSS](https://fileinfo.com/extension/dss#:~:text=Audio%20file%20saved%20by%20a,environments%2C%20such%20as%20law%20firms.), and .txt files.

#### `parse_json_file(json_file, out_path, out_file_name)`
This function turns a JSON file representation of the power distribution system model into a [pandas](https://pandas.pydata.org/docs/) data frame of the billing meter names and positions.
``` 
Args:
	json_file (JSON file) - JSON file of the power distribution system model.
    
    	out_path (path) - Path to send the data frame. Saves the data frame as a csv.
    
    	out_file_name (str) - Name of the output file.

Returns:
	(null)
```
Here's an example of using this function:
```
import os
from utils import parse_json_file

if __name__ == '__main__':
	# Reading in the file:
	data_file = os.path.join(os.getcwd(), 'my_json.json')

	# Creating an output path to send the csv:
	my_out_path = os.path.join(os.getcwd())

	# Creating a name for the file:
	my_out_name = 'my_reformatted_file'

	# Creating and saving the csv to my path:
	parse_json_file(data_file, my_out_path, my_out_name)
```
Now, let's look at `parse_dss_file`.  This function takes two files: one that has meter names, and another that has the coordinates for those meters. The file that has meter names is a [DSS](https://fileinfo.com/extension/dss#:~:text=Audio%20file%20saved%20by%20a,environments%2C%20such%20as%20law%20firms.) file. The file that has the coordinates for those meters is a .txt file. These two file formats match the file format of real-world data sets.

#### `parse_dss_file(load_file, coord_file, out_path, out_file_name)`
This function parses the lines of the load\* and coordinate file, and it saves them as a single csv file.

\* *Note: The load file should be the DSS file.*
```
Args:
	load_file (str) - Name of the load file. This dss file has bus and load data, among other data. We use this to pair its data with the correct coordinates.

        coord_file (str) - Name of the coordinate file. This contains the coordinates for the bus(es).

        out_path (path) - Path to send the reformatted data file(s).

        out_file_name (str) - Name to give the data file(s).

Returns:
        (null)
```
Here's an example:
```
import os
from utils import parse_json_file

if __name__ == '__main__':
	# Reading in the files:
	meter_file = os.path.join(os.getcwd(), 'my_meters.dss')
	coord_file = os.path.join(os.getcwd(), 'my_coords.txt')

	# Creating an output path to send the csv:
	my_out_path = os.path.join(os.getcwd())

	# Creating a name for the file:
	my_out_name = 'my_reformatted_file'

	# Creating and saving the csv to my path:
	parse_dss_file(meter_file, coord_file, my_out_path, my_out_name)
```
It's that simple!

*Note: It's important that the JSON file and/or DSS match the formatting we are using. Our next steps with these functions are to accommodate ANY format these files are in; that way people can use these instead of their own data re-formatting.* 

### `system`
This module provides the capability for turning the power distribution system model into a Python object. This allows for the ease in calculation and computation.

In addition, this module provides the capability for creating and saving the model as a network plot, using [NetworkX](https://networkx.org/documentation/stable/index.html), [HoloViews](https://holoviews.org/), and [hvplot](https://hvplot.holoviz.org/).

This module can read in data from JSON files, Excel spreadsheets, and CSV files. For our analysis, it grabs the meter names and positional information; all our metrics need to know the distance between these meters. In addition, it grabs the name of the model and the names of the feeders.

To make things easy for testing potentially large sets of models, we created a class called `MeterNetwork` to house all the functions and methods we need to perform analysis.

Here's a basic example:
```
from system import MeterNetwork


if __name__ == '__main__':
	# Initializing the MeterNetwork object:
	MN = MeterNetwork()

	# Adding meters to the object:
	MN.meter_nodes = ['meter1', 'meter2', 'meter3', 'meter4']

	# Adding edges (aka abstract connections between meters)
	MN.meter_edges = [
		('meter1', 'meter2'), ('meter1', 'meter3'),
		('meter1', 'meter4'), ('meter2', 'meter3'),
		('meter2', 'meter4'), ('meter3', 'meter4')]

        # Adding meter positional information:
	MN.meter_positions = {
		'meter1': (1, 2), 'meter2': (2, 2),
		'meter3': (3, 4), 'meter4': (5, 4)}

	# Adding model name and feeder information
	MN.model_name = 'my_model'
	MN.feeder = 'my_feeder
```
The above example shows how to make a meter network from scratch.

However, this is not the primary purpose of this class. This class has different methods for reading in models to do the above example for you. These methods are `from_json`, `from_csv`, and `from_excel`, respectively.

Let's look at each of these individually to see how they can be used. In general, these methods turn the data into a [NetworkX](https://networkx.org/documentation/stable/index.html) representation of the model. This makes things easier for plotting and calculating our metrics.

#### `from_excel(excel_file, sheet, columns)`
This method turns an Excel file into a NetworkX representation of the meter system.
```
Args:
	excel_file (file) - Excel file of the system that contains meter locations, connections between meters, among other information.

    	sheet (str) - The sheet of the Excel file with meters' (aka nodes') information in it.

    	columns (list) - List of node columns to call for reading in the data, e.g. 'name' or 'id', 'latitude', 'longitude', etc. The format assumes the name of the node is first and the location data is second.

Returns:
    	G (NetworkX graph) - NetworkX graph representation of the meter system.
```
Here's an example:
```
import os
from system import MeterNetwork


if __name__ == '__main__':
	# Initializing the MeterNetwork class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.xlsx')

	# Creating our graph representation of our model:
	my_graph = MN.from_excel(my_file, 'meters', ['name', 'x', 'y'])
```
By doing this, the attributes that we care about (e.g. `meter_nodes`, `meter_edges`, etc.) get filled out for you.

The following methods do the same operation, but for different file types.

#### `from_csv(csv_file, columns)`
This method turns a CSV file into a NetworkX representation of the meter system.
```
Args:
	csv_file (file) - CSV file of the system that contains meter location, meter names, and other information.

    	columns (list) - List of node columns to call for reading in the data, e.g. 'name' or 'id', 'latitude', 'longitude', etc. The format assumes the name of the node is first and the location data is second.

Returns:
	G (NetworkX graph) - NetworkX graph representation of the meter system.
```

```
import os
from system import MeterNetwork


if __name__ == '__main__':
	# Initializing the MeterNetwork class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph represenation of our model:
	my_graph = MN.from_csv(my_file, ['name', 'x', 'y'])
```
#### `from_json(json_file, key_list, position_labels)`
This method turns a JSON file into a NetworkX representation of the meter system.
```
Args:
	json_file (file) - JSON file of the system that contains meter locations, connections between meters, and other information.

    	key_list (list) - List of the keys from the JSON file. They should be something like 'name', 'id', etc. This method assumes the first key listed is the key that has the names/ids of the meters.

    	position_labels (list) - List of the meter position keys in the JSON, e.g. 'lat' and 'lon', 'latitude' and 'longitude', 'x' and 'y', etc. This method assumes the first element is the 'longitude' element.

Returns:
     	G (NetworkX graph) - NetworkX graph reprsentation of the meter system.
```
```
import os
from system import MeterNetwork


if __name__ == '__main__':
	# Initializing the MeterNetwork class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.json')

	# Creating our graph represenation of our model:
	my_graph = MN.from_csv(my_file, ['name'], ['x', 'y'])
```
For all of these methods, if you want to make sure they grabbed the right information from your data, print out `meter_nodes`, `meter_edges`, and/or `meter_positions`.
```
print('Here are the meters we grabbed from your data:')
print(MN.meter_nodes)
```
```
Here are the meters we grabbed from your data:
['meter1', 'meter2', 'meter3', 'meter4', 'meter5',
 'meter6', 'meter7', 'meter8', 'meter9', 'meter10',
 'meter11', 'meter12', 'meter13', 'meter14', 'meter15',
 'meter16', 'meter17, 'meter18', 'meter19', 'meter20',
 'meter21']
```

As mentioned previously, this module turns our data into a format can be used for calculations and computations more easily. To do this, we turn our models into [pandas](https://pandas.pydata.org/docs/) data frames. `make_dataframe` does that for us, instead of knowing how to make a data frame from scratch.
#### `make_dataframe()`
This method turns the meter graph into a pandas data frame. This allows for ease and the ability to perform metrics calculations and validation of the system as a whole.
```
Args:
	(null)

Returns:
	dataframe (pandas data frame) - Pandas data frame representation of the meter names, locations, and other information.
```
Here's an example:
```
import os
from system import MeterNetwork


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	my_graph = MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe()
```
Or, you could do this for any of the above methods:
```
import os
from system import MeterNetwork


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Another way of creating our graph representation
	# of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Another way of creating a dataframe of our graph:
	df = MN.make_dataframe()
```
Now, our data is in a format that we can start performing metrics calculations.

But before we get to that, let's look at how to make a plot of this meter network.

#### `plot_graph(nodes, node_args, edges, edge_args, plot_positions, opts_dict, output_dir, save_plot=True)`
This method creates a visual representation of the meter system using [HoloViews](https://holoviews.org/) and NetworkX drawing capabilities.
```
Args:
	nodes (list) - List of the nodes in the NetworkX representation of the meter system.

    	node_args (dict) - Dictionary of data of how to draw the graph. Things to consider include node color, node size, node labels, etc. See the above link for more examples.

    	edges (list) - List of the edges that connect the meters.

    	edge_args (dict) - Dictionary of the meter connections within the graph. Things to consider include edge color, edge size, etc. See the above link for more information.

    	plot_positions (dict) - Dictionary of the meter positions within the graph. If they are not provided or updated, the plot_positions will be the default positions after instantiation of the MeterNetwork object.

    	opts_dict (dict) - Dictionary of how the final plot should look. Things to consider include title, font size, the height and width of the plot, etc.

    	output_dir (directory) - Directory to send the final plot of the graph.

    	save_plot (bool) - Boolean of whether or not to save the plot generated. Default is 'True'.

Returns:
    	(null)
```
Let's plot our meter network.

```
import os
from system import MeterNetwork


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating the argument dictionaries:
	n_args = {
		'node_color': 'tan', 'node_size': 3500,
		'alpha': 0.5}
	e_args = {
		'edge_color': 'grey', 'edge_size': 1,
		'style': 'dotted', 'alpha': 0.65}
	o_args = {
		'width': 900, 'height': 500,
		'title': 'My Meter Network:', 'fontsize': {'title': 30}}

	# Creating the output path:
	out_dir = os.path.join(os.getcwd())

	# Creating a plot of the meter network:
	MN.plot_graph(
		MN.meter_nodes, n_args, MN.meter_edges, e_args,
		MN.meter_positions, o_args, out_dir, True)
```
Pretty simple!

We have seen how to do some data pre-processing. In addition, we have seen how we can turn our data into a meter network. Now, we'll look at how we can evaluate our meter network, and even multiple networks.
### `metrics`
This module provides different metrics to evaluate the overall communication for a given power distribution system. As mentioned previously, we want to know how well meters can communicate with each other.

For our analysis, we care about how far away meters are from each other. We have developed different metrics that capture things like, how many meters are near a central meter, how many meters are isolated, what is the largest radius to envelope all meters in one circle, etc.

This module allows for performing this analysis on a single model or multiple models. It has the ability to save these results for further analysis.

This module has three classes: `EvaluateSystem`, `Results`, and `Compare`. The `EvaluateSystem` class contains all the possible metric calculations we want to perform for a meter network or networks. The `Results` class simply saves the results from those calculations as an HDF5 file, to compensate for large file sizes. The `Compare` class contains the calculations to compare the models provided to the real power distribution systems' results.

The methods that perform the metric calculations can  be summarized into two approaches: ad-hoc and iterative. The ad-hoc methods are to be used for one-off testing, especially for small power distribution system models. The iterative methods are to be used for testing against a range of values for multiple models at once.

Let's take a look! First, we'll have to initialize the `EvaluateSystem` class. A more detailed description of what this class does and how to initialize it is contained in the documentation string.

Here's an example:
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe()

	# Creating an EvaluateSystem object from our network:
	#     NOTE: To initialize the EvaluateSystem object, we
	# 	  need the data frame that represents the model, the
	# 	  meters (as nodes), their positional data, and what
	# 	  unit of measurement the positional data is in. 
	ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo') 
```
So, we have successfully created an `EvaluateSystem` object. Now, let's do some calculations on this power distribution model.

Before we can do those calculations, we have to calculate the distances between all the meters in the model. Here's how we do that:
#### `get_distances`
This method calculates the distances between all the meters in the system and saves the result as a data frame to be used for further analysis.
```
Args:
	(null)

Returns:
     distance_dataframe (pandas data frame) - This is a dataframe that has the calculated distance between all meters in a given meter network (aka model).
```
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe()

	# Creating an EvaluateSystem object from our network:
	ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

	# Calculating the distances between all the meters in
	# our model:
	dd = ES.get_distances()
```
Okay. Now that we have calculated the distances between all the meters in the model, we can start calculating the metrics.
#### `meter_density(meter, radius)`
This method returns the number of meters within a distance of *x* from the meter in question. For example, suppose we have a model of 10 meters ('meter1', 'meter2', … , 'meter10'). Choose 'meter1' as the center. Suppose further our radius to test is 100 feet. This method counts how many meters are within 100 feet of 'meter1'.
```
Args:
	meter (str) - The meter in question (aka the starting node in a graph).

    	radius (float) - The distance to envelope the meters near the starting meter.

Returns:
    	total_meters (int) - The total number of meters within the radius.
```
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe()

	# Creating an EvaluateSystem object from our network:
	ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

	# Calculating the distances between all the meters in
	# our model:
	dd = ES.get_distances()

	# Calculating the total number of meters within
	# 100 feet of 'meter1':
	density = ES.meter_density('meter1', 100.0)

	# This should print out the total number of
	# meters within 100 feet of 'meter1'.
	print('The number of meters within 100 feet of meter1:')
	print(density)
```
```
The number of meters within 100 feet of meter1:
14 
```
Suppose we want to know the largest radius we need to capture all the meters in the model
in one circle around a certain meter as the center. We would use the `meter_range` method.
#### `meter_range(meter)`
This method returns the radius, *x*, of the circle centered on a given meter encompasses all meters.

For example, suppose we have a model of 10 meters ('meter1', 'meter2', … , 'meter10'). Choose 'meter1' as the center. This method finds the largest radius between 'meter1' and all the remaining meters.
```
Args:
	meter (str) - The meter in question (aka the starting node in a graph).

Returns:
    	radius (float) - The maximum distance that envelopes all meters with a given meter as the center.
```
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe()

	# Creating an EvaluateSystem object from our network:
	ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

	# Calculating the distances between all the meters in
	# our model:
	dd = ES.get_distances()

	# Calculating the largest radius to capture all the
	# meters in one circle around 'meter1':
	meter_range = ES.meter_range('meter1')

	# This will print out the largest radius to capture
	# all the meters in one circle around 'meter1'.
	print('The largest radius to get all meters around meter1:')
	print(meter_range)
```
```
The largest radius to get all meters around meter1:
176.21
```
Suppose we want to know the total number of isolated meters within a certain radius. We would use the `isolated_meter_count` method.
#### `isolated_meter_count(radius)`
This method returns how many meters have no other meters within *x* distance of them.

For example, suppose we have a model of 10 meters ('meter1', 'meter2', … , 'meter10'). Suppose further 'meter2' and 'meter3' are 300+ feet from each other and the remaining meters, and the remaining meters are 150 feet or less from each other. Let the radius to test against be 200 feet. Then, this method would say there are two meters that are isolated from the other meters because their distances are greater than 200 feet.
```
Args:
	radius (float) - A given distance to test whether or not meters are near each other.

Returns:
    	isolated_count (int) - The total number of meters that are isolated from others, given a specific distance.
```
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe()

	# Creating an EvaluateSystem object from our network:
	ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

	# Calculating the distances between all the meters in
	# our model:
	dd = ES.get_distances()

	# Calculating the number of isolated meters that
	# are greater than 100 feet from each other:
	isos = ES.isolated_meter_count(30.0)

	# This will print the total number of isolated
	# meters that are greater than 30 feet from each
	# other:
	print('The total number of isolated meters:')
	print(isos)
```
```
The total number of isolated meters:
6
```
Suppose we want to know if there exists (an abstract) direct or indirect path between any two meters in the model. We would use the `meter_continuity` method.
#### `meter_continuity(radius)`
This method aims to see if any two meters can communicate with each other, either directly or indirectly, within a certain distance.

For example, suppose we have a model of 10 meters ('meter1', 'meter2', … , 'meter10'). Suppose further 'meter2' and 'meter3' are 300+ feet from each other, but they are 100 feet from the remaining meters. Let the radius to test against be 200 feet. Since 'meter2' and 'meter3' are closer to the remaining meters (rather than each other), this method will say that there is continuity because there is an indirect path from 'meter2' to 'meter3' through any of the remaining meters.
```
Args:
	radius (float) - A given distance to test whether or not a path exists between any two meters.

Returns:
    	continuity (bool) - Whether or not the meters are connected to each other.
```
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe(MN.graph)

	# Creating an EvaluateSystem object from our network:
	ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

	# Calculating the distances between all the meters in
	# our model:
	dd = ES.get_distances()

	# Checking to see if there are direct or indirect
	# paths from any two meters where each distance is
	# less than or equal to 100 feet:
	continuity = ES.meter_continuity(100.0)

	# This will print whether or not direct or indirect
	# paths exist between any two meters in the model:
	print(continuity)
```
```
True
```
Now, let's complicate things a little bit. Suppose we want to find the total number of meters that have a certain number of meters within a specified radius. We would use the `single_hop_count` method. This is a specialized version of the `meter_density` method.
#### `single_hop_count(radius, y)`
This method returns the number of meters with *y* meters within *x* distance of them.

For example, suppose we have a model of 10 meters ('meter1', 'meter2', … , 'meter10'). Let *y* = 2 and let radius = 200 feet. This method counts how many meters have less than or equal to 2 meters within 200 feet of them. Suppose 'meter1', 'meter2', and 'meter3' are all 150 feet from each other, while the remaining meters are 300+ feet from them and each other. This method will return 3 because 'meter1', 'meter2', and 'meter3' all have 2 meters or less within 200 feet.
```
Args:
	radius (float) - A given distance to test whether or not a number of meters, y, are within a certain distance of a specified meter as the center.

    y (int) - Specific number of meters near the starting meters.

Returns:
    single_hop_count (int) - The total number of meters with a certain number of meters near them within a given distance.
```
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe()

	# Creating an EvaluateSystem object from our network:
	ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

	# Calculating the distances between all the meters in
	# our model:
	dd = ES.get_distances()

	# Counting how many meters have 3 or less meters
	# within 100 feet:
	shc = ES.single_hop_count(100.0, 3)

	# This will print how many meters that have
	# 3 or less meters within 100 feet:
	print('This is the total number of meters with 3 meters nearby:')
	print(shc)
```
```
This is the total number of meters with 3 meters nearby:
22
```
Another important metric to calculate is the number of islands in the system. An island is a group of one or more meters with distances from each other less than a specified radius. This tells us that there is still some communication between meters when some connections are removed. For this analysis, a lower number of islands indicates better communication between the meters.

#### `island_count(radius)`
```
Args:
	radius (float) - A given distance to count how many islands there are in the model.

Returns:
	island_count (int) - The number of islands in the model.
```

Let's look at an example of how to use this method.

```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe()

	# Creating an EvaluateSystem object from our network:
	ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

	# Calculating the distances between all the meters in
	# our model:
	dd = ES.get_distances()

	# Counting how many islands there are with
	# meters that are less than 100 feet away:
	isl = ES.island_count(100.0)

	# This will print how many islands there are
	# with meters that are less than 100 feet away:
	print('This is the total number of islands:')
	print(isl)
```
```
This is the total number of islands:
607
```

So far, we have looked at small tests for a single model. What if we want to test against multiple radii or all the meters in a model? What if we want to do these calculations for many models?

Below, we provide an example for performing these calculations for a range of radii for more than one model\*. 

\* *Note: For the sake of simplicity, we leave the descriptions for each of the methods to the reader. The documentation strings for the methods provide more details. In general, these methods are the same as what we've seen thus far, but are done iteratively for many meters, radii, and models.*
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Grabbing all the models:
	model_path = os.path.join(os.getcwd(), 'models')
	for root, dirs, files in os.walk(model_path):
		for file in files:
			# Initializing the class:
			MN = MeterNetwork()

			# Creating our graph representation of our model: 
			MN.from_csv(
				os.path.join(model_path, file), ['name', 'x', 'y'])

			# Creating a dataframe of our graph:
			df = MN.make_dataframe()

			# Creating an EvaluateSystem object from our network:
			ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

			# Calculating the distances between all the meters in
			# our model:
			dd = ES.get_distances()

			# Calculating all the densities for all the meters
			# for radii of 100, 200, and 300 feet:
			densities = ES.all_densities([100.0, 200.0, 300.0])

			# Calculating all the radii for all meters
			# as the center:
            		ranges = ES.all_ranges()
 
            		# Calculating all the isolated meters for radii
            		# of 100, 200, and 300 feet:
            		isolates = ES.all_isolates([100.0, 200.0, 300.0])
 
 		        # Checking if paths exits between any two meters
            		# for radii of 100, 200, and 300 feet:
            		continuous = ES.all_continuous([100.0, 200.0, 300.0])
 
            		# Calculating all the single_hop_counts for
            		# radii of 100, 200, 300 feet:
            		shc = ES.all_single_hops([100.0, 200.0, 300.0])

			# Calculating all the islandcounts for
			# radii of 100, 200, 300 feet:
			isl = ES.all_islands([100.0, 200.0, 300.0])
```
This is good, but how can we use these values to figure out how well the meters in our models can communicate with each other?

We can use the `evaluate_system`\* method. This method turns the results of the above values into an overall, weighted score. In general, the higher the score, the better the meters in the model(s) can communicate with each other.

\* *Note: A more detailed description of how we use these values and generate the score is contained in the documentation string of this method.*
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem


if __name__ == '__main__':
	# Initializing the class:
	MN = MeterNetwork()

	# Grabbing our data:
	my_file = os.path.join(os.getcwd(), 'my_file.csv')

	# Creating our graph representation of our model:
	MN.from_csv(my_file, ['name', 'x', 'y'])

	# Creating a dataframe of our graph:
	df = MN.make_dataframe()

	# Creating an EvaluateSystem object from our network:
	ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

	# Calculating the distances between all the meters in
	# our model:
	dd = ES.get_distances()

	# Calculating all the densities for all the meters
	# for radii of 100, 200, and 300 feet:
	densities = ES.all_densities([100.0, 200.0, 300.0])

	# Calculating all the radii for all meters
	# as the center:
    	ranges = ES.all_ranges()

    	# Calculating all the isolated meters for radii
    	# of 100, 200, and 300 feet:
    	isolates = ES.all_isolates([100.0, 200.0, 300.0])

    	# Checking if paths exits between any two meters
    	# for radii of 100, 200, and 300 feet:
    	continuous = ES.all_continuous([100.0, 200.0, 300.0])

    	# Calculating all the single_hop_counts for
    	# radii of 100, 200, 300 feet:
    	shc = ES.all_single_hops([100.0, 200.0, 300.0])

	# Calculating all the island counts for
	# radii of 100, 200, 300 feet:
	isl = ES.all_islands([100.0, 200.0, 300.0])

	# Calculating the overall score for this
	# model:
	score = ES.evaluate_system([100.0, 200.0, 300.0])

	# This will print a value that represents how well
	# the meters can communicate with each other:
	print(score)
```
```
80.9
```
A similar approach can be applied for more than one model.

We have shown different things to calculate and how to get them. Now, we need a way to save the results for further analysis. So, we use the `Results` class.

This class collects and saves the results from more than one power distribution system model evaluation.

For our analysis, we not only care about the communication between meters for a single model, but many models. This class is for collecting **all** the results from **all** models tested for analysis.

The `Results` class has two methods: `add` and `save`. The `add` method simply appends each `EvaluateSystem` object to a list. The `save` method saves all the results from all the models into one HDF5 file.

Let's put it all together!
```
import os
from system import MeterNetwork
from metrics import EvaluateSystem, Results


if __name__ == '__main__':
	# Grabbing all the models:
	model_path = os.path.join(os.getcwd(), 'models')

	# Creating a Results object:
	RS = Results()
	for root, dirs, files in os.walk(model_path):
		for file in files:
			# Initializing the class:
			MN = MeterNetwork()

			# Creating our graph representation of our model: 
			MN.from_csv(
				os.path.join(model_path, file), ['name', 'x', 'y'])

			# Creating a dataframe of our graph:
			df = MN.make_dataframe()

			# Creating an EvaluateSystem object from our network:
			ES = EvaluateSystem(df, MN.meter_nodes, 'x', 'y', 'geo')

			# Calculating the distances between all the meters in
			# our model:
			dd = ES.get_distances()

			# Calculating all the densities for all the meters
			# for radii of 100, 200, and 300 feet:
			densities = ES.all_densities([100.0, 200. 0, 300. 0])

			# Calculating all the radii for all meters
			# as the center:
            		ranges = ES.all_ranges()
 
            		# Calculating all the isolated meters for radii
            		# of 100, 200, and 300 feet:
            		isolates = ES.all_isolates([100.0, 200.0, 300.0])
 
            		# Checking if paths exits between any two meters
            		# for radii of 100, 200, and 300 feet:
            		continuous = ES.all_continuous([100.0, 200.0, 300.0])
 
            		# Calculating all the single_hop_counts for
            		# radii of 100, 200, 300 feet:
            		shc = ES.all_single_hops([100.0, 200.0, 300.0])

			# Calculating all the island counts for
			# radii of 100, 200, 300 feet:
			isl = ES.all_islands([100.0, 200.0, 300.0])

			# Calculating the overall score for this
			# model:
			score = ES.evaluate_system([100.0, 200.0, 300.0])

			# Adding the model to the Results object:
			RS.add(ES)
	
	# Saving the results for all the models:
	out_dir = os.path.join(os.getcwd())
	out_name = 'all_models_results.h5'
	RS.save(out_dir, out_name)
```
The main goal of this project is to compare modelled power distribution systems to real power distribution systems. To do that, we developed the `Compare` class. This class takes the metrics results of the real and modelled systems and calculates the mean squared errors of those results; the lower the mean squared error, the better the models match the real data.

Each of the above metrics have their own corresponding comparison method to be used. Each of the comparison methods have the capability to compare the models to the real power distribution systems as a whole, or individual feeders of the real systems.

Let's look at what `Compare` has to offer. Again, more descriptions of what the methods in this class can be found in the documentation strings.

The first comparison method compares the meter density results between the real power distribution systems and the models.
#### `compare_meter_density(models, how, radii)`
```
Args:
	models (list) - List of all the models (as pandas dataframes) for comparing to real data.

	how (str) - How we should compare the models to the real data. The options are as follows:
		'agg' - Choosing how='agg' will compare the model(s) to the real data as a whole, meaning we will compare the model(s) to ALL of the feeders at once in a particular region and demographic.
		'single' - Choosing how='single' will compare the model(s) to the real data individually, meaning we will compare the model(s) to EACH of the feeders, one at a time.
	radii (list) - List of radii (in feet) to count the number of meters near a given meter.

Returns:
	stats_df (pandas dataframe) - A pandas dataframe that contains the results of calculating the MSE. If how equals 'agg', then the dataframe will have the scores based off of comparing the model(s) to the WHOLE real dataset. If how equals 'single', the dataframe will have the scores based off of comparing the model(s) to each of the real feeders in the real data set individually.
```
Let's look at an example of how to use this method.
```
import pandas as pd
from metrics import Compare

if __name__ == '__main__`:
	# Create a Compare object:
	C = Compare()
	
	# Load the real metrics results:
	C.load_data()

	# Load the modelled metrics results:
	model = pd.read_hdf('results.h5', key='density')

	# Comparing the modelled results to
	# the real results:
	stats_df = C.compare_meter_density([model], 'agg', [100.0, 200.0, 300.0])

	# Looking at the results:
	print(stats_df)
```

| feeder  | radius |   mse    |
|:-------:|:------:|:--------:|
| feeder1 | 100.0  | 0.017425 |
| feeder1 | 200.0  | 0.231688 |
| feeder1 | 300.0  | 3.021774 |

Again, each of the comparison methods calculate the mean squared error between the models and the real power distribution systems; we omit a description for each of the remaining methods because they're doing the same calculation, just on different metrics' results. More information is provided in the documentation string of each comparison method.

#### `compare_meter_range(models, how)`
```
Args:
	models (list) - List of all the models (as pandas dataframes) for comparing to real data.
	how (str) - How we should compare the models to the real data. The options are as follows:
		'agg' - Choosing how='agg' will compare the model(s) to the real data as a whole, meaning we will compare the model(s) to ALL of the feeders at once.
		'single' - Choosing how='single' will compare the model(s) to the real data individually, meaning we will compare the model(s) to EACH of the feeders, one at a time, in a particular region and demographic

Returns:
	stats_df (pandas dataframe) - A pandas dataframe that contains the results of calculating the MSE. If how equals 'agg', then the dataframe will have the scores based off of comparing the model(s) to the WHOLE real dataset. If how equals 'single', the dataframe will have the scores based off of comparing the model(s) to each of the real feeders in the real data set individually.
```
Example:
```
import pandas as pd
from metrics import Compare

if __name__ == '__main__`:
	# Create a Compare object:
	C = Compare()
	
	# Load the real metrics results:
	C.load_data()

	# Load the modelled metrics results:
	model = pd.read_hdf('results.h5', key='range')

	# Comparing the modelled results to
	# the real results:
	stats_df = C.compare_meter_range([model], 'agg')

	# Looking at the results:
	print(stats_df)
```

| feeder  |   mse    |
|:-------:|:--------:|
| feeder1 | 2.396914 |

#### `compare_isolated_meters(models, how, radii)`
```
Args:
	models (list) - List of all the models (as pandas dataframes) for comparing to real data.
	how (str) - How we should compare the models to the real data. The options are as follows:
		'agg' - Choosing how='agg' will compare the model(s) to the real data as a whole, meaning we will compare the model(s) to ALL of the feeders at once.
		'single' - Choosing how='single' will compare the model(s) to the real data individually, meaning we will compare the model(s) to EACH of the feeders, one at a time.
	radii (list) - List of radii (in feet) to count the number of meters near a given meter.

Returns:
    stats_df (pandas dataframe) - A pandas dataframe that contains the results of calculating the MSE. If how equals 'agg', then the dataframe will have the scores based off of comparing the model(s) to the WHOLE real dataset. If how equals 'single', the dataframe will have the scores based off of comparing the model(s) to each of the real feeders in the real data set individually.
```
Example:
```
import pandas as pd
from metrics import Compare

if __name__ == '__main__`:
	# Create a Compare object:
	C = Compare()
	
	# Load the real metrics results:
	C.load_data()

	# Load the modelled metrics results:
	model = pd.read_hdf('results.h5', key='isolated')

	# Comparing the modelled results to
	# the real results:
	stats_df = C.compare_isolated_meters([model], 'agg', [100.0, 200.0, 300.0])

	# Looking at the results:
	print(stats_df)
```

| feeder  | radius |   mse    |
|:-------:|:------:|:--------:|
| feeder1 | 100.0  | 2.032204 |
| feeder1 | 200.0  | 1.906663 |
| feeder1 | 300.0  | 1.938369 |

#### `compare_meter_continuity(models, how, radii)`
```
Args:
	models (list) - List of all the models (as pandas dataframes) for comparing to real data.
	how (str) - How we should compare the models to the real data. The options are as follows:
		'agg' - Choosing how='agg' will compare the model(s) to the real data as a whole, meaning we will compare the model(s) to ALL of the feeders at once.
		'single' - Choosing how='single' will compare the model(s) to the real data individually, meaning we will compare the model(s) to EACH of the feeders, one at a time.
	radii (list) - List of radii (in feet) to count the number of meters near a given meter.

Returns:
	stats_df (pandas dataframe) - A pandas dataframe that contains the results of calculating the MSE. If how equals 'agg', then the dataframe will have the scores based off of comparing the model(s) to the WHOLE real dataset. If how equals 'single', the dataframe will have the scores based off of comparing the model(s) to each of the real feeders in the real data set individually.
```
Example
```
import pandas as pd
from metrics import Compare

if __name__ == '__main__`:
	# Create a Compare object:
	C = Compare()
	
	# Load the real metrics results:
	C.load_data()

	# Load the modelled metrics results:
	model = pd.read_hdf('results.h5', key='continuous')

	# Comparing the modelled results to
	# the real results:
	stats_df = C.compare_meter_continuity([model], 'agg', [100.0, 200.0, 300.0])

	# Looking at the results:
	print(stats_df)
```

| feeder  |   mse    |
|:-------:|:--------:|
| feeder1 | 0.000798 |

#### `compare_single_hop_count(models, how, radii)`
```
Args:
	models (list) - List of all the models (as pandas dataframes) for comparing to real data.
	how (str) - How we should compare the models to the real data. The options are as follows:
		'agg' - Choosing how='agg' will compare the model(s) to the real data as a whole, meaning we will compare the model(s) to ALL of the feeders at once.
		'single' - Choosing how='single' will compare the model(s) to the real data individually, meaning we will compare the model(s) to EACH of the feeders, one at a time.
	radii (list) - List of radii (in feet) to count the number of meters near a given meter.

Returns:
	stats_df (pandas dataframe) - A pandas dataframe that contains the results of calucalting the MSE. If how equals 'agg', then the dataframe will have the scores based off of comparing the model(s) to the WHOLE real dataset. If how equals 'single', the dataframe will have the scores based off of comparing the model(s) to each of the real feeders in the real data set individually.
```
Example
```
import pandas as pd
from metrics import Compare

if __name__ == '__main__`:
	# Create a Compare object:
	C = Compare()
	
	# Load the real metrics results:
	C.load_data()

	# Load the modelled metrics results:
	model = pd.read_hdf('results.h5', key='single_hop')

	# Comparing the modelled results to
	# the real results:
	stats_df = C.compare_single_hop_count([model], 'agg', [100.0, 200.0, 300.0])

	# Looking at the results:
	print(stats_df)
```

| feeder  | radius |   mse    |
|:-------:|:------:|:--------:|
| feeder1 | 100.0  | 2.007354 |
| feeder1 | 200.0  | 2.009119 |
| feeder1 | 300.0  | 1.947478 |

#### `compare_island_count(models, how, radii)`
```
Args:
	models (list) - List of all the models (as pandas dataframes) for comparing to real data.
	how (str) - How we should compare the models to the real data. The options are as follows:
		'agg' - Choosing how='agg' will compare the model(s) to the real data as a whole, meaning we will compare the model(s) to ALL of the feeders at once.
		'single' - Choosing how='single' will compare the model(s) to the real data individually, meaning we will compare the model(s) to EACH of the feeders, one at a time.
	radii (list) - List of radii (in feet) to count the number of meters near a given meter.

Returns:
	stats_df (pandas dataframe) - A pandas dataframe that contains the results of calculating the MSE. If how equals 'agg', then the dataframe will have the scores based off of comparing the model(s) to the WHOLE real dataset. If how equals 'single', the dataframe will have the scores based off of comparing the model(s) to each of the real feeders in the real data set individually.
```
Example
```
import pandas as pd
from metrics import Compare

if __name__ == '__main__`:
	# Create a Compare object:
	C = Compare()
	
	# Load the real metrics results:
	C.load_data()

	# Load the modelled metrics results:
	model = pd.read_hdf('results.h5', key='island')

	# Comparing the modelled results to
	# the real results:
	stats_df = C.compare_island_count([model], 'agg', [100.0, 200.0, 300.0])

	# Looking at the results:
	print(stats_df)
```

| feeder  | radius  |   mse    |
|:-------:|:-------:|:--------:|
| feeder1 |  100.0  | 1.840693 |
| feeder1 |  200.0  | 2.007030 |
| feeder1 |  300.0  | 2.004431 |

That's `validation` in a nutshell!

## Future Work
Right now, the only calculation to evaluate how well the models match the real power distribution systems is the mean squared error. This does not tell us what value of mean squared error indicates that a model does not match the real data. We would like to expand upon this calculation and investigate similar calculations that will better determine whether or not the models match the real data.

We would also like to investigate and expand upon the current metrics we have developed. We have a small set of metrics that we generated to evaluate our models. There are certainly more things we could create and use for our analysis. In addition, we desire to appropriately weight the metrics we have in the `evaluate_system` method.

Some of our data pre-processing and other functions are developed to match a specific data format. We would like to generalize these functions to handle potentially any data or file format that is provided. For example, this would require creating more functions that can parse different file formats.

Right now, we have one method that can create and save a plot. This plot is just the power distribution system model represented as a network. We would like to develop more methods and/or a module for plotting the results of the metric calculations. Since we use [HoloViews](https://holoviews.org/) and [NetworkX](https://networkx.org/documentation/stable/index.html) throughout our modules, we can use some of their methods for generating analytical plots.