'''
Back-testing engine that controls 
- data/event flow
- clock
- owning components in the full system
'''
from mbte.event_store import EventStore
from mbte.events import EventType
from mbte.execution import Execution
from mbte.portfolio import Portfolio
from mbte.strategy import Strategy

class Engine(object):
    def __init__(
            self, 
            event_store: EventStore, 
            strategy: Strategy, 
            portfolio: Portfolio,
            execution: Execution
    ):
        self._event_store = event_store
        self._strategy = strategy
        self._portfolio = portfolio
        self._execution = execution

    def run(self):
        while self._event_store.has_event():
            event = self._event_store.next_event()
            if event is None:
                pass
            
            # process the event to generate signal
            signal = self._strategy.on_event(event)
        
            # process trading event signal
            order = self._portfolio.on_event(event, signal)
            
            if order is None:
                pass

            # trade the order
            self._execution.send(order)
            