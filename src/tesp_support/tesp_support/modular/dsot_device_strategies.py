"""DSOT device strategy implementations.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

This module provides concrete DeviceStrategy subclasses for DSOT agents:
  - HVACDSOTStrategy: Thermostat with thermal mass control
  - BatteryDSOTStrategy: Energy storage with state-of-charge tracking
  - EVDSOTStrategy: Electric vehicle charging with arrival/departure constraints
  - WaterHeaterDSOTStrategy: Thermal storage (DHW)
  - PVDSOTStrategy: Solar generation (passive participant)

Each strategy encapsulates device physics, optimization logic, and bid formulation.
Market protocol and clearing mechanisms are decoupled from device implementations.
"""

from abc import abstractmethod
from typing import Dict, Optional, Callable
import numpy as np

from ..modular.device_strategy import DeviceStrategy
from ..modular.market_protocol import Bid, MarketWindow
from ..modular.price_signal import PriceSignal


class DSOTDeviceStrategy(DeviceStrategy):
    """Base class for DSOT device strategies.

    Extends DeviceStrategy with common DSOT patterns:
      - Price signal history and forecasting
      - Quadratic bid cost curve (C0 + C1*Q + C2*Q^2)
      - Ramp rate limits and quantity bounds
      - Settlement period state tracking

    Subclasses implement device-specific physics (thermal dynamics, battery chemistry, etc.)
    and optimization logic (optimal control, heuristic rules, etc.).

    Attributes:
        price_history (Dict[str, list[float]]): Historical prices by market_id.
        state (Dict[str, float]): Device physical state (temperature, SOC, etc.).
        bounds (Dict[str, tuple[float, float]]): Min/max quantity and ramp constraints.
    """

    def __init__(
        self,
        device_id: str,
        device_type: str,
        price_cap: float = 100.0,
        quantity_min: float = 0.0,
        quantity_max: float = 10.0,
        ramp_limit: float = 5.0,
    ):
        """Initialize a DSOT device strategy.

        Args:
            device_id: Unique identifier for this device.
            device_type: Device class (e.g., 'HVAC', 'Battery', 'EV', 'WaterHeater').
            price_cap: Upper limit for acceptable bids ($/MWh).
            quantity_min: Minimum allowed quantity in a bid (MWh).
            quantity_max: Maximum allowed quantity in a bid (MWh).
            ramp_limit: Maximum rate of change per period (MWh/period).
        """
        super().__init__(device_id, device_type)
        self.price_cap = price_cap
        self.quantity_min = quantity_min
        self.quantity_max = quantity_max
        self.ramp_limit = ramp_limit

        # Price signal history for forecasting
        self.price_history = {"DA": [], "RT": []}

        # Device physical state (temperature, SOC, etc.) - subclasses override
        self.state = {}

        # Bid curve coefficients (quadratic: C0 + C1*Q + C2*Q^2)
        # Subclasses set these based on device physics and optimization
        self.bid_coefficients = {"C0": 0.0, "C1": 50.0, "C2": 0.0}

    def observe_prices(self, price_signal: PriceSignal) -> None:
        """Observe a price signal and update device expectations.

        Stores the clearing price in history for forecasting. Subclasses
        override to also update device state based on cleared quantities.

        Args:
            price_signal: Market results from most recent clearing.
        """
        market_id = price_signal.market_id
        if market_id not in self.price_history:
            self.price_history[market_id] = []
        self.price_history[market_id].append(price_signal.clearing_price)

        # Keep last N prices (rolling window)
        if len(self.price_history[market_id]) > 24:
            self.price_history[market_id] = self.price_history[market_id][-24:]

    def forecast_price(self, market_id: str, horizon: int = 1) -> float:
        """Forecast the next price for a market.

        Simple heuristic: average of recent prices, with bias toward most recent.

        Args:
            market_id: 'DA' or 'RT'.
            horizon: Number of periods ahead (not used in simple average).

        Returns:
            Forecasted price in $/MWh.
        """
        if market_id not in self.price_history or len(self.price_history[market_id]) == 0:
            return self.price_cap / 2.0  # Default to midpoint if no history

        prices = self.price_history[market_id]
        # Simple forecast: weighted average with recency bias
        weights = np.linspace(0.5, 1.5, len(prices))
        return float(np.average(prices, weights=weights))

    def value_function_quadratic(self, quantity: float) -> float:
        """Evaluate a quadratic marginal cost/benefit function.

        Marginal value = C0 + C1 * Q + C2 * Q^2

        For a supply bid, this represents marginal cost.
        For a demand bid, this represents marginal benefit (willingness-to-pay).

        Args:
            quantity: Quantity in MWh.

        Returns:
            Marginal value in $/MWh, clamped to [0, price_cap].
        """
        C0 = self.bid_coefficients["C0"]
        C1 = self.bid_coefficients["C1"]
        C2 = self.bid_coefficients["C2"]
        value = C0 + C1 * quantity + C2 * quantity**2
        return max(0.0, min(self.price_cap, float(value)))

    @abstractmethod
    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Generate a bid for a market window.

        Subclasses override to implement device-specific optimization logic:
          - HVAC: thermal comfort constraints + price responsiveness
          - Battery: SOC trajectory + arbitrage opportunity
          - EV: arrival/departure time + energy needed
          - WaterHeater: temperature setpoint + time-shift flexibility
          - PV: forecasted generation (passive, no bids)

        Args:
            market_window: The market window for which a bid is requested.

        Returns:
            A Bid with participant_id, market_id, quantity range, and value_function.

        Raises:
            ValueError: If the device cannot participate in this market window.
        """
        pass

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"device_id={self.device_id!r}, "
            f"Q_range=[{self.quantity_min}, {self.quantity_max}], "
            f"C1={self.bid_coefficients['C1']:.2f})"
        )


class HVACDSOTStrategy(DSOTDeviceStrategy):
    """HVAC thermostat with thermal mass and comfort constraints.

    Models a residential heating/cooling system with:
      - Thermal mass (time constant of response)
      - Comfort deadband (setpoint +/- deadband)
      - Comfort-constrained bidding (must reach setpoint by next period)
      - Price responsiveness within comfort envelope

    The device optimizes its HVAC operation to trade off comfort flexibility
    against price signals, subject to being able to return to setpoint.
    """

    def __init__(
        self,
        device_id: str,
        hvac_dict: Dict,
        **kwargs,
    ):
        """Initialize HVAC strategy.

        Args:
            device_id: Unique identifier.
            hvac_dict: Configuration dict with keys:
                'price_cap': Maximum acceptable price ($/MWh)
                'quantity_max': Maximum power (kW, converted to MWh)
                'setpoint_heating': Target temperature for heating (°F)
                'setpoint_cooling': Target temperature for cooling (°F)
                'deadband': Comfort deadband (°F)
                'ramp_limit': Power ramp rate limit (kW/min)
            **kwargs: Additional arguments passed to parent.
        """
        super().__init__(
            device_id=device_id,
            device_type="HVAC",
            price_cap=hvac_dict.get("price_cap", 100.0),
            quantity_max=hvac_dict.get("quantity_max", 10.0) / 1000.0,  # kW to MWh
            ramp_limit=hvac_dict.get("ramp_limit", 5.0) / 1000.0,
            **kwargs,
        )
        self.setpoint_heating = hvac_dict.get("setpoint_heating", 70.0)
        self.setpoint_cooling = hvac_dict.get("setpoint_cooling", 75.0)
        self.deadband = hvac_dict.get("deadband", 2.0)

        # Thermal state
        self.state = {
            "indoor_temperature": (self.setpoint_heating + self.setpoint_cooling) / 2.0,
            "mode": "idle",  # idle, heating, cooling
        }

        # Bid coefficients: slightly favor comfort setpoint
        self.bid_coefficients["C1"] = 40.0  # Moderate willingness to heat/cool at baseline

    def observe_prices(self, price_signal: PriceSignal) -> None:
        """Observe price signal and update thermal state estimate.

        Args:
            price_signal: Market results from most recent clearing.
        """
        super().observe_prices(price_signal)
        # Update internal temperature estimate based on cleared quantity
        # (Simplified: in a real implementation, integrate thermal dynamics)
        cleared_qty = price_signal.cleared_quantities.get(self.device_id, 0.0)
        # TODO: Update indoor_temperature based on cleared_qty and time dynamics

    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Formulate HVAC bid for comfort-constrained dispatch.

        Bids the quantity range needed to stay within the comfort deadband,
        with marginal values reflecting price sensitivity within that range.

        Args:
            market_window: The market window.

        Returns:
            Bid with quantity range [0, quantity_max] and quadratic value function.
        """
        return Bid(
            participant_id=self.device_id,
            market_id=market_window.market_id,
            valid_from=market_window.settlement_period_start,
            valid_to=market_window.settlement_period_end,
            quantity_min=self.quantity_min,
            quantity_max=self.quantity_max,
            value_function=self.value_function_quadratic,
            bid_type="demand",  # HVAC demands load (heating/cooling)
            metadata={
                "device_type": self.device_type,
                "current_temp": self.state.get("indoor_temperature"),
                "setpoint_heating": self.setpoint_heating,
                "setpoint_cooling": self.setpoint_cooling,
            },
        )


