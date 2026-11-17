# Copyright (C) 2026 Battelle Memorial Institute
# See LICENSE file at https://github.com/pnnl/tesp
"""Tests for pyso_tso.py: TSO stub cleared by PySO/Egret.

Hand-calculated case (kW, $/kWh):
    supply steps: 20 kW @ 0.02, 100 kW @ 0.10, 80 kW @ 0.20
    demand: inelastic 40 kW below nothing else -> flat 40 kW at any price
"""

import pytest

pytest.importorskip("pyso")
pytest.importorskip("egret")

from tesp_support.curve_and_agent.data_types import BidCurve, BidPoint
from tesp_support.tesp_support.curve_and_agent.markets.market_operator import SupplyCurve
from tesp_support.curve_and_agent.pyso_dso import PySODSO
from tesp_support.curve_and_agent.pyso_tso import PySOTSO

SUPPLY = SupplyCurve([BidPoint(0.02, 20), BidPoint(0.10, 120), BidPoint(0.20, 200)])


def _run_cycle(tso, bids, t0=0):
    tso.step(t0)
    assert tso.state == "bidding"
    tso.submit_supply(SUPPLY)
    for who, curve in bids.items():
        tso.submit_demand(who, curve)
    tso.step(t0 + 240)
    assert tso.state == "clearing"


class TestGetModel:
    def test_curves_become_generators_and_loads(self):
        import pandas as pd

        tso = PySOTSO()
        tso.submit_supply(SUPPLY)
        tso.submit_demand("d", BidCurve([BidPoint(0.2, 50), BidPoint(0.05, 100)]))
        md = tso.get_model(pd.date_range("2025-01-01", periods=1, freq="5min"))
        gens = md.data["elements"]["generator"]
        assert sorted(g["p_max"] for n, g in gens.items() if n.startswith("supply_")) == [20, 80, 100]
        assert [g["p_max"] for n, g in gens.items() if "curtail" in n] == [50]
        assert md.data["elements"]["load"]["d"]["p_load"]["values"] == [100]


class TestPySOTSO:
    def test_inelastic_demand_clears_at_marginal_supply(self):
        tso = PySOTSO()
        _run_cycle(tso, {"d": BidCurve([BidPoint(0.20, 60), BidPoint(0.19, 60)])})
        # 60 kW > the 20 kW @ 0.02 step, so the 0.10 step is marginal.
        assert tso.last_result.cleared_price == pytest.approx(0.10, abs=1e-6)
        assert tso.last_result.cleared_quantity == pytest.approx(60.0, abs=1e-6)

    def test_elastic_demand_curtails_above_willingness_to_pay(self):
        tso = PySOTSO()
        # Demand falls from 200 kW to 100 kW between 0.05 and 0.20 (mid-price 0.125);
        # supply at <= 0.10 is only 120 kW, so the demand segment sets the price.
        _run_cycle(tso, {"d": BidCurve([BidPoint(0.20, 100), BidPoint(0.05, 200)])})
        assert tso.last_result.cleared_price == pytest.approx(0.125, abs=1e-6)
        assert tso.last_result.cleared_quantity == pytest.approx(120.0, abs=1e-6)

    def test_bid_book_resets_each_cycle(self):
        tso = PySOTSO()
        _run_cycle(tso, {"d": BidCurve([BidPoint(0.20, 100), BidPoint(0.19, 100)])})
        _run_cycle(tso, {"e": BidCurve([BidPoint(0.20, 30), BidPoint(0.19, 30)])}, t0=300)
        assert tso.last_result.cleared_quantity == pytest.approx(30.0, abs=1e-6)

    def test_existing_dso_works_against_pyso_tso(self):
        tso = PySOTSO()
        tso.submit_supply(SUPPLY)
        dso = PySODSO("dso1", tso)
        dso.inflexible_kw = 40.0
        dso.step(0)
        tso.step(0)
        dso.submit_agent_bid("hvac", BidCurve([BidPoint(0.20, 30), BidPoint(0.05, 60)]))
        dso.step(240)  # DSO forwards its aggregate before the TSO clears
        tso.step(240)
        assert tso.last_result.cleared_quantity > 0
        per_agent = dso.receive_price(tso.last_result)
        assert "hvac" in per_agent
