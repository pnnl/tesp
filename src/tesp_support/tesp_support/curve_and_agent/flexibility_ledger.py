# ============================================================================
# FILE: flexibility_ledger.py
# PURPOSE: Capacity commitment tracking and availability queries 
#          (Agent Function F6).
#          Provides three-tier availability: hard, expected, economic.
# ============================================================================

from typing import Dict, List, Optional, Tuple
from data_types import EconomicCommitment, FlexibilityEnvelope
from enums_and_constants import CommitmentStatus, MarketType, ProductType


class DisplaceableBlock:
    """A block of capacity that could be freed by displacing an existing
    commitment, along with the cost of doing so.
    
    Attributes:
        source_market: Market ID of the commitment that could be displaced.
        source_status: Current status of that commitment.
        quantity: How much capacity could be freed (kW).
        displacement_cost: Net cost of displacing ($/kW).
            = marginal_penalty - marginal_net_value of the displaced commitment.
        net_gain: Expected net gain from displacement ($/kW).
            = candidate_value - displacement_cost.
    """

    def __init__(
        self,
        source_market: str,
        source_status: CommitmentStatus,
        quantity: float,
        displacement_cost: float,
        net_gain: float
    ):
        self.source_market = source_market
        self.source_status = source_status
        self.quantity = quantity
        self.displacement_cost = displacement_cost
        self.net_gain = net_gain


class EconomicEnvelope:
    """Extended flexibility envelope including displaceable capacity.
    
    Attributes:
        hard_Q_min_avail: Hard minimum (all commitments deducted).
        hard_Q_max_avail: Hard maximum (all commitments deducted).
        displaceable_blocks: Sorted list of capacity that could be freed.
        total_displaceable: Sum of all displaceable kW.
        soft_Q_max_avail: hard_Q_max + total_displaceable.
    """

    def __init__(
        self,
        hard_Q_min_avail: float,
        hard_Q_max_avail: float,
        displaceable_blocks: Optional[List[DisplaceableBlock]] = None,
        total_displaceable: float = 0.0,
        soft_Q_max_avail: float = 0.0
    ):
        self.hard_Q_min_avail = hard_Q_min_avail
        self.hard_Q_max_avail = hard_Q_max_avail
        self.displaceable_blocks = displaceable_blocks or []
        self.total_displaceable = total_displaceable
        self.soft_Q_max_avail = soft_Q_max_avail


