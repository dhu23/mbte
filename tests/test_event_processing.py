import random
from datetime import datetime
from mbte.clock import SimulationClock
from mbte.event_processing import EventProcessor, EventSequencer, EventStore, MbtePriorityQueue
from mbte.events import Event, MarketCloseEvent, MarketOpenEvent, PortfolioConstruction, PortfolioLiquidation

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
        assert pq.peek() == (1, "value 1")

        pq.add(0, "value 0")
        assert pq.peek() == (0, "value 0")

        pq.add(2, "value 2")
        assert pq.peek() == (0, "value 0")
        
        assert (0, "value 0") == self._assert_pop(pq)
        assert (1, "value 1") == self._assert_pop(pq)
        assert (2, "value 2") == self._assert_pop(pq)
        

    def test_priority_queue_random(self):
        for _ in range(5):
            self._test_priority_queue_random(100)

        
    def _test_priority_queue_random(self, total: int):
        nums = list(range(total))
        random.shuffle(nums)

        pq = self._get_pq()

        current_min = None
        for n in nums:
            current_min = n if current_min is None else min(n, current_min)
            pq.add(n, f'value {n}')

        for i in range(total):
            assert (i, f'value {i}') == self._assert_pop(pq)
        
        assert pq.peek() is None


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


class MockEventProcessor(EventProcessor):
    def __init__(self):
        super().__init__()
        self._events: list[Event] = []

    def process(self, event: Event):
        self._events.append(event)

    def get_processed_events(self) -> list[Event]:
        return self._events


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

    EXPECTED_EXECUTION_SEQUENCE: list[Event] = [
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

    def _get_sim_clock(self):
        return SimulationClock(self.INITIAL_TIME)

    def _get_event_processor(self):
        return MockEventProcessor()

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
    
    def _get_standard_setup(self) -> tuple[
        SimulationClock, MockEventProcessor, EventSequencer
    ]:
        sim_clock = self._get_sim_clock()
        event_processor = self._get_event_processor()
        sequencer = EventSequencer(
            sim_clock=sim_clock,
            event_stores=[
                self._get_market_data_store(),
                self._get_portfolio_event_store(),
            ],
            event_processor=event_processor,
        )

        return (sim_clock, event_processor, sequencer)


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
            assert sequencer.run_once()
            assert self.EXPECTED_EXECUTION_SEQUENCE[:i+1] == event_processor.get_processed_events()

            print(f'clock={sim_clock.now()}, event time={self.EXPECTED_EXECUTION_SEQUENCE[i]}')
            assert sim_clock.now() == self.EXPECTED_EXECUTION_SEQUENCE[i].timestamp
            print(f'finished running for {i}')

        # no more events in the queue
        assert not sequencer.run_once()

    def test_merging_event_store_streams(self):
        sim_clock, event_processor, sequencer = self._get_standard_setup()

        # total 8 events to run through based on standard setup
        sequencer.run()

        assert sim_clock.now() == self.EXPECTED_EXECUTION_SEQUENCE[-1].timestamp
        assert event_processor.get_processed_events() == self.EXPECTED_EXECUTION_SEQUENCE