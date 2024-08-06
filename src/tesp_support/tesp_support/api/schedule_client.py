# Copyright (C) 2021-2023 Battelle Memorial Institute
# file: schedule_client.py
"""Client class used by entities to access schedule server

The schedule server was implemented to reduce the memory footprint of large
co-simulations with many entities reading in identical data files; see
file docstring of "schedule_server.py" for further details. This class is 
intended to be instantiated in every software entity that needs to access the
data provided by the schedule server.
"""


from multiprocessing.managers import BaseManager
# import psutil  # 3rd party module for process info (not strictly required)


# Grab the shared proxy class.  All methods in that class will be available here
class DataClient(object):
    def __init__(self, port):
        # assert self._checkForProcess('DataServer.py'), 'Must have DataServer running'

        class myManager(BaseManager):
            pass

        myManager.register('DataProxy')
        self.mgr = myManager(address=('localhost', port), authkey=b'DataProxy01')
        self.mgr.connect()
        self.proxy = self.mgr.DataProxy()

    # Verify the server is running (not required)
    @staticmethod
    def _checkForProcess(name):
        for proc in psutil.process_iter():
            if proc.name() == name:
                return True
        return False
