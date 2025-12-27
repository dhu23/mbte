'''
Clock for simulation owns the current time of the system.
'''
from datetime import datetime

class SimulationClock(object):
    def __init__(self, init_time: datetime):
        self._time = init_time

    def set_time(self, new_time: datetime):
        if new_time > self._time:
            self._time = new_time

    def now(self):
        return self._time
    
