TESP Demonstrations and Examples
================================

To help users of TESP to better understand how the software platform has been created and integrated, a number of sample projects are included in the distribution of TESP and are divided into two categories: capability demonstrations and analysis examples. 

Capability demonstrations are sample projects that are relatively simple and intended to show off a single or very small number of features of TESP. They may be a demonstration of the use of one of the third-party tools and its integration into TESP or one of the custom agents that are provided with TESP. These demonstrations are not legitimate analysis in and of themselves and the results from them are not intended to provide any significant insight into good transactive system design principles or behaviors.

In contract, analysis examples are versions of analysis that have been performed in the past with TESP with specific analysis objectives. These examples have much more comprehensive documentation within TESP and have produced one or more publications that provide further detail. The versions of these analysis that are included in TESP are not necessarily the same as those that were originally used but they are very similar and are examples of specific transactive concepts or mechanisms. The results of the version of these examples that are distributed with TESP are not only examples of how a transactive energy study could be assembled with TESP but the results produced by running the examples will be as meaningful (though not necessarily identical) to those used to produce the original analysis conclusions and publications.

TESP Capability Demonstrations
------------------------------

.. toctree::
    :maxdepth: 2
    
    ./demonstrations/loadshed.rst
    ./demonstrations/pypower.rst
    ./demonstrations/weatherAgent.rst
    ./demonstrations/energyplys.rst
    ./demonstrations/te30.rst
    ./demonstrations/ieee8500.rst
    
TESP uses TCP/IP port 5570 for communication and requires Python 3. Simulations can start many processes, and take minutes or hours to complete. At this time, instructions are given only for the Linux package or Docker version of TESP, which is installable. See below for advice on running TESP in native Mac OS X or Windows.

Some general tips for Linux:

- invoke **python3** instead of just *python*
- we recommend 16 GB of memory
- high-performance computing (HPC) should be considered if simulating more than one substation-week
- you may have to increase the number of processes and open file handles allowed
- **lsof -i :5570** will show all processes connected to port 5570 
- use **ls -al** or **cat** or **tail** on log files or csv filesto show progress of a case solution
- **./kill5570.sh** will terminate all processes connected to port 5570; if you have to do this, make sure **lsof -i :5570** shows nothing before attempting another case
- it is recommended that you append **&** to any python plot commands, so they run in the background.




TESP Example Analysis 
---------------------

.. toctree::
    :maxdepth: 2

    
    ./examples/SGIP1_Example
    ./examples/DSOT_Study