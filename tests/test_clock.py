
from datetime import datetime
from mbte.clock import SimulationClock


def test_simulation_clock():
    clock = SimulationClock(init_time=datetime(2025, 12, 24, 9, 30))
    assert clock.now() == datetime(2025, 12, 24, 9, 30)

    clock.set_time(datetime(2025, 12, 24, 10, 30))
    assert clock.now() == datetime(2025, 12, 24, 10, 30)