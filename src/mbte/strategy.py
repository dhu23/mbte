'''
Strategy abstract-base class
'''

from abc import ABC, abstractmethod
from dataclasses import dataclass
from mbte.events import Event, Signal



class Strategy(ABC):
    '''
    The role of a strategy is to process external events and produces a
    trading signal that can be actioned by the portfolio
    '''
    @abstractmethod
    def on_event(self, event: Event) -> Signal | None:
        pass