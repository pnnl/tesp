# Copyright (C) 2021-2022 Battelle Memorial Institute
# file: schedule_client.py

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
