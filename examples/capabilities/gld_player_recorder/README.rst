

This example demonstrates how to use GridLAB-D's player and recorder functions. GridLAB-D's player functionality allows external data to be played into a simulation and define the value of any of the parameter in most objects. Recorders do the converse and record the value of any object's parameter and writes it out to file. Further details can be found in GridLAB-D's documentation on `players <http://gridlab-d.shoutwiki.com/wiki/Player>`_ and `recorders. <http://gridlab-d.shoutwiki.com/wiki/Recorder>`_

Directories TE30 and ieee8500 provides more in-depth examples. 

To run the example:

1. ./run.sh

File Directory
--------------

- *README.rst*: this file
- *run.sh*: script that writes houses, creates a dictionary and runs GridLAB-D
- *SG_LNODE13A.player*: player file that has lmps values for a node for testing
- *testImp.glm*: GridLAB-D file that an SG_LNODE13A.player that uses the object player

Results
-------
The file lmp_value.csv is created and can be compared with SG_LNODE13A.player which was used for input.
