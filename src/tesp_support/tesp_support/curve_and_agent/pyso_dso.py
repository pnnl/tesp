# ============================================================================
# FILE: pyso_dso.py
# PURPOSE: DSO stub for the PySO-backed TSO (pyso_tso.PySOTSO); independent
#          counterpart of dso.py. A pyso BasicMarket with no EnergyMarket, so
#          it shares the TSO's state machine and timing. No retail market: it
#          aggregates device-agent bids into one demand curve for the TSO at
#          'clearing', then evaluates agent bids at the TSO's price.
#          Run directly for a demo:  python -m ...curve_and_agent.pyso_dso
# ============================================================================

import pandas as pd
from pyso.marketmodels.market import BasicMarket

from .data_types import BidCurve, BidPoint, ClearingResult, MarketTimingParams
from .enums_and_constants import MarketType
from .markets.market_operator import DSOInflexibleLoadBid, MarketOperator, SupplyCurve
from .pyso_tso import PySOTSO


def _book() -> MarketOperator:
    return MarketOperator(MarketType.RT_ENERGY, MarketTimingParams())


class PySODSO(BasicMarket):
    def __init__(self, dso_id: str, tso: PySOTSO):
        self.dso_id, self.tso = dso_id, tso
        self.inflexible_kw = 0.0  # set from a forecast each cycle
        self.mo = _book()
        super().__init__(dso_id, tso.market_timing, tso.start_time, tso.end_time, market=None)

    def submit_agent_bid(self, agent_id: str, bid: BidCurve) -> None:
        self.mo.submit_agent_bid(agent_id, bid)

    def step(self, t: float) -> None:
        self.current_time = self.start_time + pd.Timedelta(seconds=t)

    # --- pyso market callbacks ---
    def collect_bids(self, event) -> None:
        self.mo = _book()

    def clear_market(self, event) -> None:
        """For a DSO, 'clearing' is forwarding the aggregate demand to the TSO."""
        t0 = (self.current_time - self.start_time - self.market_timing["clearing"]["start_time"]).total_seconds()
        window = (t0, t0 + self.market_timing.market_interval.total_seconds())
        self.mo.submit_dso_inflexible_bid(self.dso_id, DSOInflexibleLoadBid(self.dso_id, self.inflexible_kw, window))
        self.tso.submit_demand(self.dso_id, BidCurve(self.mo.aggregate_demand()))

    def receive_price(self, result: ClearingResult) -> dict[str, ClearingResult]:
        """Per-agent results at the TSO's cleared price."""
        return {a: self.mo.get_agent_clearing(a, result.cleared_price) for a in self.mo._agent_bids}


if __name__ == "__main__":
    tso = PySOTSO()
    tso.submit_supply(SupplyCurve([BidPoint(0.02, 20), BidPoint(0.10, 120), BidPoint(0.20, 200)]))
    dsos = [PySODSO("dso1", tso), PySODSO("dso2", tso)]
    dsos[0].inflexible_kw, dsos[1].inflexible_kw = 40.0, 20.0

    for t in range(0, 601, 60):
        for dso in dsos:
            dso.step(t)  # DSOs act before the TSO so their bids arrive in time
            if dso.state == "bidding":
                dso.submit_agent_bid(f"{dso.dso_id}_hvac", BidCurve([BidPoint(0.20, 30), BidPoint(0.05, 60)]))
                dso.submit_agent_bid(f"{dso.dso_id}_wh", BidCurve([BidPoint(0.20, 10), BidPoint(0.05, 25)]))
        tso.step(t)
        if tso.state == "clearing" and t % 300 == 240:
            r = tso.last_result
            print(f"t={t:4d} price={r.cleared_price:.3f} total={r.cleared_quantity:.1f} kW")
            for dso in dsos:
                print("   ", dso.dso_id, {a: round(c.cleared_quantity, 1) for a, c in dso.receive_price(r).items()})
