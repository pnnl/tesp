..
    _ Copyright (C) 2023 Battelle Memorial Institute
    _ file: gld_modifier.rst


============================
GridLAB-D Model Modification
============================

For many transactive energy analysis, detailed modeling of the distribution system is an important part of the analysis and GridLAB-D is often chosen as the modeling tool. It is not unusual, though, for a given GridLAB-D model to be non-ideal for the particular analysis scenario to be modeled and need modification in some way: adding rooftop solar, replacing the existing heat pumps with higher efficiency models, changing voltage regulator settings, etc. To aid in this, TESP includes a GridLAB-D modification API to provides a class- and object-oriented way of manipulating the model that we hope provides a (relatively) painless process for editing GridLAB-D models.

GLMModifier Philosophy
~~~~~~~~~~~~~~~~~~~~~~
There have been several other scripts previously developed that provide GridLAB-D model modification. Most of these are text-line-based where the model is read in line-by-line and at appropriate points and lines are edited before being printed out to file or additional lines are inserted before moving through the model (for example, adding rooftop solar). Though these have been used for over a decade, they always presented a challenge in that model modifications could not be made holistically as the entire model was not parsed, but rather remained as text that could be manipulated.

TESP's GLMModifier overcomes these shortcomings by providing an internal data structure into which the model can be read and parsed. By doing so, the modeler has the ability to evaluate the entire model, manipulate the necessary portions, and then write out the entire model to file. For example, after GLMModifier reads in the model and parses it into its data structure, it is possible to count the number of houses that use gas heating, convert them to use heat pumps, and upgrade any necessary transformers and power lines to handle the increased load.

There are two primary ways to access the model using GLMModifier:

* Object- or class-based - GLMModifier's data structure allows for evaluation and modification of GridLAB-D objects based on their class. For example, all GridLAB-D "house" objects are easily accessible and their parameters editable.
* Graph-based - GLMModifier uses the `networkx library <https://networkx.org/>`_ to create a graph of the electrical network. Using this library it is possible to evaluate the GridLAB-D model in terms of electrical connectivity and modify it in more specific ways. For example, networkx allows the modeler to identify which components lie between a newly added load and the substation so their capacity can be evaluated and potentially increased.


GLMModifier API Example Walk-Through
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The following is a walk-through of an example use of the GLMModifier API ("gld_modifier.py") in the TESP "examples/capabilities" folder.

GLMModifier is Python-based so the first step (after installing TESP) is importing the appropriate libraries.::

    from tesp_support.api.modify_GLM import GLMModifier
    from tesp_support.api.data import feeders_path

Then create a GLMModifier object to do the manipulation::

    glmMod = GLMModifier()

With the modifier, we can read the GridLAB-D model into the GLMModifier data structure for manipulation::

    glmMod.model.read('path/to/model.glm')

GridLAB-D split it's functionality into various modules and for this example, we're going to be adding houses to the model, which means we need to make sure the "residential" module gets added to the model file.::

    glmMod.add_module('residential', [])
    
The GLMModifier has an attribute that holds the entire GridLAB-D model, "glm". Purely to make our live a few characters easier when using the GLMModifier, we can assign this to another variable of our choice and strip out the need constantly prepend many of our commands with "GLMModifier".::

	glm = GLMMod.glm

GLMModifier makes it easy to get the names of all of the objects of a given class. In this case, since we're adding "house" objects, we need to look for GridLAB-D's "triplex_meters" to attach the houses to.::

    tp_meter_objs = glm.triplex_meter
    tp_meter_names = list(tp_meter_objs)

``tp_meter_objs`` is a Python dictionary with the keys being the object names and the value being a Python dictionary of the object parameters and values. To make a list of the names of the meters, we just need to ask for the keys of the dictionary as a list.

Adding Objects
--------------

``tp_meter_names`` is a list of the names of the GridLAB-D ``triplex_meter`` objects as strings. Using those names we can build up a Python dictionary that defines the parameters of another ``triplex_meter`` object we're going to add to the model. The dictionary is called "meter_params" and has three members all defined by the data from an existing specific ``triplex_meter`` in the model.::

    new_name = tp_meter_names[house_num]
    billing_meter_name = f"{new_name}_billing"
    billing_meter_params = {
        "parent": new_name,
        "phases": glm.triplex_meter[f"{new_name}"]["phases"],
        "nominal_voltage": glm.triplex_meter[f"{new_name}"]["nominal_voltage"],
    }

The ``phases`` and ``nominal_voltage`` are easily defined using GLMModifier as they are just members of a dictionary that defines a specific triplex meter. 

