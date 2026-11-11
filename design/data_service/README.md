# Data Service

**Author: Trevor Hardy**

**Last Updated: 4 Nov. 2026**

In FY27, the TESP team will be re-designing and implementing the data service that was created as part of DSO+T.

## Motivation

The data service designed in DSO+T was called the "weather server" and was designed to solve a particular problem: many entities in the DSO+T simulation needed a common set of data and rather than making multiple copies of the files containing the data, a data server could provide those values over the network. Through discusssion with the TENT team we learned they have implemented a generic data service and doing so for TESP seems like the best path forward.

## Requirements
The likely incomplete requirements are as follows:

1. **Data sent over HELICS** - Though we've traditionally run our TESP analysis on a single server but we want to keep our options open. HELICS is the primary method by which we've facilitated data exchange between simulation executables and the data server should not break this capability.
2. **Use HELICS values (publication and subscription)** - Using the HELICS value interface to distribute the values allows intended receipients to self-select which values they need from the data server. 
3. **HELICS publish values so they are "live" at the correct time** - Due to the architecture of HELICS and how it distributes values, it will be necessary for the data server to publish values slightly before the time they are defined in the data source. This pre-emption time should be configurable and should default to one second. Broadcasting new values early like this will ensure they are seen by all other federates on the time step they are valid.
4. **Use CoSim Toolbox to create the data server federate** - The use of CST will not only simplify the development of the server, it also supports readers for a variety of file formats and databases. This will simplify the method by which the data to be distributed by the server is accessed.
5. **Data defined in local files and network resources** - The data server should be able to read the data it needs to distribute from both a local file or a network resources such as a database or web service. In FY27, we should support the use of local files and, to the extent it is easy to do with CoSim Toolbox's Postgres database, grab the data from there as well. The use of a database is particularly attractive as it makes that data available for post-processing for anybody who can reach that server without having to pass around potentially large files containing the served data.
6. **Configuration** - The HELICS configuration effectively defines the output and metadata of the data being served. HELICS supports the definition of data type and units for each publication and other federates can query the data server federate's publication interface to learn these metadata if needed.
7. **Data format** - Regardless of the file format used (i.e. Parquet, CSV, Postgres), the data format will define a time step in ISO 8601 and the value to be broadcast. Multiple data values can be defined at each timestep such as might be seen in a table (e.g. single timestamp per row with multiple values, each in its own column). The data server is responsible for validating the input data prior to the launch of the co-simulation to ensure proper values (i.e. data types) exist for all publications. Depending on the size of the data being served, this may take some time. As a stretch goal, more sophisticated mechanisms of tracking the validation state of the inputs so that they are not unnecessarily repeated can be implemented.
8. **HELICS memory limit** - As the data server only publishes data, HELICS will grant it every requested time immediately which can lead to very large memory consumption as all the data in data source is moved from disk to memory. HELICS has recently implemented (or will implement) a maximum memory flag that should be set to limit the memory use for this federate. This will keep the data server live for more of the co-simulation.
9. **Logging** - Logging is expected to be minimal, probably only errors or warning encountered during the verification of the input data source.

## Expected Operation

As the data server is a HELICS and CST federate, it will launch alongside all the other federates. To the extent that we control the order in which the federates are launched, the data server should launch early in the process, prior to all other subscribing federates. This will allow subscribing federates to query the data server interfaces as necessarily to define their subscriptions or validate their existing subscriptions. Shorly after launch, the data server will verify that the input data specified contains data to be published during the entirety of the co-simulation; the data source may contain data beyond this time without consequence.

 Once the co-simulation begins, the data server will periodically read in the necessary data from disk (i.e. local file or database) and broadcast it out. As required by the configuration, some of these values may be read into the monitoring database. At the conclusion of the co-simulation, the federate will terminate.