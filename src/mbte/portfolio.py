'''
Portfolio
'''

from typing import Any
from mbte.events import Event, OrderNew, Signal


class Portfolio(object):
    def __init__(self, positiions):
        self._positions = dict(positiions)

    def on_event(self, event: Event, signal: Signal) -> Any[OrderNew]:
        pass