# ============================================================================
# FILE: pyso_tso.py
# PURPOSE: TSO stub that clears the real-time energy market with PySO
#          (https://github.com/pnnl/pyso) instead of curve intersection.
#          PySOTSO is a pyso BasicMarket (bidding -> clearing state machine)
#          and also the DataProvider that turns the bid book into a
#          single-bus Egret model for pyso's EnergyMarket to solve.
#          Run directly for a demo:  python -m ...curve_and_agent.pyso_tso
# ============================================================================
import itertools
import os

import pandas as pd
from egret.data.model_data import ModelData
from pyso.engine import DataProvider, EnergyMarket
from pyso.marketmodels.market import BasicMarket, MarketTiming

from .data_types import BidCurve, BidPoint, ClearingResult
from .markets.market_operator import SupplyCurve

# Real-time energy market in PySO's native timing form: bid for 4 min, then clear.
RT_TIMING = {
    "market_interval": 300,
    "time_unit": "second",
    "timing": [{"name": "bidding", "start_time": 0}, {"name": "clearing", "start_time": 240}],
}

BUS = "bus"


class PySOTSO(BasicMarket, DataProvider):
    """Clears submitted supply and demand curves with an Egret solve per interval.

    Egret works in MW and $/h; curves are kW and $/kWh. Cost is price * quantity
    either way, so kW pass through as "MW" and prices come back in $/kWh.

    Curve -> Egret translation (single bus):
      * Supply (price, cumulative kW): one generator per step, offering the
        step's width at the step's price.
      * Each DSO's demand (price descending): a fixed load equal to its largest
        quantity, plus one "curtailment" generator per segment offering the
        segment's width at its mid-price. A segment is curtailed when the LMP
        exceeds what that demand is willing to pay; above the highest bid price
        the demand is inelastic.
    """

    def __init__(self, timing=RT_TIMING, start_time="2025-01-01", end_time="2026-01-01", solver=None):
        timing = timing if isinstance(timing, MarketTiming) else MarketTiming(**timing)
        self.supply = SupplyCurve()
        self.bids: dict[str, BidCurve] = {}
        self.last_result = ClearingResult()
        em = EnergyMarket(
            self,
            config={
                "time": {"window": 1, "lookahead": 0, "min_freq": max(1, round(timing.market_interval.total_seconds() / 60))},
                # One relaxed LP solve gives dispatch and LMPs; no separate pricing solve.
                "simulation": {"price_model": None},
                "solve_arguments": {"solver": solver or os.environ.get("PSST_SOLVER", "cbc"), "kwargs": {"relaxed": True, "solver_tee": False}},
                "logging": {"level": "WARNING", "print_config": False},
            },
        )
        super().__init__("rt_energy", timing, start_time, end_time, em)

    # --- bid submission (DSOs / generator agents, while 'bidding') ---
    def submit_demand(self, dso_id: str, curve: BidCurve) -> None:
        self.bids[dso_id] = curve

    def submit_supply(self, curve: SupplyCurve) -> None:
        self.supply = curve

    def step(self, t: float) -> None:
        """Advance to t seconds after start_time; enters any states reached."""
        self.current_time = self.start_time + pd.Timedelta(seconds=t)

    # --- pyso market callbacks ---
    def collect_bids(self, event) -> None:
        self.bids = {}  # fresh bid book each cycle

    def clear_market(self, event) -> None:
        self.em.get_model(self.current_time)  # -> self.get_model()
        self.em.solve_model()
        sol = self.em.mdl_sol
        gens = sol.data["elements"]["generator"]
        self.last_result = ClearingResult(
            cleared_price=float(sol.data["elements"]["bus"][BUS]["lmp"]["values"][0]),
            cleared_quantity=sum(float(g["pg"]["values"][0]) for n, g in gens.items() if n.startswith("supply_")),
        )

    # --- pyso DataProvider ---
    def get_model(self, daterange: pd.DatetimeIndex) -> ModelData:
        n = len(daterange)
        gens, loads, prices = {}, {}, [1.0]

        def offer(name, width, price):
            if width > 0:
                prices.append(price)
                gens[name] = {
                    "generator_type": "thermal", "bus": BUS, "in_service": True,
                    "p_min": 0.0, "p_max": width,
                    "p_cost": {"data_type": "cost_curve", "cost_curve_type": "piecewise", "values": [(0.0, 0.0), (width, width * price)]},
                    # Required by Egret's unit commitment; set so that nothing binds.
                    "ramp_up_60min": 1e6, "ramp_down_60min": 1e6, "min_up_time": 0, "min_down_time": 0,
                    "initial_status": 1, "initial_p_output": 0.0,
                }

        prev = 0.0
        for i, pt in enumerate(sorted(self.supply.points, key=lambda p: p.price)):
            offer(f"supply_{i}", pt.quantity - prev, pt.price)
            prev = pt.quantity
        for dso, curve in self.bids.items():
            pts = sorted(curve.points, key=lambda p: -p.price)
            if pts:
                loads[dso] = {"bus": BUS, "in_service": True, "p_load": {"data_type": "time_series", "values": [pts[-1].quantity] * n}}
            for i, (hi, lo) in enumerate(itertools.pairwise(pts, pts[1:])):
                offer(f"{dso}:curtail_{i}", lo.quantity - hi.quantity, 0.5 * (hi.price + lo.price))

        return ModelData({
            "system": {
                "time_keys": [str(t) for t in daterange], "baseMVA": 1.0,
                "reference_bus": BUS, "reference_bus_angle": 0.0,
                "load_mismatch_cost": 100.0 * max(prices),  # unserved energy costs more than any bid
            },
            "elements": {"bus": {BUS: {}}, "load": loads, "generator": gens},
        })


if __name__ == "__main__":
    tso = PySOTSO()
    supply = SupplyCurve([BidPoint(0.02, 20), BidPoint(0.10, 120), BidPoint(0.20, 200)])
    for t in range(0, 601, 60):
        tso.step(t)
        if tso.state == "bidding":
            tso.submit_supply(supply)
            tso.submit_demand("dso1", BidCurve([BidPoint(0.20, 50), BidPoint(0.05, 100)]))
            tso.submit_demand("dso2", BidCurve([BidPoint(0.20, 30), BidPoint(0.05, 80)]))
        r = tso.last_result
        print(f"t={t:4d} {tso.state:9s} price={r.cleared_price:.3f} qty={r.cleared_quantity:.1f}")
