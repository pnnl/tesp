# AgentRedesign

**Author: Trevor Hardy**

**Last Updated: Jan 30, 2025**

This folder contains design ideas for agent architecture, design, and operation based on the experience gained during the DSO+T study and in preparation for a larger re-work of agents in TESP. None of this should be considered definitive but rather a reflection of the thinking at the time it was created. Later design work may or may not reference this or build upon on depending on how thinking at that time is consistent with the ideas expressed here.

The design work done here is largely an attempt to understand and restructure the DSO+T agent, using the HVAC agent as a representative example. By documenting and diagraming the operation of the DSO+T HVAC agent, the fundamental operations that it performs were made more clear and a path forward to re-architect this and other agents was also clearer. 

To demonstrate the new HVAC agent operation, a practical implementation of the newly architected HVAC agent was made and placed in the "new_hvac_dsot_demo" folder in this folder. This demonstration mostly shows the new proposed architecture in action where the functionality performed by the agent is more cleanly structured and (hopefully) easier to understand. The correctness of the agent, particularly with regard to the device model and the bid produced has not been verified. That is, this demonstration was create to show that the restructuring was viable more than to demonstrate a new working agent.