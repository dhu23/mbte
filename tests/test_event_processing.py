from datetime import datetime
from anvil.clock import SimulationClock
from anvil.event_processing import (
    EventProcessor, 
    EventScheduler, 
    EventSequencer, 
    EventStore, 
    MbtePriorityQueue,
)
from anvil.events import (
    Event, 
    InternalSchedulingEvent, 
    MarketCloseEvent, 
    MarketOpenEvent, 
    PortfolioConstruction, 
    PortfolioLiquidation,
)

class TestMbtePriorityQueue(object):
    def _get_pq(self) -> MbtePriorityQueue[int, str]:
        return MbtePriorityQueue[int, str]()

    def _assert_pop(self, pq: MbtePriorityQueue[int, str]):
        root = pq.peek() 
        if root is None:
            assert pq.pop() is None
        else:
            assert pq.pop() == root
        return root

    def test_priority_queue(self):
        pq = self._get_pq()

        # nothing to pop when it is empty
        assert pq.peek() is None
        assert pq.pop() is None

        # add node
        pq.add(1, "value 1")
        assert pq.peek() == (1, 1, "value 1")

        pq.add(0, "value 0")
        assert pq.peek() == (0, 2, "value 0")

        pq.add(2, "value 2")
        assert pq.peek() == (0, 2, "value 0")

        pq.add(2, "value 22")
        assert pq.peek() == (0, 2, "value 0")

        pq.add(0, "value 00")
        assert pq.peek() == (0, 2, "value 0")
        
        assert (0, 2, "value 0") == self._assert_pop(pq)
        assert (0, 5, "value 00") == self._assert_pop(pq)
        assert (1, 1, "value 1") == self._assert_pop(pq)
        assert (2, 3, "value 2") == self._assert_pop(pq)
        assert (2, 4, "value 22") == self._assert_pop(pq)


class MockEventStore(EventStore):
    def __init__(self, name: str, events: list[Event]):
        super().__init__()
        self._name = name
        self._events = list(events)
        self._index = 0

    def name(self) -> str:
        return self._name

    def peek(self) -> Event | None:
        if self._index >= len(self._events):
            return None
        else:
            return self._events[self._index]

    def pop(self):
        item = self.peek()
        if item is not None:
            self._index += 1
        return item
    
    def reset(self):
        self._index = 0

    def get_index(self):
        return self._index


class MockStandardEventProcessor(EventProcessor):
    def __init__(self):
        super().__init__()
        self._events: list[Event] = []

    def process(self, event: Event):
        self._events.append(event)

    def get_processed_events(self) -> list[Event]:
        return self._events


class MockInternalSchedulingEvent1(InternalSchedulingEvent):
    pass


class MockInternalSchedulingEvent2(InternalSchedulingEvent):
    pass


class MockMixedEventProcessor(MockStandardEventProcessor):
    '''
    MockMixedEventProcessor creates a sophisticated scenario with scheduling
    '''
    def __init__(self, clock: SimulationClock, scheduler: EventScheduler):
        super().__init__()
        self._clock = clock
        self._scheduler = scheduler
        self._first_scheduled: tuple[InternalSchedulingEvent, int] | None = None
        self._second_scheduled: tuple[InternalSchedulingEvent, int] | None = None


    def process(self, event: Event):
        super().process(event)

        # will receive PortfolioConstruction event then MarketOpenEvent in order
        # on PortfolioConstructionEvent, schedule InternalSchedulingEvent at 11:30AM
        # on MarketOpenEvent, schedule another InternalSchedulingEvent at 11:00AM
        # on InternalSchedulingEvent at 11:00AM, cancel the 11:30AM one
        now = self._clock.now()
        if isinstance(event, PortfolioConstruction):
            scheduled_event = MockInternalSchedulingEvent1(
                timestamp=datetime(now.year, now.month, now.day, 11, 30),
                symbol=event.symbol,
            )
            scheduled_id = self._scheduler.schedule(scheduled_event)
            self._first_scheduled = (scheduled_event, scheduled_id)
        elif isinstance(event, MarketOpenEvent):
            scheduled_event = MockInternalSchedulingEvent2(
                timestamp=datetime(now.year, now.month, now.day, 11, 0),
                symbol=event.symbol,
            )
            scheduled_id = self._scheduler.schedule(scheduled_event)
            self._second_scheduled = (scheduled_event, scheduled_id)
        elif isinstance(event, InternalSchedulingEvent):
            assert self._first_scheduled is not None
            assert self._second_scheduled is not None
            
            assert event == self._second_scheduled[0]
            # cancel first scheduled
            self._scheduler.cancel(self._first_scheduled[1])
            

