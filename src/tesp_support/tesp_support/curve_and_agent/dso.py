# ============================================================================
# FILE: dso.py
# PURPOSE: Minimal DSO stub. No retail market: it aggregates device-agent
#          bids into one demand curve for the TSO, then hands the TSO's
#          cleared price back to the agents. Reuses MarketOperator for the
#          aggregation and per-agent evaluation.
#          Run directly for a demo:  python -m ...curve_and_agent.dso
# ============================================================================

from typing import Dict

from .data_types import BidCurve, BidPoint, ClearingResult, MarketTimingParams
from .enums_and_constants import MarketType
from .market_operator import DSOInflexibleLoadBid, MarketOperator
from .market_state_machine import RT_TIMING, MarketStateMachine
from .tso import TSO


class DSO:
    """Collects agent bids while 'bidding', forwards the aggregate to the TSO at 'clearing'."""

    def __init__(self, dso_id: str, tso: TSO, timing=RT_TIMING):
        self.dso_id = dso_id
        self.tso = tso
        self.inflexible_kw = 0.0  # set from a forecast each cycle
        self.machine = MarketStateMachine(timing)
        self.machine.on_enter("bidding", self.collect_bids)
        self.machine.on_enter("clearing", self.submit_to_tso)
        self._new_book()

    def _new_book(self) -> None:
        self.mo = MarketOperator(MarketType.RT_ENERGY, MarketTimingParams())

    def submit_agent_bid(self, agent_id: str, bid: BidCurve) -> None:
        self.mo.submit_agent_bid(agent_id, bid)

    # --- state callbacks ---
    def collect_bids(self, cycle_start: float) -> None:
        self._new_book()

    def submit_to_tso(self, cycle_start: float) -> None:
        end = cycle_start + self.machine.timing.interval
        self.mo.submit_dso_inflexible_bid(
            self.dso_id, DSOInflexibleLoadBid(self.dso_id, self.inflexible_kw, (cycle_start, end))
        )
        self.tso.submit_demand(self.dso_id, BidCurve(self.mo.aggregate_demand()))

    def receive_price(self, result: ClearingResult) -> Dict[str, ClearingResult]:
        """Evaluate each agent's bid at the TSO price; returns per-agent results."""
        return {a: self.mo.get_agent_clearing(a, result.cleared_price) for a in self.mo._agent_bids}

    def step(self, t: float) -> None:
        self.machine.advance(t)


if __name__ == "__main__":
    from .data_types import BidPoint
    from .market_operator import SupplyCurve

    tso = TSO()
    tso.submit_supply(SupplyCurve([BidPoint(0.02, 20), BidPoint(0.10, 120), BidPoint(0.20, 200)]))
    dsos = {"dso1": DSO("dso1", tso), "dso2": DSO("dso2", tso)}
    dsos["dso1"].inflexible_kw, dsos["dso2"].inflexible_kw = 40.0, 20.0

    for t in range(0, 601, 60):
        for dso in dsos.values():
            dso.step(t)  # DSOs act before the TSO so their bids arrive in time
            if dso.machine.state == "bidding":
                dso.submit_agent_bid(f"{dso.dso_id}_hvac", BidCurve([BidPoint(0.20, 30), BidPoint(0.05, 60)]))
                dso.submit_agent_bid(f"{dso.dso_id}_wh", BidCurve([BidPoint(0.20, 10), BidPoint(0.05, 25)]))
        tso.step(t)
        if tso.machine.state == "clearing" and t % 300 == 240:
            r = tso.last_result
            print(f"t={t:4d} price={r.cleared_price:.3f} total={r.cleared_quantity:.1f} kW")
            for dso in dsos.values():
                per_agent = dso.receive_price(r)
                print("   ", dso.dso_id, {a: round(c.cleared_quantity, 1) for a, c in per_agent.items()})