class FlexibilityLedger:
    """Tracks capacity commitments across all markets and provides
    three-tier availability queries.
    
    This is the single source of truth for "how much of the device's
    operating range is currently spoken for."
    
    The three tiers:
    1. HARD: Physical capacity minus ALL commitments (tentative, 
       advisory, and firm). Guarantees zero conflict.
    2. EXPECTED: Deducts firm fully, advisory weighted by confidence,
       tentative at a baseline probability. Realistic planning estimate.
    3. ECONOMIC: Capacity that could be freed by displacing lower-value
       commitments, net of penalty costs.
    
    Args:
        Q_min_device: Physical minimum power (kW). For batteries, negative.
        Q_max_device: Physical maximum power (kW).
    """

    def __init__(self, Q_min_device: float, Q_max_device: float):
        self._Q_min = Q_min_device
        self._Q_max = Q_max_device
        self._commitments: List[EconomicCommitment] = []
        self._tentative_weight: float = 0.4

    def hold_tentative(
        self,
        market_id: str,
        market_type: MarketType,
        product_type: ProductType,
        quantity: float,
        interval: Tuple[float, float],
        cleared_price: float = 0.0,
        penalty_model_id: str = ""
    ) -> None:
        """Record a tentative commitment when a bid is submitted.
        
        Replaces any existing tentative/advisory for the same market_id.
        
        Args:
            market_id: ID of the market.
            market_type: Type of market product.
            product_type: Energy, reg up/down, reserve up/down.
            quantity: Bid quantity (kW).
            interval: (start_time, end_time) of delivery.
            cleared_price: Expected price (for economic calculations).
            penalty_model_id: Reference to applicable penalty model.
        """
        self._commitments = [
            c for c in self._commitments if c.market_id != market_id]
        self._commitments.append(EconomicCommitment(
            market_id=market_id,
            market_type=market_type,
            product_type=product_type,
            quantity=quantity,
            interval=interval,
            status=CommitmentStatus.TENTATIVE,
            cleared_price=cleared_price,
            penalty_model_id=penalty_model_id,
        ))

    def update_advisory(
        self,
        market_id: str,
        quantity: float,
        interval: Tuple[float, float],
        confidence: float,
        cleared_price: float,
        penalty_model_id: str,
        iteration: int,
        marginal_nv: float = 0.0,
        marginal_pen: float = 0.0
    ) -> None:
        """Create or update an advisory commitment after informational clear.
        
        Replaces any existing tentative/advisory for the same market_id.
        
        Args:
            market_id: ID of the market.
            quantity: Projected operating point (kW).
            interval: Delivery interval.
            confidence: Convergence confidence (0–1).
                INTERNAL: From convergence tracker computation.
            cleared_price: Informational clearing price.
                INTERNAL: From MO clearing result.
            penalty_model_id: Penalty model reference.
            iteration: Iteration number.
            marginal_nv: Marginal net value ($/kW).
            marginal_pen: Marginal penalty ($/kW).
        """
        self._commitments = [
            c for c in self._commitments if c.market_id != market_id]
        self._commitments.append(EconomicCommitment(
            market_id=market_id,
            quantity=quantity,
            interval=interval,
            status=CommitmentStatus.ADVISORY,
            confidence=confidence,
            cleared_price=cleared_price,
            penalty_model_id=penalty_model_id,
            iteration=iteration,
            marginal_nv=marginal_nv,
            marginal_pen=marginal_pen,
        ))

    def book_firm(
        self,
        market_id: str,
        quantity: float,
        interval: Tuple[float, float],
        cleared_price: float,
        penalty_model_id: str,
        marginal_nv: float = 0.0,
        marginal_pen: float = 0.0
    ) -> None:
        """Convert a commitment to firm status after binding clear.
        
        Args:
            market_id: ID of the market.
            quantity: Cleared quantity (kW).
            interval: Delivery interval.
            cleared_price: Binding clearing price.
                INTERNAL: From MO binding clearing result.
            penalty_model_id: Penalty model reference.
            marginal_nv: Marginal net value at cleared price.
            marginal_pen: Marginal penalty rate.
        """
        self._commitments = [
            c for c in self._commitments if c.market_id != market_id]
        self._commitments.append(EconomicCommitment(
            market_id=market_id,
            quantity=quantity,
            interval=interval,
            status=CommitmentStatus.FIRM,
            cleared_price=cleared_price,
            penalty_model_id=penalty_model_id,
            marginal_nv=marginal_nv,
            marginal_pen=marginal_pen,
        ))

    def release(self, market_id: str) -> None:
        """Release a commitment after reconciliation.
        
        Args:
            market_id: ID of the market to release.
        """
        self._commitments = [
            c for c in self._commitments if c.market_id != market_id]

    def hard_available(
        self,
        time_interval: Tuple[float, float],
        excluding: Optional[str] = None
    ) -> Tuple[float, float]:
        """TIER 1: Hard availability. Deducts ALL commitments.
        
        Args:
            time_interval: (start, end) of the query interval.
            excluding: Market ID to exclude from the calculation.
                Used when re-bidding for the same market.
        
        Returns:
            (Q_min_avail, Q_max_avail) in kW.
        """
        committed = 0.0
        for c in self._overlapping(time_interval, excluding):
            committed += c.quantity
        return (self._Q_min, self._Q_max - committed)

    def expected_available(
        self,
        time_interval: Tuple[float, float],
        excluding: Optional[str] = None
    ) -> Tuple[float, float]:
        """TIER 2: Expected availability. Weights advisory by confidence.
        
        Args:
            time_interval: Query interval.
            excluding: Market ID to exclude.
        
        Returns:
            (Q_min_avail, Q_max_avail) in kW.
        """
        weighted = 0.0
        for c in self._overlapping(time_interval, excluding):
            if c.status == CommitmentStatus.FIRM:
                weighted += c.quantity
            elif c.status == CommitmentStatus.ADVISORY:
                weighted += c.quantity * c.confidence
            elif c.status == CommitmentStatus.TENTATIVE:
                weighted += c.quantity * self._tentative_weight
        return (self._Q_min, self._Q_max - weighted)

    def economic_available(
        self,
        time_interval: Tuple[float, float],
        candidate_value: float,
        candidate_penalty: float,
        excluding: Optional[str] = None
    ) -> EconomicEnvelope:
        """TIER 3: Economic availability including displaceable capacity.
        
        Args:
            time_interval: Query interval.
            candidate_value: Marginal value of the proposed new use ($/kW).
            candidate_penalty: Marginal penalty of the proposed new use.
            excluding: Market ID to exclude.
        
        Returns:
            EconomicEnvelope with hard availability plus displacement options.
        """
        _, hard_max = self.hard_available(time_interval, excluding)
        hard_min = self._Q_min

        blocks = []
        for c in self._overlapping(time_interval, excluding):
            if c.status in (CommitmentStatus.ADVISORY, CommitmentStatus.TENTATIVE):
                disp_cost = c.marginal_pen - c.marginal_nv
                net_gain = candidate_value - disp_cost
                if net_gain > 0:
                    blocks.append(DisplaceableBlock(
                        source_market=c.market_id,
                        source_status=c.status,
                        quantity=c.quantity,
                        displacement_cost=disp_cost,
                        net_gain=net_gain,
                    ))
        blocks.sort(key=lambda b: b.displacement_cost)
        total_disp = sum(b.quantity for b in blocks)

        return EconomicEnvelope(
            hard_Q_min_avail=hard_min,
            hard_Q_max_avail=hard_max,
            displaceable_blocks=blocks,
            total_displaceable=total_disp,
            soft_Q_max_avail=hard_max + total_disp,
        )

    def get_commitments_overlapping(
        self,
        time_interval: Tuple[float, float]
    ) -> List[EconomicCommitment]:
        """Get all commitments that overlap a time interval.
        
        Args:
            time_interval: (start, end) to check.
        
        Returns:
            List of overlapping EconomicCommitment records.
        """
        return self._overlapping(time_interval)

    def _overlapping(
        self,
        time_interval: Tuple[float, float],
        excluding: Optional[str] = None
    ) -> List[EconomicCommitment]:
        """Internal: commitments overlapping interval, optionally excluding one."""
        t_start, t_end = time_interval
        result = []
        for c in self._commitments:
            if excluding and c.market_id == excluding:
                continue
            c_start, c_end = c.interval
            if c_start < t_end and c_end > t_start:
                result.append(c)
        return result