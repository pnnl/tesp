# Simple LLM Interface Mapping Test
To verify that an LLM could take interface definitions that did not exactly match each other and determine which interfaces mapped to each other, the following prompt was provided. The files referenced in the prompt are included in this folder.

# Input 
>Attached are two interface definition files. These files define the inputs and outputs from two software objects that I need to connect together. I need you to determine the mapping between the inputs and outputs of these two files. The results of this mapping should be provided according to the interface definition (also attached). Please produce an output matching JSON file showing these mappings.

## Results
The LLM was able to correctly map the interfaces and identified incompatibilities that were created in the two interface files.

```json
[
  {
    "src": "setpnt",
    "dst": "thermostat setpoint"
  },
  {
    "src": "indoor air temperature",
    "dst": "temp"
  },
  {
    "src": "HVAC state",
    "dst": "running"
  },
  {
    "src": "indoor air humidity",
    "dst": "humidity"
  },
  {
    "src": "outdoor air temperature",
    "dst": "outside_temp"
  }
]
```

>The mappings follow the agent and device interface definitions hvac_agent_inte...ition.json hvac_device_int...ition.json and use the provided connection format interface_conne...plate.json. Two mappings need value conversion: outdoor air temperature is in °F, while outside_temp expects °C; and HVAC state uses values such as heating and cooling, while running expects heat, cool, or off. The device’s emergency heating state has no direct equivalent in running, so that case needs an explicit handling rule.