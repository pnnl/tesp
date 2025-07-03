# TESP Component Definitions

## Introduction
Though TESP is often presented as an intergrated set of tooling, there are a few general classes of components that comprise TESP.

## APIs
TESP provides a set of APIs that are used by TESP Modelers (see [TESP Role Definitions](./tesp_roles.md)) to develop the models used in a given analysis. Generally these APIs provide functionality like system model modification (see [GLMMod](./demonstrations/gld_modifier.rst)) and data collection (forthcoming).

## Models
Both abstract classes for models and generic component models. "Component" generally refers to a physical device (_e.g._ HVAC system, rooftop solar array). The abstract classes provide a starting point for implementing a component of that type (_e.g._ device agent, market), providing necessary functions and methods that need to be defined for that class. 

The component models are provided as examples that could be used by TESP users as part of a larger system. For example, in DSO+T, because of the inclusion of DERs in the day-ahead market, these DERs need an physical device model that lets them estimate the future operation of the device.

## Integrated Simulation Tools
Some simulation tools have broad enough appeal or have been used often enough that they have received extra attention from TESP and have been "integrated".

(What does integrated even mean? Am I just making this all up?)

## Documentation
To assist users in understanding how to use TESP, documentation has been written. It is helpful, we promise.

## Examples
To assist users in understanding how to use TESP, we've developed several examples that show off the capabilities of TESP. Additionally, there are a number of existing analysis that use TESP; these reside in separate repositories but can be helpful in building a new analysis.