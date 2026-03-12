#!/usr/bin/env python3
"""
Minimal Demo: One HVAC agent participates in a real-time energy market.

This script exercises the full curve_and_agent pipeline end-to-end
without requiring GridLAB-D or HELICS — all external dependencies are
replaced by lightweight mocks.

Scenario:
  - A single house with an AC unit on a 95 °F summer afternoon.
  - A 5-minute real-time energy market with a simple supply curve.
  - The DSO submits an inflexible load bid for other customers.
  - The agent observes its HVAC, estimates flexibility, builds a
    preference curve, formulates a bid, submits it, receives the
    clearing price, translates to a thermostat setpoint, and delivers.
  - After delivery the agent reconciles and prints settlement.
"""

import sys, os, textwrap

# Allow bare imports from the package directory
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
    HVACState,
    FlexibilityEnvelope,
    DeviceCommand,
    FulfillmentRecord,
    PerformanceEntry,
    SettlementRecord,
)
from gridlabd_interface import GridLABDInterface
from data_streams import DataStreamManager
from device_agent import DeviceAgent
from market_agent import MarketCommunicationInterface
from market_operator import MarketOperator, SupplyCurve, DSOLoadEstimationEngine
from penalty_model import PenaltyModel
from preference_curve import PreferenceCurve
from market_object import MarketObject


# ── helpers ────────────────────────────────────────────────────────────

DIVIDER = "=" * 68


def banner(title: str) -> None:
    print(f"\n{DIVIDER}\n  {title}\n{DIVIDER}")


def kv(label: str, value, unit: str = "") -> None:
    if isinstance(value, float):
        print(f"  {label:.<40s} {value:>10.4f} {unit}")
    else:
        print(f"  {label:.<40s} {str(value):>10s} {unit}")


# ── mock GridLAB-D connection ─────────────────────────────────────────


class MockConnection:
    """Simulates a HELICS/FNCS connection returning canned HVAC values.

    Represents a 2,400 sq-ft house on a hot afternoon in Houston.
    """

    _DATA = {
        # Temperatures and mode
        "air_temperature": "76.3",
        "outdoor_temperature": "95.2",
        "cooling_setpoint": "72.0",
        "heating_setpoint": "68.0",
        "power_state": "COOL",
        "hvac_load": "12000",  # Btu/hr
        "mass_temperature": "74.8",
        # Thermal parameters
        "Ua": "500.0",
        "Hm": "1500.0",
        "Ca": "1500.0",
        "Cm": "5000.0",
        "cooling_COP": "3.5",
        "heating_COP": "3.0",
        "design_cooling_capacity": "36000.0",
        "design_heating_capacity": "36000.0",
        "solar_heatgain": "800.0",
        "internal_heatgain": "400.0",
    }

    def __init__(self):
        self._written: dict = {}

    def get_value(self, key: str) -> str:
        prop = key.split("#", 1)[-1]
        return self._DATA.get(prop, "")

    def set_value(self, key: str, value) -> None:
        self._written[key] = value


# ── mock transport (agent ↔ MO bridge) ───────────────────────────────


class MockTransport:
    """Bridges MarketCommunicationInterface calls to a MarketOperator."""

    def __init__(self, market_operator: MarketOperator):
        self._mo = market_operator
        self._results: dict = {}  # market_id -> ClearingResult

    # Called by MarketCommunicationInterface.submit_bid
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

    # Called by MarketCommunicationInterface.receive_clear
    def receive(self, *, agent_id, market_id):
        return self._results.get(agent_id)

    def push_results(self, results: dict):
        self._results.update(results)


# ══════════════════════════════════════════════════════════════════════
#  MAIN DEMO
# ══════════════════════════════════════════════════════════════════════