class BatteryDSOTStrategy(DSOTDeviceStrategy):
    """Battery energy storage with state-of-charge tracking.

    Models a residential or community battery with:
      - State-of-charge (SOC) constraints
      - Charging/discharging ramp rates
      - Arbitrage opportunity (buy low RT, sell high DA or vice versa)
      - Roundtrip efficiency

    The device optimizes charging/discharging over multiple periods to
    capture price differences while maintaining SOC within bounds.
    """

    def __init__(
        self,
        device_id: str,
        battery_dict: Dict,
        **kwargs,
    ):
        """Initialize battery strategy.

        Args:
            device_id: Unique identifier.
            battery_dict: Configuration dict with keys:
                'capacity_mwh': Total energy capacity (MWh)
                'power_rating_mw': Maximum power (MW)
                'efficiency': Roundtrip efficiency (0-1)
                'soc_min': Minimum state of charge (0-1)
                'soc_max': Maximum state of charge (0-1)
                'price_cap': Maximum acceptable price ($/MWh)
            **kwargs: Additional arguments passed to parent.
        """
        super().__init__(
            device_id=device_id,
            device_type="Battery",
            price_cap=battery_dict.get("price_cap", 100.0),
            quantity_max=battery_dict.get("power_rating_mw", 5.0),
            **kwargs,
        )
        self.capacity_mwh = battery_dict.get("capacity_mwh", 10.0)
        self.efficiency = battery_dict.get("efficiency", 0.90)
        self.soc_min = battery_dict.get("soc_min", 0.2)
        self.soc_max = battery_dict.get("soc_max", 0.95)

        # Battery state
        self.state = {
            "soc": 0.5,  # State of charge (fraction)
            "mode": "idle",  # idle, charging, discharging
        }

        # Bid coefficients: charge when prices are low, discharge when high
        self.bid_coefficients["C1"] = 30.0  # Baseline arbitrage incentive

    def observe_prices(self, price_signal: PriceSignal) -> None:
        """Observe price signal and update SOC estimate.

        Args:
            price_signal: Market results from most recent clearing.
        """
        super().observe_prices(price_signal)
        cleared_qty = price_signal.cleared_quantities.get(self.device_id, 0.0)
        # TODO: Update SOC based on cleared_qty and efficiency

    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Formulate battery bid for energy arbitrage.

        Bids both charging (demand) and discharging (supply) depending on SOC
        and price forecasts.

        Args:
            market_window: The market window.

        Returns:
            Bid with quantity range and arbitrage-driven value function.
        """
        # Simple heuristic: if SOC is low and price is forecast to rise, bid to charge
        # If SOC is high and price is forecast to fall, bid to discharge
        forecast_price = self.forecast_price(market_window.market_id)
        avg_recent_price = (
            np.mean(self.price_history.get(market_window.market_id, [forecast_price]))
            if self.price_history.get(market_window.market_id)
            else forecast_price
        )

        bid_type = "demand" if self.state["soc"] < 0.5 else "supply"

        return Bid(
            participant_id=self.device_id,
            market_id=market_window.market_id,
            valid_from=market_window.settlement_period_start,
            valid_to=market_window.settlement_period_end,
            quantity_min=self.quantity_min,
            quantity_max=self.quantity_max,
            value_function=self.value_function_quadratic,
            bid_type=bid_type,
            metadata={
                "device_type": self.device_type,
                "soc": self.state.get("soc"),
                "capacity_mwh": self.capacity_mwh,
            },
        )


class EVDSOTStrategy(DSOTDeviceStrategy):
    """Electric vehicle charging with arrival/departure constraints.

    Models EV charging with:
      - Arrival and departure times
      - Energy needed to reach full charge
      - Time-dependent flexibility (more flexible if not leaving soon)
      - Charging efficiency

    The device bids to charge when prices are low and before departure,
    subject to being fully charged by departure time.
    """

    def __init__(
        self,
        device_id: str,
        ev_dict: Dict,
        **kwargs,
    ):
        """Initialize EV charging strategy.

        Args:
            device_id: Unique identifier.
            ev_dict: Configuration dict with keys:
                'battery_capacity_kwh': Vehicle battery capacity (kWh)
                'charger_rating_kw': Charger power rating (kW)
                'efficiency': Charging efficiency (0-1)
                'arrival_time_sec': Time vehicle arrives (seconds from start of day)
                'departure_time_sec': Time vehicle must depart (seconds from start of day)
                'current_soc': Current state of charge (0-1)
            **kwargs: Additional arguments passed to parent.
        """
        super().__init__(
            device_id=device_id,
            device_type="EV",
            price_cap=ev_dict.get("price_cap", 50.0),
            quantity_max=ev_dict.get("charger_rating_kw", 7.0) / 1000.0,  # kW to MW
            **kwargs,
        )
        self.battery_capacity_kwh = ev_dict.get("battery_capacity_kwh", 60.0)
        self.efficiency = ev_dict.get("efficiency", 0.85)
        self.arrival_time_sec = ev_dict.get("arrival_time_sec", 0)
        self.departure_time_sec = ev_dict.get("departure_time_sec", 86400)

        self.state = {
            "soc": ev_dict.get("current_soc", 0.2),
            "is_connected": False,
        }

    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Formulate EV charging bid based on time-to-departure constraints.

        Args:
            market_window: The market window.

        Returns:
            Bid to charge (demand) with reduced quantity if time-to-departure is short.

        Raises:
            ValueError: If the vehicle has already departed.
        """
        if market_window.clearing_time > self.departure_time_sec:
            raise ValueError(
                f"EV {self.device_id} has already departed at {self.departure_time_sec}"
            )

        # Quantity to fully charge (reduced by current SOC and efficiency)
        kwh_needed = (1.0 - self.state["soc"]) * self.battery_capacity_kwh
        energy_needed_mwh = kwh_needed / 1000.0 / self.efficiency

        # Reduce max quantity if departure is soon (next few periods)
        time_to_departure = self.departure_time_sec - market_window.clearing_time
        if time_to_departure < 3600:  # Less than 1 hour
            # Require charging to complete: max_qty = energy_needed / time_to_departure (in hours)
            hours_available = max(time_to_departure / 3600.0, 0.1)
            quantity_max = min(
                self.quantity_max, max(self.quantity_min, energy_needed_mwh / hours_available)
            )
        else:
            quantity_max = min(self.quantity_max, energy_needed_mwh)

        return Bid(
            participant_id=self.device_id,
            market_id=market_window.market_id,
            valid_from=market_window.settlement_period_start,
            valid_to=market_window.settlement_period_end,
            quantity_min=self.quantity_min,
            quantity_max=quantity_max,
            value_function=self.value_function_quadratic,
            bid_type="demand",
            metadata={
                "device_type": self.device_type,
                "soc": self.state.get("soc"),
                "time_to_departure_sec": time_to_departure,
            },
        )


