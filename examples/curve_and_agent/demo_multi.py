#!/usr/bin/env python3
"""
TESP Curve-and-Agent Demo
==========================
50 HVAC agents on a hot afternoon participate in a 5-minute
real-time energy market.  No GridLAB-D or HELICS required —
a lightweight MockConnection stands in.

The script walks through every major function in the pipeline:
  F1  Observe device state      (GridLABDInterface)
  F2  Estimate flexibility      (DeviceModel)
  F3  Generate preference curve (PreferenceCurve)
  F4  Formulate bid             (DeviceAgent)
  F5  Submit bid                (MarketCommunicationInterface)
  --  Market clearing           (MarketOperator)
  F7  Price response            (DeviceAgent)
  F8  Translate to control      (DeviceAgent + DeviceModel)
  F9  Actuate device            (CommandArbiter → GridLABDInterface)
  F12 Log performance           (DeviceAgent)
  F13 Reconcile                 (DeviceAgent)

House_1 is traced step-by-step; the other 49 run in the background
to produce a realistic aggregate demand curve and clearing price.
"""

import sys, os, random, textwrap

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "tesp_support", "curve_and_agent")
)

from enums_and_constants import (
    DeviceType,
    MarketType,
    OperatingMode,
    PenaltyStructureType,
)
from data_types import (
    BidCurve,
    BidPoint,
    ClearingResult,
    MarketTimingParams,
    PerformanceEntry,
)
from gridlabd_interface import GridLABDInterface
from data_streams import DataStreamManager
from device_agent import DeviceAgent
from market_agent import MarketCommunicationInterface
from market_operator import MarketOperator, SupplyCurve, DSOLoadEstimationEngine
from penalty_model import PenaltyModel

# ── formatting helpers ────────────────────────────────────────────────

SEP = "=" * 68


