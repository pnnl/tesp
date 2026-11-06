# ============================================================================
# FILE: pyso_tso.py
# PURPOSE: TSO stub that clears the real-time energy market with PySO
#          (https://github.com/pnnl/pyso) instead of curve intersection.
#
#          Same interface as tso.TSO (submit_demand / submit_supply / step /
#          last_result / published), so dso.DSO works against it unchanged.
#
#          Pieces:
#            CurveDataProvider  pyso DataProvider: bid book -> single-bus Egret model
#            CurveMarket        pyso BasicMarket: bidding -> clearing state machine
#            PySOTSO            glue: owns the book, EnergyMarket and CurveMarket
#
#          Run directly for a demo:  python -m ...curve_and_agent.pyso_tso
# ============================================================================

import os
from typing import Dict, List, Optional

import pandas as pd
from egret.data.model_data import ModelData
from pyso.engine import DataProvider, EnergyMarket
from pyso.marketmodels.market import BasicMarket

from .data_types import BidCurve, BidPoint, ClearingResult, MarketTimingParams
from .enums_and_constants import MarketType
from .market_operator import DSOInflexibleLoadBid, MarketOperator, SupplyCurve
from .market_state_machine import RT_TIMING, MarketTiming

BUS = "bus"
SUPPLY_PREFIX = "supply_"
CURTAIL_PREFIX = "curtail_"
_EPS = 1e-9


def _block_cost(width: float, price: float) -> dict:
    return {"data_type": "cost_curve", "cost_curve_type": "piecewise", "values": [(0.0, 0.0), (width, width * price)]}


def _free_generator(width: float, price: float, n: int) -> dict:
    """A single-block, always-available Egret thermal unit (no commitment cost, no ramp limits)."""
    return {
        "generator_type": "thermal",
        "bus": BUS,
        "in_service": True,
        "p_min": 0.0,
        "p_max": width,
        "p_cost": _block_cost(width, price),
        "ramp_up_60min": 1e6,
        "ramp_down_60min": 1e6,
        "startup_capacity": width,
        "shutdown_capacity": width,
        "min_up_time": 0,
        "min_down_time": 0,
        "initial_status": 1,
        "initial_p_output": 0.0,
        "startup_cost": [(0, 0.0)],
        "shutdown_cost": 0.0,
        "fuel": "none",
        "unit_type": "OTHER",
    }


class CurveDataProvider(DataProvider):
    """Translates the current bid book into a single-bus Egret model.

    Units: Egret works in MW and $/h, TESP curves in kW and $/kWh. Cost is
    price * quantity either way, so kW are passed through as "MW" and $/kWh
    as "$/MWh"; the numbers are consistent and LMPs come back in $/kWh.

    Translation:
      * SupplyCurve (price, cumulative qty) -> one generator per step, offering
        the step's width at the step's price.
      * Aggregate demand (price descending, qty) -> fixed load equal to the
        quantity at the lowest price, plus one "curtailment" generator per
        segment offering that segment's width at its mid-price. A segment is
        curtailed when the LMP exceeds what the demand is willing to pay.
        The flat part above the highest bid price is inelastic.
    """

    def __init__(self) -> None:
        self.supply: SupplyCurve = SupplyCurve()
        self.demand: List[BidPoint] = []

    def get_model(self, daterange: pd.DatetimeIndex) -> ModelData:
        n = len(daterange)
        gens: Dict[str, dict] = {}

        prev_q = 0.0
        for i, pt in enumerate(sorted(self.supply.points, key=lambda p: p.price)):
            width = pt.quantity - prev_q
            prev_q = max(prev_q, pt.quantity)
            if width > _EPS:
                gens[f"{SUPPLY_PREFIX}{i}"] = _free_generator(width, pt.price, n)

        demand = sorted(self.demand, key=lambda p: -p.price)  # price descending
        total_load = demand[-1].quantity if demand else 0.0
        for i, (hi, lo) in enumerate(zip(demand, demand[1:])):
            width = lo.quantity - hi.quantity
            if width > _EPS:
                gens[f"{CURTAIL_PREFIX}{i}"] = _free_generator(width, 0.5 * (hi.price + lo.price), n)

        max_price = max([p.price for p in self.supply.points] + [p.price for p in demand] + [1.0])
        data = {
            "system": {
                "time_keys": [str(t) for t in daterange],
                "time_period_length_minutes": 5,  # overwritten by EnergyMarket
                "baseMVA": 1.0,
                "reference_bus": BUS,
                "reference_bus_angle": 0.0,
                "load_mismatch_cost": 100.0 * max_price,  # unserved energy costs more than any bid
                "reserve_requirement": {"data_type": "time_series", "values": [0.0] * n},
            },
            "elements": {
                "bus": {BUS: {}},
                "load": {BUS: {"bus": BUS, "in_service": True, "p_load": {"data_type": "time_series", "values": [total_load] * n}}},
                "generator": gens,
            },
        }
        return ModelData(data)


class CurveMarket(BasicMarket):
    """PySO market whose bidding/clearing callbacks delegate to a PySOTSO."""

    def __init__(self, tso: "PySOTSO", **kwargs):
        self.tso = tso
        super().__init__(**kwargs)

    def collect_bids(self, event):
        self.tso._open_bidding()

    def clear_market(self, event):
        self.tso._solve(self.current_time)
        self.market_results = self.em.mdl_sol

    def publish_results(self, event):
        pass  # results are already available on the TSO as soon as clearing finishes


