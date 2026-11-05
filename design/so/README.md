# System Operator

**Author: Trevor Hardy**

**Last Updated: 4 Nov 2026**

In FY27, the TESP team will develop basic system operator classes along with reference "stub" implementations that show some of the basic functionalities. In this context, "system operators" are the entities that manage the power system on behalf of the asset owners. The transmission system operators (ISOs) are the most readily identified examples but DSOs also exist in some parts of the world and can be modeled as well. 

The TESP team will implement a generic system operator class based on PySO, a transmission system model developed at PNNL and used by other PNNL projects. From this generic class, specific "stub" instances of the TSO and DSO will be implemented. "stub" refers to the system operator models performing a small set of the full functionality that would be expected in larger studies. The expectation is that the stub versions implemented here will be useful as both examples of how a system operator can be modeled but also as stand-ins for a more fully-featured portion of the modeled system. Making this substitution will allow users to more quickly iterate as they design and implement the full power system model being simulated.