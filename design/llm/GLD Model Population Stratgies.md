# GLD Model Population Strategies

**Author: Trevor Hardy**
**Last Updated: 10 Nov 2026**

## Introduction 

As we're trying to figure out how to populate a GridLAB-D model as part of our ambition to use LLM's to instantiate models, I've been mentally finding myself running in circles to define how the process might work. To help get my head straight and serve as a starting point for discussion with the larger team, here's how my thoughts are starting to be more organized.

## Approach 1 - We don't need no stinkin' LLM!
We could write APIs that handle all of the existing use cases that we need for populating a GLD model. These would be APIs like

- `add_residential_solar(houses: Union(float, list))` - Takes a percentage of houses to be assigned solar or a list of houses to add solar to
- `convert_zip_to_houses(avg_house_load: float)` - Converts all ZIP loads on secondaries to house objects based on the size of the ZIP load and the specified average house load. Generally more than one house will be created in the location of the ZIP.

We already have APIs similar to these or can make these kinds of APIs easily using a coding agent. These APIs would be a supplemental library that we would design to be used in conjunction with the new GridLAB-D API. We document the APIs, provide some examples, and leave it up to the user to be able to do what we want to do. Potentially, we could have a standard population script that takes an input JSON and makes all the necessary calls to the APIs; I think this is similar to how things are now with DSO+T and PAVER.

The use of LLMs would come in making that input JSON, maybe? We have an existing process that buildings up the GridALB-D default distribution values for many parameters based on RECS and the input config JSON would override those values when necessary.

Required from user:
- Input config JSON 

Required from TESP:
- APIs to execute individual component populations using the GLD API
- Standard population script that calls component APIs using parameters provided in input config JSON



## Approach 2 - MCP
MCPs are designed to focus the attention of LLMs by providing interaction points to software that are specifically formulated to make it clear what the MCP call is intended to do and what the expected response will be. This is similar to an API in general but sometimes APIs return larger quantities of data that are harder for LLMs to understand.

We could build the APIs as defined in Approach #1 and provide an interface to them via an MCP. This would allow the LLM to make the necessary calls for the model population operations without having to build a larger block of code than is necessary. The LLM would be able to execute the population actions through the MCP which call the the GridLAB-D APIs we've already defined. 

This requires the development of the MCP to support the calls to GridLAB-D but opens the door for more expressive or varied approaches to populating a feeder. For example, there is likely to be flexibility that is difficult or impossible to directly encode into a generic population script BUT could be easily achieved through interaction with an LLM that is empowered through an MCP to modify a GridLAB-D model.

MCPs are designed to be model agnostic and thus their use would provide a level of generality that is likely desirable.


Inputs required from user:
- Input config information fed to LLM; could be same input config JSON file as in Approach #1 

Required from TESP:
- APIs to execute individual component populations using the GLD API
- MCP to properly expose APIs

## Approach 3 - Skills
Rather than relying on users to be able to prompt an LLM appropriately to achieve the population process correctly, skills could be drafted that guide the LLM through the population process. When the user provides information on how to populate the GridLAB-D model, the LLM can refer to skills that help it correctly execute the population process. The skills may be effectively acting as a more flexible and plain language programming script. The skill would still define the process of populating and likely reference TESP APIs or MCP calls but would do so in a way that allows the LLM to correctly form the necessary inputs to the API/MCP more flexibly rather than in a way that defined rigidly by a Python script. For example, the population skill could allow users to tell the LLM that all houses under a certain size should never be randomly chosen to have rooftop solar. Via API/MCP, the LLM could figure out which houses would be candidates for being randomly assigned rooftop solar on its own. A traditional approach to programming would require the development of a bespoke population script to achieve this functionality. 

The benefit of defining these skills is an increased liklihood that the LLM will successfully and correctly execute the GridLAB-D model population activity in a way 

Inputs required from user:
- Input config information fed to LLM; could be same input config JSON file as in Approach #1 

Required from TESP:
- APIs to execute individual component populations using the GLD API
- (optional) MCP to properly expose APIs


## Not Mutually Exclusive
In case its not clear, these three approaches are not mutually exclusive and there is reason to believe that the best forward is one that utilizes at least some components from each. It seems likely that defining good, low-level APIs that allow for the manipulation of GridLAB-D models in various, generic ways would be helpful, whether being used by humans or LLMs to implement specific functionality. Similarly, these APIs would have the usual inline documentation to make the functionality of the API clearer.

It is possible that the API calls are simple and clean enough that the value of a MCP is limited. My understanding of MCPs is growing and it is not clear to me what the criteria would be to determine if we would expect and MCP to add value or not. An MCP does have increased complexity in that it likely would involve running another persistent service in the CST stack.

Skills seem likely to be beneficial to make it super-clear to an LLM how to handle specific user requests. Given that these are natural language descriptions, as I have been drafting skills I have found it helpful in developing my own thinking around how certain functionality should be achieved. Describing the processes in a general but clear way refines my own thinking of how the specific functionality should be achieved.