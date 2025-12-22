'''
EventStore that owns the generation and sequencing of events 
that drive back-testing computation. 

Such events are external events imposed on the system, including 
clock/time advancing, market data events for example. Generated 
order execution or signals are not part of the store's responsibility.
We can track somewhere there but they are not replayed into the system.

'''

from abc import ABC, abstractmethod 
from mbte.event.event import Event

class EventStore(ABC):
    '''
    A subclass of EventStore should own the logic of generating clock/market
    data events and be responsible of the right sequencing. It should be fully
    aware of the time/clock implementation for the strategy it targets. 
    That is, a day strategy event store doesn't need to know wall clock time, 
    and an intraday strategy would need to be more time aware. 
    '''

    @abstractmethod
    def has_event(self) -> bool:
        '''
        indicates if the event stream is finished
        
        :param self: Description
        '''
        pass

    @abstractmethod
    def next_event(self) -> Event:
        '''
        Docstring for next_event
        
        :param self: Description
        '''
        pass

    @abstractmethod
    def pause(self):
        '''
        Docstring for pause
        
        :param self: Description
        '''
        pass