class WaterHeaterDSOTStrategy(DSOTDeviceStrategy):
    """Water heater thermal storage with time-shift flexibility.

    Models a residential or commercial water heater with:
      - Thermal mass (time constant)
      - Temperature setpoint with deadband
      - Time-shift flexibility (can shift heating to off-peak hours)

    Similar structure to HVAC but with different comfort metrics
    (water temperature instead of indoor air temperature).
    """

    def __init__(
        self,
        device_id: str,
        wh_dict: Dict,
        **kwargs,
    ):
        """Initialize water heater strategy.

        Args:
            device_id: Unique identifier.
            wh_dict: Configuration dict with keys:
                'capacity_liters': Tank capacity (liters)
                'power_rating_kw': Heating element power (kW)
                'setpoint_temp': Target water temperature (°C)
                'deadband': Comfortable deadband (°C)
            **kwargs: Additional arguments passed to parent.
        """
        super().__init__(
            device_id=device_id,
            device_type="WaterHeater",
            price_cap=wh_dict.get("price_cap", 80.0),
            quantity_max=wh_dict.get("power_rating_kw", 4.0) / 1000.0,  # kW to MW
            **kwargs,
        )
        self.capacity_liters = wh_dict.get("capacity_liters", 200.0)
        self.setpoint_temp = wh_dict.get("setpoint_temp", 50.0)
        self.deadband = wh_dict.get("deadband", 5.0)

        self.state = {
            "water_temp": self.setpoint_temp,
            "is_heating": False,
        }

    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Formulate water heater bid.

        Args:
            market_window: The market window.

        Returns:
            Bid to heat (demand) with quantity based on current temperature.
        """
        return Bid(
            participant_id=self.device_id,
            market_id=market_window.market_id,
            valid_from=market_window.settlement_period_start,
            valid_to=market_window.settlement_period_end,
            quantity_min=self.quantity_min,
            quantity_max=self.quantity_max,
            value_function=self.value_function_quadratic,
            bid_type="demand",
            metadata={
                "device_type": self.device_type,
                "water_temp": self.state.get("water_temp"),
                "setpoint": self.setpoint_temp,
            },
        )


class PVDSOTStrategy(DSOTDeviceStrategy):
    """Solar PV generation (passive, no active bidding).

    Models distributed solar generation. Currently a passive participant:
    the device does not bid into the market, but instead publishes its
    forecasted generation which is treated as a supply-side constraint.

    Future: Can be extended to include battery co-optimization or
    demand-side management by the host customer.
    """

    def __init__(
        self,
        device_id: str,
        pv_dict: Dict,
        **kwargs,
    ):
        """Initialize PV strategy.

        Args:
            device_id: Unique identifier.
            pv_dict: Configuration dict with keys:
                'capacity_kw': Nameplate capacity (kW)
                'forecast_generation_mwh': Expected generation this period (MWh)
            **kwargs: Additional arguments passed to parent.
        """
        super().__init__(
            device_id=device_id,
            device_type="PV",
            **kwargs,
        )
        self.capacity_kw = pv_dict.get("capacity_kw", 5.0)
        self.state = {"forecasted_generation_mwh": 0.0}

    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """PV does not actively bid; raise an error.

        Args:
            market_window: The market window.

        Raises:
            ValueError: PV is a passive generator and does not bid.
        """
        raise ValueError(
            f"PV device {self.device_id} is passive and does not formulate bids. "
            "Its generation is handled as a supply-side constraint."
        )
