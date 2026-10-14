#/bin/bash/python3

"""
Experiments to test various parallelization libraries in Python.

In TESP, there are lots of processes we have to manage and 

"""
from pympler import asizeof
import sys
import numpy as np
from multiprocessing import Process, current_process
import time
from joblib import Parallel, delayed

class MemoryTests:

    def __init__(self):
        pass
    
    def get_module_memory_size(self, module_name: str)-> float:
        # Get the size of the module
        module_memory_size = asizeof.asizeof(sys.modules[module_name])
        module_memory_size_kB = module_memory_size / 1024
        module_memory_size_MB = module_memory_size_kB / 1024
        return module_memory_size_MB
        
    def dummy_task(self, sleep_time):
        # zeros = np.zeros(1,2)
        time.sleep(sleep_time)
    

if __name__ == '__main__':
    
    test = MemoryTests()
    num_processes = 10
    sleep_time = 10 # Long enough to look at system activity monitor to see
    # impacts of processes being spawned
    
    # Module size
    module_to_size = "numpy"
    size_MB = test.get_module_memory_size(module_to_size)
    print(f"Memory footprint of {module_to_size}: {size_MB:0.4} MB")
    time.sleep(5)
    
    # Multiprocessing test
    print("Beginning 'multiprocessing' module test")
    processes = []
    for _ in range(num_processes):
        process = Process(target=test.dummy_task, args=(sleep_time,))
        processes.append(process)
    for process in processes:
        process.start()
    for process in processes:
        process.join()
        
        
    # joblib test
    # The 'n_jobs=-1' parameter uses all available CPU cores
    print("Beginning 'joblib' module test")
    processes = []
    for _ in range(num_processes):
        task = delayed(test.dummy_task)(sleep_time)
        processes.append(task)
    dummy = Parallel(n_jobs=-1)(processes)
    