Once the Python dictionary with the GridLAB-D object parameters are defined, it can simply be added to the model.::

    glmMod.add_object('triplex_meter', billing_meter_name, billing_meter_params)

``.add_objects()`` has three parameters: the type of object, the name of the object (which the API uses to define the ``name`` parameter of the object behind the scenes), and the dictionary with the object parameters.

Adding a House
--------------

Now that we have a billing meter, we can add a house object. It is good practice to add the house as a child of a separate triplex meter (called the "house meter") if also adding solar and storage for this customer (as we will in the next step). This allows the modeler to investigate the powerflow at each node individually. We follow the same process as adding a billing meter.::

    house_meter_name = f"{new_name}_house"
    meter_params = {
        "parent": billing_meter_name,
        "phases": glm.triplex_meter[f"{new_name}"]["phases"],
        "nominal_voltage": glm.triplex_meter[f"{new_name}"]["nominal_voltage"],
    }
    house_params = {
        "parent": house_meter_name,
        "heating_setpoint": 69,
        "cooling_setpoint": 74,
        "heating_system_type": "GAS",
        "cooling_system_type": "ELECTRIC"
    }

This is a very simple house, with the majority of its parameters left to GridLAB-D default values. For a comprehensive look at the house model, check out `house_e.cpp <https://github.com/gridlab-d/gridlab-d/blob/master/residential/house_e.cpp>`_ 

Adding Solar and Storage
------------------------

Now that we have a house and a billing meter, we can add solar and storage to it. In order for GridLAB-D to parse the relationship between the house, rooftop solar, and behind-the-meter energy storage correctly, and allow us to individually manage and meter each object, the parent/child hierarchy would be as follows

* Customer Billing Meter
    * House Meter  
        * House Object
            * Water Heater
            * ZIP Loads
            * EV Charger
    * Solar Meter
        * Solar Inverter
            * Solar Object
    * Battery Meter
        * Battery Inverter
            * Battery Object