def banner(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def kv(label, value, unit=""):
    if isinstance(value, float):
        print(f"  {label:.<42s} {value:>10.4f} {unit}")
    else:
        print(f"  {label:.<42s} {str(value):>10s} {unit}")


# ── mock GridLAB-D connection ─────────────────────────────────────────


class MockConnection:
    """Return canned HVAC values; optionally vary indoor temp per house."""

    BASE = {
        "outdoor_temperature": "95.2",
        "cooling_setpoint": "72.0",
        "heating_setpoint": "68.0",
        "power_state": "COOL",
        "hvac_load": "12000",
        "mass_temperature": "74.8",
        "Ua": "500",
        "Hm": "1500",
        "Ca": "1500",
        "Cm": "5000",
        "cooling_COP": "3.5",
        "heating_COP": "3.0",
        "design_cooling_capacity": "36000",
        "design_heating_capacity": "36000",
        "solar_heatgain": "800",
        "internal_heatgain": "400",
    }

    def __init__(self, indoor_temp=76.3):
        self._data = dict(self.BASE)
        self._data["air_temperature"] = str(indoor_temp)
        self.written = {}

    def get_value(self, key):
        prop = key.split("#", 1)[-1]
        return self._data.get(prop, "")

    def set_value(self, key, value):
        self.written[key] = value


# ── mock transport (agent ↔ MO bridge) ───────────────────────────────


class MockTransport:
    def __init__(self, mo):
        self._mo = mo
        self._results = {}

    def submit(
        self,
        *,
        agent_id,
        market_type=None,
        bid=None,
        settlement=None,
        market_id=None,
        interval_id=None,
    ):
        if bid is not None:
            return self._mo.submit_agent_bid(agent_id, bid)
        return True

    def receive(self, *, agent_id, market_id):
        return self._results.get(agent_id)

    def push_results(self, results):
        self._results.update(results)


# ══════════════════════════════════════════════════════════════════════

N_HOUSES = 50


def main():
    random.seed(42)

    banner(f"TESP Demo — {N_HOUSES} HVAC Agents, RT Energy Market")

    # ── Market Operator ───────────────────────────────────────────────
    rt_timing = MarketTimingParams()  # defaults: 5-min RT
    mo = MarketOperator(
        market_type=MarketType.RT_ENERGY,
        timing_params=rt_timing,
        iteration_protocol="fixed_count",
        n_informational=0,
    )
    supply = SupplyCurve(
        points=[
            BidPoint(price=0.02, quantity=0.0),
            BidPoint(price=0.05, quantity=100.0),
            BidPoint(price=0.08, quantity=200.0),
            BidPoint(price=0.12, quantity=350.0),
            BidPoint(price=0.20, quantity=500.0),
            BidPoint(price=0.50, quantity=600.0),
            BidPoint(price=1.00, quantity=600.0),
        ]
    )
    mo.set_supply_curve(supply)

    # DSO inflexible load (non-participating customers)
    dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
    dso_bid = dso.estimate_inflexible_load(
        interval=(0.0, 300.0),
        total_load_forecast=300.0,  # 300 kW non-participating
        flexible_committed=0.0,
        btm_solar_forecast=50.0,  # some rooftop PV
        loss_factor=0.04,
    )
    mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
    print(f"  DSO inflexible bid: {dso_bid.quantity:.1f} kW")

    transport = MockTransport(mo)

    rt_penalty = PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
    )

    # ── Create 50 agents ──────────────────────────────────────────────
    agents = []
    conns = []
    comms = []
    for i in range(N_HOUSES):
        indoor = round(random.uniform(73.0, 79.0), 1)
        k = round(random.uniform(0.15, 0.85), 2)
        conn = MockConnection(indoor_temp=indoor)
        conns.append(conn)
        gld = GridLABDInterface(
            connection=conn,
            object_name=f"house_{i + 1}",
            device_type=DeviceType.HVAC_AC_ONLY,
        )
        dsm = DataStreamManager(DeviceType.HVAC_AC_ONLY)
        ag = DeviceAgent(
            agent_id=f"hvac_{i + 1}",
            device_type=DeviceType.HVAC_AC_ONLY,
            gridlabd=gld,
            customer_preference_k=k,
            data_stream_manager=dsm,
        )
        ag.initialize({})
        comm = MarketCommunicationInterface(
            transport=transport,
            agent_id=f"hvac_{i + 1}",
            market_type=MarketType.RT_ENERGY,
        )
        ag.register_market(
            market_type=MarketType.RT_ENERGY,
            timing_params=rt_timing,
            operating_mode=OperatingMode.BIDDING,
            penalty_model=rt_penalty,
            communication=comm,
        )
        agents.append(ag)
        comms.append(comm)

    print(f"  Created {N_HOUSES} agents (k ranges from 0.15 to 0.85)")

    # ══════════════════════════════════════════════════════════════════
    #  Detailed trace for HOUSE_1
    # ══════════════════════════════════════════════════════════════════

    agent = agents[0]
    conn = conns[0]

    # ── F1 ────────────────────────────────────────────────────────────
    banner("F1  Observe Device State  (house_1)")
    state = agent.observe_device_state()
    kv("Indoor air temp", state.indoor_air_temp, "°F")
    kv("Outdoor air temp", state.outdoor_air_temp, "°F")
    kv("Thermostat setpoint", state.thermostat_setpoint, "°F")
    kv("HVAC mode", state.hvac_mode)
    kv("Power draw", state.power_draw, "kW")
    kv("Cooling COP", state.cooling_COP)

    # ── F2 ────────────────────────────────────────────────────────────
    banner("F2  Estimate Flexibility  (house_1)")
    flex = agent.estimate_flexibility(state, 300.0)
    kv("Q_min", flex.Q_min, "kW")
    kv("Q_max", flex.Q_max, "kW")
    kv("Q_baseline", flex.Q_baseline, "kW")

    # ── F3 ────────────────────────────────────────────────────────────
    banner("F3  Preference Curve  (house_1)")
    pref = agent.generate_preference_curve(flex)
    print(f"  k={pref._k:.2f}  Q₀={pref._Q_0:.2f} kW  P₀=${pref._P_0:.4f}/kWh")
    print()
    print(f"  {'Price':>12s}  {'Desired Q':>10s}")
    print(f"  {'─' * 12}  {'─' * 10}")
    for p in [0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.30, 0.50]:
        q = pref.evaluate(p)
        print(f"  ${p:>10.4f}  {q:>9.3f} kW")

    # ── F4 ────────────────────────────────────────────────────────────
    banner("F4  Formulate Bid  (house_1)")
    mid = agent.spawn_market_cycle(MarketType.RT_ENERGY, clearing_time=300.0)
    mo_obj = agent._market_objects[mid]
    mo_obj.available_flexibility = flex
    mo_obj.preference_curve = pref
    bid = agent.formulate_bid(mo_obj, flex, pref)
    print(f"  {len(bid.points)} points  market_id={mid}")
    print(f"  {'Price':>12s}  {'Quantity':>10s}")
    print(f"  {'─' * 12}  {'─' * 10}")
    for pt in bid.points:
        print(f"  ${pt.price:>10.4f}  {pt.quantity:>9.3f} kW")

    # ── Submit all 50 bids ────────────────────────────────────────────
    banner("F5  Submit Bids  (all 50 agents)")
    # house_1 already formulated its bid; submit it
    comms[0].submit_bid(bid, market_id=mid, interval_id=f"int_{mid}")

    # Other 49 agents: formulate and submit
    for i in range(1, N_HOUSES):
        ag = agents[i]
        st = ag.observe_device_state()
        fl = ag.estimate_flexibility(st, 300.0)
        pr = ag.generate_preference_curve(fl)
        m = ag.spawn_market_cycle(MarketType.RT_ENERGY, clearing_time=300.0)
        mobj = ag._market_objects[m]
        mobj.available_flexibility = fl
        mobj.preference_curve = pr
        b = ag.formulate_bid(mobj, fl, pr)
        comms[i].submit_bid(b, market_id=m, interval_id=f"int_{m}")

    print(f"  {len(mo._agent_bids)} bids on file at Market Operator")
    total_flex = sum(b.points[-1].quantity for b in mo._agent_bids.values() if b.points)
    print(f"  Aggregate max flexible demand: {total_flex:.1f} kW")
    print(f"  Inflexible demand:             {dso_bid.quantity:.1f} kW")
    print(f"  Total potential demand:         {total_flex + dso_bid.quantity:.1f} kW")

    # ── Market Clearing ───────────────────────────────────────────────
    banner("Market Clearing")
    clearing = mo.clear_market()
    kv("Iteration type", clearing.iteration_type.name)
    kv("Clearing price", clearing.cleared_price, "$/kWh")
    kv("Aggregate cleared quantity", clearing.cleared_quantity, "kW")
    kv(
        "Supply at clearing price",
        supply.get_supply_at_price(clearing.cleared_price),
        "kW",
    )

    per_agent = mo.propagate_results()
    transport.push_results(per_agent)

    h1_result = per_agent.get("hvac_1", clearing)
    print()
    kv("house_1  cleared quantity", h1_result.cleared_quantity, "kW")

    # Show distribution of cleared quantities
    qtys = sorted((aid, r.cleared_quantity) for aid, r in per_agent.items())
    print(f"\n  Cleared quantities across {len(qtys)} agents:")
    print(
        f"    min={qtys[0][1]:.3f}  median={qtys[len(qtys) // 2][1]:.3f}"
        f"  max={qtys[-1][1]:.3f} kW"
    )

    # ── F7 + F8 for house_1 ───────────────────────────────────────────
    banner("F7/F8  Price Response → Control  (house_1)")
    target_q = agent.evaluate_price_response(clearing.cleared_price, pref)
    cmd = agent.translate_to_control(target_q, state)
    kv("Market price", clearing.cleared_price, "$/kWh")
    kv("Desired power", target_q, "kW")
    kv("New thermostat setpoint", cmd.setpoint, "°F")
    kv("Original setpoint", state.thermostat_setpoint, "°F")
    delta = cmd.setpoint - state.thermostat_setpoint
    direction = "raised" if delta > 0 else "lowered"
    print(f"\n  → Setpoint {direction} by {abs(delta):.1f} °F to save money")

    # ── Delivery (5 ticks) ────────────────────────────────────────────
    banner("Delivery  (house_1, 5×60 s)")
    mo_obj.cleared_price = clearing.cleared_price
    mo_obj.cleared_quantity = h1_result.cleared_quantity
    agent._command_arbiter.register_delivery(
        market_id=mid,
        market_type=str(MarketType.RT_ENERGY),
        product_type="ENERGY_BASE",
        committed_qty=h1_result.cleared_quantity,
        cleared_price=clearing.cleared_price,
        penalty_model=rt_penalty,
        interval=(0.0, 300.0),
    )
    print(
        f"  {'tick':>6s}  {'committed':>10s}  {'actual':>10s}"
        f"  {'revenue':>10s}  {'penalty':>10s}"
    )
    print(f"  {'─' * 6}  {'─' * 10}  {'─' * 10}  {'─' * 10}  {'─' * 10}")
    for tick in range(5):
        t = tick * 60.0
        frs = agent._command_arbiter.resolve_and_actuate(
            device_state=state,
            preference_curve=pref,
            amenity_weight=agent._k,
            current_time=t,
        )
        for m_id, fr in frs.items():
            mo_obj.performance_log.append(
                PerformanceEntry(
                    timestamp=t,
                    committed=fr.committed,
                    actual=fr.actual,
                    shortfall=fr.shortfall,
                    revenue=fr.revenue,
                    penalty=fr.penalty,
                    net_value=fr.net_value,
                )
            )
            print(
                f"  {t:>5.0f}s  {fr.committed:>9.3f}kW"
                f"  {fr.actual:>9.3f}kW"
                f"  ${fr.revenue:>8.4f}"
                f"  ${fr.penalty:>8.4f}"
            )

    # ── F13 Reconciliation ────────────────────────────────────────────
    banner("F13  Reconciliation  (house_1)")
    settlement = agent.reconcile(mo_obj)
    kv("Total revenue", settlement.total_revenue, "$")
    kv("Total penalty", settlement.total_penalty, "$")
    kv("Net settlement", settlement.net_settlement, "$")
    kv("Energy committed (5 ticks)", settlement.total_energy_committed, "kW")
    kv("Energy delivered (5 ticks)", settlement.total_energy_delivered, "kW")
    kv("Shortfall", settlement.total_shortfall, "kW")

    # ── GridLAB-D writes ──────────────────────────────────────────────
    banner("GridLAB-D Writes  (house_1 mock)")
    for key, val in conn.written.items():
        print(f"  {key} = {val}")

    # ── Final summary ─────────────────────────────────────────────────
    banner("Summary")
    print(
        textwrap.dedent(f"""\
      Houses in market       : {N_HOUSES}
      Outdoor temperature    : {state.outdoor_air_temp} °F
      Inflexible load (DSO)  : {dso_bid.quantity:.1f} kW
      Clearing price         : ${clearing.cleared_price:.4f}/kWh
      Aggregate cleared load : {clearing.cleared_quantity:.1f} kW

      House 1 detail:
        Indoor temp          : {state.indoor_air_temp} °F
        Preference k         : {agent._k} (0=comfort, 1=financial)
        Original setpoint    : {state.thermostat_setpoint} °F
        New setpoint         : {cmd.setpoint:.1f} °F  ({direction} {abs(delta):.1f} °F)
        Power target         : {target_q:.3f} kW
        5-minute settlement  : ${settlement.net_settlement:.4f}

      Modules exercised: GridLABDInterface, DeviceAgent, DeviceModel,
      DataStreamManager, PreferenceCurve, PenaltyModel, MarketObject,
      MarketCommunicationInterface, MarketOperator, SupplyCurve,
      DSOLoadEstimationEngine, FlexibilityLedger, CommandArbiter,
      DispatchOptimizer, DeliveryValueCalculator, PriceForecastService
    """)
    )
    print(SEP)
    print("  Demo complete.")
    print(SEP)


if __name__ == "__main__":
    main()
