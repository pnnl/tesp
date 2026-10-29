# ============================================================================
# FILE: market_state_machine.py
# PURPOSE: One shared market state-machine definition for operators (TSO/DSO)
#          and participants (agents). Mirrors PySO's MarketTiming / state
#          names (bidding -> clearing) but is dependency-free.
# ============================================================================

from typing import Callable, Dict, List, Tuple


class MarketTiming:
    """Named states and their start offsets (seconds) within one market interval.

    Args:
        interval: Length of one market cycle (s).
        states: Ordered (name, start_offset) pairs. The first must start at 0.
    """

    def __init__(self, interval: float, states: List[Tuple[str, float]]):
        starts = [s for _, s in states]
        if starts[0] != 0 or starts != sorted(starts) or starts[-1] >= interval:
            raise ValueError("states must start at 0, be ordered, and fit in interval")
        self.interval = interval
        self.states = states


# Default real-time energy market: bid for 4 min, then clear and publish.
RT_TIMING = MarketTiming(300.0, [("bidding", 0.0), ("clearing", 240.0)])


class MarketStateMachine:
    """Cycles through the timing states as time advances.

    Participants and operators register callbacks by state name with
    on_enter(). A callback receives the cycle start time.
    """

    def __init__(self, timing: MarketTiming = RT_TIMING, start_time: float = 0.0):
        self.timing = timing
        self.cycle_start = start_time
        self._index = -1  # nothing entered yet
        self._callbacks: Dict[str, List[Callable[[float], None]]] = {}

    @property
    def state(self) -> str:
        return self.timing.states[self._index][0] if self._index >= 0 else "initialization"

    def on_enter(self, state: str, callback: Callable[[float], None]) -> None:
        self._callbacks.setdefault(state, []).append(callback)

    def advance(self, t: float) -> None:
        """Enter every state whose start time has been reached by time t."""
        while True:
            nxt = (self._index + 1) % len(self.timing.states)
            cycle = self.cycle_start + (self.timing.interval if nxt == 0 and self._index >= 0 else 0)
            name, offset = self.timing.states[nxt]
            if t < cycle + offset:
                return
            self.cycle_start, self._index = cycle, nxt
            for cb in self._callbacks.get(name, []):
                cb(self.cycle_start)