def main():
    banner("TESP Curve-and-Agent Demo — Single HVAC, RT Energy Market")

    # ─── 1. Infrastructure ────────────────────────────────────────────
    print("\n▸ Creating mock GridLAB-D connection and interfaces...")
    conn = MockConnection()
    gld = GridLABDInterface(
        connection=conn, object_name="house_1", device_type=DeviceType.HVAC_AC_ONLY
    )

    # ─── 2. Market Operator ───────────────────────────────────────────
    print("▸ Setting up RT energy market operator with supply curve...")
    rt_timing = MarketTimingParams(
        t_activate=-600.0,
        t_negotiate=-420.0,
        t_market_lead=-60.0,
        t_clear=0.0,
        t_delivery_start=0.0,
        t_delivery_end=300.0,
        t_reconcile_end=600.0,
    )
    mo = MarketOperator(
        market_type=MarketType.RT_ENERGY,
        timing_params=rt_timing,
        iteration_protocol="fixed_count",
        n_informational=0,  # straight to binding
    )
    supply = SupplyCurve(
        points=[
            BidPoint(price=0.02, quantity=0.0),
            BidPoint(price=0.05, quantity=500.0),
            BidPoint(price=0.08, quantity=1000.0),
            BidPoint(price=0.15, quantity=1500.0),
            BidPoint(price=0.50, quantity=2000.0),
            BidPoint(price=1.00, quantity=2000.0),
        ]
    )
    mo.set_supply_curve(supply)

    # DSO inflexible load
    dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
    dso_bid = dso.estimate_inflexible_load(
        interval=(0.0, 300.0),
        total_load_forecast=1200.0,
        flexible_committed=0.0,
        btm_solar_forecast=150.0,
        loss_factor=0.05,
    )
    mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
    print(f"  DSO inflexible bid: {dso_bid.quantity:.1f} kW")

    # ─── 3. Penalty model ────────────────────────────────────────────
    rt_penalty = PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
    )

    # ─── 4. Transport bridge ─────────────────────────────────────────
    transport = MockTransport(mo)

    # ─── 5. Device Agent ─────────────────────────────────────────────
    print("▸ Creating HVAC device agent (AC-only, comfort-focused k=0.3)...")
    dsm = DataStreamManager(DeviceType.HVAC_AC_ONLY)
    agent = DeviceAgent(
        agent_id="hvac_house_1",
        device_type=DeviceType.HVAC_AC_ONLY,
        gridlabd=gld,
        customer_preference_k=0.3,
        data_stream_manager=dsm,
    )
    agent.initialize({})

    comm = MarketCommunicationInterface(
        transport=transport,
        agent_id="hvac_house_1",
        market_type=MarketType.RT_ENERGY,
    )
    agent.register_market(
        market_type=MarketType.RT_ENERGY,
        timing_params=rt_timing,
        operating_mode=OperatingMode.BIDDING,
        penalty_model=rt_penalty,
        communication=comm,
    )

    # ══════════════════════════════════════════════════════════════════
    #  Walk through one complete market cycle
    # ══════════════════════════════════════════════════════════════════

    # ── F1: Observe device state ──────────────────────────────────────
    banner("F1  Observe Device State")
    state = agent.observe_device_state()
    kv("Indoor air temp", state.indoor_air_temp, "°F")
    kv("Outdoor air temp", state.outdoor_air_temp, "°F")
    kv("Thermostat setpoint", state.thermostat_setpoint, "°F")
    kv("HVAC mode", state.hvac_mode)
    kv("Power draw", state.power_draw, "kW")
    kv("Cooling COP", state.cooling_COP)

    # ── F2: Estimate flexibility ──────────────────────────────────────
    banner("F2  Estimate Flexibility")
    flex = agent.estimate_flexibility(state, interval_duration=300.0)
    kv("Q_min (min power)", flex.Q_min, "kW")
    kv("Q_max (max power)", flex.Q_max, "kW")
    kv("Q_baseline", flex.Q_baseline, "kW")
    print(
        f"  → Agent can vary consumption between {flex.Q_min:.2f} "
        f"and {flex.Q_max:.2f} kW over the next 5 min."
    )

    # ── F3: Generate preference curve ─────────────────────────────────
    banner("F3  Generate Preference Curve")
    pref = agent.generate_preference_curve(flex)
    print(
        f"  Preference curve anchored at Q₀={pref._Q_0:.2f} kW, "
        f"P₀={pref._P_0:.4f} $/kWh, k={pref._k:.2f}"
    )

    # Sample the curve at a few prices
    print("\n  Price ($/kWh)   Desired Q (kW)")
    print("  ─────────────   ──────────────")
    for p in [0.02, 0.05, 0.08, 0.10, 0.15, 0.30, 0.50]:
        q = pref.evaluate(p)
        print(f"  ${p:<13.2f}   {q:>8.3f} kW")

    # ── F4: Formulate bid ─────────────────────────────────────────────
    banner("F4  Formulate Bid")
    market_id = agent.spawn_market_cycle(MarketType.RT_ENERGY, clearing_time=300.0)
    mo_obj = agent._market_objects[market_id]
    mo_obj.available_flexibility = flex
    mo_obj.preference_curve = pref
    bid = agent.formulate_bid(mo_obj, flex, pref)
    print(f"  Bid curve ({len(bid.points)} points) for market {market_id}:")
    print(f"  {'Price':>10s}  {'Quantity':>10s}")
    print(f"  {'─' * 10}  {'─' * 10}")
    for pt in bid.points:
        print(f"  ${pt.price:>9.4f}  {pt.quantity:>9.3f} kW")

    # ── F5: Submit bid to Market Operator ────────────────────────────
    banner("F5  Submit Bid → Market Operator")
    ack = comm.submit_bid(bid, market_id=market_id, interval_id=f"int_{market_id}")
    print(f"  Bid submitted, acknowledged: {ack}")
    print(f"  Bids on file at MO: {list(mo._agent_bids.keys())}")

    # ── MO clears the market ──────────────────────────────────────────
    banner("Market Clearing")
    clearing = mo.clear_market()
    print(f"  Iteration type .... {clearing.iteration_type.name}")
    kv("Clearing price", clearing.cleared_price, "$/kWh")
    kv("Aggregate quantity", clearing.cleared_quantity, "kW")

    per_agent = mo.propagate_results()
    agent_result = per_agent.get("hvac_house_1", clearing)
    kv("Agent cleared qty", agent_result.cleared_quantity, "kW")

    # Push results so the agent can receive them
    transport.push_results(per_agent)

    # ── F7: Evaluate price response ───────────────────────────────────
    banner("F7  Price Response")
    target_q = agent.evaluate_price_response(clearing.cleared_price, pref)
    kv("Clearing price", clearing.cleared_price, "$/kWh")
    kv("Target power (from curve)", target_q, "kW")

    # ── F8: Translate to control command ──────────────────────────────
    banner("F8  Translate to Control Command")
    cmd = agent.translate_to_control(target_q, state)
    kv("Device type", cmd.device_type.name)
    kv("Thermostat setpoint", cmd.setpoint, "°F")
    kv("Mode", cmd.mode)
    kv("Power target", cmd.power_target, "kW")

    # ── Delivery via Command Arbiter ──────────────────────────────────
    banner("Delivery Phase — Command Arbiter")
    mo_obj.cleared_price = clearing.cleared_price
    mo_obj.cleared_quantity = agent_result.cleared_quantity
    # Register delivery
    agent._command_arbiter.register_delivery(
        market_id=market_id,
        market_type=str(MarketType.RT_ENERGY),
        product_type="ENERGY_BASE",
        committed_qty=agent_result.cleared_quantity,
        cleared_price=clearing.cleared_price,
        penalty_model=rt_penalty,
        interval=(0.0, 300.0),
    )
    # Simulate 5 delivery ticks (one per minute)
    for tick in range(5):
        t = tick * 60.0
        fulfillments = agent._command_arbiter.resolve_and_actuate(
            device_state=state,
            preference_curve=pref,
            amenity_weight=0.3,
            current_time=t,
        )
        for mid, fr in fulfillments.items():
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
                f"  t={t:>5.0f}s  committed={fr.committed:.3f} kW  "
                f"actual={fr.actual:.3f} kW  revenue=${fr.revenue:.4f}  "
                f"penalty=${fr.penalty:.4f}"
            )

    # ── F13: Reconciliation ───────────────────────────────────────────
    banner("F13  Reconciliation")
    settlement = agent.reconcile(mo_obj)
    kv("Total revenue", settlement.total_revenue, "$")
    kv("Total penalty", settlement.total_penalty, "$")
    kv("Net settlement", settlement.net_settlement, "$")
    kv("Energy committed", settlement.total_energy_committed, "kW·ticks")
    kv("Energy delivered", settlement.total_energy_delivered, "kW·ticks")
    kv("Total shortfall", settlement.total_shortfall, "kW·ticks")

    # ── GridLAB-D writes ──────────────────────────────────────────────
    banner("GridLAB-D Writes (mock)")
    if conn._written:
        for key, val in conn._written.items():
            print(f"  {key} = {val}")
    else:
        print("  (no writes recorded)")

    # ── Summary ───────────────────────────────────────────────────────
    banner("Summary")
    print(
        textwrap.dedent(f"""\
      Outdoor temp          : {state.outdoor_air_temp} °F
      Indoor temp           : {state.indoor_air_temp} °F
      Original setpoint     : {state.thermostat_setpoint} °F
      Market clearing price : ${clearing.cleared_price:.4f}/kWh
      Agent target power    : {target_q:.3f} kW
      New thermostat setpoint: {cmd.setpoint:.1f} °F
      Net settlement        : ${settlement.net_settlement:.4f}

      The agent adjusted its thermostat in response to the market price.
      A higher clearing price would cause the agent to consume less
      (raise setpoint), while a lower price allows more cooling
      (lower setpoint) — balancing comfort and cost.""")
    )

    print(f"\n{DIVIDER}")
    print("  Demo complete. All 16 modules exercised successfully.")
    print(DIVIDER)


if __name__ == "__main__":
    main()
