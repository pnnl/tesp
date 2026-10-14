# Agent Redesign Open Questions

The following are questions that Trevor has run into during his prototype redesign of the DSO+T HVAC agent.

## Spell out all parameters?
Does it make sense to spell out all the parameters used for class methods instead of just passing in "self"? Adding all the parameters explicitely makes it clear (without looking at the code) what the inputs and the outputs of the method are, though it is more work. The purest form of this may have all the parameters of the method defined as object attributes: _e.g_: `def calc_stuff(self.a: float, self.b: float, self.c: float) -> float:`

## Returing an object parameter?
Right now Trevor defines a return value for any method/function that should philosophically have one. That is, if the method calculates something, Trevor returns the result of that calculation, even if the value is also stored as an object attribute (as it usually is). Do we think this is a good idea? Should we always be doing something like this?

## Do we want configurable logging per method?
Some existing HVAC agent code passes in a logging level. This is an interesting idea and wouldn't take too much work. The default logging level could be whatever the calling object is using so it wouldn't have to be defined except where the user wanted to change it. Do we want to update this functionality and make it an optional parameter for all Agent (and probably DSO+T) classes?

## Classes within classes?
It's a bit weird but Python allows classes to be defined within classes. This would allow us to move some of stuff that is highly related and only in separate classes now into a single class. For example, the StructuralModel, EnvironmentalModel, and SystemModel share some data that would be more easily accessed inside the the AssetModel. Maybe they should live in AssetModel still as distinct classes? It would make the AssetModel file pretty long...

## Conflicting definitions of solar_heatgain_factor?
In "calc_ETP_model()", "solar_heatgain_factor" (l.1237) is defined as the product of the area of the windows, the Wg, and the WETC. This implies it has to do with the energy that is making it through the windows to the indoor air. In formulate_bid_rt, though, Qs is defined as the product of the solar_gain and the solar_heatgain_factor (l.1939). When calculating Qm (heatflow into the mass of the structure) it is multiplied by the mass_solar_gain_fraction (l.1946), implying it is the energy that is energy striking the building. Which is it?

Answer: Trevor talked with Rob and solar_heatgain_factor uses tha ASHRAE definition  and it is the amount of energy that heats the iunterior building mass. It should probably be renamed to something like `total_solar_aperature`. It is the effective area that is allowing sunlight to enter the building. Qs gets split between heating the air and heating the mass in the ETP model. As of Jan 30 2025 this clarification has not been implemented in hvac_new_agent.py.

## "copy_attributes_from()" as a higher level class method?
"copy_attributes_from()" allows the copying of attributes from one object to another, typically on object creation. This is useful if you need to simulate the behavior of a system but don't want to change the original model's state and instead just want to make a dummy copy of the object to play around with. Trevor has implemented this in the HVACDSOTAssetState class but it feels like it might be useful in other classes like HVACDSOTEnvironmentModel so that hypothetical future environmental states can be used without messing up the current environmental state.

Answer: no need for this method, Python has a `copy()` method that works on object.

## Use a units package for all our variables?
There are [many units packages out there in Python-land](https://kdavies4.github.io/natu/seealso.html) that allow a unit to be associated with a variable. Many of them allow fancy things like unit conversions which I generally don't think is necessary but one, [quantify](https://quantiphy.readthedocs.io/en/stable/user.html) is more about documentation (though it does support some features in those other packages). [From the QuantiPhy documentation](https://github.com/KenKundert/quantiphy/blob/5e48f7f77b60846183fc5cd78462ffb3130b828e/README.rst):

> In contrast, QuantiPhy treats units basically as documentation. They are simply strings that are attached to quantities largely so they can be presented to the user when the values are printed. As such, QuantiPhy is a light-weight package that demands little from the user. It is used when inputting and outputting values, and then only when it provides value. As a result, it provides a simplicity in use that cannot be matched by the other packages.

What do we think about adopting this? I know from working with in the HVAC code that units would be helpful in making the code more self-documenting. It would take some work to retroactively go through and update the code but it might be worth it.

## Standardized agent (per market structure)?
Could we achieve simplification of the agent code such that it is largely or entirely standardized and all the device-specific functionality is wrapped up in device specific classes? It feels like this might be possible where we have logic that is used in `__init__()` to determine what type of device the agent is managing and any device-specific parameters. At least for DSOT (DA and RT energy markets), there doesn't seem to be a lot of agent-specific code. Same patterns of operation, just different device models.


## Data Classes?
Trevor has heard Mitch express a preference in the past for any complex data structure being turned into a data class as a form of specifying it and providing documentation about its contents. These classes may or may not have any methods. For example, if you have a complex JSON that is a dictionary of dictionaries of lists, should we make a class to hold that data and give it a name so that when you see an instance of it, you know because of the datatype how it is structured. Good idea?

## Interaction between bidding strategy (optimization) and asset model
The DSOT agent has the bidding strategy (optimization problem formulation) and the asset model in the same code ("hvac_agent.py") Ideally we would like these two in separate classes but I suspect that is going to make the interaction between the two more challenging. That is, the optimization formulation needs to know the exact name of all the variables and their definitions to allow for the creation of the problem formulation. This makes me (Trevor) think that the bidding strategies will always be intimately tied to the asset model they are using. Maybe there's a way to create a clean abstraction but it's not jumping out to me right now.

## All objects having references to all other objects?
The way to code is structured now, there are lots of objects that have references to many other objects. Though not strictly necessary, it is convenient to have the ability to get the current state of another objects attributes as a sub-attribute of your own, _a la_ `my_attribute = self.other_obj.attribute_I_need`. This creates a level of interconnected-ness that makes it possible for other classes to change the state of my class more or less directly (`self.other_obj.attribute = new_value`). The original HVAC DSOT agent code avoided this by having everything in one class; this made comprehending more difficult but made a single monolithic object. By breaking into sub-classes, comprehension of the code goes up but there is largely the same degree of connectedness between the parts (unavoidable?) and more hassle in figuring out which class owns the attribute or method I need.

## Generally make references for attributes of referenced objects?
To save space inside object code, should we generally make specific local class attributes that reference referenced object attributeds instead of accessing them as-needed in the object code? For example `hvac_on_tmp = self.asset_state.hvac_on` pulls in the attribute as-needed from the referenced `asset_state` object. This makes for longer lines throughout the code BUT makes it very clear where the value is coming from. Alternatively, we could do `self.hvac_on = self.asset_state.hvac_on` in the `__init__()` and then the line of code becomes `hvac_on_tmp = self.hvac_on`. See fuller example in `HVACDSOTRTBidding.estimate_hvac_runtime()`
