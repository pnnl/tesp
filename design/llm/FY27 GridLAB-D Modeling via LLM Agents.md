# FY27 GridLAB-D Modeling via LLM Agents

**Author: Trevor Hardy**

**Last Updated: 13 Nov 2026**

## Motivation
In FY27 TESP is working to develop techniques to leverage the growing utility provided by LLMs and their corresponding agents. One specific action we're pursuing is the the use of natural language to define the composition of GridLAB-D models. 

Typically, the process of taking a GridLAB-D model designed for running powerflows and modifying it into one with a richer load composition needed for exploring customer behavior and DER integration has involved a configuration file that read by a Python script that uses the parameters to convert the existing static loads. This is a multi-step process where the size of loads is converted into a specific number of house objects and then any supporting DERs are added. All of the parameter values for the new objects are defined based on statistical distributions built up from datasets like RECS and through the use of heuristics based on engineering judgment or common practice. This is often referred to as "populating a model".

For those that are trying to populate a specific model in a specific way, using the existing script and configuration file or creating new versions of each are likely to be necessary. That is, defining the manner in which specific parameters should be defined via prose to an LLM agent is likely to be less effective and take more time than just writing the code to do so (or having an LLM agent write the code).

Alternatively, we see great potential in supporting users that are less concerned with all the details and parameter choices but can concisely describe the model they need built. For example, 

>"I need a model for a residential feeder from Texas in 2020. Instead of using the actual distribution of rooftop solar seen at the time, I want all houses 2000 square feet or less to have a rooftop solar installation. Also, convert all the gas water heaters to electric water heaters." 

We desire that such prompts would produce a viable GridLAB-D model that conforms to the characteristics the user specified; this document is a proposal for how to achieve that end.

## Strategy and Implementation

### Skills
In my limited understanding of how skills are expected to work, it appears that part of the purpose of a skill is to increase the likelihood that the LLM agent is able to correctly understand the task being asked and execute the necessary functions to achieve the task. The more clearly that path is defined and constrained, the more likely success will be had. Skills are a way to define specific activities. Furthermore, if skills can call existing code to achieve some portion of the defined activity, all the better. 

For this work, I propose that we draft skills for the atomic operations necessary to populate the GridLAB-D model and a more general skill that defines the process by which the atomic skills are called. Examples of atomic skills would define activities like loading the GridLAB-D model from file, removing ZIP loads, adding billing meters and house objects, etc. These skills would leverage the new GridLAB-D API and would likely have a Python script implementation that would guarantee correct operation for each of the atomic operations.

### GridLAB-D Server
There is a problem with atomic skills that call local Python scripts, though: lack of preservation of state in memory. As best as I can tell, there is no way to allow an LLM agent to execute a script and hold that state in memory while it figures out the next activity it needs to perform. Because of this, if these atomic actions need to be performed using local scripts, the state of the model will have to be preserved in file on disk and each atomic operation will need to first load the model, perform the necessary model edits, and then write it out to disk. This is inefficient and will dramatically increase the time of performing model modification.

To provide the continuity of the model state in memory, I propose that we develop a GridLAB-D server. This server would be able to accept commands that would perform the operations of the GridLAB-D API and persist the state of the model between modification steps performed by the LLM agent. For example, the GridLAB-D server would support operations like load model, delete object, add object, write model, etc. The atomic skills could then reference these specific operations (endpoints?) on the server needed to perform the skills.

It's not clear to me write now as I right this but there may be a way this same server could be used to execute the GridLAB-D model. For example, what if the prompt from the user was

>"I need a model for a residential feeder from Texas in 2020. Instead of using the actual distribution of rooftop solar seen at the time, I want all houses 2000 square feet or less to have a rooftop solar installation. Also, convert all the gas water heaters to electric water heaters. Simulate year of 2020 using historical weather data and record the total net load of the all customers, saving it as a Parquet file."

The GridLAB-D API supports running the model and some of the other functionality could be achieved by other datasets or services we already have or could have; post-processing isn't covered in this document but also seems ripe for developing LLM agent support.

### GridLAB-D MCP Server?
I understand the purpose of MCP server for about ten minutes after I watch a video on MCP servers and then it evaporates out of my brain. It's been more than ten minutes since I watched an MCP video so I don't see a reason to develop an MCP server to support model population. Assuming we were to implement a GridLAB-D server, we would be one step closer to an MCP server making sense. 

## Example
Let's start out with our first prompt:

>"I need a model for a residential feeder from Texas in 2020. Instead of using the actual distribution of rooftop solar seen at the time, I want all houses 2000 square feet or less to have a rooftop solar installation. Also, convert all the gas water heaters to electric water heaters." 

After getting this prompt, the LLM agent would recognize that this was a GridLAB-D modeling task and through our careful skill definition, would know to invoke the top-level GridLAB-D modeling skill. That skill would do the following using other more atomic skills we've written
- Identify the most appropriate existing unpopulated model to use
- Load in the parameter distributions for objects from 2020 and build them if necessary
- Load the unpopulated model via the GridLAB-D server
- Identify the points at which house objects will be added and how many house objects to add at each point
- Add billing meters for each customer
- Add house meters and objects for each billing meter (house parameters defined by parameter distributions)


To support the more complex logic around adding solar to houses with 2000 square feet or less, I'm guessing we would need skills like
- Getting objects (lists of objects with their parameters defined)
- Adding solar (using size of house as a guide as to how much to add)

These skills can also define what information should be requested from users (via the LLM agent) if a necessary input has not been provided. Defining "necessary" will likely take some iteration as the goal of this activity is to allow ambiguous descriptions as in the prompt above to be sufficient to produce a working model. And all parties involved will need to accept that such a model may not be what the user actually wants but it is a valid interpretation of what the user asked for. Presumably if such details were of concern to the user, such details would have been provided in the prompt.