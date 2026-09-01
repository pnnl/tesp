"""Adapter pattern for PV agent — wraps legacy PVDSOT as DeviceStrategy.

**Note, the `modular` architecture was written by an AI-assistant trained on the TESP codebase, and asked to envision a more modular, customizable version of DSOT-like simulations.**

"""

from ..dsot.pv_agent import PVDSOT
from ..modular.dsot_device_strategies import PVDSOTStrategy
from ..modular.market_protocol import Bid, MarketWindow
from ..modular.price_signal import PriceSignal


class PVDSOTStrategyAdapter(PVDSOTStrategy):
    """Adapter that wraps an existing PVDSOT legacy agent as a DeviceStrategy.
    
    Special characteristics:
    - PV is a PASSIVE supply device: it doesn't respond to prices
    - Supply is determined by solar irradiance (weather-based)
    - Does not formulate market bids (always supplies available power)
    - May observe prices for informational/reporting purposes only
    
    This adapter:
    - Preserves all existing PV logic (power calculation, forecasting)
    - Returns a special "passive supply" Bid indicating no price response
    - Implements observe_prices() but typically has no effect
    
    Args:
        device_id (str): Identifier for this PV device
        pv_dict (dict): Configuration dictionary for PV parameters
        inverter_properties (dict): GridLAB-D inverter properties
        legacy_agent (PVDSOT, optional): Existing legacy agent to wrap.
    
    Attributes:
        legacy_agent (PVDSOT): The wrapped legacy agent instance
        available_power_kw (float): Current available solar power (kW)
    """
    
    def __init__(self, device_id: str, pv_dict: dict, inverter_properties: dict, legacy_agent=None):
        """Initialize PV adapter with legacy agent wrapping."""
        self.legacy_agent = legacy_agent
        self.available_power_kw = 0.0
        
        # Initialize as PVDSOTStrategy
        super().__init__(device_id, pv_dict)
        
        # If no legacy agent provided, create one
        if self.legacy_agent is None:
            from ..api.helpers import enable_logging
            log = enable_logging('INFO', 11, device_id)
            current_time_str = '2019-01-01 00:00:00'
            solver = pv_dict.get('solver', 'ipopt')
            
            self.legacy_agent = PVDSOT(pv_dict, inverter_properties, device_id, 11, current_time_str, solver)
    
    def observe_prices(self, price_signal: PriceSignal) -> None:
        """Update PV state based on price signal.
        
        For PV, this is informational only. Prices do not affect solar supply.
        Used for reporting/logging purposes.
        
        Args:
            price_signal: PriceSignal containing cleared price (for logging)
        """
        if price_signal is None:
            return
        
        # PV doesn't respond to prices, but we can log for analysis
        # In a real implementation, this might trigger data logging for metrics
        if hasattr(self, 'price_history'):
            self.price_history.append(price_signal.clearing_price)
            if len(self.price_history) > 24:
                self.price_history.pop(0)
    
    def formulate_bid(self, market_window: MarketWindow) -> Bid:
        """Formulate a passive supply bid for the given market window.
        
        PV doesn't actively bid. Instead, it declares its available supply
        and offers to supply at zero or very low price (passive supply).
        
        Args:
            market_window: MarketWindow specifying DA or RT market
        
        Returns:
            Bid object indicating passive supply (zero price offer)
        
        Raises:
            ValueError: If market window type is not supported
        """
        if market_window.market_id not in ['DA', 'RT']:
            raise ValueError(f"Unsupported market type: {market_window.market_id}")
        
        # Get available power from legacy agent if available
        available_power = 0.0
        if hasattr(self.legacy_agent, 'get_power_output'):
            try:
                available_power = self.legacy_agent.get_power_output()
                self.available_power_kw = available_power
            except Exception:
                pass
        
        # PV provides passive supply: quantity = available power, price = 0 (willing to supply at any price)
        # Create a constant zero-price value function
        def value_function_passive_pv(q: float) -> float:
            """PV always offers at zero (or very low) price - passive supply."""
            return 0.001  # Negligible price (technically 0 but use small value for numerical stability)
        
        return Bid(
            participant_id=self.device_id,
            market_id=market_window.market_id,
            valid_from=market_window.settlement_period_start,
            valid_to=market_window.settlement_period_end,
            quantity_min=0.0,
            quantity_max=available_power,  # Maximum: available solar power
            value_function=value_function_passive_pv,
            bid_type='supply',
            metadata={
                'bid_format': 'passive_supply',
                'available_power_kw': available_power,
                'source': 'PVDSOT_legacy_adapter',
                'note': 'PV is passive supply; quantity=available power, price=0 (always willing to supply)',
            },
        )


if __name__ == '__main__':
    print("PV Adapter module loaded")
