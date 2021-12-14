# Player Example

This example uses the Gridlabd player and recorder functions.
Directories TE30 and ieee8500 provides more in depth examples.

To run the example:

1. ./run.sh

### File Directory

- *README.rst*; this file
- *run.sh*; script that writes houses, creates a dictionary and runs GridLAB-D
- *SG_LNODE13A.player*; player file that has lmps values for a node for testing
- *testImp.glm*; GridLAB-D file that an SG_LNODE13A.player that uses the object player

### Results
The file lmp_value.csv is created and can be compared with SG_LNODE13A.player which was used for input.
