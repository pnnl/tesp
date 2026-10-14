#!/usr/bin/env python3
"""
Generate an interactive Plotly dashboard from the demo_multi simulation.

Produces dashboard.html with:
  1. Supply vs Aggregate Demand — clearing intersection
  2. Individual agent bid curves (all 50)
  3. Agent preference parameter (k) vs cleared quantity
  4. Delivery timeline for house_1
  5. Setpoint shift distribution across all agents
  6. Summary statistics table
"""

import sys, os, random

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

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Mocks (same as demo_multi) ───────────────────────────────────────


class MockConnection:
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
        return self._data.get(key.split("#", 1)[-1], "")

    def set_value(self, key, value):
        self.written[key] = value


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


# ── Run the simulation and collect data ───────────────────────────────

N_HOUSES = 50


def run_simulation():
    random.seed(42)

    rt_timing = MarketTimingParams()
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

    dso = DSOLoadEstimationEngine(feeder_id="feeder_1")
    dso_bid = dso.estimate_inflexible_load(
        interval=(0.0, 300.0),
        total_load_forecast=300.0,
        flexible_committed=0.0,
        btm_solar_forecast=50.0,
        loss_factor=0.04,
    )
    mo.submit_dso_inflexible_bid("feeder_1", dso_bid)
    transport = MockTransport(mo)

    rt_penalty = PenaltyModel(
        market_type=MarketType.RT_ENERGY,
        structure_type=PenaltyStructureType.PROPORTIONAL,
        params={"rate_reference": "cleared_price_multiple", "multiplier": 2.0},
    )

    # ── Create agents and collect metadata ────────────────────────────
    agents, conns, comms = [], [], []
    agent_meta = []  # list of dicts with per-agent info
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
        agent_meta.append({"id": f"hvac_{i + 1}", "k": k, "indoor": indoor})

    # ── F1–F5 for all agents ──────────────────────────────────────────
    all_bids = {}  # agent_id -> list of (price, qty)
    all_prefs = {}  # agent_id -> list of (price, qty) dense samples
    all_states = {}
    all_flexes = {}

    for i, ag in enumerate(agents):
        st = ag.observe_device_state()
        fl = ag.estimate_flexibility(st, 300.0)
        pr = ag.generate_preference_curve(fl)
        m = ag.spawn_market_cycle(MarketType.RT_ENERGY, clearing_time=300.0)
        mobj = ag._market_objects[m]
        mobj.available_flexibility = fl
        mobj.preference_curve = pr
        bid = ag.formulate_bid(mobj, fl, pr)
        comms[i].submit_bid(bid, market_id=m, interval_id=f"int_{m}")

        all_bids[agent_meta[i]["id"]] = [(pt.price, pt.quantity) for pt in bid.points]
        all_states[agent_meta[i]["id"]] = st
        all_flexes[agent_meta[i]["id"]] = fl

        # Dense preference curve sampling
        pref_pts = []
        for p_cents in range(1, 101):
            p = p_cents / 100.0
            q = pr.evaluate(p)
            pref_pts.append((p, q))
        all_prefs[agent_meta[i]["id"]] = pref_pts

    # ── Market Clearing ───────────────────────────────────────────────
    clearing = mo.clear_market()
    per_agent = mo.propagate_results()

    # Build aggregate demand curve (same logic as MO)
    agg_demand = mo.aggregate_demand()

    # ── For each agent: cleared qty, setpoint shift ───────────────────
    for meta in agent_meta:
        aid = meta["id"]
        r = per_agent.get(aid)
        meta["cleared_qty"] = r.cleared_quantity if r else 0.0
        st = all_states[aid]
        # Compute new setpoint via F7/F8 on the agent
        idx = int(aid.split("_")[1]) - 1
        ag = agents[idx]
        pref_curve = ag._current_preference_curve
        target_q = ag.evaluate_price_response(clearing.cleared_price, pref_curve)
        cmd = ag.translate_to_control(target_q, st)
        meta["new_setpoint"] = cmd.setpoint
        meta["old_setpoint"] = st.thermostat_setpoint
        meta["setpoint_delta"] = cmd.setpoint - st.thermostat_setpoint
        meta["target_q"] = target_q

    # ── House_1 delivery trace ────────────────────────────────────────
    agent = agents[0]
    state = all_states["hvac_1"]
    pref = agent._current_preference_curve
    h1_result = per_agent["hvac_1"]
    mid_h1 = list(agent._market_objects.keys())[0]
    mo_obj = agent._market_objects[mid_h1]
    mo_obj.cleared_price = clearing.cleared_price
    mo_obj.cleared_quantity = h1_result.cleared_quantity

    agent._command_arbiter.register_delivery(
        market_id=mid_h1,
        market_type=str(MarketType.RT_ENERGY),
        product_type="ENERGY_BASE",
        committed_qty=h1_result.cleared_quantity,
        cleared_price=clearing.cleared_price,
        penalty_model=rt_penalty,
        interval=(0.0, 300.0),
    )

    delivery_trace = []
    for tick in range(5):
        t = tick * 60.0
        frs = agent._command_arbiter.resolve_and_actuate(
            device_state=state,
            preference_curve=pref,
            amenity_weight=agent._k,
            current_time=t,
        )
        for m_id, fr in frs.items():
            delivery_trace.append(
                {
                    "t": t,
                    "committed": fr.committed,
                    "actual": fr.actual,
                    "shortfall": fr.shortfall,
                    "revenue": fr.revenue,
                    "penalty": fr.penalty,
                    "net_value": fr.net_value,
                }
            )

    settlement = agent.reconcile(mo_obj)

    return {
        "supply": supply,
        "dso_bid": dso_bid,
        "agg_demand": agg_demand,
        "clearing": clearing,
        "per_agent": per_agent,
        "agent_meta": agent_meta,
        "all_bids": all_bids,
        "all_prefs": all_prefs,
        "delivery_trace": delivery_trace,
        "settlement": settlement,
    }


