# Python Parallel Libraries
TESP in general has a strong need for parallel execution due to the role of agents in the simulations. Generally, each device has one agent that manages it and for larger studies like DSO+T, this can result in thousands of agents to manage. Furthermore, to achieve their functionality, some of the tasks the agents must execute can be computationally expensive, such as solving an optimization problem to create a day-ahead energy bid. Therefore, there is a need to find a way to make best use of the computational resources available and generally this means providing some kind of parallelization of the tasks the agents need to perform.

Below is a preliminary investigation into the parallelization libraries in Python with, in some cases, testing to evaluate their suitability for use in TESP. Previous investigations during early DSO+T development revelead that memory requirements for each parallel task could be significant enough to limit their application to thousands of independent executables (the philosophically purest co-simulation implementation). To prevent the large memory footprint required, all agents were instantiated as objects in a single Python executable. The parallelization was implemented as appropriate manually inside this code.


## `multiprocessing`

Stealing from [the documentation](https://docs.python.org/3/library/multiprocessing.html): "multiprocessing is a package that supports spawning processes using an API similar to the threading module."

Furthermore, using the ["spawn" technique](https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods) for starting new processes (the only strategy that works on all three OSes):

"The parent process starts a fresh Python interpreter process. The child process will only inherit those resources necessary to run the process object’s run() method. In particular, unnecessary file descriptors and handles from the parent process will not be inherited. Starting a process using this method is rather slow compared to using fork or forkserver.

Available on POSIX and Windows platforms. The default on Windows and macOS."

In Jan 2024 in Python 3.13 Trevor confirmed this is the case: for every process started a new Python interpreter appeared in his Mac's "Activity Monitor" with a footprint of ~30MB. This is likely not a viable option for managing our agents.

## `joblib`

Stealing from [the documentation](https://joblib.readthedocs.io/en/stable/): "Joblib is a set of tools to provide lightweight pipelining in Python. In particular: 1)transparent disk-caching of functions and lazy re-evaluation (memoize pattern) 2) easy simple parallel computing".

This library was used in the DSO+T study to parallelize the day-ahead market bidding for each agent as it required solving an optimization problem.

In Jan 2024 in Python 3.13 Trevor ran a similar test as to what was done with the "multiprocessing" library and saw that the number of processes spawned was equal to the number of cores on his Mac. Each process had the similar ~30MB memory footprint. This library seems well-suited to the task it was used in DSO+T. In fact, with good software architecutre, this could likely be used more heavily to parallelize all of the major agent tasks. Defining an abstract class for the agents that outlines their major functions that can be called with joblib.

## `threads`

Stealing from [the documentation](https://docs.python.org/3/library/threading.html): "This module constructs higher-level threading interfaces on top of the lower level _thread module."

"CPython implementation detail: In CPython, due to the Global Interpreter Lock, only one thread can execute Python code at once (even though certain performance-oriented libraries might overcome this limitation). If you want your application to make better use of the computational resources of multi-core machines, you are advised to use multiprocessing or concurrent.futures.ProcessPoolExecutor. However, threading is still an appropriate model if you want to run multiple I/O-bound tasks simultaneously."

Given that our transactive analysis are not generally I/O-bound tasks, this probably isn't the right choice for us. Trevor didn't do any testing on it.