Note that because the house meter, solar meter, and battery meter all have the same parentage, we can conveniently use the meter_params we defined when adding the house, for each. To add solar and storage according to this convention, this might look like: ::

    solar_meter_name = f"{new_name}_solar"
    glmMod.add_object('triplex_meter', solar_meter_name, meter_params)

    inverter_params = {                 
                'phases': glmMod.get_object('triplex_meter').instance[billing_meter_name]['phases'],
                'parent': solar_meter_name,
                'generator_status':'ONLINE',
                'inverter_type': 'FOUR_QUADRANT',
                'inverter_efficiency': 0.95,
                'rated_power': 8000, #VA 
                'four_quadrant_control_mode': 'LOAD_FOLLOWING',
                'sense_object': house_obj  #name of object inverter trying to mitigate load
                }
    glmMod.add_object('inverter', f"{new_name}_solar_inverter", inverter_params)

    solar_params = { 
            'parent': f"{new_name}_solar_inverter",
         	'rated_power': 7.5, #kW
            'panel_type': 'SINGLE_CRYSTAL_SILICON',
         	'tilt_angle': 45.5, 
         	'efficiency': 0.20,
         	'shading_factor': 0.1,
         	'orientation_azimuth': 270.0, 
         	'orientation': 'FIXED_AXIS',
         	'SOLAR_TILT_MODEL': 'SOLPOS',
         	'SOLAR_POWER_MODEL': 'FLATPLATE',
        }
    glmMod.add_object('solar', f"{new_name}_solar, solar_params)

    battery_meter_name = f"{new_name}_battery"
    glmMod.add_object('triplex_meter', battery_meter_name, meter_params)
    glmMod.add_object('inverter', f"{new_name}_battery_inverter", inverter_params)

    battery_params = {
                'parent': f"{new_name}_battery_inverter",
             	'use_internal_battery_model': 'TRUE',
             	'battery_type': 'LI_ION',
             	'battery_capacity': 5000, #kWh
             	'base_efficiency': .95,
                'generator_mode': 'SUPPLY_DRIVEN'
             	}
    glmMod.add_object('battery', f"{new_name}_battery", battery_params)

These are very simple solar and battery definitions, with the majority of their parameters left to GridLAB-D default values. For a comprehensive look at the solar, battery, and inverter models, check out `solar <https://github.com/gridlab-d/gridlab-d/blob/master/generators/solar.cpp>`_, `battery.cpp <https://github.com/gridlab-d/gridlab-d/blob/master/generators/battery.cpp>`_, and `inverter.cpp <https://github.com/gridlab-d/gridlab-d/blob/master/generators/inverter.cpp>`_. 

We now have a house attached to a triplex meter, that has both rooftop solar and behind-the-meter energy storage. We can add recorder objects in similar fashion, parented to the object under investigation, to monitor the solar generation (property: measured_real_energy), or the state of charge of the battery (property: state_of_charge), for example. 


Adding and Modifying Existing Object Parameter Values
-----------------------------------------------------
Further down in the example, there's a portion of code showing how to modify an existing object. In this case, we use the fact that ``.add_object()`` method returns the the GridLAB-D object (effectively a Python dictionary) once it is added to the model. Once you have the GridLAB-D object, it's easy to modify any of its properties such as::

    house_obj["floor_area"] = 2469

This exact syntax is also valid for adding a parameter that is undefined to an existing GridLAB-D object.

Deleting Existing Object Parameter Values
-----------------------------------------
To delete a GridLAB-D object parameter value, you can just set to to `None`::

    house_to_edit["Rroof"] = None

Note that GridLAB-D requires some parameters to be defined to run its simulations. Removing the parameter will remove it from the GridLAB-D model file that gets created (.glm) but may effectively force GridLAB-D to use its internal default value. That is, clearing the parameter value in this way is not the same as setting it to an undefined value.

Deleting Existing Objects
-------------------------
Its possible to delete an object and all its parameter values from the GridLAB-D model::

    glmMod.del_object('house', house_to_delete)

To prevent problems with electrical continuity of the models, by default this method will delete children objects. For example, deleting this house would also delete its water heater and any ZIP loads that may be attached to it.

networkx APIs
-------------
`networkx library <https://networkx.org/>`_ is a general graph Python library and it is utilized by TESP to store the topology of the electrical network in GridLAB-D. The core GLMModifier APIs are oriented around the GridLAB-D classes and their objects in the model and from these the topology of the electrical circuit can be derived, but not easily or quickly. To make topology-based modifications easier, we've done the hard work of parsing the model and building the networkx graph. With this graph, modelers can more easily and comprehensively explore and edit the model. 

First, if any edits have been made to the GridLAB-D model since importing it, the networkx object needs to be updated prior to including those changes. Conveniently, this also returns the networkx graph object::

    graph = glmMod.model.draw_network()


As you can see, the networkx graph is a property of the GLMModifier.model object and the above line of code simply makes a more succinct reference to it.

After that, you can use networkx APIs to explore the model. For example, starting at a particular node, traverse the graph in a breadth-first manner::

    for edge in nx.bfs_edges(graph, "starting bus name"):

You, the modeler, can look at the properties of each edge (GridLAB-D link objects) to see if it is of particular interest and modify it in a specific way.


Plotting Model
--------------
GLMModifier includes the capability of creating a visual representation of the network for manual inspection. This allows the user to visually inspect the model and make sure the changes made are as expected and has the topology expected. To create the plot of the graph of the model a simple API is used::

    glmMod.model.plot_model()

Under the hood, this API makes an update to the networkx graph and then automatically lays it out and plots it on screen, as shown below.

.. figure:: ../media/glmmodGraphPlot.png
    :name: glmmodGraphPlot


Mousing over the nodes of the system shows some of the metadata associated with them; in the example image shown above, one of the houses is selected. As of this writing, this metadata is not available for the links/edges in the graph but we're anticipating adding that data soon. The layout chosen is algorithmic and does not respect coordinates that may be present in the imported .glm. For larger networks, it can take tens (or many tens) of seconds for the layout calculation to complete; creating the graph is a blocking call in the script and the rest of the script will not run until the plotting window is closed.



Writing Out Final Model
-----------------------
Once all the edits to the model have been made, the model can be written out to file as a .glm and run in GridLAB-D.::

    glmMod.write_model("output file path including file name.glm")


GLMModifier House Object Population
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Previous GridLAB-D model modification tools also included methods by which to choose the parameters for some objects (the house object in particular). The re-implementation of these features using updated data and methodologies are currently being implemented in what we are calling a "reference implementation" to show users one possible way of defining values for all these parameters. We want to not only provide an empirically-based method for defining these parameter values but also clearly document it so that other users can better understand what we did and customize or modify it to better suit their needs.


Future work
~~~~~~~~~~~~
We've put in a lot of work to support all of GridLAB-D syntax but are not quite there yet. In particular, the last remaining element we haven't been able to capture well in our data structure are the ``#ifdef`` C-like conditionals GridLAB-D supports. `This feature is on our to-do list <https://github.com/pnnl/tesp/issues/104>`_.

Currently, when GLMModifier writes out the model it does so in a manner that groups all the classes together. Alternative methods of writing out this non-linear data structure need to be evaluated so that human-readers of the file have an easier time (at least in some cases). `This is on our to-do list as well <https://github.com/pnnl/tesp/issues/105>`_.