# ── Build Dashboard ──────────────────────────────────────────────────


def build_dashboard(data):
    supply = data["supply"]
    dso_bid = data["dso_bid"]
    agg_demand = data["agg_demand"]
    clearing = data["clearing"]
    agent_meta = data["agent_meta"]
    all_bids = data["all_bids"]
    delivery_trace = data["delivery_trace"]
    settlement = data["settlement"]

    # Colors
    SUPPLY_COLOR = "#2ecc71"
    DEMAND_COLOR = "#3498db"
    CLEARING_COLOR = "#e74c3c"
    INFLEXIBLE_COLOR = "#95a5a6"
    H1_COLOR = "#e67e22"
    BG_COLOR = "#fafbfc"
    GRID_COLOR = "#e0e0e0"

    fig = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=(
            "Supply vs Aggregate Demand",
            "Individual Agent Bid Curves",
            "Preference k vs Cleared Quantity",
            "House 1 — Delivery Timeline",
            "Thermostat Setpoint Shifts",
            "Settlement Summary (House 1)",
        ),
        specs=[
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "table"}],
        ],
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
    )

    # ── 1. Supply vs Aggregate Demand ─────────────────────────────────
    # Supply curve
    s_qty = [pt.quantity for pt in supply.points]
    s_price = [pt.price for pt in supply.points]
    fig.add_trace(
        go.Scatter(
            x=s_qty,
            y=s_price,
            mode="lines+markers",
            name="Supply",
            line=dict(color=SUPPLY_COLOR, width=3),
            marker=dict(size=6),
        ),
        row=1,
        col=1,
    )

    # Aggregate demand curve (sorted by quantity for plotting)
    d_qty = [pt.quantity for pt in agg_demand]
    d_price = [pt.price for pt in agg_demand]
    fig.add_trace(
        go.Scatter(
            x=d_qty,
            y=d_price,
            mode="lines+markers",
            name="Agg. Demand",
            line=dict(color=DEMAND_COLOR, width=3),
            marker=dict(size=6),
        ),
        row=1,
        col=1,
    )

    # DSO inflexible load (vertical line)
    fig.add_trace(
        go.Scatter(
            x=[dso_bid.quantity, dso_bid.quantity],
            y=[0, 1.0],
            mode="lines",
            name=f"Inflexible ({dso_bid.quantity:.0f} kW)",
            line=dict(color=INFLEXIBLE_COLOR, width=2, dash="dash"),
        ),
        row=1,
        col=1,
    )

    # Clearing point
    fig.add_trace(
        go.Scatter(
            x=[clearing.cleared_quantity],
            y=[clearing.cleared_price],
            mode="markers",
            name="Clearing Point",
            marker=dict(
                color=CLEARING_COLOR,
                size=14,
                symbol="star",
                line=dict(width=2, color="white"),
            ),
            text=[
                f"${clearing.cleared_price:.4f}/kWh<br>{clearing.cleared_quantity:.1f} kW"
            ],
            hoverinfo="text",
        ),
        row=1,
        col=1,
    )

    # Clearing price horizontal line
    fig.add_trace(
        go.Scatter(
            x=[0, max(s_qty[-1], d_qty[0]) * 1.05],
            y=[clearing.cleared_price, clearing.cleared_price],
            mode="lines",
            name=f"Price ${clearing.cleared_price:.4f}",
            line=dict(color=CLEARING_COLOR, width=1.5, dash="dot"),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    fig.update_xaxes(title_text="Quantity (kW)", row=1, col=1)
    fig.update_yaxes(title_text="Price ($/kWh)", row=1, col=1)

    # ── 2. Individual Agent Bid Curves ────────────────────────────────
    for i, meta in enumerate(agent_meta):
        aid = meta["id"]
        pts = all_bids[aid]
        prices = [p for p, q in pts]
        qtys = [q for p, q in pts]
        is_h1 = i == 0
        fig.add_trace(
            go.Scatter(
                x=qtys,
                y=prices,
                mode="lines",
                name=aid if is_h1 else None,
                showlegend=is_h1,
                line=dict(
                    color=H1_COLOR if is_h1 else f"rgba(52,152,219,0.15)",
                    width=3 if is_h1 else 1,
                ),
                hovertemplate=(
                    f"<b>{aid}</b> (k={meta['k']:.2f})<br>"
                    "Price: $%{y:.4f}/kWh<br>Qty: %{x:.3f} kW<extra></extra>"
                ),
            ),
            row=1,
            col=2,
        )

    # Annotation for house_1
    fig.add_annotation(
        x=all_bids["hvac_1"][-1][1],
        y=all_bids["hvac_1"][-1][0],
        text="house_1",
        showarrow=True,
        arrowhead=2,
        font=dict(color=H1_COLOR, size=11),
        row=1,
        col=2,
    )

    fig.update_xaxes(title_text="Quantity (kW)", row=1, col=2)
    fig.update_yaxes(title_text="Price ($/kWh)", row=1, col=2)

    # ── 3. k vs Cleared Quantity scatter ──────────────────────────────
    ks = [m["k"] for m in agent_meta]
    cqs = [m["cleared_qty"] for m in agent_meta]
    deltas = [m["setpoint_delta"] for m in agent_meta]
    ids = [m["id"] for m in agent_meta]

    fig.add_trace(
        go.Scatter(
            x=ks,
            y=cqs,
            mode="markers",
            marker=dict(
                size=10,
                color=deltas,
                colorscale="RdYlBu_r",
                colorbar=dict(title="Setpoint Δ °F", x=0.44, len=0.25, y=0.5),
                line=dict(width=1, color="white"),
            ),
            text=[
                f"{aid}<br>k={k:.2f}<br>Q={q:.3f} kW<br>Δ={d:.1f}°F"
                for aid, k, q, d in zip(ids, ks, cqs, deltas)
            ],
            hoverinfo="text",
            name="Agents",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    # Highlight house_1
    fig.add_trace(
        go.Scatter(
            x=[agent_meta[0]["k"]],
            y=[agent_meta[0]["cleared_qty"]],
            mode="markers+text",
            marker=dict(
                size=14,
                color=H1_COLOR,
                symbol="star",
                line=dict(width=2, color="white"),
            ),
            text=["house_1"],
            textposition="top center",
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    fig.update_xaxes(title_text="Preference k (0=comfort, 1=financial)", row=2, col=1)
    fig.update_yaxes(title_text="Cleared Quantity (kW)", row=2, col=1)

    # ── 4. House_1 Delivery Timeline ──────────────────────────────────
    times = [d["t"] for d in delivery_trace]
    committed = [d["committed"] for d in delivery_trace]
    actual = [d["actual"] for d in delivery_trace]
    revenues = [d["revenue"] for d in delivery_trace]

    fig.add_trace(
        go.Bar(
            x=times,
            y=committed,
            name="Committed",
            marker_color=DEMAND_COLOR,
            opacity=0.5,
            width=40,
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Bar(
            x=times,
            y=actual,
            name="Actual",
            marker_color=SUPPLY_COLOR,
            opacity=0.8,
            width=30,
        ),
        row=2,
        col=2,
    )

    # Revenue on secondary y? Just overlay as text
    for d in delivery_trace:
        fig.add_annotation(
            x=d["t"],
            y=d["actual"] * 1.08,
            text=f"${d['revenue']:.3f}",
            showarrow=False,
            font=dict(size=9, color="#555"),
            row=2,
            col=2,
        )

    fig.update_xaxes(title_text="Time (s)", row=2, col=2)
    fig.update_yaxes(title_text="Power (kW)", row=2, col=2)

    # ── 5. Setpoint Shift Histogram ───────────────────────────────────
    fig.add_trace(
        go.Histogram(
            x=deltas,
            nbinsx=15,
            name="Setpoint Δ",
            marker_color=DEMAND_COLOR,
            opacity=0.8,
            hovertemplate="Δ %{x:.1f}°F: %{y} agents<extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig.add_vline(
        x=agent_meta[0]["setpoint_delta"],
        line_dash="dash",
        line_color=H1_COLOR,
        annotation_text="house_1",
        row=3,
        col=1,
    )

    fig.update_xaxes(title_text="Setpoint Change (°F)", row=3, col=1)
    fig.update_yaxes(title_text="Number of Agents", row=3, col=1)

    # ── 6. Settlement Summary Table ───────────────────────────────────
    labels = [
        "Houses in market",
        "Outdoor temperature",
        "Clearing price",
        "Aggregate cleared load",
        "Inflexible load (DSO)",
        "",
        "<b>House 1</b>",
        "  Preference k",
        "  Indoor temp",
        "  Original setpoint",
        "  New setpoint",
        "  Setpoint change",
        "  Cleared quantity",
        "  5-min revenue",
        "  5-min penalty",
        "  Net settlement",
    ]
    values = [
        f"{N_HOUSES}",
        f"{95.2} °F",
        f"${clearing.cleared_price:.4f}/kWh",
        f"{clearing.cleared_quantity:.1f} kW",
        f"{dso_bid.quantity:.1f} kW",
        "",
        "",
        f"{agent_meta[0]['k']}",
        f"{agent_meta[0]['indoor']} °F",
        f"{agent_meta[0]['old_setpoint']:.1f} °F",
        f"{agent_meta[0]['new_setpoint']:.1f} °F",
        f"+{agent_meta[0]['setpoint_delta']:.1f} °F",
        f"{agent_meta[0]['cleared_qty']:.3f} kW",
        f"${settlement.total_revenue:.4f}",
        f"${settlement.total_penalty:.4f}",
        f"<b>${settlement.net_settlement:.4f}</b>",
    ]

    fig.add_trace(
        go.Table(
            header=dict(
                values=["<b>Metric</b>", "<b>Value</b>"],
                fill_color="#34495e",
                font=dict(color="white", size=12),
                align="left",
                height=28,
            ),
            cells=dict(
                values=[labels, values],
                fill_color=[["#f7f9fa", "white"] * (len(labels) // 2 + 1)],
                align="left",
                height=24,
                font=dict(size=11),
            ),
        ),
        row=3,
        col=2,
    )

    # ── Layout ────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text=(
                "<b>TESP Curve-and-Agent Dashboard</b>"
                f"<br><sup>{N_HOUSES} HVAC agents · RT energy market · "
                f"Clearing: ${clearing.cleared_price:.4f}/kWh "
                f"@ {clearing.cleared_quantity:.1f} kW</sup>"
            ),
            x=0.5,
            y=0.98,
            yanchor="top",
            font=dict(size=20),
        ),
        height=1250,
        width=1400,
        margin=dict(t=140),
        template="plotly_white",
        paper_bgcolor=BG_COLOR,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.065,
            xanchor="center",
            x=0.5,
        ),
        barmode="overlay",
    )

    # Apply consistent grid styling
    for i in range(1, 4):
        for j in range(1, 3):
            try:
                fig.update_xaxes(gridcolor=GRID_COLOR, row=i, col=j)
                fig.update_yaxes(gridcolor=GRID_COLOR, row=i, col=j)
            except Exception:
                pass

    return fig


# ── Main ──────────────────────────────────────────────────────────────


def main():
    print("Running simulation...")
    data = run_simulation()

    print("Building dashboard...")
    fig = build_dashboard(data)

    out_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    fig.write_html(out_path, include_plotlyjs=True, full_html=True)
    print(f"Dashboard written to {out_path}")
    print(f"Open in browser:  file://{os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
