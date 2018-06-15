Steps to Run SGIP1b
===================

This is a 1594-house model simulating 2 days. It may take 1-2 hours to run.  On Windows and Mac OS X, this example uses PYPOWER in the following steps:

1 - python prep_agents.py SGIP1b

2 - python glm_dict.py SGIP1b

3 - ./runSGIP1b.sh

4 - use "lsof -i :5570" or cat various files to show progress

5 - python process_pypower.py SGIP1b

6 - python process_gld.py SGIP1b

7 - python process_agents.py SGIP1b

8 - python process_eplus.py SGIP1b

On Linux, PYPOWER may be used following the same steps. An option to use MATPOWER is also available on Linux.