def _to_pyso_timing(timing: MarketTiming) -> dict:
    """Convert the shared TESP MarketTiming into the dict PySO's MarketTiming takes."""
    return {
        "market_interval": timing.interval,
        "time_unit": "second",
        "timing": [{"name": n, "start_time": s} for n, s in timing.states],
    }


def default_pyso_config(solver: Optional[str] = None) -> dict:
    return {
        "time": {"window": 1, "lookahead": 0, "min_freq": 5},
        "simulation": {"price_model": "lmp"},
        "solve_arguments": {
            "solver": solver or os.environ.get("PSST_SOLVER", "cbc"),
            "slack": "TRANSMISSION_LIMITS",
            "kwargs": {"solver_tee": False},
        },
        "logging": {"level": "WARNING", "print_config": False},
    }


class PySOTSO:
    """TSO whose clearing is an Egret unit-commitment solve run through PySO.

    Args:
        timing: Shared market timing (seconds). Must contain 'bidding' and 'clearing'.
        start: Wall-clock time that simulation t=0 maps to.
        config: Overrides merged into pyso's EnergyMarket configuration.
    """

    def __init__(
        self,
        timing: MarketTiming = RT_TIMING,
        start: str = "2025-01-01 00:00:00",
        end: str = "2026-01-01 00:00:00",
        config: Optional[dict] = None,
    ):
        self.start = pd.Timestamp(start)
        self.provider = CurveDataProvider()
        cfg = default_pyso_config()
        for section, vals in (config or {}).items():
            cfg[section] = {**cfg.get(section, {}), **vals}
        cfg["time"]["min_freq"] = max(1, round(timing.interval / 60))
        self.energy_market = EnergyMarket(self.provider, config=cfg)
        self.market = CurveMarket(
            tso=self,
            market_name="rt_energy",
            market_timing=_to_pyso_timing(timing),
            start_time=self.start,
            end_time=end,
            market=self.energy_market,
        )
        self.timing = timing
        self.supply = SupplyCurve()
        self.last_result = ClearingResult()
        self.published: Dict[str, ClearingResult] = {}
        self._open_bidding()

    # --- bid submission (called by DSOs / generator agents while 'bidding') ---
    def submit_demand(self, dso_id: str, curve: BidCurve) -> None:
        self.mo.submit_agent_bid(dso_id, curve)

    def submit_supply(self, curve: SupplyCurve) -> None:
        self.supply = curve

    def submit_inflexible(self, bid_id: str, kw: float, window: tuple) -> None:
        self.mo.submit_dso_inflexible_bid(bid_id, DSOInflexibleLoadBid(bid_id, kw, window))

    @property
    def state(self) -> str:
        return self.market.current_state

    # --- called back from CurveMarket ---
    def _open_bidding(self) -> None:
        # MarketOperator is used only as the bid book / per-agent evaluator here.
        self.mo = MarketOperator(MarketType.RT_ENERGY, MarketTimingParams())

    def _solve(self, now: pd.Timestamp) -> None:
        self.provider.supply = self.supply
        self.provider.demand = self.mo.aggregate_demand() if self.mo._agent_bids or self.mo._dso_bids else []
        em = self.energy_market
        em.get_model(now)  # -> CurveDataProvider.get_model
        # Initial conditions are deliberately not carried over: every unit is a
        # free single block, and the unit set changes from cycle to cycle.
        em.solve_model()
        sol = em.mdl_sol
        price = float(sol.data["elements"]["bus"][BUS]["lmp"]["values"][0])
        gens = sol.data["elements"]["generator"]
        served = sum(float(g["pg"]["values"][0]) for n, g in gens.items() if n.startswith(SUPPLY_PREFIX))
        self.last_result = ClearingResult(
            cleared_price=price,
            cleared_quantity=served,
            aggregate_demand=served,
            aggregate_supply=served,
            timestamp=(now - self.start).total_seconds(),
        )
        # Per-agent results are available immediately (as with tso.TSO), not on
        # PySO's exit-from-clearing hook, so DSOs can read them during 'clearing'.
        self.published = {a: self.mo.get_agent_clearing(a, price) for a in self.mo._agent_bids}

    def step(self, t: float) -> None:
        self.market.current_time = self.start + pd.Timedelta(seconds=t)


if __name__ == "__main__":
    from .tso import TSO

    supply = SupplyCurve([BidPoint(0.02, 20), BidPoint(0.10, 120), BidPoint(0.20, 200)])
    pyso_tso, ref = PySOTSO(), TSO()
    for t in range(0, 601, 60):
        for tso in (pyso_tso, ref):
            tso.step(t)
            if tso.machine.state == "bidding" if tso is ref else tso.state == "bidding":
                tso.submit_demand("dso1", BidCurve([BidPoint(0.20, 50), BidPoint(0.05, 100)]))
                tso.submit_demand("dso2", BidCurve([BidPoint(0.20, 30), BidPoint(0.05, 80)]))
                tso.submit_supply(supply)
        r, q = pyso_tso.last_result, ref.last_result
        print(f"t={t:4d} {pyso_tso.state:9s} pyso: price={r.cleared_price:.3f} qty={r.cleared_quantity:6.1f} | curve: price={q.cleared_price:.3f} qty={q.cleared_quantity:6.1f}")
