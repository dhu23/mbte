'''
Event Processing related implementations
'''
from datetime import datetime
from abc import ABC, abstractmethod 
from mbte.clock import SimulationClock
from mbte.events import Event, InternalSchedulingEvent
import heapq
from typing import Generic, TypeVar, NamedTuple

K = TypeVar('K')
V = TypeVar('V')

class MbtePriorityQueue(Generic[K, V]):
    '''
    A wrapper around python native heap queue. 
    A monotonic sequence number is used to break key tie.

    :var streams: Description
    :var Data: Description
    :var Data: Description
    :var scheduling: Description
    :var Implementation: Description
    '''
    def __init__(self, init_seq: int=0):
        self._seq = init_seq
        self._queue: list[tuple[K, int, V]] = []

    def add(self, key: K, value: V):
        heapq.heappush(self._queue, (key, self._seq, value))
        self._seq += 1

    def pop(self) -> tuple[K, int, V] | None:
        if self._queue:
            return heapq.heappop(self._queue)
        else:
            return None
        
    def peek(self) -> tuple[K, int, V] | None:
        if self._queue:
            return self._queue[0]
        else:
            return None


class EventStore(ABC):
    '''
    EventStore that owns the generation and sequencing of events 
    that drive back-testing computation. 

    Such events are external events imposed on the system, including 
    clock/time advancing, market data events for example. Generated 
    order execution or signals are not part of the store's responsibility.
    We can track somewhere there but they are not replayed into the system.

    A subclass of EventStore should own the logic of generating 
    data events and be responsible of the right sequencing. It should be fully
    aware of the relevant time stamping for the strategy it targets.  
    '''
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def peek(self) -> Event | None:
        '''
        Docstring for peek
        
        :param self: Description
        :return: Description
        :rtype: Event | None
        '''
        pass

    @abstractmethod
    def pop(self) -> Event | None:
        '''
        Docstring for pop
        
        :param self: Description
        :return: Description
        :rtype: Event | None
        '''
        pass


class EventProcessor(ABC):
    @abstractmethod
    def process(self, event: Event) -> None:
        pass


class EventStoreItem(NamedTuple):
    event: Event
    event_store: EventStore


class ScheduledItem(NamedTuple):
    event: Event
    schedule_id: int


class EventSequencerError(RuntimeError):
    pass


class EventScheduler(ABC):
    @abstractmethod
    def schedule(self, internal_event: InternalSchedulingEvent) -> int:
        pass

    @abstractmethod
    def cancel(self, schedule_id: int) -> bool:
        pass


class EventSequencer(EventScheduler):
    '''
    EventSequencer manages multiple EventStore objects and presents produced
    events in the system in a properly sorted way, by sequence number, 
    timestamp or anything that's comparable. 

    In addtion, EventSequencer also takes on the responsibility to manauge 
    ad-hoc scheduling events that out-of-order scneario can happen due to 
    strategy logic. 
    
    Illustration of Normal EventStore streams:
    For example, we can have two EventStore, one generates market data and
    one generates portfolio sell off event. The events are lazily proposed
    in the following sequence in a simulation run:
    Market Data: 
        MD-1: 2025-12-24 9:30AM  Market Open Price
        MD-2: 2025-12-24 1:00PM  Market Close Price
    Portfolio Event Data:
        P-1: 2025-12-24 9:35AM  Build Portfolio
        P-2: 2025-12-25 1:25PM  Liquidate Portfolio
    The EventQueue object is responsible for generate the following sequence 
        MD-1, P-1, P-2, MD-2 

    Illustration of ad-hoc scheduling:
    The strategy might want to schedule a trading event at 10:00AM after
    processing MD-1, however after P-1, it decides to add another scheduled
    event at 9:50AM. Due to the addition of the second event is out of order,
    allowing these events to go directly to participating the ordering of the
    EventSequencer internal priority queue can nicely resolve the issue without
    introducing any complexity.
    
    Implementation:
    It uses an algorithm that does a k-way merge of sorted data streams. 
    Each EventStore can lazily propose the next event to be inserted into a
    priority queue that  
    '''
    
    def __init__(
            self,
            sim_clock: SimulationClock, 
            event_stores: list[EventStore], 
    ):
        self._sim_clock = sim_clock
        self._event_stores = list(event_stores)
        self._event_processor: EventProcessor | None = None

        self._merger_queue = MbtePriorityQueue[datetime, EventStoreItem | ScheduledItem]()
        self._internal_scheduling_id: int = 1
        self._scheduled_id_set: set[int] = set()

        self._init_queue()

    def set_processor(self, event_processor: EventProcessor):
        self._event_processor = event_processor

    def schedule(self, internal_event: InternalSchedulingEvent) -> int:
        schedule_id = self._get_schedule_id()
        self._merger_queue.add(
            internal_event.timestamp,
            ScheduledItem(event=internal_event, schedule_id=schedule_id),
        )
        self._scheduled_id_set.add(schedule_id)
        return schedule_id
    
    def cancel(self, schedule_id: int) -> bool:
        return self._remove_scheduled_id(schedule_id)

    def run(self):
        if self._event_processor is None:
            return
        # keep running event by event util it is done
        while self.advance():
            pass

    def _init_queue(self):
        for event_store in self._event_stores:
            if not self._replenish_from_store(event_store):
                raise EventSequencerError(
                    f'no event in event store {event_store.name()}'
                )
            
    def _remove_scheduled_id(self, schedule_id: int) -> bool:
        if schedule_id in self._scheduled_id_set:
            self._scheduled_id_set.remove(schedule_id)
            return True
        else:
            return False

    def _replenish_from_store(self, event_store: EventStore) -> bool:
        head = event_store.peek()
        if head is None:
            return False
        
        # put the next one from the event store into the merge queue
        self._merger_queue.add(
            head.timestamp, 
            EventStoreItem(event=head, event_store=event_store)
        )
        return True

    def _get_schedule_id(self) -> int:
        ret = self._internal_scheduling_id
        self._internal_scheduling_id += 1
        return ret

    def advance(self) -> bool:
        assert self._event_processor is not None
        
        head = self._merger_queue.pop()
        if head is None:
            return False
        
        timestamp, _, item = head
        if isinstance(item, ScheduledItem):
            # if the scheduled_id is still effective, then run it
            if item.schedule_id in self._scheduled_id_set:
                self._advance_clock(timestamp)
                self._event_processor.process(item.event)
                self._remove_scheduled_id(item.schedule_id)
            return True
        else: # isinstance(item, EventStoreItem)
            # process the event (still in the queue) and remove it
            self._advance_clock(timestamp)
            self._event_processor.process(item.event)
            item.event_store.pop()

            # prepare the next event in the queue, without removing it
            self._replenish_from_store(item.event_store)
            return True

    def _advance_clock(self, timestamp: datetime) -> None:
        # advance time if it sees a newer timestamp
        if self._sim_clock.now() < timestamp:
            self._sim_clock.set_time(timestamp)