class TestEventSequencer(object):
    MARKET_DATA_EVENTS: list[Event] = [
        MarketOpenEvent(
            timestamp=datetime(2025, 12, 24, 9, 30),
            symbol='SPY',
            price=409,
            volume=100000,
        ),
        MarketCloseEvent(
            timestamp=datetime(2025, 12, 24, 13, 0),
            symbol='SPY',
            price=410,
            volume=150000,
        ),
        MarketOpenEvent(
            timestamp=datetime(2025, 12, 26, 9, 30),
            symbol='SPY',
            price=411,
            volume=90000,
        ),
        MarketCloseEvent(
            timestamp=datetime(2025, 12, 26, 16, 0),
            symbol='SPY',
            price=412,
            volume=80000,
        )
    ]

    PORTFOLIO_EVENT_DATA: list[Event] = [
        PortfolioConstruction(
            timestamp=datetime(2025, 12, 24, 9, 29),
            symbol='SPY',
            qty=250,
        ),
        PortfolioLiquidation(
            timestamp=datetime(2025, 12, 24, 13, 1),
            symbol='SPY',
        ),
        PortfolioConstruction(
            timestamp=datetime(2025, 12, 26, 9, 29),
            symbol='SPY',
            qty=350,
        ),
        PortfolioLiquidation(
            timestamp=datetime(2025, 12, 26, 16, 1),
            symbol='SPY',
        ),
    ]

    EXPECTED_EXECUTION_SEQUENCE_NO_INTERNAL: list[Event] = [
        # first day 2025.12.24
        PORTFOLIO_EVENT_DATA[0],
        MARKET_DATA_EVENTS[0],
        MARKET_DATA_EVENTS[1],
        PORTFOLIO_EVENT_DATA[1],
        # second day 2025.12.26
        PORTFOLIO_EVENT_DATA[2],
        MARKET_DATA_EVENTS[2],
        MARKET_DATA_EVENTS[3],
        PORTFOLIO_EVENT_DATA[3],
    ]

    INITIAL_TIME = datetime(2025, 12, 24, 8, 30)
    MARKET_DATA_STORE_NAME = 'market-data'
    PORTFOLIO_STORE_NAME = 'portfolio-data'

    INTERNAL_SCHEDULING_EVENTS: list[InternalSchedulingEvent] = [
        MockInternalSchedulingEvent1(
            timestamp=datetime(2025, 12, 24, 11, 30),
            symbol='SPY',
        ),
        # later scheduling an event for an earlier time
        MockInternalSchedulingEvent2(
            timestamp=datetime(2025, 12, 24, 11, 0),
            symbol='SPY',
        ),
        MockInternalSchedulingEvent1(
            timestamp=datetime(2025, 12, 26, 11, 30),
            symbol='SPY',
        ),
        # later scheduling an event for an earlier time
        MockInternalSchedulingEvent2(
            timestamp=datetime(2025, 12, 26, 11, 0),
            symbol='SPY',
        ),
    ]

    EXPECTED_EXECUTION_SEQUENCE_WITH_INTERNAL: list[Event] = [
        # first day 2025.12.24
        PORTFOLIO_EVENT_DATA[0],
        MARKET_DATA_EVENTS[0],
        INTERNAL_SCHEDULING_EVENTS[1], # the surviving scheduling
        MARKET_DATA_EVENTS[1],
        PORTFOLIO_EVENT_DATA[1],
        # second day 2025.12.26
        PORTFOLIO_EVENT_DATA[2],
        MARKET_DATA_EVENTS[2],
        INTERNAL_SCHEDULING_EVENTS[3], # the surviving scheduling
        MARKET_DATA_EVENTS[3],
        PORTFOLIO_EVENT_DATA[3],
    ]

    def _get_market_data_store(self):
        return MockEventStore(
            self.MARKET_DATA_STORE_NAME, 
            self.MARKET_DATA_EVENTS
        )
    
    def _get_portfolio_event_store(self):
        return MockEventStore(
            self.PORTFOLIO_STORE_NAME, 
            self.PORTFOLIO_EVENT_DATA
        )
    
    def _get_standard_setup(self, with_init_stores: bool=True) -> tuple[
        SimulationClock, MockStandardEventProcessor, EventSequencer
    ]:
        sim_clock = SimulationClock(self.INITIAL_TIME)
    
        event_stores: list[EventStore] = []
        if with_init_stores:
            event_stores.append(self._get_market_data_store())
            event_stores.append(self._get_portfolio_event_store())

        sequencer = EventSequencer(
            sim_clock=sim_clock,
            event_stores=event_stores,
        )

        event_processor = MockStandardEventProcessor()
        sequencer.set_processor(event_processor)

        return (sim_clock, event_processor, sequencer)

    def _get_mixed_setup(self) -> tuple[
        SimulationClock, MockMixedEventProcessor, EventSequencer
    ]:
        sim_clock = SimulationClock(self.INITIAL_TIME)

        sequncer = EventSequencer(
            sim_clock=sim_clock,
            event_stores=[
                self._get_market_data_store(),
                self._get_portfolio_event_store(),
            ],
        )

        event_processor = MockMixedEventProcessor(sim_clock, sequncer)
        sequncer.set_processor(event_processor)

        return (sim_clock, event_processor, sequncer)

    def test_mock_event_store(self):
        market_data_store = self._get_market_data_store()
        assert market_data_store.name() == self.MARKET_DATA_STORE_NAME
        
        # peek and pop the 1st event 
        assert market_data_store.peek() == self.MARKET_DATA_EVENTS[0]
        assert market_data_store.pop() == self.MARKET_DATA_EVENTS[0]
        
        # pop the 2nd, 3rd and 4th event
        assert market_data_store.pop() == self.MARKET_DATA_EVENTS[1]
        assert market_data_store.pop() == self.MARKET_DATA_EVENTS[2]
        assert market_data_store.pop() == self.MARKET_DATA_EVENTS[3]

        # nothing left
        assert market_data_store.peek() is None
        assert market_data_store.pop() is None

    def test_merging_event_store_streams_by_step(self):
        sim_clock, event_processor, sequencer = self._get_standard_setup()

        # total 8 events to run through based on standard setup
        for i in range(8):
            print(f'running for {i}')
            assert sequencer.advance()
            assert self.EXPECTED_EXECUTION_SEQUENCE_NO_INTERNAL[:i+1] == event_processor.get_processed_events()

            print(f'clock={sim_clock.now()}, event time={self.EXPECTED_EXECUTION_SEQUENCE_NO_INTERNAL[i]}')
            assert sim_clock.now() == self.EXPECTED_EXECUTION_SEQUENCE_NO_INTERNAL[i].timestamp
            print(f'finished running for {i}')

        # no more events in the queue
        assert not sequencer.advance()

    def test_merging_event_store_streams(self):
        sim_clock, event_processor, sequencer = self._get_standard_setup()

        # total 8 events to run through based on standard setup
        sequencer.run()

        assert sim_clock.now() == self.EXPECTED_EXECUTION_SEQUENCE_NO_INTERNAL[-1].timestamp
        assert event_processor.get_processed_events() == self.EXPECTED_EXECUTION_SEQUENCE_NO_INTERNAL

    def test_scheduling(self):
        sim_clock, event_processor, sequencer = self._get_standard_setup(with_init_stores=False)
        
        # schedule later events
        sequencer.schedule(self.INTERNAL_SCHEDULING_EVENTS[2])
        sequencer.schedule(self.INTERNAL_SCHEDULING_EVENTS[3])

        # schedule earlier events
        sequencer.schedule(self.INTERNAL_SCHEDULING_EVENTS[0])
        sequencer.schedule(self.INTERNAL_SCHEDULING_EVENTS[1])
        
        expected_scheduling_events = [
            self.INTERNAL_SCHEDULING_EVENTS[1],
            self.INTERNAL_SCHEDULING_EVENTS[0],
            self.INTERNAL_SCHEDULING_EVENTS[3],
            self.INTERNAL_SCHEDULING_EVENTS[2],
        ]

        for i in range(4):
            sequencer.advance()
            assert sim_clock.now() == event_processor.get_processed_events()[-1].timestamp
            assert expected_scheduling_events[:i+1] == event_processor.get_processed_events()

    def test_canceling(self):
        sim_clock, event_processor, sequencer = self._get_standard_setup(with_init_stores=False)
        
        # schedule later events
        id2 = sequencer.schedule(self.INTERNAL_SCHEDULING_EVENTS[2]) # runs 4th
        sequencer.schedule(self.INTERNAL_SCHEDULING_EVENTS[3]) # runs 3rd

        # schedule earlier events
        id0 = sequencer.schedule(self.INTERNAL_SCHEDULING_EVENTS[0]) # runs 2nd
        id1 = sequencer.schedule(self.INTERNAL_SCHEDULING_EVENTS[1]) # runs 1st
        
        sequencer.advance()
        assert len(event_processor.get_processed_events()) == 1
        assert sim_clock.now() == event_processor.get_processed_events()[-1].timestamp

        assert not sequencer.cancel(id1) # the event is executed, nothing to cancel

        assert sequencer.cancel(id0) # should cancel event 
        sequencer.advance() # nothing happens as id0 event is canceled
        assert len(event_processor.get_processed_events()) == 1
        assert sim_clock.now() == event_processor.get_processed_events()[-1].timestamp

        sequencer.advance() # this should hit the next event
        assert len(event_processor.get_processed_events()) == 2
        assert sim_clock.now() == event_processor.get_processed_events()[-1].timestamp

        assert sequencer.cancel(id2)
        sequencer.advance() # nothing happens as id2 event is canceled
        assert len(event_processor.get_processed_events()) == 2
        assert sim_clock.now() == event_processor.get_processed_events()[-1].timestamp

        # assert only two events are processed
        expected_scheduling_events = [
            self.INTERNAL_SCHEDULING_EVENTS[1],
            self.INTERNAL_SCHEDULING_EVENTS[3],
        ]
        assert expected_scheduling_events == event_processor.get_processed_events()

    def test_mixed_scenario(self):
        _, event_processor, sequencer = self._get_mixed_setup()
        
        sequencer.run()
        assert event_processor.get_processed_events() == self.EXPECTED_EXECUTION_SEQUENCE_WITH_INTERNAL

