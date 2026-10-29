# ============================================================================
# FILE: example_rt_market.py
# PURPOSE: End-to-end example. Dummy agents -> DSOs -> TSO -> price back down.
#          Agents only send demand curves; supply is a fixed stack at the TSO.
#          Run:  python example_rt_market.py
# ============================================================================

import math

from tesp_support.curve_and_agent.data_types import BidCurve, BidPoint, ClearingResult
from tesp_support.curve_and_agent.dso import DSO
from tesp_support.curve_and_agent.market_operator import SupplyCurve
from tesp_support.curve_and_agent.tso import TSO

INTERVAL = 300.0  # 5-minute real-time market
DAY = 24 * 3600.0


class DummyAgent:
    """Sends a demand curve that follows a daily load shape and shrinks as price rises."""

    def __init__(self, agent_id: str, base_kw: float):
        self.agent_id = agent_id
        self.base_kw = base_kw
        self.setpoint_kw = 0.0

    def make_bid(self, t: float) -> BidCurve:
        shape = 1.0 + 0.4 * math.sin(2 * math.pi * (t / DAY - 0.3))  # peaks in the evening
        q = self.base_kw * shape
        # Highest price first: consume 70% at $0.20/kWh, 130% at $0.05/kWh.
        return BidCurve([BidPoint(0.20, 0.7 * q), BidPoint(0.05, 1.3 * q)])

    def receive_price(self, result: ClearingResult) -> None:
        self.setpoint_kw = result.cleared_quantity  # would command the device here


def main() -> None:
    tso = TSO()
    # Generators (not agents yet): upward-sloping stack, $/kWh vs kW.
    tso.submit_supply(SupplyCurve([BidPoint(0.02, 100), BidPoint(0.08, 250), BidPoint(0.25, 400)]))

    dsos = {}
    agents = {}  # dso_id -> its dummy agents
    for i, inflexible in enumerate([40.0, 25.0], start=1):
        dso = DSO(f"dso{i}", tso)
        dso.inflexible_kw = inflexible
        agents[dso.dso_id] = [DummyAgent(f"dso{i}_a{j}", base_kw=30.0 + 10 * j) for j in range(3)]
        dsos[dso.dso_id] = dso

    hourly = []
    for k in range(int(DAY / INTERVAL)):
        t0 = k * INTERVAL

        # 1) Start of cycle: everyone enters 'bidding'; agents send demand curves to their DSO.
        for dso in dsos.values():
            dso.step(t0)
            for agent in agents[dso.dso_id]:
                dso.submit_agent_bid(agent.agent_id, agent.make_bid(t0))
        tso.step(t0)

        # 2) Clearing time: DSOs forward aggregates first, then the TSO clears.
        t1 = t0 + 240.0
        for dso in dsos.values():
            dso.step(t1)
        tso.step(t1)

        # 3) Publish: DSOs turn the TSO price into per-agent results for the agents.
        for dso in dsos.values():
            for agent in agents[dso.dso_id]:
                agent.receive_price(dso.receive_price(tso.last_result)[agent.agent_id])
        hourly.append((tso.last_result.cleared_price, tso.last_result.cleared_quantity))

    print("hour  price($/kWh)  demand(kW)")
    for h in range(24):
        block = hourly[h * 12:(h + 1) * 12]
        print(f"{h:4d}  {sum(p for p, _ in block) / 12:11.3f}  {sum(q for _, q in block) / 12:10.1f}")


if __name__ == "__main__":
    main()
