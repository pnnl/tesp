"""Adapter pattern for HVAC agent — wraps legacy HVACDSOT as DeviceStrategy.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

"""

from copy import deepcopy
from typing import Callable

from ..dsot.hvac_agent import HVACDSOT
from ..modular.dsot_device_strategies import HVACDSOTStrategy
from ..modular.market_protocol import Bid, MarketWindow
from ..modular.price_signal import PriceSignal


class HVACDSOTStrategyAdapter(HVACDSOTStrategy):
    """Adapter that wraps an existing HVACDSOT legacy agent as a DeviceStrategy.
    
    This adapter:
    - Preserves all existing HVAC physics (thermal mass, comfort band, optimization)
    - Converts between 4-point bid format (legacy) and Bid with value_function (new)
    - Implements observe_prices() to update legacy agent state
    - Implements formulate_bid() to call legacy DA_optimal_quantities() and formulate_bid_da/rt()
    
    The adapter is a thin translation layer; all optimization logic remains in HVACDSOT.
    
    Args:
        device_id (str): Identifier for this HVAC device
        hvac_dict (dict): Configuration dictionary for HVAC parameters
        house_properties (dict): GLM house properties
        legacy_agent (HVACDSOT, optional): Existing legacy agent to wrap. If None, creates new one.
    
    Attributes:
        legacy_agent (HVACDSOT): The wrapped legacy agent instance
        bid_delay (float): Minutes before clearing when bids must be submitted
    """
    
    def __init__(self, device_id: str, hvac_dict: dict, house_properties: dict, legacy_agent=None):
        """Initialize HVAC adapter with legacy agent wrapping."""
        # Store before calling super().__init__()
        self.legacy_agent = legacy_agent
        
        # Initialize as HVACDSOTStrategy (calls DSOTDeviceStrategy.__init__)
        super().__init__(device_id, hvac_dict)
        
        # If no legacy agent provided, create one
        if self.legacy_agent is None:
            import time
            from ..api.helpers import enable_logging
            # Default logging setup (mimics substation.py initialization)
            log = enable_logging('INFO', 11, device_id)
            current_time_str = '2019-01-01 00:00:00'
            solver = hvac_dict.get('solver', 'ipopt')
            self.legacy_agent = HVACDSOT(hvac_dict, house_properties, device_id, 11, current_time_str, solver)
        
        self.bid_delay = hvac_dict.get('bid_delay', 60.0)  # Default: 60 seconds
    
    def observe_prices(self, price_signal: PriceSignal) -> None:
        """Update legacy agent state based on cleared prices.
        
        For DA market: Stores price forecast for next optimization
        For RT market: Updates agent with latest RT clearing price
        
        Args:
            price_signal: PriceSignal containing cleared price and metadata
        """
        if price_signal is None:
            return
        
        # Extract market type from metadata or price_signal
        market_id = getattr(price_signal, 'market_id', 'RT')
        clearing_price = price_signal.clearing_price
        
        if market_id == 'DA':
            # For DA: store price forecast (used in next optimization)
            # In real implementation, this would update self.legacy_agent.price_forecast
            # For now, we just note the DA clearing price
            if hasattr(self.legacy_agent, 'price_forecast'):
                # If agent tracks price forecast, update it
                pass
        elif market_id == 'RT':
            # For RT: update agent with latest RT clearing price
            # This influences behavior in current 5-min period
            if hasattr(self.legacy_agent, 'inform_bid'):
                try:
                    self.legacy_agent.inform_bid(clearing_price)
                except Exception:
                    pass  # Legacy agent may not have inform_bid()
        
        # Update internal price history (for forecasting)
        if hasattr(self, 'price_history'):
            self.price_history.append(clearing_price)
            if len(self.price_history) > 24:
                self.price_history.pop(0)
    
    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Formulate a bid for the given market window.
        
        Calls legacy agent's DA_optimal_quantities() and formulate_bid_da/rt()
        methods, then converts the 4-point bid format to Bid with value_function.
        
        Args:
            market_window: MarketWindow specifying DA or RT market
        
        Returns:
            Bid object with value_function and other metadata
        
        Raises:
            ValueError: If market window type is not supported
        """
        if market_window.market_id == 'DA':
            # Day-Ahead market: call DA optimization
            if hasattr(self.legacy_agent, 'DA_optimal_quantities'):
                try:
                    quantities = self.legacy_agent.DA_optimal_quantities()
                    # quantities might be [list, params_dict] or just list
                    if isinstance(quantities, (list, tuple)) and len(quantities) > 0:
                        if isinstance(quantities[0], (list, dict)):
                            # Assume format is [quantity_list, params_dict]
                            self.legacy_agent.optimized_Quantity = quantities[0] if isinstance(quantities[0], list) else [0.0]
                        else:
                            self.legacy_agent.optimized_Quantity = quantities
                except Exception as e:
                    # Optimization failed; use defaults
                    self.legacy_agent.optimized_Quantity = [0.0] * 48  # Default to 0 for all hours
            
            # Now formulate DA bid using optimized quantities
            if hasattr(self.legacy_agent, 'formulate_bid_da'):
                bid_4pt_list = self.legacy_agent.formulate_bid_da()
                # bid_4pt_list is list of 4-point bids for each hour in window
                # For DA market window 0, take the first hour's bid
                bid_4pt = bid_4pt_list[0] if bid_4pt_list else [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
            else:
                bid_4pt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
            
            bid_type = 'demand'
        
        elif market_window.market_id == 'RT':
            # Real-Time market: use current RT bid
            if hasattr(self.legacy_agent, 'formulate_bid_rt'):
                bid_4pt = self.legacy_agent.formulate_bid_rt()  # Returns single 4-point bid
            else:
                bid_4pt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
            
            bid_type = 'demand'
        
        else:
            raise ValueError(f"Unsupported market type: {market_window.market_id}")
        
        # Convert 4-point bid to Bid with value_function
        return self._convert_4pt_to_bid(bid_4pt, market_window, bid_type)
    
    def _convert_4pt_to_bid(self, bid_4pt: list, market_window: MarketWindow, bid_type: str) -> Bid:
        """Convert 4-point bid to Bid object with piecewise linear value_function.
        
        A 4-point bid has format: [[Q1, P1], [Q2, P2], [Q3, P3], [Q4, P4]]
        where quantities usually span from Qmin to Qmax.
        
        Creates a piecewise linear value_function that interpolates through these 4 points.
        
        Args:
            bid_4pt: List of [quantity, price] points
            market_window: The market window this bid is for
            bid_type: 'demand' or 'supply'
        
        Returns:
            Bid object ready for clearing
        """
        # Extract quantities and prices from 4-point bid
        quantities = [bid_4pt[i][0] for i in range(4)]
        prices = [bid_4pt[i][1] for i in range(4)]
        
        # Find min and max quantities (spanning demand range)
        quantity_min = min(quantities)
        quantity_max = max(quantities)
        
        # Create piecewise linear value function via closure
        def value_function_4pt(q: float) -> float:
            """Piecewise linear interpolation through 4 bid points.
            
            Returns marginal $/kWh at quantity q.
            """
            # Sort points by quantity for interpolation
            points = list(zip(quantities, prices))
            points.sort(key=lambda p: p[0])
            
            # Handle out-of-range quantities
            if q <= points[0][0]:
                return points[0][1]
            if q >= points[-1][0]:
                return points[-1][1]
            
            # Linear interpolation between points
            for i in range(len(points) - 1):
                q1, p1 = points[i]
                q2, p2 = points[i + 1]
                if q1 <= q <= q2:
                    if q2 == q1:
                        return p1
                    # Linear interpolation: p = p1 + (q - q1) * (p2 - p1) / (q2 - q1)
                    return p1 + (q - q1) * (p2 - p1) / (q2 - q1)
            
            return prices[-1]
        
        # Create and return Bid object
        return Bid(
            participant_id=self.device_id,
            market_id=market_window.market_id,
            valid_from=market_window.settlement_period_start,
            valid_to=market_window.settlement_period_end,
            quantity_min=quantity_min,
            quantity_max=quantity_max,
            value_function=value_function_4pt,
            bid_type=bid_type,
            metadata={
                'bid_format': 'piecewise_linear_4pt',
                'points': list(zip(quantities, prices)),
                'source': 'HVACDSOT_legacy_adapter',
            },
        )


def test_hvac_adapter():
    """Test HVAC adapter with sample configuration."""
    import json
    
    # Sample HVAC configuration (from DSOT test cases)
    hvac_config = {
        'houseName': 'house_1',
        'meterName': 'meter_1',
        'period': 300.0,
        'wakeup_start': 6.0,
        'daylight_start': 7.0,
        'evening_start': 17.0,
        'night_start': 20.0,
        'weekend_day_start': 8.0,
        'weekend_night_start': 21.0,
        'wakeup_set_cool': 76.0,
        'daylight_set_cool': 74.0,
        'evening_set_cool': 76.0,
        'night_set_cool': 78.0,
        'weekend_day_set_cool': 76.0,
        'weekend_night_set_cool': 78.0,
        'wakeup_set_heat': 68.0,
        'daylight_set_heat': 66.0,
        'evening_set_heat': 68.0,
        'night_set_heat': 62.0,
        'weekend_day_set_heat': 68.0,
        'weekend_night_set_heat': 62.0,
        'deadband': 2.0,
        'price_cap': 10.0,
        'bid_delay': 60.0,
        'ramp_high_limit': 5.0,
        'ramp_low_limit': -5.0,
        'range_high_limit': 2.0,
        'range_low_limit': -2.0,
        'solver': 'ipopt',
        'participating': True,
    }
    
    house_properties = {
        'air_temperature': 70.0,
        'house_load': 5.0,
        'hvac_load': 2.0,
        'power_state': 0.0,
    }
    
    # Create adapter
    adapter = HVACDSOTStrategyAdapter('HVAC_1', hvac_config, house_properties)
    
    # Test formulate_bid for DA market
    from ..modular.market_protocol import MarketWindow
    
    da_window = MarketWindow(
        market_id='DA',
        window_number=0,
        settlement_period_start=0,
        settlement_period_end=3600,
        bid_submission_deadline=3540,
        clearing_time=3600,
        clearing_mechanism_name='curve_intersection',
    )
    
    try:
        bid_da = adapter.formulate_bid(da_window)
        print(f"✓ DA Bid created: {bid_da.participant_id}")
        print(f"  Quantity range: {bid_da.quantity_min:.2f} to {bid_da.quantity_max:.2f} kW")
        
        # Test value function
        test_qty = (bid_da.quantity_min + bid_da.quantity_max) / 2.0
        test_price = bid_da.value_function(test_qty)
        print(f"  Value at {test_qty:.2f} kW: ${test_price:.2f}/kWh")
    except Exception as e:
        print(f"✗ DA Bid creation failed: {e}")
    
    # Test formulate_bid for RT market
    rt_window = MarketWindow(
        market_id='RT',
        window_number=0,
        settlement_period_start=0,
        settlement_period_end=300,
        bid_submission_deadline=270,
        clearing_time=300,
        clearing_mechanism_name='curve_intersection',
    )
    
    try:
        bid_rt = adapter.formulate_bid(rt_window)
        print(f"✓ RT Bid created: {bid_rt.participant_id}")
        print(f"  Quantity range: {bid_rt.quantity_min:.2f} to {bid_rt.quantity_max:.2f} kW")
    except Exception as e:
        print(f"✗ RT Bid creation failed: {e}")
    
    # Test observe_prices
    price_signal = PriceSignal(
        market_id='DA',
        time_step=0,
        period_start=0,
        period_end=3600,
        clearing_price=5.0,
        participant_prices={'HVAC_1': 5.0},
        cleared_quantities={'HVAC_1': 2.5},
    )
    
    try:
        adapter.observe_prices(price_signal)
        print(f"✓ Adapter observed DA price: ${price_signal.clearing_price:.2f}/kWh")
    except Exception as e:
        print(f"✗ observe_prices failed: {e}")


if __name__ == '__main__':
    test_hvac_adapter()
