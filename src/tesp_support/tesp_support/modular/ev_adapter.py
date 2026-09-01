"""Adapter pattern for EV agent — wraps legacy EVDSOT as DeviceStrategy.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

"""

from typing import Callable

from ..dsot.ev_agent import EVDSOT
from ..modular.dsot_device_strategies import EVDSOTStrategy
from ..modular.market_protocol import Bid, MarketWindow
from ..modular.price_signal import PriceSignal


class EVDSOTStrategyAdapter(EVDSOTStrategy):
    """Adapter that wraps an existing EVDSOT legacy agent as a DeviceStrategy.
    
    This adapter:
    - Preserves all existing EV logic (battery chemistry, time-to-departure, SOC tracking)
    - Converts between 4-point bid format (legacy) and Bid with value_function (new)
    - Implements observe_prices() to update legacy agent state
    - Implements formulate_bid() to call legacy formulate_bid_da/rt()
    
    Special handling for EV time-to-departure: raises ValueError if vehicle has departed.
    
    Args:
        device_id (str): Identifier for this EV device
        ev_dict (dict): Configuration dictionary for EV parameters
        ev_properties (dict): GridLAB-D EV properties
        legacy_agent (EVDSOT, optional): Existing legacy agent to wrap. If None, creates new one.
    
    Attributes:
        legacy_agent (EVDSOT): The wrapped legacy agent instance
        time_to_departure (float): Hours until vehicle must depart (updated from legacy agent)
    """
    
    def __init__(self, device_id: str, ev_dict: dict, ev_properties: dict, legacy_agent=None):
        """Initialize EV adapter with legacy agent wrapping."""
        self.legacy_agent = legacy_agent
        
        # Initialize as EVDSOTStrategy
        super().__init__(device_id, ev_dict)
        
        # If no legacy agent provided, create one
        if self.legacy_agent is None:
            from ..api.helpers import enable_logging
            log = enable_logging('INFO', 11, device_id)
            current_time_str = '2019-01-01 00:00:00'
            solver = ev_dict.get('solver', 'ipopt')
            
            # EVDSOT expects (ev_dict, house_properties, key, ...)
            # house_properties contains houseName, which should be in ev_dict
            self.legacy_agent = EVDSOT(ev_dict, ev_properties, device_id, 11, current_time_str, solver)
        
        self.time_to_departure = ev_dict.get('time_to_departure', 8.0)  # Default: 8 hours
    
    def observe_prices(self, price_signal: PriceSignal) -> None:
        """Update legacy agent state based on cleared prices.
        
        For DA market: Stores price forecast for next optimization
        For RT market: Updates agent with latest RT clearing price and SOC
        
        Args:
            price_signal: PriceSignal containing cleared price and metadata
        """
        if price_signal is None:
            return
        
        market_id = getattr(price_signal, 'market_id', 'RT')
        clearing_price = price_signal.clearing_price
        
        if market_id == 'DA':
            # For DA: store price forecast (used in next optimization)
            if hasattr(self.legacy_agent, 'set_price_forecast'):
                try:
                    # DA typically has 48-hour forecast
                    forecast = [clearing_price] * 48
                    self.legacy_agent.set_price_forecast(forecast)
                except Exception:
                    pass
        elif market_id == 'RT':
            # For RT: update agent with latest RT clearing price
            if hasattr(self.legacy_agent, 'inform_bid'):
                try:
                    self.legacy_agent.inform_bid(clearing_price)
                except Exception:
                    pass
        
        # Update internal price history
        if hasattr(self, 'price_history'):
            self.price_history.append(clearing_price)
            if len(self.price_history) > 24:
                self.price_history.pop(0)
    
    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Formulate a bid for the given market window.
        
        Calls legacy agent's DA_optimal_quantities() and formulate_bid_da/rt()
        methods, then converts the 4-point bid format to Bid with value_function.
        
        Special handling: Raises ValueError if time_to_departure is exceeded.
        
        Args:
            market_window: MarketWindow specifying DA or RT market
        
        Returns:
            Bid object with value_function and other metadata
        
        Raises:
            ValueError: If vehicle has departed or market window type is not supported
        """
        # Check if vehicle has departed
        if self.time_to_departure <= 0:
            raise ValueError(f"EV {self.device_id} has departed; cannot formulate bid")
        
        if market_window.market_id == 'DA':
            # Day-Ahead market: call DA optimization
            if hasattr(self.legacy_agent, 'DA_optimal_quantities'):
                try:
                    quantities = self.legacy_agent.DA_optimal_quantities()
                    if isinstance(quantities, (list, tuple)) and len(quantities) > 0:
                        if isinstance(quantities[0], (list, dict)):
                            self.legacy_agent.optimized_Quantity = quantities[0] if isinstance(quantities[0], list) else [0.0]
                        else:
                            self.legacy_agent.optimized_Quantity = quantities
                except Exception:
                    self.legacy_agent.optimized_Quantity = [0.0] * 48
            
            # Formulate DA bid
            if hasattr(self.legacy_agent, 'formulate_bid_da'):
                bid_4pt_list = self.legacy_agent.formulate_bid_da()
                bid_4pt = bid_4pt_list[0] if bid_4pt_list else [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
            else:
                bid_4pt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
            
            bid_type = 'demand'
        
        elif market_window.market_id == 'RT':
            # Real-Time market
            if hasattr(self.legacy_agent, 'formulate_bid_rt'):
                bid_4pt = self.legacy_agent.formulate_bid_rt()
            else:
                bid_4pt = [[0., 0.], [0., 0.], [0., 0.], [0., 0.]]
            
            bid_type = 'demand'
        
        else:
            raise ValueError(f"Unsupported market type: {market_window.market_id}")
        
        # Convert 4-point bid to Bid with value_function
        return self._convert_4pt_to_bid(bid_4pt, market_window, bid_type)
    
    def _convert_4pt_to_bid(self, bid_4pt: list, market_window: MarketWindow, bid_type: str) -> Bid:
        """Convert 4-point bid to Bid object with piecewise linear value_function."""
        quantities = [bid_4pt[i][0] for i in range(4)]
        prices = [bid_4pt[i][1] for i in range(4)]
        
        quantity_min = min(quantities)
        quantity_max = max(quantities)
        
        def value_function_4pt(q: float) -> float:
            """Piecewise linear interpolation through 4 bid points."""
            points = list(zip(quantities, prices))
            points.sort(key=lambda p: p[0])
            
            if q <= points[0][0]:
                return points[0][1]
            if q >= points[-1][0]:
                return points[-1][1]
            
            for i in range(len(points) - 1):
                q1, p1 = points[i]
                q2, p2 = points[i + 1]
                if q1 <= q <= q2:
                    if q2 == q1:
                        return p1
                    return p1 + (q - q1) * (p2 - p1) / (q2 - q1)
            
            return prices[-1]
        
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
                'source': 'EVDSOT_legacy_adapter',
                'time_to_departure': self.time_to_departure,
            },
        )


if __name__ == '__main__':
    print("EV Adapter module loaded")
