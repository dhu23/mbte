from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventType(Enum):
    MARKET_OPEN = "MD-Open"
    MARKET_CLOSE = "MD-close"

    SIGNAL = "Signal"

    ORDER_NEW = "OrderNew"
    ORDER_FILL = "OrderFill"


@dataclass(frozen=True)
class Event:
    timestamp: datetime
    symbol: str
    etype: EventType


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
class Signal(Event):
    value: float


##################### Execution ######################

@dataclass(frozen=True)
class OrderNew(Event):
    price: float
    qty: int


@dataclass(frozen=True)
class OrderFill(Event):
    last_price: float
    last_qty: int