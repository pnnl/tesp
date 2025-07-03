# TESP Role Definitions

## Introduction
TESP is a complex collection of software which users interact with in a variety of ways; thsi document clarifies the various user types for TESP with the goal of helping users understand the expected prerequisite skill sets for performing various tasks with or in TESP. Though these are presented as discrete roles, the reality is that an individual may perform multiple roles for a given project and that these roles span the spectrum of work done on and to TESP. Conversely, though this document is written as if each role was fulfilled by a single individual, this is not the general case; it is entirely possible and sometimes likely or necessary that multiple individuals are involved in each of these roles.

## Post-Processor
The least demanding role for TESP users is one that only interacts with the data that is produced by TESP, the Post-Processors. As of this writing, there is no standardized API for writing data and thus there is no API for reading data produced by a given TESP simulation. The TESP development team sees this as a deficiency and is working to understand how such APIs should work and being planning for their implementation.

Given this, the role of Post-Processor requires that the user work with Modeler users to understand which data is being collected, how it is being written out (_e.g._ file formats, schema), and how to access it. Using this information, the Post-Processor is able to access TESP results and produce appropriate data presentations needed both for the purposes of verifying correct operation of the simulation while also calculating appropriate performance metrics to evaluate the performance of the system under study.

## Runner
TESP Runners are responsible for being able to adjust specific parameters of the model that the Modeler has exposed and appropriately instantiate one or more scenarios and execute the simulations. Furthermore, runners are expected to be able to perform the jobs of Post-processors to verify the correct operation of the simulation(s), providing feedback to or working with the Modeler to fix bugs that may be present in the analysis code.

The Runner is expected to be familiar enough with the analysis code to be able to understand the provenance of the data being written out but is not expected to be able to trouble-shoot bugs that may appear. (A good data collection API would make this work much easier as it would make it clear across model components when data is being collected.)

## Modeler
TESP Modelers are responsible for writing new simulation tools and/or incorporating existing tools to build the models required to perform the analysis as it has been defined. This will utilize the TESP APIs developed by the Core Developer. The work of the Modeler is generally extensive as the Modeler is responsible for producing a fully functional set of integrated software that is able to be executed by the Runner and whose data is used by the Post-Processor to validate the performance of the system. 

The Modeler is expected to be intimately familiar with all the code of the model and is the primary party responsible to verify the performance of the model. Becuase of this, it is likely that, in addition to developing the model, the Modeler will write test and diagnostic code that is used in the development and debugging process to ensure the model is preforming as designed.

## Core Developer
The most fundamental role is that of Core Developer, the individual responsible for creating and maintaining the TESP APIs that are used by all the other roles. The Core Developer is also responsible for maintaining the integrations of any simulation tools that have been welcomed into the TESP fold as blessed. These tools are expected to be generally useful enough that they are able to be used across multiple analysis and whose operation is well understood and validated. 