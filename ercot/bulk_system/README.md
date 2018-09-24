- Each of the 200 nodes (“buses”) in '200NodesData.json' provides the following information: 
	"bus":  Indicates bus ID or number
	"busType":  Indicates bus type.  A bus can be one of three types:  Gen (only generation), Load (only load), or Hybrid (both generation and load)
	"coordinates":  Indicates geographical location of a bus by providing latitude and longitude information in degrees. The latitude is preceded by a minus sign ( – ) if it is south of the equator (a positive number implies north), and the longitude is preceded by a minus sign if it is west of the prime meridian (a positive number implies east) 
	"weightdict":  Indicates generation capacity (MW) by fuel types for a Gen bus, load (MW) for a Load bus, or both attributes for a Hybrid bus.

	Example of a Bus:  {  "bus":  0,
"busType": "Hybrid",
"coordinates": [33.02, -96.85],
"weightdict": {"Load": 5267.95, "Natural Gas Internal Combustion Engine": 3.5, "Solar Photovoltaic": 2.0, "Natural Gas Steam Turbine": 126.5 }
 }

- The fuel types used in forming 200 cluster nodes are as follows:
		-	 'Onshore Wind Turbine'
		-	'Natural Gas Fired Combined Cycle'
		-	 'Conventional Steam Coal'
		-	 'Solar Photovoltaic'
		-	 'Natural Gas Steam Turbine'
		-	 'Nuclear'
		-	 'Natural Gas Internal Combustion Engine'
		-	 'Natural Gas Fired Combustion Turbine'


- The 200 Bus ERCOT Test System is not yet built for both AMES V3.1 and AMES V5.0.
