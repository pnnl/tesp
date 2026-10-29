# ============================================================================
# FILE: tso.py
# PURPOSE: Minimal TSO stub (option B). Shared MarketStateMachine drives a
#          MarketOperator that already does curve-intersection clearing.
#          Run directly for a small demo:  python -m ...curve_and_agent.tso
# ============================================================================

from typing import Dict

from .data_types import BidCurve, BidPoint, ClearingResult, MarketTimingParams
from .enums_and_constants import MarketType
from .market_operator import DSOInflexibleLoadBid, MarketOperator, SupplyCurve
from .market_state_machine import RT_TIMING, MarketStateMachine


class TSO:
    """Collects supply and demand during 'bidding', clears and publishes at 'clearing'."""

    def __init__(self, timing=RT_TIMING):
        self.machine = MarketStateMachine(timing)
        self.machine.on_enter("bidding", self.collect_bids)
        self.machine.on_enter("clearing", self.clear_market)
        self._new_operator()
        self.supply = SupplyCurve()
        self.last_result: ClearingResult = ClearingResult()
        self.published: Dict[str, ClearingResult] = {}

    def _new_operator(self) -> None:
        self.mo = MarketOperator(MarketType.RT_ENERGY, MarketTimingParams())

    # --- bid submission (called by DSOs / generator agents while 'bidding') ---
    def submit_demand(self, dso_id: str, curve: BidCurve) -> None:
        self.mo.submit_agent_bid(dso_id, curve)

    def submit_supply(self, curve: SupplyCurve) -> None:
        self.supply = curve

    # --- state callbacks ---
    def collect_bids(self, cycle_start: float) -> None:
        self._new_operator()  # fresh bid book each cycle

    def clear_market(self, cycle_start: float) -> None:
        self.mo.set_supply_curve(self.supply)
        self.last_result = self.mo.clear_market()
        self.published = self.mo.propagate_results()

    def step(self, t: float) -> None:
        self.machine.advance(t)


if __name__ == "__main__":
    tso = TSO()
    for t in range(0, 601, 60):
        tso.step(t)
        if tso.machine.state == "bidding":
            # Two DSOs bid downward-sloping demand; generators offer an upward stack.
            tso.submit_demand("dso1", BidCurve([BidPoint(0.20, 50), BidPoint(0.05, 100)]))
            tso.submit_demand("dso2", BidCurve([BidPoint(0.20, 30), BidPoint(0.05, 80)]))
            tso.submit_supply(SupplyCurve([BidPoint(0.02, 20), BidPoint(0.10, 120), BidPoint(0.20, 200)]))
            tso.mo.submit_dso_inflexible_bid("f1", DSOInflexibleLoadBid("f1", 40.0, (t, t + 300)))
        r = tso.last_result
        print(f"t={t:4d} state={tso.machine.state:9s} price={r.cleared_price:.3f} qty={r.cleared_quantity:.1f}")
