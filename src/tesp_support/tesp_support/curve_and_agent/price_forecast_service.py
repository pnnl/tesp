# ============================================================================
# FILE: price_forecast_service.py
# PURPOSE: Maintains and distributes evolving price estimates from
#          informational market clears and external sources.
# ============================================================================

from typing import Dict, List, Optional, Tuple
from data_types import ContinuousDataPoint
from enums_and_constants import MarketType


class PriceForecast:
    """Price forecast for a specific market type and time interval.
    
    Attributes:
        market_type: Which market's price this forecasts.
        interval: (start, end) of the interval.
        price_estimate: Current best estimate ($/kWh or $/kW).
        confidence: How confident the estimate is (0–1).
        source: Where the estimate came from.
        iteration: Which informational iteration produced it.
        history: List of (iteration, price) showing convergence.
    """

    def __init__(
        self,
        market_type: MarketType,
        interval: Tuple[float, float],
        price_estimate: float = 0.0,
        confidence: float = 0.0,
        source: str = "prior",
        iteration: int = 0
    ):
        self.market_type = market_type
        self.interval = interval
        self.price_estimate = price_estimate
        self.confidence = confidence
        self.source = source
        self.iteration = iteration
        self.history: List[Tuple[int, float]] = []


class PriceForecastService:
    """Central service for maintaining price forecasts across all markets.
    
    Updated by informational market clears and external forecast sources.
    Consumed by bid formulation, risk assessment, preference curve 
    calibration, and the planning optimizer.
    """

    def __init__(self):
        self._forecasts: Dict[Tuple[MarketType, Tuple[float, float]], 
                              PriceForecast] = {}

    def update(
        self,
        market_type: MarketType,
        interval: Tuple[float, float],
        price: float,
        confidence: float,
        source: str,
        iteration: int = 0
    ) -> None:
        """Update the price forecast for a market-interval combination.
        
        Called after each informational clear, or when an external
        price forecast is received.
        
        Args:
            market_type: Which market.
            interval: Time interval this price applies to.
            price: Price estimate ($/kWh).
                INTERNAL: From ClearingResult.cleared_price after
                    informational iteration.
                OR EXTERNAL: From wholesale market data, MO forecast.
            confidence: Confidence in this estimate (0–1).
                INTERNAL: From convergence tracker.
            source: Where this came from ('informational_clear', 
                'external', 'historical').
            iteration: Iteration number (for informational clears).
        """
        key = (market_type, interval)
        if key in self._forecasts:
            fc = self._forecasts[key]
            fc.history.append((iteration, price))
            fc.price_estimate = price
            fc.confidence = confidence
            fc.source = source
            fc.iteration = iteration
        else:
            fc = PriceForecast(
                market_type=market_type,
                interval=interval,
                price_estimate=price,
                confidence=confidence,
                source=source,
                iteration=iteration,
            )
            fc.history.append((iteration, price))
            self._forecasts[key] = fc

    def get_forecast(
        self,
        market_type: MarketType,
        interval: Tuple[float, float]
    ) -> Optional[PriceForecast]:
        """Get the price forecast for a specific market and interval.
        
        Args:
            market_type: Which market.
            interval: Time interval.
        
        Returns:
            PriceForecast or None if no forecast exists.
        """
        return self._forecasts.get((market_type, interval))

    def get_price(
        self,
        market_type: MarketType,
        interval: Tuple[float, float],
        default: float = 0.0
    ) -> float:
        """Convenience: get the point estimate price.
        
        Args:
            market_type: Which market.
            interval: Time interval.
            default: Value to return if no forecast exists.
        
        Returns:
            Price estimate or default.
        """
        fc = self.get_forecast(market_type, interval)
        if fc is not None:
            return fc.price_estimate
        return default

    def get_trajectory(
        self,
        market_type: MarketType,
        t_start: float,
        t_end: float,
        resolution: float = 3600.0
    ) -> List[Tuple[Tuple[float, float], float]]:
        """Get a price trajectory over a planning horizon.
        
        Used by the planning optimizer to optimize battery schedules
        and pre-conditioning strategies.
        
        Args:
            market_type: Which market.
            t_start: Start of horizon.
            t_end: End of horizon.
            resolution: Interval length (seconds).
        
        Returns:
            List of (interval, price_estimate) tuples.
        """
        result = []
        t = t_start
        while t < t_end:
            interval = (t, t + resolution)
            fc = self.get_forecast(market_type, interval)
            if fc is not None:
                result.append((interval, fc.price_estimate))
            t += resolution
        return result