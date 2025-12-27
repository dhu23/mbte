from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    timestamp: datetime
    symbol: str


################# Market Events ##################

@dataclass(frozen=True)
class MarketOpenEvent(Event):
    price: float
    volume: float


@dataclass(frozen=True)
class MarketCloseEvent(Event):
    price: float
    volume: float


###################### Signal ######################

@dataclass(frozen=True)
class SignalEvent(Event):
    value: float


##################### Execution ######################

@dataclass(frozen=True)
class PortfolioConstruction(Event):
    qty: int


@dataclass(frozen=True)
class PortfolioLiquidation(Event):
    pass


@dataclass(frozen=True)
class OrderEvent(Event):
    price: float | None
    qty: int


@dataclass(frozen=True)
class FillEvent(Event):
    last_price: float
    last_qty: int


############## Internal Scheduling ###################

@dataclass(frozen=True)
class InternalSchedulingEvent(Event):
    '''
    This is used as an internal scheduling event base class
    '''
    pass